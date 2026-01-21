"""
Middleware package for ScholaRAG_Graph backend.

Includes:
- RateLimiterMiddleware: IP-based rate limiting for all endpoints
- QuotaTrackingMiddleware: Per-user/project API quota tracking
- QuotaService: Quota management service
- ErrorTrackingMiddleware: HTTP error tracking for monitoring
"""

from middleware.rate_limiter import RateLimiterMiddleware
from middleware.quota_middleware import (
    QuotaDependency,
    QuotaTrackingMiddleware,
    add_quota_headers,
    quota_exceeded_response,
    track_api_usage,
)
from middleware.quota_service import (
    ApiType,
    QuotaExceededException,
    QuotaPlan,
    QuotaService,
    QuotaStatus,
    get_quota_service,
    init_quota_service,
)
from middleware.error_tracking import (
    ErrorEvent,
    ErrorStats,
    ErrorTracker,
    ErrorTrackingMiddleware,
    get_error_tracker,
    init_error_tracker,
    should_alert,
)

__all__ = [
    # Rate limiting
    "RateLimiterMiddleware",
    # Quota middleware
    "QuotaDependency",
    "QuotaTrackingMiddleware",
    "add_quota_headers",
    "quota_exceeded_response",
    "track_api_usage",
    # Quota service
    "ApiType",
    "QuotaExceededException",
    "QuotaPlan",
    "QuotaService",
    "QuotaStatus",
    "get_quota_service",
    "init_quota_service",
    # Error tracking
    "ErrorEvent",
    "ErrorStats",
    "ErrorTracker",
    "ErrorTrackingMiddleware",
    "get_error_tracker",
    "init_error_tracker",
    "should_alert",
]
