"""
FinBot Configuration Module
Centralizes all settings, environment variables, and constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")

# ---------------------------------------------------------------------------
# Groq LLM Settings
# ---------------------------------------------------------------------------
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

# ---------------------------------------------------------------------------
# Qdrant Vector Database
# ---------------------------------------------------------------------------
QDRANT_URL: str = os.getenv("QDRANT_URL", "local")
QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "finbot_docs")
QDRANT_PATH: str = str(_project_root / "qdrant_data")

# ---------------------------------------------------------------------------
# Embedding Model – Qwen for both doc storage & semantic router
# ---------------------------------------------------------------------------
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B")

# ---------------------------------------------------------------------------
# JWT / Auth
# ---------------------------------------------------------------------------
JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_PATH: str = os.getenv(
    "DATABASE_PATH",
    str(Path(__file__).resolve().parent.parent / "finbot.db"),
)

# ---------------------------------------------------------------------------
# Data directory (source documents)
# ---------------------------------------------------------------------------
DATA_DIR: str = os.getenv("DATA_DIR", str(_project_root / "data"))

# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------
RATE_LIMIT_PER_SESSION: int = int(os.getenv("RATE_LIMIT_PER_SESSION", "20"))

# ---------------------------------------------------------------------------
# RBAC Access Matrix
# Each role maps to a list of document collections it can access.
# ---------------------------------------------------------------------------
COLLECTIONS = ["general", "finance", "engineering", "marketing"]

ACCESS_MATRIX: dict[str, list[str]] = {
    "employee": ["general"],
    "finance": ["general", "finance"],
    "engineering": ["general", "engineering"],
    "marketing": ["general", "marketing"],
    "c_level": ["general", "finance", "engineering", "marketing"],
}

# Map data sub-folders to collections (hr → general)
FOLDER_TO_COLLECTION: dict[str, str] = {
    "general": "general",
    "hr": "general",
    "finance": "finance",
    "engineering": "engineering",
    "marketing": "marketing",
}

# Roles allowed for each collection (inverse of ACCESS_MATRIX)
COLLECTION_ACCESS_ROLES: dict[str, list[str]] = {
    "general": ["employee", "finance", "engineering", "marketing", "c_level"],
    "finance": ["finance", "c_level"],
    "engineering": ["engineering", "c_level"],
    "marketing": ["marketing", "c_level"],
}

# System prompt for the RAG LLM
SYSTEM_PROMPT = """You are FinBot, an internal Q&A assistant for FinSolve Technologies.
Your role is to answer employee questions accurately based ONLY on the provided context documents.

Rules:
1. ONLY answer based on the retrieved context. Do NOT make up information.
2. Always cite the source document name and page number in your answer.
3. If the context does not contain enough information to answer, say so clearly.
4. Never reveal confidential information from collections the user does not have access to.
5. Be professional, concise, and helpful.
6. Format your answers clearly with proper structure.

Context:
{context}

User's Role: {user_role}
Accessible Collections: {accessible_collections}
"""
