# app/routers/chat_stream.py

import asyncio
import concurrent.futures
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Optional
import json

# We’ll reuse your pipeline functions from Lexmo_chat_stream.py
from app.services.Lexmo_chat_stream import (
    search_vector_store,
    format_raw_retrieved_data,
    generate_combined_summary,
)

# We also want your config values from Lexmo_chat_stream or define them here
VECTOR_STORES = {
    "State_Acts": "vs_67e99fa07b488191834d5a49905b414f",
    "Union_Acts": "vs_67e99e7010c081918f81a5b784b5bd6d"
}
RELEVANCE_SCORE_THRESHOLD = 0.2
MAX_RESULTS = 4
CHUNK_SIZE = 7000

# --------------  API KEY AUTH FOR WEBSOCKET ---------------------------
# Because websockets don’t support normal FastAPI dependencies (like `Depends(get_user)`)
# out of the box, we need a custom handshake approach.
# We can place the raw_key in query params: ws://...?api_key=XXXX
# Or let the client send it in the first message. 
# Here we’ll parse it from the query param for simplicity.

from sqlalchemy.orm import Session
from app.db import SessionLocal, APIKeyModel
from passlib.hash import bcrypt
import datetime

def verify_api_key(raw_key: Optional[str]) -> bool:
    if not raw_key:
        return False
    db: Session = SessionLocal()
    try:
        all_keys = db.query(APIKeyModel).filter(APIKeyModel.active == True).all()
        for record in all_keys:
            if bcrypt.verify(raw_key, record.hashed_key):
                # Valid
                record.last_used_at = datetime.datetime.utcnow()
                db.commit()
                return True
    except:
        pass
    finally:
        db.close()
    return False

# --------------  HELPER: Directly perform retrieval and send each result ---------------------------
def parallel_search(name, store_id, q, max_results):
    return search_vector_store(name, store_id, q, max_results)


# --------------  THE WEBSOCKET ROUTE  ---------------------------
router = APIRouter()

@router.websocket("/chat_stream")
async def chat_stream_endpoint(websocket: WebSocket, api_key: Optional[str] = Query(None)):
    """
    WebSocket endpoint:
      1) Expects an `api_key` in the query params, e.g. ws://...?api_key=xxx
      2) Waits for a JSON message from the client: { "query": "..." }
      3) Runs vector store retrieval and sends a JSON with "retrieved_files".
      4) Streams the final LLM answer token-by-token over the WebSocket.
    """

    # Accept the websocket connection
    await websocket.accept()

    # 1) Verify the API key
    if not verify_api_key(api_key):
        await websocket.send_json({"error": "Invalid or missing API key."})
        await websocket.close()
        return
    
    while True:
        try:
            # 2) Wait for the client to send a JSON message with { "query": "..." }
            data = await websocket.receive_json()
        except WebSocketDisconnect:
            print("Client disconnected.")
            break
        
        except Exception:
        # If the client forcibly closed or sent invalid JSON, break or handle as needed
            await websocket.send_json({"error": "Invalid message format"})
            continue


    # Check for a "quit" or "done" message if you want a graceful exit
    # E.g. if data == {"query": "done"}:
    #     await websocket.send_json({"info": "Goodbye!"})
    #     break
        if data == {"query": "done"}:
            await websocket.send_json({"info": "Goodbye!"})
            await websocket.close()
            break

        if "query" not in data:
            await websocket.send_json({"error": "No query provided"})
            # await websocket.close()
            continue

        user_query = data["query"]
        await websocket.send_text("[START_STREAM]")
        await asyncio.sleep(0)
        await websocket.send_text("[START_RAW_FILES]")
        await asyncio.sleep(0)  

