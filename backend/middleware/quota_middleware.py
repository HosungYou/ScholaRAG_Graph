"""
API Quota Middleware and Dependencies for FastAPI.

Provides:
- FastAPI dependency for quota checking
- Middleware for automatic quota tracking
- Response headers with quota information

Usage in routers:
    from middleware.quota_middleware import QuotaDependency

    @router.post("/semantic-scholar/search")
    async def search(
        request: SearchRequest,
        quota: QuotaStatus = Depends(QuotaDependency(api_type="semantic_scholar"))
    ):
        # Quota already checked, proceed with API call
        ...
"""

import logging
import time
from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from auth.dependencies import get_current_user_optional
from auth.models import User
from middleware.quota_service import (
    ApiType,
    QuotaExceededException,
    QuotaService,
    QuotaStatus,
    get_quota_service,
)

logger = logging.getLogger(__name__)


# ============================================================================
# FastAPI Dependencies
# ============================================================================


class QuotaDependency:
    """
    FastAPI dependency for checking API quota before endpoint execution.

    Usage:
        @router.post("/semantic-scholar/search")
        async def search(
            quota: QuotaStatus = Depends(QuotaDependency(api_type="semantic_scholar"))
        ):
            # Quota already checked
            ...
    """

    def __init__(
        self,
        api_type: str,
        call_count: int = 1,
        raise_on_exceed: bool = True,
    ):
        """
        Initialize quota dependency.

        Args:
            api_type: Type of API (semantic_scholar, openalex, zotero)
            call_count: Number of API calls to account for
            raise_on_exceed: Whether to raise HTTPException when exceeded
        """
        self.api_type = api_type
        self.call_count = call_count
        self.raise_on_exceed = raise_on_exceed

    async def __call__(
        self,
        request: Request,
        current_user: Optional[User] = Depends(get_current_user_optional),
    ) -> QuotaStatus:
        """Check quota and return status."""
        quota_service = get_quota_service()

        user_id = str(current_user.id) if current_user else None
        project_id = request.query_params.get("project_id")

        try:
            status = await quota_service.check_quota(
                user_id=user_id,
                api_type=self.api_type,
                project_id=project_id,
                call_count=self.call_count,
            )

            # Store in request state for later tracking
            request.state.quota_status = status
            request.state.quota_api_type = self.api_type
            request.state.quota_user_id = user_id
            request.state.quota_project_id = project_id

            return status

        except QuotaExceededException as e:
            if self.raise_on_exceed:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "quota_exceeded",
                        "message": e.message,
                        "quota": e.status.to_dict(),
                    },
                    headers={
                        "X-Quota-Limit": str(e.status.limit),
                        "X-Quota-Used": str(e.status.used),
                        "X-Quota-Remaining": "0",
                        "X-Quota-Reset": e.status.reset_time.isoformat(),
                        "Retry-After": str(
                            int((e.status.reset_time - __import__("datetime").datetime.now()).total_seconds())
                        ),
                    },
                )
            # Return status even if exceeded (for soft limits)
            return e.status


def get_current_user_optional(request: Request) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.

    This is a fallback implementation - the actual one should be
    imported from auth.dependencies.
    """
    # Try to get from request state (set by auth middleware)
    if hasattr(request.state, "user"):
        return request.state.user
    return None


# ============================================================================
# Quota Tracking Helper
# ============================================================================


async def track_api_usage(
    request: Request,
    endpoint: str,
    response_status: int,
    response_time_ms: int,
    error_message: Optional[str] = None,
    call_count: int = 1,
) -> None:
    """
    Track API usage after endpoint execution.

    Called by endpoints or middleware after API call completes.

    Args:
        request: FastAPI request object
        endpoint: Endpoint path
        response_status: HTTP status code
        response_time_ms: Response time in milliseconds
        error_message: Error message if call failed
        call_count: Number of API calls made
    """
    quota_service = get_quota_service()

    # Get user/project from request state
    user_id = getattr(request.state, "quota_user_id", None)
    project_id = getattr(request.state, "quota_project_id", None)
    api_type = getattr(request.state, "quota_api_type", "unknown")

    # Get client info
    request_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    await quota_service.track_usage(
        user_id=user_id,
        api_type=api_type,
        endpoint=endpoint,
        call_count=call_count,
        project_id=project_id,
        response_status=response_status,
        response_time_ms=response_time_ms,
        error_message=error_message,
        request_ip=request_ip,
        user_agent=user_agent,
    )


# ============================================================================
# FastAPI Middleware
# ============================================================================


class QuotaTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic quota tracking on integration endpoints.

    Automatically tracks API usage for endpoints matching specific patterns.
    Adds quota information headers to responses.
    """

    # Endpoints that should be tracked
    TRACKED_PREFIXES = {
        "/api/integrations/semantic-scholar": ApiType.SEMANTIC_SCHOLAR.value,
        "/api/integrations/openalex": ApiType.OPENALEX.value,
        "/api/integrations/zotero": ApiType.ZOTERO.value,
    }

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    def _get_api_type(self, path: str) -> Optional[str]:
        """Determine API type from request path."""
        for prefix, api_type in self.TRACKED_PREFIXES.items():
            if path.startswith(prefix):
                return api_type
        return None

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with quota tracking."""
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        api_type = self._get_api_type(path)

        # Skip non-integration endpoints
        if not api_type:
            return await call_next(request)

        # Skip OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # Track timing
        start_time = time.time()

        # Store API type in request state for tracking
        request.state.quota_api_type = api_type

        # Get quota status if not already checked by dependency
        quota_status = getattr(request.state, "quota_status", None)

        try:
            response = await call_next(request)
            response_time_ms = int((time.time() - start_time) * 1000)

            # Track successful call
            await track_api_usage(
                request=request,
                endpoint=path,
                response_status=response.status_code,
                response_time_ms=response_time_ms,
            )

            # Add quota headers to response
            if quota_status:
                response.headers["X-Quota-Limit"] = str(quota_status.limit)
                response.headers["X-Quota-Used"] = str(quota_status.used)
                response.headers["X-Quota-Remaining"] = str(quota_status.remaining)

            return response

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)

            # Track failed call
            await track_api_usage(
                request=request,
                endpoint=path,
                response_status=500,
                response_time_ms=response_time_ms,
                error_message=str(e),
            )

            raise


# ============================================================================
# Response Helpers
# ============================================================================


def quota_exceeded_response(status: QuotaStatus) -> JSONResponse:
    """
    Create a 429 response for quota exceeded.

    Args:
        status: Quota status with details

    Returns:
        JSONResponse with quota information
    """
    from datetime import datetime

    reset_seconds = int((status.reset_time - datetime.now()).total_seconds())

    return JSONResponse(
        status_code=429,
        content={
            "detail": "API quota exceeded",
            "quota": status.to_dict(),
            "retry_after_seconds": max(0, reset_seconds),
        },
        headers={
            "X-Quota-Limit": str(status.limit),
            "X-Quota-Used": str(status.used),
            "X-Quota-Remaining": "0",
            "X-Quota-Reset": status.reset_time.isoformat(),
            "Retry-After": str(max(0, reset_seconds)),
        },
    )


def add_quota_headers(response, status: QuotaStatus):
    """Add quota information headers to a response."""
    response.headers["X-Quota-Limit"] = str(status.limit)
    response.headers["X-Quota-Used"] = str(status.used)
    response.headers["X-Quota-Remaining"] = str(status.remaining)
    response.headers["X-Quota-Reset"] = status.reset_time.isoformat()

    if status.is_warning:
        response.headers["X-Quota-Warning"] = "true"

    return response
