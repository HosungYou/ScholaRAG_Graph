"""
Error Tracking Middleware for ScholaRAG_Graph.

Tracks HTTP error responses (especially 503 errors) for monitoring and alerting.
Provides metrics endpoints for observability and Render log analysis.

PERF-004: 503 Error Monitoring Implementation
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, List, Optional, Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class ErrorEvent:
    """Single error event record."""
    timestamp: datetime
    status_code: int
    path: str
    method: str
    error_detail: Optional[str] = None
    response_time_ms: float = 0.0
    user_id: Optional[str] = None


@dataclass
class ErrorStats:
    """Aggregated error statistics."""
    total_errors: int = 0
    error_counts: Dict[int, int] = field(default_factory=dict)
    recent_errors: List[ErrorEvent] = field(default_factory=list)
    errors_by_path: Dict[str, int] = field(default_factory=dict)
    avg_response_time_ms: float = 0.0
    last_error_time: Optional[datetime] = None


class ErrorTracker:
    """
    Thread-safe error tracking service.

    Maintains rolling window of errors for monitoring and alerting.
    Designed for high-throughput with minimal memory footprint.
    """

    # Maximum number of recent errors to keep in memory
    MAX_RECENT_ERRORS = 100

    # Time window for error rate calculation (in seconds)
    ERROR_RATE_WINDOW = 300  # 5 minutes

    def __init__(self, max_recent_errors: int = MAX_RECENT_ERRORS):
        self._lock = Lock()
        self._max_recent = max_recent_errors
        self._errors: List[ErrorEvent] = []
        self._total_requests = 0
        self._total_errors = 0
        self._error_counts: Dict[int, int] = defaultdict(int)
        self._errors_by_path: Dict[str, int] = defaultdict(int)
        self._response_times: List[float] = []
        self._startup_time = datetime.utcnow()

    def record_request(self, response_time_ms: float) -> None:
        """Record a request (successful or not)."""
        with self._lock:
            self._total_requests += 1
            self._response_times.append(response_time_ms)

            # Keep response times limited
            if len(self._response_times) > 1000:
                self._response_times = self._response_times[-500:]

    def record_error(
        self,
        status_code: int,
        path: str,
        method: str,
        error_detail: Optional[str] = None,
        response_time_ms: float = 0.0,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Record an error event.

        Args:
            status_code: HTTP status code (4xx or 5xx)
            path: Request path
            method: HTTP method
            error_detail: Error message or detail
            response_time_ms: Response time in milliseconds
            user_id: Optional user identifier
        """
        event = ErrorEvent(
            timestamp=datetime.utcnow(),
            status_code=status_code,
            path=path,
            method=method,
            error_detail=error_detail,
            response_time_ms=response_time_ms,
            user_id=user_id,
        )

        with self._lock:
            self._total_errors += 1
            self._error_counts[status_code] += 1
            self._errors_by_path[path] += 1

            # Add to recent errors (FIFO)
            self._errors.append(event)
            if len(self._errors) > self._max_recent:
                self._errors = self._errors[-self._max_recent:]

            # Log 503 errors prominently for Render log monitoring
            if status_code == 503:
                logger.error(
                    f"[503_ERROR] path={path} method={method} "
                    f"response_time_ms={response_time_ms:.2f} "
                    f"detail={error_detail or 'N/A'}"
                )
            elif status_code >= 500:
                logger.warning(
                    f"[{status_code}_ERROR] path={path} method={method} "
                    f"response_time_ms={response_time_ms:.2f}"
                )

    def get_stats(self) -> ErrorStats:
        """Get aggregated error statistics."""
        with self._lock:
            avg_response_time = (
                sum(self._response_times) / len(self._response_times)
                if self._response_times else 0.0
            )

            last_error = self._errors[-1] if self._errors else None

            return ErrorStats(
                total_errors=self._total_errors,
                error_counts=dict(self._error_counts),
                recent_errors=list(self._errors[-20:]),  # Last 20 errors
                errors_by_path=dict(self._errors_by_path),
                avg_response_time_ms=avg_response_time,
                last_error_time=last_error.timestamp if last_error else None,
            )

    def get_error_rate(self, window_seconds: int = ERROR_RATE_WINDOW) -> Dict[str, Any]:
        """
        Calculate error rate over a time window.

        Args:
            window_seconds: Time window in seconds (default: 5 minutes)

        Returns:
            Dict with error rate statistics
        """
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)

        with self._lock:
            recent = [e for e in self._errors if e.timestamp >= cutoff]

            # Count errors by status code in window
            window_counts: Dict[int, int] = defaultdict(int)
            for error in recent:
                window_counts[error.status_code] += 1

            return {
                "window_seconds": window_seconds,
                "total_errors_in_window": len(recent),
                "error_counts": dict(window_counts),
                "503_count": window_counts.get(503, 0),
                "5xx_count": sum(c for code, c in window_counts.items() if code >= 500),
                "4xx_count": sum(c for code, c in window_counts.items() if 400 <= code < 500),
                "errors_per_minute": len(recent) / (window_seconds / 60) if window_seconds > 0 else 0,
            }

    def get_503_analysis(self) -> Dict[str, Any]:
        """
        Get detailed analysis of 503 errors.

        Returns:
            Dict with 503-specific metrics for alerting
        """
        with self._lock:
            errors_503 = [e for e in self._errors if e.status_code == 503]

            # Time since last 503
            last_503 = max((e.timestamp for e in errors_503), default=None)
            time_since_last = (
                (datetime.utcnow() - last_503).total_seconds()
                if last_503 else None
            )

            # Paths affected
            paths_affected = set(e.path for e in errors_503)

            # Rate in last 5 minutes
            cutoff_5min = datetime.utcnow() - timedelta(minutes=5)
            recent_503 = [e for e in errors_503 if e.timestamp >= cutoff_5min]

            return {
                "total_503_errors": self._error_counts.get(503, 0),
                "recent_503_count": len(recent_503),
                "503_per_minute_5min": len(recent_503) / 5 if recent_503 else 0,
                "last_503_time": last_503.isoformat() if last_503 else None,
                "seconds_since_last_503": time_since_last,
                "paths_affected": list(paths_affected),
                "uptime_seconds": (datetime.utcnow() - self._startup_time).total_seconds(),
            }

    def reset(self) -> None:
        """Reset all error tracking data."""
        with self._lock:
            self._errors.clear()
            self._total_errors = 0
            self._total_requests = 0
            self._error_counts.clear()
            self._errors_by_path.clear()
            self._response_times.clear()