# ---- Retrieval Phase: send each retrieved file as soon as available ----
        retrieved_results = []  # Will hold raw results for later use in combined summary
        seen_lengths = set()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_map = {
                executor.submit(parallel_search, store_name, store_id, user_query, MAX_RESULTS): store_name
                for store_name, store_id in VECTOR_STORES.items()
            }

            # As soon as each future completes, process its results immediately.
            for fut in concurrent.futures.as_completed(future_map):
                store_name = future_map[fut]
                try:
                    store_name, results_data = fut.result()
                except Exception:
                    continue

                filtered_data = [item for item in results_data if item.score >= RELEVANCE_SCORE_THRESHOLD]

                for result in filtered_data:
                    content_length = len(result.content[0].text)
                    if content_length in seen_lengths:
                        continue
                    seen_lengths.add(content_length)
                    # Save the raw result (keep the same format as before)
                    retrieved_results.append([
                        result.score,
                        store_name,
                        result.filename,
                        result.content
                    ])
                    # Build a JSON friendly structure for this retrieved file
                    item = {
                        "store_name": store_name,
                        "filename": result.filename,
                        "content": [seg.text for seg in result.content],
                        "score": result.score
                    }
                    # Send each retrieved file immediately as JSON
                    await websocket.send_json({"retrieved_file": item})
                    await asyncio.sleep(0)
                    


        await websocket.send_text("[END_RAW_FILES]")
        await asyncio.sleep(0)
        
        await websocket.send_text("[START_PROCESSED_DATA]")
        await asyncio.sleep(0)
        # 6) Now generate the final answer in streaming mode
        combined_knowledge = generate_combined_summary(retrieved_results, user_query, CHUNK_SIZE)
        raw_data_text = format_raw_retrieved_data(retrieved_results)
        
        await websocket.send_text(combined_knowledge)

        await asyncio.sleep(0)
        
        await websocket.send_text("[END_PROCESSED_DATA]")
        await asyncio.sleep(0)
        # Instead of capturing the entire response, we'll forward each chunk as we get it:
        # We'll intercept the `client.chat.completions.create(..., stream=True)` calls
        # inside generate_final_response. That function prints to stdout now,
        # but we want to *send them to the websocket*.
        # So we'll create an alternative version that yields chunks, or we can monkey-patch.

        # Easiest solution: We'll replicate the final logic here, but we won't
        # call the existing generate_final_response function directly, because
        # it prints tokens. We'll re-implement that part so we can send them via websocket.

        final_prompt = build_final_prompt(user_query, combined_knowledge, raw_data_text)
        # Now stream from openai
        import openai
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=final_prompt,
            stream=True
        )

        # 7) Send each chunk as text frames
        await websocket.send_text("[START_RESPONSE_STREAM]")
        for chunk in response:
            content_piece = chunk.choices[0].delta.content
            if content_piece:
            # Only send if it's a non-empty string
                await websocket.send_text(content_piece)
                await asyncio.sleep(0)
        
        await websocket.send_text("[END_RESPONSE_STREAM]")

        await websocket.send_text("[END_STREAM]")

        # 8) Close or keep open if you want to allow multiple queries in one socket
        # We'll close for simplicity
        # await websocket.close()

    # except WebSocketDisconnect:
    #     print("Client disconnected")
    print("WebSocket session ended gracefully.")
    

# --------------  HELPER FOR THE FINAL PROMPT  -------------------------
main_llm_prompt_template = """
You are a compassionate, empathetic legal assistant. The user’s question is:
"{user_query}"

You have a combined set of legal knowledge (cited from various sources), 
and the following raw references (verbatim) from the vector store are also at your disposal:

{raw_data}

Important instructions for your final answer:
1. Do NOT mention or reveal any specific filenames or source names in your response.
2. Provide a detailed, thorough explanation of any relevant legal procedures, requirements, or considerations based on the materials.
3. If the combined summary or raw references mention **specific laws or acts by name** (e.g. "Hindu Marriage Act, 1955"), please include them in your explanation so the user knows which legislation is relevant.
4. Express empathy and understanding for the user's situation.
5. Offer disclaimers where needed (e.g., not a substitute for a professional legal advisor).
6. Conclude by asking one or two clarifying questions that could help you provide a more targeted answer if the user decides to respond with more details.

Answer structure:
- **An empathetic opening**: acknowledge the user's situation and feelings.
- **A detailed explanation**: share any relevant legal information or processes found in your references (without citing filenames), 
  specifically naming any Acts or Laws that appear in your materials (e.g., "Under the Hindu Marriage Act, 1955...").
- **A short disclaimer**: clarify your role and the limitations of the information provided.
- **A brief set of clarifying questions**: help refine the user’s query by prompting them for additional information.

Remember:
- Do NOT introduce new information beyond what is in the combined summary or raw references.
- Do NOT mention or show the filenames from the raw references.
- Maintain a warm, helpful tone.
"""

def build_final_prompt(user_query, combined_knowledge, raw_data_text):
    # Build the messages list used by openai.ChatCompletion
    # Essentially replicates generate_final_response but doesn't print tokens
    # so we can intercept them ourselves.

    final_user_text = main_llm_prompt_template.format(
        user_query=user_query,
        raw_data=raw_data_text
    ) + (
        "\n\nHere is the combined summary of all relevant legal material you can reference:\n"
        + combined_knowledge
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a legal assistant providing comprehensive, empathetic responses. "
                "Do not reveal or mention specific filenames or store references."
            )
        },
        {
            "role": "user",
            "content": final_user_text
        }
    ]
    return messages
