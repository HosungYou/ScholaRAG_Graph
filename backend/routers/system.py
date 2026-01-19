"""
System Status API Router

Provides real-time system status information including:
- LLM connection status
- Vector database status
- Data source information
"""

import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from database import db
from auth.dependencies import require_auth_if_configured
from auth.models import User
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# Response Models
class LLMStatus(BaseModel):
    provider: str
    model: str
    connected: bool


class VectorStatus(BaseModel):
    total: int
    indexed: int
    status: str  # 'ready', 'pending', 'error'


class DataSourceStatus(BaseModel):
    type: Optional[str] = None  # 'zotero', 'pdf', 'scholarag'
    importedAt: Optional[str] = None
    paperCount: int = 0


class SystemStatusResponse(BaseModel):
    llm: LLMStatus
    vectors: VectorStatus
    dataSource: DataSourceStatus


async def check_llm_connection() -> LLMStatus:
    """
    Check if LLM provider is configured and accessible.
    """
    provider = getattr(settings, 'DEFAULT_LLM_PROVIDER', 'anthropic')
    model = getattr(settings, 'DEFAULT_LLM_MODEL', 'claude-3-5-haiku-20241022')

    # Check if API key is configured
    connected = False
    if provider == 'anthropic':
        api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
        connected = bool(api_key and len(api_key) > 10)
    elif provider == 'openai':
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        connected = bool(api_key and len(api_key) > 10)
    elif provider == 'google':
        api_key = getattr(settings, 'GOOGLE_API_KEY', None)
        connected = bool(api_key and len(api_key) > 10)
    else:
        # Assume connected for other providers if configured
        connected = True

    return LLMStatus(
        provider=provider,
        model=model,
        connected=connected
    )


@router.get("/api/system/status", response_model=SystemStatusResponse)
async def get_system_status(
    project_id: UUID = Query(..., description="Project ID to get status for"),
    user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Get system status for a specific project.

    Returns:
    - LLM connection status (provider, model, connected)
    - Vector database status (total entities, indexed count, status)
    - Data source information (type, import date, paper count)
    """
    database = await db.get_connection()

    try:
        # 1. Check LLM connection
        llm_status = await check_llm_connection()

        # 2. Get vector status
        # Count total entities
        total_entities = await database.fetchval(
            "SELECT COUNT(*) FROM entities WHERE project_id = $1",
            project_id
        ) or 0

        # Count entities with embeddings (if embeddings table exists)
        try:
            indexed_count = await database.fetchval(
                """
                SELECT COUNT(DISTINCT e.id)
                FROM entities e
                WHERE e.project_id = $1
                AND e.embedding IS NOT NULL
                """,
                project_id
            ) or 0
        except Exception:
            # Fallback if embedding column doesn't exist
            indexed_count = total_entities

        # Determine vector status
        if total_entities == 0:
            vector_status = 'pending'
        elif indexed_count >= total_entities:
            vector_status = 'ready'
        else:
            vector_status = 'pending'

        vectors = VectorStatus(
            total=total_entities,
            indexed=indexed_count,
            status=vector_status
        )

        # 3. Get data source info
        project = await database.fetchrow(
            """
            SELECT
                import_source,
                last_synced_at,
                (SELECT COUNT(*) FROM paper_metadata WHERE project_id = $1) as paper_count
            FROM projects
            WHERE id = $1
            """,
            project_id
        )

        if project:
            data_source = DataSourceStatus(
                type=project.get('import_source'),
                importedAt=project['last_synced_at'].isoformat() if project.get('last_synced_at') else None,
                paperCount=project.get('paper_count', 0) or 0
            )
        else:
            data_source = DataSourceStatus()

        return SystemStatusResponse(
            llm=llm_status,
            vectors=vectors,
            dataSource=data_source
        )

    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        # Return default status on error
        return SystemStatusResponse(
            llm=LLMStatus(provider='unknown', model='N/A', connected=False),
            vectors=VectorStatus(total=0, indexed=0, status='error'),
            dataSource=DataSourceStatus()
        )


@router.get("/api/system/health")
async def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok", "service": "scholarag-graph"}
