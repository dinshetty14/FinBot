"""
FinBot FastAPI Application
Main entry point for the backend API server.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.config import ACCESS_MATRIX
from app.database import init_db
from app.auth import authenticate_user, create_access_token, get_current_user
from app.models import LoginRequest, LoginResponse, ChatRequest, ChatResponse, UserInfo
from app.rag.pipeline import process_query
from app.admin.routes import router as admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# App Lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    logger.info("Initializing FinBot backend...")
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("FinBot backend shutting down")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="FinBot API",
    description="FinSolve Technologies Internal Q&A Assistant with RBAC",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include admin routes
app.include_router(admin_router)


# ---------------------------------------------------------------------------
# Auth Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """Authenticate a user and return a JWT token."""
    user = authenticate_user(req.username, req.password)
    if not user:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(user["id"])
    role = user["role"]
    return LoginResponse(
        access_token=token,
        user=UserInfo(
            id=user["id"],
            username=user["username"],
            role=role,
            department=user["department"],
            accessible_collections=ACCESS_MATRIX.get(role, []),
        ),
    )


# ---------------------------------------------------------------------------
# User Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/user/me", response_model=UserInfo)
def get_me(current_user: UserInfo = Depends(get_current_user)):
    """Get the current authenticated user's info."""
    return current_user


# ---------------------------------------------------------------------------
# Chat Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    current_user: UserInfo = Depends(get_current_user),
):
    """
    Main chat endpoint.
    Processes the query through the full RAG pipeline with RBAC enforcement.
    """
    logger.info(f"Chat request from {current_user.username} (role={current_user.role})")
    response = process_query(
        request=req,
        user_role=current_user.role,
        accessible_collections=current_user.accessible_collections,
    )
    return response


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "FinBot API"}
