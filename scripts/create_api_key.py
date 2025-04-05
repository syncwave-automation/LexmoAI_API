# scripts/create_api_key.py

import secrets
import datetime
import sys
from passlib.hash import bcrypt
from app.db import SessionLocal, init_db, APIKeyModel


def create_api_key(owner="Unknown", role="user"):
    raw_key = secrets.token_hex(16)
    hashed_key = bcrypt.hash(raw_key)

    db = SessionLocal()
    record = APIKeyModel(
        hashed_key=hashed_key,
        owner=owner,
        role=role,
        active=True,
        created_at=datetime.datetime.utcnow()
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    db.close()

    print("Raw API Key:", raw_key)
    print("Give this to the client. It will not be shown again.")


if __name__ == "__main__":
    init_db()

    owner_arg = sys.argv[1] if len(sys.argv) > 1 else "Unknown"
    role_arg = sys.argv[2] if len(sys.argv) > 2 else "user"

    create_api_key(owner=owner_arg, role=role_arg)
