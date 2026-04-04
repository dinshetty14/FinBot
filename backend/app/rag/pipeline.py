"""
FinBot RAG Pipeline
Full pipeline: input guardrails → semantic routing → RBAC retrieval → LLM generation → output guardrails.
"""

import logging
import os
import ssl
import uuid
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchValue
from sentence_transformers import SentenceTransformer

from app.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    QDRANT_URL,
    QDRANT_COLLECTION,
    QDRANT_PATH,
    EMBEDDING_MODEL,
    SYSTEM_PROMPT,
    RATE_LIMIT_PER_SESSION,
)
from app.models import ChatRequest, ChatResponse, SourceCitation, GuardrailInfo
from app.rbac import build_rbac_filter, get_accessible_collections
from app.routing.semantic_router import classify_query
from app.guardrails.input_guards import run_input_guards
from app.guardrails.output_guards import run_output_guards

# SSL Bypass for local environments experiencing certificate verification issues
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['PYTHONHTTPSVERIFY'] = '0'
if not os.environ.get('PYTHONHTTPSVERIFY', '') == '0':
    ssl._create_default_https_context = ssl._create_unverified_context

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton components (lazy initialization)
# ---------------------------------------------------------------------------
_llm: Optional[ChatGroq] = None
_embed_model: Optional[SentenceTransformer] = None
_qdrant_client: Optional[QdrantClient] = None


def _get_llm() -> ChatGroq:
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            model=GROQ_MODEL,
            api_key=GROQ_API_KEY,
            temperature=0.3,
            max_tokens=1024,
        )
    return _llm


def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)
    return _embed_model


