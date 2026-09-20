import sys
from pathlib import Path

# Ensure project root (containing 'ai') and backend are always on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent
for p in [str(PROJECT_ROOT), str(BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.core.observability import init_observability, is_observability_enabled
from app.api.api import api_router
from ai.agents.checkpointer import checkpointer_manager
from app.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    init_db()
    # Initialize LangSmith Observability
    init_observability()
    # Initialize cloud checkpointer (creates tables in PostgreSQL if available)
    checkpointer_manager.get_checkpointer()
    # Start periodic background scheduler (overdue task cron job)
    start_scheduler()
    try:
        yield
    finally:
        # Gracefully stop background scheduler
        stop_scheduler()
        # Gracefully close connection pool on shutdown
        checkpointer_manager.close_checkpointer_pool()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered college club event operations platform",
    version=settings.VERSION,
    lifespan=lifespan
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers under both /api and /api/v1 for compatibility
app.include_router(api_router, prefix="/api")
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {
        "message": "Welcome to ClubOps AI API",
        "version": settings.VERSION,
        "docs": "/docs"
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "ClubOps AI",
        "observability": {
            "langsmith_enabled": is_observability_enabled(),
            "project": settings.LANGCHAIN_PROJECT
        }
    }
