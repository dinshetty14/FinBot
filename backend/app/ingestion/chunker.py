"""
FinBot Hierarchical Chunker
Uses Docling to parse documents and produce structure-aware chunks
with the full metadata schema required by the assignment.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional, Any

from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker import HierarchicalChunker

from app.config import COLLECTION_ACCESS_ROLES

logger = logging.getLogger(__name__)


def _determine_chunk_type(chunk) -> str:
    """Determine the chunk type from Docling metadata."""
    if hasattr(chunk, "meta") and hasattr(chunk.meta, "doc_items"):
        for item in chunk.meta.doc_items:
            label = getattr(item, "label", "text")
            if label in ("table",):
                return "table"
            elif label in ("section_header", "title"):
                return "heading"
            elif label in ("code",):
                return "code"
    return "text"


def _extract_page_number(chunk) -> Optional[int]:
    """Extract page number from Docling chunk provenance."""
    if hasattr(chunk, "meta") and hasattr(chunk.meta, "doc_items"):
        for item in chunk.meta.doc_items:
            if hasattr(item, "prov") and item.prov:
                for prov in item.prov:
                    if hasattr(prov, "page_no"):
                        return prov.page_no
    return None


def _extract_headings(chunk) -> str:
    """Extract section headings from chunk metadata."""
    if hasattr(chunk, "meta") and hasattr(chunk.meta, "headings"):
        headings = chunk.meta.headings
        if headings:
            return " > ".join(headings)
    return ""


def parse_and_chunk_document(
    file_path: str | Path,
    collection: str,
    converter: Optional[DocumentConverter] = None,
) -> list[dict]:
    """
    Parse a document using Docling and produce hierarchical chunks
    with full metadata.

    Args:
        file_path: Path to the document file.
        collection: The collection this document belongs to.
        converter: Pre-initialized DocumentConverter instance.

    Returns:
        List of chunk dicts ready for embedding and storage.
    """
    file_path = Path(file_path)
    logger.info(f"Parsing document: {file_path.name} → collection={collection}")

    # Parse document with Docling
    if converter is None:
        converter = DocumentConverter()
        
    result = converter.convert(str(file_path))
    doc = result.document

    # Apply hierarchical chunking
    chunker = HierarchicalChunker()
    chunks = list(chunker.chunk(doc))

    logger.info(f"  Generated {len(chunks)} chunks from {file_path.name}")

    # Hash the entire file path to create a deterministic parent ID
    parent_namespace = hashlib.md5(str(file_path.name).encode()).hexdigest()
    parent_chunk_id = str(hashlib.md5(f"doc:{parent_namespace}".encode()).hexdigest())

    # Build chunk dicts with full metadata
    chunk_dicts = []
    
    for i, chunk in enumerate(chunks):
        text = chunk.text if hasattr(chunk, "text") else str(chunk)
        if not text or not text.strip():
            continue

        # Generate a deterministic ID for this chunk based on its content and source
        content_hash = hashlib.md5(f"{file_path.name}:{i}:{text[:100]}".encode()).hexdigest()
        chunk_id = str(content_hash)

        chunk_type = _determine_chunk_type(chunk)
        page_number = _extract_page_number(chunk)
        section_title = _extract_headings(chunk)
        access_roles = COLLECTION_ACCESS_ROLES.get(collection, [])

        chunk_dict = {
            "id": chunk_id,
            "text": text.strip(),
            "metadata": {
                "source_document": file_path.name,
                "collection": collection,
                "access_roles": access_roles,
                "section_title": section_title,
                "page_number": page_number,
                "chunk_type": chunk_type,
                "parent_chunk_id": parent_chunk_id,
                "chunk_index": i,
            },
        }
        chunk_dicts.append(chunk_dict)

    return chunk_dicts
