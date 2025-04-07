# app/routers/chat.py

import concurrent.futures
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from starlette.requests import Request

from ..auth import get_user
from ..limiter import limiter

# 1) Import the existing functions & objects from Lexmo_chat.py
#    DO NOT modify them in Lexmo_chat.py; just import them here.
#    We'll also define local config variables to pass as needed.
from app.services.Lexmo_chat import (
    search_vector_store,
    format_raw_retrieved_data,
    generate_combined_summary,
    generate_final_response,
    custom_response,
    # If you have global constants or a dictionary like "vector_stores" or "relevance_score_threshold",
    # you can import them here OR define them locally in this file.
)

router = APIRouter()

# 2) Example configuration that you had in Lexmo_chat.py
#    You can replicate or import them from Lexmo_chat if they’re made global there.
VECTOR_STORES = {
    "State_Acts": "vs_67e99fa07b488191834d5a49905b414f",
    "Union_Acts": "vs_67e99e7010c081918f81a5b784b5bd6d"
}
RELEVANCE_SCORE_THRESHOLD = 0.2
MAX_RESULTS = 4
CHUNK_SIZE = 7000

class ChatRequest(BaseModel):
    query: str

@router.post("/chat")
@limiter.limit("3/minute")  # Example route-level rate limit
def lexmo_chat_endpoint(payload: ChatRequest, request: Request, user: dict = Depends(get_user)):
    """
    This endpoint:
    1) Receives a user's query as JSON: {"query": "..."}
    2) Runs the Lexmo_chat pipeline (vector store search + LLM calls)
    3) Returns a JSON with:
       - 'retrieved_files': list of store_name, filename, snippet, etc.
       - 'final_answer': string from the LLM
    """
    user_query = payload.query

    # -------------------------------------------------------------------
    # STEP A: SEARCH ALL VECTOR STORES (parallel) using the same logic
    # -------------------------------------------------------------------
    search_results = []
    seen_lengths = set()  # to filter duplicates if needed

    def parallel_search(name, store_id, query, max_results):
        return search_vector_store(name, store_id, query, max_results)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_store = {
            executor.submit(parallel_search, store_name, store_id, user_query, MAX_RESULTS): store_name
            for store_name, store_id in VECTOR_STORES.items()
        }

        for future in concurrent.futures.as_completed(future_to_store):
            store_name = future_to_store[future]
            try:
                store_name, results_data = future.result()
            except Exception as exc:
                # Gracefully handle any vector store errors
                continue

            # Filter out results below threshold
            filtered_data = [item for item in results_data if item.score >= RELEVANCE_SCORE_THRESHOLD]

            # Collect each result, skipping duplicates
            for result in filtered_data:
                content_length = len(result.content[0].text)
                if content_length not in seen_lengths:
                    seen_lengths.add(content_length)
                    search_results.append([
                        result.score,
                        store_name,
                        result.filename,
                        result.content
                    ])

    # -------------------------------------------------------------------
    # STEP B: CREATE COMBINED SUMMARY & FINAL ANSWER
    # -------------------------------------------------------------------
    combined_knowledge = generate_combined_summary(search_results, user_query, CHUNK_SIZE)
    raw_data_text = format_raw_retrieved_data(search_results)
    final_answer = generate_final_response(user_query, combined_knowledge, raw_data_text)
    final_answer_sanitized = custom_response(final_answer)

    # -------------------------------------------------------------------
    # STEP C: Build a return structure
    #  1) "retrieved_files": which store, filename, snippet (like you asked)
    #  2) "final_answer": the final LLM text
    # -------------------------------------------------------------------
    retrieved_info = []
    for (score, store_name, filename, content_obj) in search_results:
        # Each "content_obj" is typically a list of text segments
        text_snippets = [seg.text for seg in content_obj]
        retrieved_info.append({
            "store_name": store_name,
            "filename": filename,
            "content": text_snippets,
            "score": score
        })

    return {
        "retrieved_files": retrieved_info,
        "final_answer": final_answer_sanitized
    }
