# app/db.py
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String,
    Boolean, DateTime
)
from sqlalchemy.orm import sessionmaker, declarative_base
from passlib.hash import bcrypt

DATABASE_URL = "sqlite:///./api_keys.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}, echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class APIKeyModel(Base):
    """
    Stores hashed API keys plus metadata:
      - hashed_key: Bcrypt-hashed API key
      - owner: name or identifier (e.g. “Bob”)
      - role: e.g. “admin” or “user”
      - active: if false, the key is revoked
      - created_at, last_used_at: for auditing
    """
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    hashed_key = Column(String, unique=True, index=True, nullable=False)
    owner = Column(String, nullable=False)
    role = Column(String, default="user")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now() )
    last_used_at = Column(DateTime, default=None)

    def verify_key(self, raw_key: str) -> bool:
        """
        Checks a raw key against the stored bcrypt-hashed value.
        """
        return bcrypt.verify(raw_key, self.hashed_key)


def init_db():
    """Creates tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
