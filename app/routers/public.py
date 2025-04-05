# app/routers/public.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def public_route():
    return {"message": "Hello from the public route!"}
