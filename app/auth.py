# app/auth.py

import datetime
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from .db import SessionLocal, APIKeyModel
from slowapi.util import get_remote_address
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from passlib.hash import bcrypt

######################################
# 1. Rate Limiter

######################################
# 2. Dependency: DB Session
######################################
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

######################################
# 3. Header for API Key
######################################
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

######################################
# 4. Check or retrieve user from key
######################################
def get_user(
    db: Session = Depends(get_db),
    raw_key: str = Security(api_key_header),
):
    """
    - Looks up the hashed key in the db
    - Verifies the raw key
    - Checks active status
    - Updates last_used_at
    - Raises 401 if invalid
    """
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key header"
        )

    # Retrieve all possible rows (there should normally be just one row per hashed_key).
    # Because we can't do an equality filter on the raw key (it's hashed in DB),
    # we have to pull all keys and compare. Or we could store raw_key-> hashed_key map in a separate table.
    # For simplicity, do a brute force check:
    all_keys = db.query(APIKeyModel).filter(APIKeyModel.active == True).all()
    for record in all_keys:
        if record.verify_key(raw_key):
            # Key is valid
            record.last_used_at = datetime.datetime.utcnow()
            db.commit()
            return {
                "id": record.id,
                "owner": record.owner,
                "role": record.role,
                "active": record.active,
                "created_at": record.created_at,
                "last_used_at": record.last_used_at
            }

    # If none matched
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or inactive API key"
    )

######################################
# 5. Confirm Admin Role
######################################
def require_admin(user: dict = Depends(get_user)):
    """
    A helper dependency to ensure that the user is an admin.
    If not, raise 403 Forbidden.
    """
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return user
