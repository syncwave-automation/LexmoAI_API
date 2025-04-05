# app/main.py

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from .limiter import limiter
from .db import init_db
from .routers import public, secure, admin
from .auth import require_admin

def create_app() -> FastAPI:
    """
    Factory to create the FastAPI app instance.
    """
    app = FastAPI(title="LexmoAP API")
    

    app.state.limiter = limiter

    # Add a global exception handler for 429 Too Many Requests
    @app.exception_handler(RateLimitExceeded)
    def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
        )


    # Include public router
    app.include_router(
        public.router,
        prefix="/api/v1/public",
        tags=["public"]
    )

    # Include secure router
    app.include_router(
        secure.router,
        prefix="/api/v1/secure",
        tags=["secure"]
    )
    
    # Include admin router
    app.include_router(
        admin.router,
        prefix="/api/v1/admin",
        tags=["admin"]
    )

    return app

app = create_app()

@app.on_event("startup")
def on_startup():
    init_db()

# If running with `python -m uvicorn app.main:app --reload`
# or simply `uvicorn app.main:app --reload`