def _get_qdrant() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        if QDRANT_URL.lower() == "local":
            _qdrant_client = QdrantClient(path=QDRANT_PATH)
        else:
            _qdrant_client = QdrantClient(url=QDRANT_URL)
    return _qdrant_client


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve_chunks(
    query: str,
    user_role: str,
    target_collection: Optional[str] = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Retrieve relevant chunks from Qdrant with RBAC filtering.

    The RBAC filter is applied at the Qdrant query level, ensuring
    restricted chunks are NEVER surfaced to the LLM context.
    """
    embed_model = _get_embed_model()
    client = _get_qdrant()

    # Encode query
    query_vector = embed_model.encode(query).tolist()

    # Build RBAC filter
    rbac_filter = build_rbac_filter(user_role)

    # If routing identified a specific collection, add collection filter
    if target_collection:
        filter_conditions = rbac_filter.must.copy() if rbac_filter.must else []
        filter_conditions.append(
            FieldCondition(
                key="collection",
                match=MatchValue(value=target_collection),
            )
        )
        combined_filter = Filter(must=filter_conditions)
    else:
        combined_filter = rbac_filter

    # Search Qdrant
    try:
        if hasattr(client, "query_points"):
            results = client.query_points(
                collection_name=QDRANT_COLLECTION,
                query=query_vector,
                query_filter=combined_filter,
                limit=top_k,
            ).points
        else:
            results = client.search(
                collection_name=QDRANT_COLLECTION,
                query_vector=query_vector,
                query_filter=combined_filter,
                limit=top_k,
            )
    except Exception as e:
        logger.error(f"Qdrant search failed: {e}")
        return []

    # Extract chunks
    chunks = []
    for result in results:
        payload = result.payload or {}
        chunks.append({
            "text": payload.get("text", ""),
            "source_document": payload.get("source_document", "unknown"),
            "page_number": payload.get("page_number"),
            "section_title": payload.get("section_title", ""),
            "collection": payload.get("collection", ""),
            "chunk_type": payload.get("chunk_type", "text"),
            "score": result.score,
        })

    logger.info(f"Retrieved {len(chunks)} chunks for query (role={user_role})")
    return chunks


# ---------------------------------------------------------------------------
# LLM Generation
# ---------------------------------------------------------------------------

def generate_response(
    query: str,
    chunks: list[dict],
    user_role: str,
    accessible_collections: list[str],
) -> str:
    """Generate a response using the LLM with retrieved context."""
    llm = _get_llm()

    # Build context from chunks
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source_document", "unknown")
        page = chunk.get("page_number", "N/A")
        section = chunk.get("section_title", "")
        text = chunk.get("text", "")
        context_parts.append(
            f"[Source {i}: {source}, Page: {page}, Section: {section}]\n{text}"
        )

    context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documents found."

    # Format system prompt
    system = SYSTEM_PROMPT.format(
        context=context,
        user_role=user_role,
        accessible_collections=", ".join(accessible_collections),
    )

    messages = [
        SystemMessage(content=system),
        HumanMessage(content=query),
    ]

    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return f"I apologize, but I encountered an error while generating a response. Please try again. (Error: {str(e)})"


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------

def process_query(
    request: ChatRequest,
    user_role: str,
    accessible_collections: list[str],
) -> ChatResponse:
    """
    Execute the full RAG pipeline:
    1. Input guardrails
    2. Semantic routing
    3. Route-role intersection (RBAC)
    4. Qdrant retrieval with RBAC filter
    5. LLM generation
    6. Output guardrails
    """
    session_id = request.session_id or str(uuid.uuid4())
    query = request.message

    logger.info(f"Processing query: role={user_role}, session={session_id}")

    # ---- Step 1: Input guardrails ----
    input_result = run_input_guards(query, session_id, RATE_LIMIT_PER_SESSION)
    if input_result and input_result.get("blocked"):
        return ChatResponse(
            answer=input_result["reason"],
            guardrail=GuardrailInfo(
                triggered=True,
                type="input",
                reason=input_result["guardrail_type"],
            ),
            user_role=user_role,
            accessible_collections=accessible_collections,
            blocked=True,
        )

    # ---- Step 2: Semantic routing ----
    route_result = classify_query(query, user_role)
    route_name = route_result.get("route_name")

    # Check if routing triggered a guardrail
    if not route_result.get("allowed"):
        guardrail_type = route_result.get("guardrail_type", "routing")
        return ChatResponse(
            answer=route_result.get("message", "Your query has been blocked."),
            route=route_name,
            guardrail=GuardrailInfo(
                triggered=True,
                type="input" if guardrail_type in ("off_topic", "prompt_injection") else "rbac",
                reason=guardrail_type,
            ),
            user_role=user_role,
            accessible_collections=accessible_collections,
            blocked=True,
        )

    target_collection = route_result.get("collection")

    # ---- Step 3 & 4: Retrieval with RBAC filter ----
    chunks = retrieve_chunks(query, user_role, target_collection)

    if not chunks:
        return ChatResponse(
            answer="I couldn't find any relevant documents within your authorized scope. Please try rephrasing your question or contact your administrator.",
            route=route_name,
            user_role=user_role,
            accessible_collections=accessible_collections,
        )

    # ---- Step 5: LLM generation ----
    answer = generate_response(query, chunks, user_role, accessible_collections)

    # ---- Step 6: Output guardrails ----
    output_result = run_output_guards(
        answer, chunks, user_role, accessible_collections
    )

    # Append warnings if any
    if output_result["has_warnings"]:
        for warning in output_result["warnings"]:
            answer += warning

    # Build source citations
    sources = []
    seen = set()
    for chunk in chunks:
        doc_name = chunk.get("source_document", "unknown")
        page = chunk.get("page_number")
        key = (doc_name, page)
        if key not in seen:
            seen.add(key)
            sources.append(
                SourceCitation(
                    document=doc_name,
                    page=page,
                    section=chunk.get("section_title"),
                    chunk_type=chunk.get("chunk_type"),
                )
            )

    # Include rate limit warning if applicable
    guardrail_info = None
    if input_result and not input_result.get("blocked"):
        guardrail_info = GuardrailInfo(
            triggered=True,
            type="input",
            reason=input_result["guardrail_type"],
        )
    elif output_result["has_warnings"]:
        guardrail_info = GuardrailInfo(
            triggered=True,
            type="output",
            reason="output_warning",
        )

    return ChatResponse(
        answer=answer,
        route=route_name,
        sources=sources,
        guardrail=guardrail_info,
        user_role=user_role,
        accessible_collections=accessible_collections,
    )
