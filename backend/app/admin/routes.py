"""
FinBot Admin Routes
Admin endpoints for user management and document management.
Only accessible by c_level users.
"""

import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from app.auth import require_admin, hash_password
from app.config import ACCESS_MATRIX, DATA_DIR, FOLDER_TO_COLLECTION
from app.database import create_user, delete_user, update_user_role, list_users
from app.models import (
    CreateUserRequest,
    UpdateRoleRequest,
    DocumentUploadResponse,
    UserInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------

@router.get("/users")
def admin_list_users(admin: UserInfo = Depends(require_admin)):
    """List all users (admin only)."""
    users = list_users()
    # Add accessible_collections to each user
    for user in users:
        user["accessible_collections"] = ACCESS_MATRIX.get(user["role"], [])
    return {"users": users}


@router.post("/users")
def admin_create_user(
    req: CreateUserRequest,
    admin: UserInfo = Depends(require_admin),
):
    """Create a new user (admin only)."""
    if req.role not in ACCESS_MATRIX:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {list(ACCESS_MATRIX.keys())}",
        )

    try:
        pw_hash = hash_password(req.password)
        user_id = create_user(req.username, pw_hash, req.role, req.department)
        logger.info(f"Admin {admin.username} created user {req.username} (role={req.role})")
        return {
            "message": f"User '{req.username}' created successfully",
            "user_id": user_id,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/users/{user_id}/role")
def admin_update_role(
    user_id: int,
    req: UpdateRoleRequest,
    admin: UserInfo = Depends(require_admin),
):
    """Update a user's role (admin only)."""
    if req.role not in ACCESS_MATRIX:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {list(ACCESS_MATRIX.keys())}",
        )

    success = update_user_role(user_id, req.role)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"Admin {admin.username} updated user {user_id} role to {req.role}")
    return {"message": f"User role updated to '{req.role}'"}


@router.delete("/users/{user_id}")
def admin_delete_user(
    user_id: int,
    admin: UserInfo = Depends(require_admin),
):
    """Delete a user (admin only)."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    success = delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(f"Admin {admin.username} deleted user {user_id}")
    return {"message": "User deleted successfully"}


# ---------------------------------------------------------------------------
# Document Management
# ---------------------------------------------------------------------------

@router.post("/documents", response_model=DocumentUploadResponse)
async def admin_upload_document(
    file: UploadFile = File(...),
    collection: str = Form(...),
    admin: UserInfo = Depends(require_admin),
):
    """
    Upload and ingest a new document (admin only).
    The document is saved to the appropriate data folder and ingested.
    """
    if collection not in FOLDER_TO_COLLECTION.values():
        raise HTTPException(
            status_code=400,
            detail=f"Invalid collection. Must be one of: {list(set(FOLDER_TO_COLLECTION.values()))}",
        )

    # Determine the target folder
    target_folder = None
    for folder, coll in FOLDER_TO_COLLECTION.items():
        if coll == collection:
            target_folder = folder
            break

    if target_folder is None:
        raise HTTPException(status_code=400, detail="Could not determine target folder")

    data_path = Path(DATA_DIR) / target_folder
    data_path.mkdir(parents=True, exist_ok=True)

    # Save the uploaded file
    file_path = data_path / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    logger.info(f"Admin {admin.username} uploaded document: {file.filename} → {collection}")

    # Ingest the single document
    try:
        from app.ingestion.chunker import parse_and_chunk_document
        from app.ingestion.ingest import get_embedding_model, get_qdrant_client, QDRANT_COLLECTION
        from qdrant_client.models import PointStruct

        chunks = parse_and_chunk_document(file_path, collection)
        if not chunks:
            return DocumentUploadResponse(
                message=f"Document '{file.filename}' saved but no chunks were produced.",
                chunks_created=0,
            )

        embed_model = get_embedding_model()
        texts = [c["text"] for c in chunks]
        embeddings = embed_model.encode(texts, show_progress_bar=False)

        client = get_qdrant_client()
        points = [
            PointStruct(
                id=chunk["id"],
                vector=embedding.tolist(),
                payload={"text": chunk["text"], **chunk["metadata"]},
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
        client.upsert(collection_name=QDRANT_COLLECTION, points=points)

        return DocumentUploadResponse(
            message=f"Document '{file.filename}' ingested successfully into '{collection}'",
            chunks_created=len(chunks),
        )
    except Exception as e:
        logger.error(f"Failed to ingest uploaded document: {e}")
        return DocumentUploadResponse(
            message=f"Document saved but ingestion failed: {str(e)}",
            chunks_created=0,
        )
