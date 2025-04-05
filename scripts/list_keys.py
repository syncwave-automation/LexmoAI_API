# list_keys.py
from app.db import SessionLocal, APIKeyModel

def list_keys():
    db = SessionLocal()
    try:
        all_keys = db.query(APIKeyModel).all()
        for entry in all_keys:
            print(
                f"ID={entry.id}, Owner={entry.owner}, Role={entry.role}, "
                f"Active={entry.active}, Created={entry.created_at}, "
                f"LastUsed={entry.last_used_at}"
            )
    finally:
        db.close()

if __name__ == "__main__":
    list_keys()
