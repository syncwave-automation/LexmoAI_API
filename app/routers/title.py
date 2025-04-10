from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from starlette.requests import Request

from ..auth import get_user
from ..limiter import limiter

from ..services.Lexmo_title import generate_chat_title

router = APIRouter()

class TitleRequest(BaseModel):
    query: str

@router.post("/title")
@limiter.limit("3/minute")  # Example route-level rate limit
def lexmo_title_endpoint(payload: TitleRequest, request: Request, user: dict = Depends(get_user)):
    """
    This endpoint:
    1) Receives a user's query as JSON: {"query": "..."}
    2) Runs the Lexmo_title pipeline (vector store search + LLM calls)
    3) Returns a JSON with:
       - 'retrieved_files': list of store_name, filename, snippet, etc.
       - 'final_answer': string from the LLM
    """
    user_query = payload.query

    # Generate the title using the provided query
    title = generate_chat_title(user_query)

    return {
        "title": title
    }