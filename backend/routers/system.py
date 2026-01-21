"""
System Status API Router

Provides real-time system status information including:
- LLM connection status
- Vector database status
- Data source information
- Error metrics and monitoring (PERF-004)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from database import db
from auth.dependencies import require_auth_if_configured
from auth.models import User
from config import settings
from middleware.error_tracking import get_error_tracker, should_alert

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


# ============================================================================
# Error Metrics Endpoints (PERF-004)
# ============================================================================


class ErrorMetricsResponse(BaseModel):
    """Error metrics summary."""
    total_errors: int
    error_counts: Dict[int, int]
    errors_by_path: Dict[str, int]
    avg_response_time_ms: float
    last_error_time: Optional[str] = None
    alert_triggered: bool


class ErrorRateResponse(BaseModel):
    """Error rate over time window."""
    window_seconds: int
    total_errors_in_window: int
    error_counts: Dict[int, int]
    errors_per_minute: float
    count_503: int
    count_5xx: int
    count_4xx: int


class Error503AnalysisResponse(BaseModel):
    """Detailed 503 error analysis."""
    total_503_errors: int
    recent_503_count: int
    rate_per_minute_5min: float
    last_503_time: Optional[str] = None
    seconds_since_last_503: Optional[float] = None
    paths_affected: List[str]
    uptime_seconds: float
    alert_triggered: bool


@router.get("/api/system/metrics/errors", response_model=ErrorMetricsResponse)
async def get_error_metrics():
    """
    Get aggregated error metrics.

    Returns summary of all HTTP errors tracked by the system.
    Use this for dashboards and general monitoring.
    """
    tracker = get_error_tracker()
    stats = tracker.get_stats()

    return ErrorMetricsResponse(
        total_errors=stats.total_errors,
        error_counts=stats.error_counts,
        errors_by_path=stats.errors_by_path,
        avg_response_time_ms=round(stats.avg_response_time_ms, 2),
        last_error_time=stats.last_error_time.isoformat() if stats.last_error_time else None,
        alert_triggered=should_alert(stats),
    )


@router.get("/api/system/metrics/error-rate", response_model=ErrorRateResponse)
async def get_error_rate(
    window: int = Query(300, ge=60, le=3600, description="Time window in seconds (1-60 minutes)")
):
    """
    Get error rate over a time window.

    Args:
        window: Time window in seconds (default: 300 = 5 minutes)

    Returns:
        Error rate statistics for the specified window.
        Useful for alerting on error spikes.
    """
    tracker = get_error_tracker()
    rate_data = tracker.get_error_rate(window_seconds=window)

    return ErrorRateResponse(
        window_seconds=rate_data["window_seconds"],
        total_errors_in_window=rate_data["total_errors_in_window"],
        error_counts=rate_data["error_counts"],
        errors_per_minute=round(rate_data["errors_per_minute"], 2),
        count_503=rate_data["503_count"],
        count_5xx=rate_data["5xx_count"],
        count_4xx=rate_data["4xx_count"],
    )


@router.get("/api/system/metrics/503", response_model=Error503AnalysisResponse)
async def get_503_analysis():
    """
    Get detailed 503 error analysis.

    Returns 503-specific metrics for infrastructure monitoring.
    This endpoint is designed for Render alerts and log monitoring.

    503 errors typically indicate:
    - Database connection pool exhaustion
    - Service unavailable (deployment in progress)
    - Resource limits exceeded
    """
    tracker = get_error_tracker()
    analysis = tracker.get_503_analysis()
    stats = tracker.get_stats()

    return Error503AnalysisResponse(
        total_503_errors=analysis["total_503_errors"],
        recent_503_count=analysis["recent_503_count"],
        rate_per_minute_5min=round(analysis["503_per_minute_5min"], 2),
        last_503_time=analysis["last_503_time"],
        seconds_since_last_503=analysis["seconds_since_last_503"],
        paths_affected=analysis["paths_affected"],
        uptime_seconds=round(analysis["uptime_seconds"], 2),
        alert_triggered=should_alert(stats, threshold_503=5),
    )


@router.get("/api/system/metrics/recent-errors")
async def get_recent_errors(
    limit: int = Query(20, ge=1, le=100, description="Number of recent errors to return")
):
    """
    Get list of recent errors.

    Args:
        limit: Maximum number of errors to return (default: 20)

    Returns:
        List of recent error events with details.
        Useful for debugging and incident investigation.
    """
    tracker = get_error_tracker()
    stats = tracker.get_stats()

    # Format recent errors
    errors = [
        {
            "timestamp": e.timestamp.isoformat(),
            "status_code": e.status_code,
            "method": e.method,
            "path": e.path,
            "response_time_ms": round(e.response_time_ms, 2),
            "error_detail": e.error_detail,
        }
        for e in stats.recent_errors[-limit:]
    ]

    return {
        "count": len(errors),
        "errors": list(reversed(errors)),  # Most recent first
    }
