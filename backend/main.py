"""
ScholaRAG_Graph FastAPI Backend

AGENTiGraph-style GraphRAG platform for visualizing and exploring
knowledge graphs built from ScholaRAG literature review data.
"""

import logging
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import db, init_db, close_db
from routers import auth, chat, graph, import_, integrations, prisma, projects, teams
from auth.supabase_client import supabase_client
from middleware.rate_limiter import RateLimiterMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _sanitize_database_url(url: str) -> str:
    """
    Sanitize database URL for logging by removing credentials.

    Transforms: postgresql://user:password@host:port/dbname
    Into:       postgresql://***:***@host:port/dbname
    """
    if not url:
        return "<not configured>"

    # Pattern to match credentials in database URL
    # Handles: protocol://user:password@host or protocol://user@host
    pattern = r"(://)[^:@]+(?::[^@]+)?(@)"
    sanitized = re.sub(pattern, r"\1***:***\2", url)
    return sanitized


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("ScholaRAG_Graph Backend starting...")
    logger.info(f"   Database: {_sanitize_database_url(settings.database_url)}")
    logger.info(f"   Default LLM: {settings.default_llm_provider}/{settings.default_llm_model}")
    
    # Initialize Supabase
    if settings.supabase_url and settings.supabase_anon_key:
        supabase_client.initialize(settings.supabase_url, settings.supabase_anon_key)
        logger.info("   Supabase Auth: configured")
    else:
        logger.warning("   Supabase Auth: NOT configured (running without auth)")

    # Initialize database connection
    try:
        await init_db()
        logger.info("   Database connected successfully")

        # Check pgvector availability
        if await db.check_pgvector():
            logger.info("   pgvector extension: available")
        else:
            logger.warning("   pgvector extension: NOT available")
    except Exception as e:
        logger.error(f"   Database connection failed: {e}")
        logger.warning("   Running in memory-only mode")

    yield

    # Shutdown
    logger.info("ScholaRAG_Graph Backend shutting down...")
    await close_db()


app = FastAPI(
    title="ScholaRAG_Graph API",
    description="AGENTiGraph-style GraphRAG platform for academic literature",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
# Limits: /api/auth/* - 10/min, /api/chat/* - 30/min, /api/import/* - 5/min
app.add_middleware(RateLimiterMiddleware, enabled=True)

# Include routers
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(graph.router, prefix="/api/graph", tags=["Graph"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(import_.router, prefix="/api/import", tags=["Import"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(teams.router, prefix="/api/teams", tags=["Teams"])
app.include_router(prisma.router, prefix="/api/prisma", tags=["PRISMA"])
app.include_router(integrations.router, tags=["Integrations"])


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "status": "healthy",
        "service": "ScholaRAG_Graph",
        "version": "0.1.0",
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    db_status = "disconnected"
    pgvector_status = "unavailable"

    try:
        if await db.health_check():
            db_status = "connected"
        if await db.check_pgvector():
            pgvector_status = "available"
    except Exception:
        pass

    return {
        "status": "healthy",
        "database": db_status,
        "pgvector": pgvector_status,
        "llm_provider": settings.default_llm_provider,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
