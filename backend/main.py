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
from cache import init_llm_cache, get_llm_cache
from routers import auth, chat, graph, import_, integrations, prisma, projects, teams
from auth.supabase_client import supabase_client
from auth.middleware import AuthMiddleware
from middleware.rate_limiter import RateLimiterMiddleware, init_rate_limit_store

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

    # Initialize LLM cache
    init_llm_cache(
        default_ttl=settings.llm_cache_ttl,
        max_size=settings.llm_cache_max_size,
        enabled=settings.llm_cache_enabled,
    )
    logger.info(f"   LLM Cache: {'enabled' if settings.llm_cache_enabled else 'disabled'} (TTL={settings.llm_cache_ttl}s)")

    # Initialize rate limit store (Redis or in-memory)
    init_rate_limit_store(
        use_redis=settings.redis_rate_limit_enabled and bool(settings.redis_url),
        redis_url=settings.redis_url if settings.redis_url else None,
    )
    logger.info(f"   Rate Limiter: {'Redis' if settings.redis_rate_limit_enabled and settings.redis_url else 'in-memory'}")

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
# Controlled via RATE_LIMIT_ENABLED env var (default: True in production)
# Set RATE_LIMIT_ENABLED=false for local development
_rate_limit_enabled = settings.rate_limit_enabled and settings.environment != "development"
app.add_middleware(RateLimiterMiddleware, enabled=_rate_limit_enabled)
logger.info(f"Rate Limiting: {'enabled' if _rate_limit_enabled else 'disabled (development mode)'}")

# Authentication middleware (enforces centralized auth policies)
# See auth/policies.py for route-level policy configuration
app.add_middleware(AuthMiddleware)

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

    # Get LLM cache stats
    cache_stats = get_llm_cache().get_stats()

    return {
        "status": "healthy",
        "database": db_status,
        "pgvector": pgvector_status,
        "llm_provider": settings.default_llm_provider,
        "llm_cache": cache_stats,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
