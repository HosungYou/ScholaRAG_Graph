"""
API Quota Management Router.

Provides endpoints for:
- Viewing current quota usage
- Viewing quota limits and plans
- Admin quota management (future)
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth.dependencies import require_auth_if_configured
from auth.models import User
from middleware.quota_service import (
    ApiType,
    QuotaPlan,
    QuotaService,
    QuotaStatus,
    get_quota_service,
    DEFAULT_LIMITS,
)

router = APIRouter(prefix="/api/quota", tags=["quota"])


# ============================================================================
# Response Models
# ============================================================================


class QuotaLimitResponse(BaseModel):
    """Quota limit details for an API type."""
    api_type: str
    daily_limit: int
    monthly_limit: Optional[int] = None


class QuotaPlanResponse(BaseModel):
    """Quota plan details."""
    name: str
    description: Optional[str] = None
    limits: List[QuotaLimitResponse]
    total_daily_limit: int
    price_monthly: Optional[float] = None


class QuotaUsageResponse(BaseModel):
    """Current quota usage for a user."""
    api_type: str
    plan: str
    limit: int
    used: int
    remaining: int
    usage_percentage: float
    is_exceeded: bool
    is_warning: bool
    reset_time: str  # ISO format


class QuotaSummaryResponse(BaseModel):
    """Summary of all quota usage for a user."""
    user_id: Optional[str] = None
    plan: str = "free"
    usage_date: str
    quotas: List[QuotaUsageResponse]
    total_used: int
    total_limit: int
    total_remaining: int


class QuotaHistoryItem(BaseModel):
    """Historical usage for a single day."""
    date: str
    api_type: str
    calls: int


class QuotaHistoryResponse(BaseModel):
    """Historical quota usage."""
    user_id: Optional[str] = None
    start_date: str
    end_date: str
    history: List[QuotaHistoryItem]
    total_calls: int


# ============================================================================
# Public Endpoints
# ============================================================================


@router.get("/plans", response_model=List[QuotaPlanResponse])
async def get_quota_plans():
    """
    Get all available quota plans.

    Returns list of plans with their limits for each API type.
    """
    plans = []

    for plan in QuotaPlan:
        limits = DEFAULT_LIMITS[plan]
        plans.append(QuotaPlanResponse(
            name=plan.value,
            description=f"{plan.value.capitalize()} tier quota plan",
            limits=[
                QuotaLimitResponse(
                    api_type=ApiType.SEMANTIC_SCHOLAR.value,
                    daily_limit=limits.semantic_scholar_daily,
                    monthly_limit=limits.semantic_scholar_monthly,
                ),
                QuotaLimitResponse(
                    api_type=ApiType.OPENALEX.value,
                    daily_limit=limits.openalex_daily,
                    monthly_limit=limits.openalex_monthly,
                ),
                QuotaLimitResponse(
                    api_type=ApiType.ZOTERO.value,
                    daily_limit=limits.zotero_daily,
                    monthly_limit=limits.zotero_monthly,
                ),
            ],
            total_daily_limit=limits.total_daily,
        ))

    return plans


@router.get("/current", response_model=QuotaSummaryResponse)
async def get_current_quota(
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Get current quota usage for the authenticated user.

    Returns usage details for each API type including:
    - Current usage count
    - Daily limit
    - Remaining calls
    - Warning status (>80% used)
    """
    quota_service = get_quota_service()
    user_id = str(current_user.id) if current_user else None

    quotas = []
    total_used = 0
    total_limit = 0

    for api_type in ApiType:
        try:
            status = await quota_service.check_quota(
                user_id=user_id,
                api_type=api_type.value,
                call_count=0,  # Don't count this check
            )
        except Exception:
            # If quota exceeded, get status anyway
            status = await quota_service._fetch_quota_status(user_id or "anonymous", api_type.value)

        quotas.append(QuotaUsageResponse(
            api_type=api_type.value,
            plan=status.plan_name,
            limit=status.limit,
            used=status.used,
            remaining=status.remaining,
            usage_percentage=round(status.usage_percentage, 1),
            is_exceeded=status.is_exceeded,
            is_warning=status.is_warning,
            reset_time=status.reset_time.isoformat(),
        ))

        total_used += status.used
        total_limit += status.limit

    plan_name = quotas[0].plan if quotas else "free"

    return QuotaSummaryResponse(
        user_id=user_id,
        plan=plan_name,
        usage_date=date.today().isoformat(),
        quotas=quotas,
        total_used=total_used,
        total_limit=total_limit,
        total_remaining=max(0, total_limit - total_used),
    )


@router.get("/usage/{api_type}", response_model=QuotaUsageResponse)
async def get_api_quota(
    api_type: str,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Get quota usage for a specific API type.

    Args:
        api_type: One of 'semantic_scholar', 'openalex', 'zotero'
    """
    # Validate API type
    valid_types = [t.value for t in ApiType]
    if api_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid api_type. Must be one of: {valid_types}"
        )

    quota_service = get_quota_service()
    user_id = str(current_user.id) if current_user else None

    try:
        status = await quota_service.check_quota(
            user_id=user_id,
            api_type=api_type,
            call_count=0,
        )
    except Exception:
        status = await quota_service._fetch_quota_status(user_id or "anonymous", api_type)

    return QuotaUsageResponse(
        api_type=api_type,
        plan=status.plan_name,
        limit=status.limit,
        used=status.used,
        remaining=status.remaining,
        usage_percentage=round(status.usage_percentage, 1),
        is_exceeded=status.is_exceeded,
        is_warning=status.is_warning,
        reset_time=status.reset_time.isoformat(),
    )


@router.get("/history", response_model=QuotaHistoryResponse)
async def get_quota_history(
    days: int = Query(7, ge=1, le=30, description="Number of days of history"),
    api_type: Optional[str] = Query(None, description="Filter by API type"),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Get historical quota usage for the authenticated user.

    Args:
        days: Number of days of history (1-30)
        api_type: Optional filter by API type

    Note: This endpoint requires database connection for historical data.
    Without database, returns empty history.
    """
    user_id = str(current_user.id) if current_user else None
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    # TODO: Query database for historical data
    # For now, return empty history without database
    history = []
    total_calls = 0

    return QuotaHistoryResponse(
        user_id=user_id,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        history=history,
        total_calls=total_calls,
    )


# ============================================================================
# Health Check
# ============================================================================


@router.get("/health")
async def quota_health():
    """
    Check quota service health.

    Returns service status and configuration.
    """
    quota_service = get_quota_service()

    return {
        "status": "healthy",
        "service": "quota",
        "database_connected": quota_service.db is not None,
        "cache_ttl_seconds": quota_service.cache_ttl,
        "plans_available": len(QuotaPlan),
        "api_types_tracked": [t.value for t in ApiType],
    }
