# secure.py

from fastapi import APIRouter, Depends, Request
from ..auth import get_user
from ..limiter import limiter

# Import the chat router we just wrote
from .chat import router as chat_router
from .chat_stream import router as ws_chat_router
from .title import router as title_router

router = APIRouter()

# You can mount the chat router to keep everything under /api/v1/secure/chat
router.include_router(chat_router)
router.include_router(ws_chat_router)
router.include_router(title_router)

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

