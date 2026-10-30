
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

from .database import init_db, close_db
from .api.v1 import documents


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    service: str = "beacon-lens"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Beacon Lens",
        description="Open-source LLM knowledge platform: turn raw documents into a queryable RAG, an autonomous reasoning agent, and a self-maintaining Wiki.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(documents.router, prefix="/api/v1")

    # CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health():
        return HealthResponse()

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
    async def api_health():
        return HealthResponse()

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
