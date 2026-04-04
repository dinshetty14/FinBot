"""
FinBot Document Ingestion Pipeline
Walks the data directory, parses all documents with Docling,
generates embeddings, and stores everything in Qdrant.
"""

import logging
import os
import ssl

# SSL Bypass for local environments experiencing certificate verification issues
# This is a common fix for Windows/VPN/Proxy environments
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['PYTHONHTTPSVERIFY'] = '0'
if not os.environ.get('PYTHONHTTPSVERIFY', '') == '0':
    ssl._create_default_https_context = ssl._create_unverified_context
from pathlib import Path
from typing import Optional

from docling.document_converter import DocumentConverter
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
)
from sentence_transformers import SentenceTransformer

from app.config import (
    QDRANT_URL,
    QDRANT_COLLECTION,
    QDRANT_PATH,
    EMBEDDING_MODEL,
    DATA_DIR,
    FOLDER_TO_COLLECTION,
)
from app.ingestion.chunker import parse_and_chunk_document

logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".csv", ".txt"}


def get_embedding_model() -> SentenceTransformer:
    """Load the sentence-transformer embedding model."""
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)
    return model


def get_qdrant_client() -> QdrantClient:
    """Get a Qdrant client connected to the configured URL."""
    if QDRANT_URL.lower() == "local":
        return QdrantClient(path=QDRANT_PATH)
    return QdrantClient(url=QDRANT_URL)


def create_collection(client: QdrantClient, embedding_dim: int) -> None:
    """Create the Qdrant collection if it doesn't exist."""
    collections = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION not in collections:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=embedding_dim,
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"Created Qdrant collection: {QDRANT_COLLECTION}")
    else:
        logger.info(f"Collection {QDRANT_COLLECTION} already exists")


def discover_documents(data_dir: Optional[str] = None) -> list[tuple[Path, str]]:
    """
    Walk the data directory and discover all documents with their collection.

    Returns:
        List of (file_path, collection_name) tuples.
    """
    data_path = Path(data_dir or DATA_DIR)
    documents = []

    for folder_name, collection in FOLDER_TO_COLLECTION.items():
        folder_path = data_path / folder_name
        if not folder_path.exists():
            logger.warning(f"Data folder not found: {folder_path}")
            continue

        for file_path in folder_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                documents.append((file_path, collection))
                logger.info(f"  Found: {file_path.name} → {collection}")

    logger.info(f"Discovered {len(documents)} documents total")
    return documents


def run_ingestion(data_dir: Optional[str] = None, recreate: bool = False) -> dict:
    """
    Run the full ingestion pipeline:
    1. Discover documents in data/
    2. Parse & chunk each document with Docling
    3. Generate embeddings with sentence-transformers
    4. Upsert into Qdrant with metadata

    Args:
        data_dir: Optional override for the data directory.
        recreate: If True, delete and recreate the collection.

    Returns:
        Summary dict with counts.
    """
    logger.info("=" * 60)
    logger.info("Starting FinBot Document Ingestion Pipeline")
    logger.info("=" * 60)

    # Initialize components
    embed_model = get_embedding_model()
    embedding_dim = embed_model.get_sentence_embedding_dimension()
    client = get_qdrant_client()
    doc_converter = DocumentConverter()

    # Optionally recreate collection
    if recreate:
        try:
            client.delete_collection(QDRANT_COLLECTION)
            logger.info(f"Deleted existing collection: {QDRANT_COLLECTION}")
        except Exception:
            pass

    create_collection(client, embedding_dim)

    # Discover documents
    documents = discover_documents(data_dir)
    if not documents:
        logger.warning("No documents found! Check your data directory.")
        return {"documents": 0, "chunks": 0}

    total_chunks = 0
    total_docs = 0

    for file_path, collection in documents:
        try:
            # Parse and chunk using shared converter
            chunks = parse_and_chunk_document(file_path, collection, converter=doc_converter)
            if not chunks:
                logger.warning(f"  No chunks produced from {file_path.name}")
                continue

            # Generate embeddings
            texts = [c["text"] for c in chunks]
            embeddings = embed_model.encode(texts, show_progress_bar=False)

            # Build Qdrant points
            points = []
            for chunk, embedding in zip(chunks, embeddings):
                point = PointStruct(
                    id=chunk["id"],
                    vector=embedding.tolist(),
                    payload={
                        "text": chunk["text"],
                        **chunk["metadata"],
                    },
                )
                points.append(point)

            # Upsert in batches
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                client.upsert(
                    collection_name=QDRANT_COLLECTION,
                    points=batch,
                )

            total_chunks += len(chunks)
            total_docs += 1
            logger.info(
                f"  ✓ Ingested {file_path.name}: {len(chunks)} chunks"
            )

        except Exception as e:
            logger.error(f"  ✗ Failed to ingest {file_path.name}: {e}")

    logger.info("=" * 60)
    logger.info(f"Ingestion complete: {total_docs} documents, {total_chunks} chunks")
    logger.info("=" * 60)

    return {"documents": total_docs, "chunks": total_chunks}
