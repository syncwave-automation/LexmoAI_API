# secure.py

from fastapi import APIRouter, Depends, Request
from ..auth import get_user
from ..limiter import limiter

router = APIRouter()

@router.get("/")
@limiter.limit("2/minute")  # route-level override
def secure_route(request: Request, user: dict = Depends(get_user)):
    """
    A secure route that requires a valid API key.
    """
    return {
        "message": "You have accessed a protected endpoint!",
        "user": user
    }
