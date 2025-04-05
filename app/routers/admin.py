# admin.py

from fastapi import APIRouter, Depends ,HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
import secrets
from passlib.hash import bcrypt

from ..db import SessionLocal, APIKeyModel
from ..auth import require_admin, get_db

router = APIRouter()

class CreateKeyPayload(BaseModel):
    owner: str
    role: str = "user"

@router.post("/create_key")
def create_key(
    payload: CreateKeyPayload,                   # Use Pydantic model
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin),   # Admin-only
):
    """
    Generates a new random API key and stores it hashed in the DB.
    Expects JSON like: {"owner": "TestUser", "role": "user"}
    """
    raw_key = secrets.token_hex(16)
    hashed_key = bcrypt.hash(raw_key)

    key_record = APIKeyModel(
        hashed_key=hashed_key,
        owner=payload.owner,
        role=payload.role,
        active=True,
        created_at=datetime.utcnow()
    )
    db.add(key_record)
    db.commit()
    db.refresh(key_record)

    return {
        "message": "API Key created successfully",
        "api_key": raw_key,  # Show raw key once
        "owner": key_record.owner,
        "role": key_record.role
    }

@router.delete("/delete_key/{owner}")
def delete_key(
    owner: str,
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin),
):
    """
    Deletes the first API key entry found for the given owner.
    If multiple entries exist for the same owner, only the first is deleted.
    """
    key_entry = db.query(APIKeyModel).filter(APIKeyModel.owner == owner).first()
    if not key_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No API key found for owner: {owner}"
        )
    db.delete(key_entry)
    db.commit()
    return {"message": f"Deleted API key for owner: {owner}"}

@router.get("/list_keys")
def list_keys(
    db: Session = Depends(get_db),
    admin_user: dict = Depends(require_admin)  # ensure only admins can call this
):
    """
    Return all API keys in the database (admin-only).
    """
    records = db.query(APIKeyModel).all()
    # Convert them to something JSON-friendly
    return [
        {
            "id": r.id,
            "owner": r.owner,
            "role": r.role,
            "active": r.active,
            "created_at": r.created_at,
            "last_used_at": r.last_used_at
        }
        for r in records
    ]