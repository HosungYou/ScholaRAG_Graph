"""
Rate Limiter Middleware

In-memory rate limiting for API endpoints to prevent abuse:
- /api/auth/* - 10 requests per minute (brute-force prevention)
- /api/chat/* - 30 requests per minute (DoS prevention)
- /api/import/* - 5 requests per minute (heavy operation protection)

This is an in-memory implementation. For production with multiple instances,
consider using Redis-based rate limiting or slowapi with Redis backend.
"""

import time
import logging
from collections import defaultdict
from typing import Dict, Tuple, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitConfig:
    """Rate limit configuration for different endpoint patterns."""

    # Format: (max_requests, window_seconds)
    LIMITS: Dict[str, Tuple[int, int]] = {
        "/api/auth": (10, 60),      # 10 requests per minute
        "/api/chat": (30, 60),      # 30 requests per minute
        "/api/import": (5, 60),     # 5 requests per minute
    }

    # Default limit for unmatched endpoints
    DEFAULT_LIMIT: Tuple[int, int] = (100, 60)  # 100 requests per minute


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm.

    Tracks requests per client IP and path prefix, returning 429 Too Many Requests
    when limits are exceeded.
    """

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        # Structure: {client_key: [(timestamp, count), ...]}
        self._request_counts: Dict[str, list] = defaultdict(list)
        # Lock-free cleanup tracking
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Clean up every 5 minutes

    def _get_client_key(self, request: Request, path_prefix: str) -> str:
        """
        Generate a unique key for rate limiting based on client IP and path prefix.

        Uses X-Forwarded-For header if behind a proxy, otherwise uses client.host.
        """
        # Get client IP, considering proxy headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP (client IP) from the chain
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"{client_ip}:{path_prefix}"

    def _get_rate_limit(self, path: str) -> Tuple[int, int]:
        """
        Get rate limit config for a path.

        Returns (max_requests, window_seconds) tuple.
        """
        for prefix, limit in RateLimitConfig.LIMITS.items():
            if path.startswith(prefix):
                return limit
        return RateLimitConfig.DEFAULT_LIMIT

    def _get_path_prefix(self, path: str) -> str:
        """Extract the rate-limited path prefix."""
        for prefix in RateLimitConfig.LIMITS.keys():
            if path.startswith(prefix):
                return prefix
        return "default"

    def _is_rate_limited(self, client_key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Check if a client is rate limited using sliding window.

        Returns (is_limited, remaining_requests) tuple.
        """
        now = time.time()
        window_start = now - window_seconds

        # Get timestamps within the window
        timestamps = self._request_counts[client_key]

        # Filter out old entries (outside the window)
        valid_timestamps = [ts for ts in timestamps if ts > window_start]
        self._request_counts[client_key] = valid_timestamps

        current_count = len(valid_timestamps)
        remaining = max(0, max_requests - current_count)

        if current_count >= max_requests:
            return True, remaining

        # Record this request
        self._request_counts[client_key].append(now)
        return False, remaining - 1

    def _cleanup_old_entries(self):
        """Periodically clean up expired entries to prevent memory growth."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        cutoff = now - 3600  # Remove entries older than 1 hour

        keys_to_remove = []
        for key, timestamps in self._request_counts.items():
            valid = [ts for ts in timestamps if ts > cutoff]
            if valid:
                self._request_counts[key] = valid
            else:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._request_counts[key]

        if keys_to_remove:
            logger.debug(f"Rate limiter cleanup: removed {len(keys_to_remove)} stale entries")

    async def dispatch(self, request: Request, call_next):
        """Process the request with rate limiting."""
        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for health checks and static files
        path = request.url.path
        if path in ("/", "/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        # Periodic cleanup
        self._cleanup_old_entries()

        # Get rate limit for this path
        max_requests, window_seconds = self._get_rate_limit(path)
        path_prefix = self._get_path_prefix(path)
        client_key = self._get_client_key(request, path_prefix)

        # Check rate limit
        is_limited, remaining = self._is_rate_limited(client_key, max_requests, window_seconds)

        if is_limited:
            logger.warning(f"Rate limit exceeded for {client_key} on {path}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after_seconds": window_seconds,
                },
                headers={
                    "Retry-After": str(window_seconds),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + window_seconds),
                },
            )

        # Process request and add rate limit headers
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window_seconds)

        return response
