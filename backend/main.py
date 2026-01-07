"""
ScholaRAG_Graph FastAPI Backend

AGENTiGraph-style GraphRAG platform for visualizing and exploring
knowledge graphs built from ScholaRAG literature review data.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import chat, graph, import_, projects


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("🚀 ScholaRAG_Graph Backend starting...")
    print(f"   Database: {settings.database_url[:50]}...")
    print(f"   Default LLM: {settings.default_llm_provider}/{settings.default_llm_model}")

    yield

    # Shutdown
    print("👋 ScholaRAG_Graph Backend shutting down...")


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

# Include routers
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(graph.router, prefix="/api/graph", tags=["Graph"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(import_.router, prefix="/api/import", tags=["Import"])


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
    return {
        "status": "healthy",
        "database": "connected",  # TODO: actual DB check
        "llm_provider": settings.default_llm_provider,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
