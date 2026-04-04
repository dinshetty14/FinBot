"""
FinBot Pydantic Models
Request/response schemas for the API.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ---------------------------------------------------------------------------
# Auth Models
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserInfo"


class UserInfo(BaseModel):
    id: int
    username: str
    role: str
    department: str
    accessible_collections: list[str]


# ---------------------------------------------------------------------------
# Chat Models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class SourceCitation(BaseModel):
    document: str
    page: Optional[int] = None
    section: Optional[str] = None
    chunk_type: Optional[str] = None


class GuardrailInfo(BaseModel):
    triggered: bool = False
    type: Optional[str] = None  # "input" or "output"
    reason: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    route: Optional[str] = None
    sources: list[SourceCitation] = Field(default_factory=list)
    guardrail: Optional[GuardrailInfo] = None
    user_role: str = ""
    accessible_collections: list[str] = Field(default_factory=list)
    blocked: bool = False


# ---------------------------------------------------------------------------
# Admin Models
# ---------------------------------------------------------------------------
class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str
    department: str


class UpdateRoleRequest(BaseModel):
    role: str


class DocumentUploadResponse(BaseModel):
    message: str
    chunks_created: int = 0


# Resolve forward references
LoginResponse.model_rebuild()