# Global error tracker instance
_error_tracker: Optional[ErrorTracker] = None


def get_error_tracker() -> ErrorTracker:
    """Get the global error tracker instance."""
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
    return _error_tracker


def init_error_tracker(max_recent_errors: int = 100) -> ErrorTracker:
    """Initialize the global error tracker."""
    global _error_tracker
    _error_tracker = ErrorTracker(max_recent_errors=max_recent_errors)
    logger.info(f"Error tracker initialized (max_recent={max_recent_errors})")
    return _error_tracker


# ============================================================================
# Middleware
# ============================================================================


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for tracking HTTP errors.

    Records all 4xx and 5xx responses with timing and context.
    Especially tracks 503 errors for infrastructure monitoring.
    """

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.tracker = get_error_tracker()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not self.enabled:
            return await call_next(request)

        # Start timing
        start_time = time.time()

        # Get user ID if available
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = str(getattr(request.state.user, "id", None))

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Unhandled exception - treat as 500
            response_time = (time.time() - start_time) * 1000
            self.tracker.record_request(response_time)
            self.tracker.record_error(
                status_code=500,
                path=request.url.path,
                method=request.method,
                error_detail=str(exc)[:200],
                response_time_ms=response_time,
                user_id=user_id,
            )
            raise

        # Calculate response time
        response_time = (time.time() - start_time) * 1000
        self.tracker.record_request(response_time)

        # Track errors (4xx and 5xx)
        if response.status_code >= 400:
            # Try to get error detail from response
            error_detail = None
            if hasattr(response, "body"):
                try:
                    # Note: This may not work for streaming responses
                    error_detail = str(response.body)[:200] if response.body else None
                except Exception:
                    pass

            self.tracker.record_error(
                status_code=response.status_code,
                path=request.url.path,
                method=request.method,
                error_detail=error_detail,
                response_time_ms=response_time,
                user_id=user_id,
            )

        return response


# ============================================================================
# Utility Functions
# ============================================================================


def format_error_log(event: ErrorEvent) -> str:
    """Format an error event for logging."""
    return (
        f"[{event.status_code}] {event.method} {event.path} "
        f"at {event.timestamp.isoformat()} "
        f"({event.response_time_ms:.2f}ms)"
    )


def should_alert(stats: ErrorStats, threshold_503: int = 5) -> bool:
    """
    Determine if an alert should be triggered.

    Args:
        stats: Current error statistics
        threshold_503: Number of 503 errors to trigger alert

    Returns:
        True if alert should be triggered
    """
    # Alert if 503 count exceeds threshold
    if stats.error_counts.get(503, 0) >= threshold_503:
        return True

    # Alert if 5xx rate is high
    total_5xx = sum(
        count for code, count in stats.error_counts.items()
        if code >= 500
    )
    if total_5xx >= threshold_503 * 2:
        return True

    return False
