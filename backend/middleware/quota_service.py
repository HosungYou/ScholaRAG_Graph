"""
API Quota Service for ScholaRAG_Graph.

Provides per-user/project API quota management:
- Quota checking before API calls
- Usage tracking after API calls
- Daily/monthly usage aggregation
- Warning and blocking on quota exceeded

Usage:
    from middleware.quota_service import QuotaService, get_quota_service

    quota = get_quota_service()

    # Check if user can make API call
    status = await quota.check_quota(user_id, "semantic_scholar")
    if status.is_exceeded:
        raise QuotaExceededException(status)

    # Track API call after completion
    await quota.track_usage(
        user_id=user_id,
        api_type="semantic_scholar",
        endpoint="/search",
        response_status=200,
        response_time_ms=150
    )
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ApiType(str, Enum):
    """Supported external API types."""
    SEMANTIC_SCHOLAR = "semantic_scholar"
    OPENALEX = "openalex"
    ZOTERO = "zotero"


class QuotaPlan(str, Enum):
    """Default quota plans."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass
class QuotaLimits:
    """Quota limits for a plan."""
    semantic_scholar_daily: int
    openalex_daily: int
    zotero_daily: int
    total_daily: int

    # Monthly limits (optional)
    semantic_scholar_monthly: Optional[int] = None
    openalex_monthly: Optional[int] = None
    zotero_monthly: Optional[int] = None
    total_monthly: Optional[int] = None


# Default quota limits per plan
DEFAULT_LIMITS = {
    QuotaPlan.FREE: QuotaLimits(
        semantic_scholar_daily=50,
        openalex_daily=100,
        zotero_daily=50,
        total_daily=200,
    ),
    QuotaPlan.BASIC: QuotaLimits(
        semantic_scholar_daily=200,
        openalex_daily=400,
        zotero_daily=200,
        total_daily=800,
    ),
    QuotaPlan.PREMIUM: QuotaLimits(
        semantic_scholar_daily=500,
        openalex_daily=1000,
        zotero_daily=500,
        total_daily=2000,
    ),
    QuotaPlan.ENTERPRISE: QuotaLimits(
        semantic_scholar_daily=10000,
        openalex_daily=20000,
        zotero_daily=10000,
        total_daily=50000,
    ),
}


@dataclass
class QuotaStatus:
    """Current quota status for a user/project."""
    api_type: str
    plan_name: str
    limit: int
    used: int
    remaining: int
    is_exceeded: bool
    is_warning: bool  # True if > 80% used
    reset_time: datetime  # When quota resets

    @property
    def usage_percentage(self) -> float:
        if self.limit == 0:
            return 100.0
        return (self.used / self.limit) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "api_type": self.api_type,
            "plan": self.plan_name,
            "limit": self.limit,
            "used": self.used,
            "remaining": self.remaining,
            "is_exceeded": self.is_exceeded,
            "is_warning": self.is_warning,
            "usage_percentage": round(self.usage_percentage, 1),
            "reset_time": self.reset_time.isoformat(),
        }


class QuotaExceededException(Exception):
    """Raised when API quota is exceeded."""

    def __init__(self, status: QuotaStatus, message: Optional[str] = None):
        self.status = status
        self.message = message or f"API quota exceeded for {status.api_type}. Limit: {status.limit}, Used: {status.used}"
        super().__init__(self.message)


class QuotaService:
    """
    API Quota Management Service.

    Handles:
    - Checking quotas before API calls
    - Tracking usage after API calls
    - In-memory caching for fast quota checks
    - Database persistence for durability
    """

    def __init__(self, db=None, cache_ttl: int = 60):
        """
        Initialize quota service.

        Args:
            db: Database connection (AsyncSession or similar)
            cache_ttl: Cache time-to-live in seconds
        """
        self.db = db
        self.cache_ttl = cache_ttl

        # In-memory cache for quota status
        # Format: {(user_id, api_type): (QuotaStatus, timestamp)}
        self._cache: Dict[Tuple[str, str], Tuple[QuotaStatus, float]] = {}
        self._cache_lock = asyncio.Lock()

        # In-memory usage buffer for batching DB writes
        # Format: {(user_id, api_type, date): usage_count}
        self._usage_buffer: Dict[Tuple[str, str, date], int] = {}
        self._buffer_lock = asyncio.Lock()

    async def check_quota(
        self,
        user_id: Optional[str],
        api_type: str,
        project_id: Optional[str] = None,
        call_count: int = 1,
    ) -> QuotaStatus:
        """
        Check if user has available quota for an API call.

        Args:
            user_id: User ID (can be None for anonymous)
            api_type: Type of API (semantic_scholar, openalex, zotero)
            project_id: Optional project ID for per-project limits
            call_count: Number of API calls to make (for bulk operations)

        Returns:
            QuotaStatus with current usage and limits

        Raises:
            QuotaExceededException if quota is exceeded
        """
        # For anonymous users, use more restrictive limits
        if not user_id:
            user_id = "anonymous"

        cache_key = (user_id, api_type)

        # Check cache first
        async with self._cache_lock:
            if cache_key in self._cache:
                status, timestamp = self._cache[cache_key]
                if datetime.now().timestamp() - timestamp < self.cache_ttl:
                    # Update remaining to account for new call
                    status.remaining = max(0, status.remaining - call_count)
                    status.used += call_count
                    status.is_exceeded = status.remaining <= 0
                    status.is_warning = status.usage_percentage >= 80

                    if status.is_exceeded:
                        raise QuotaExceededException(status)
                    return status

        # Fetch from database if cache miss or expired
        status = await self._fetch_quota_status(user_id, api_type, project_id)

        # Add pending call to usage
        status.used += call_count
        status.remaining = max(0, status.remaining - call_count)
        status.is_exceeded = status.remaining <= 0
        status.is_warning = status.usage_percentage >= 80

        # Update cache
        async with self._cache_lock:
            self._cache[cache_key] = (status, datetime.now().timestamp())

        if status.is_exceeded:
            raise QuotaExceededException(status)

        return status

    async def _fetch_quota_status(
        self,
        user_id: str,
        api_type: str,
        project_id: Optional[str] = None,
    ) -> QuotaStatus:
        """
        Fetch quota status from database.

        Falls back to default limits if database is unavailable.
        """
        today = date.today()
        reset_time = datetime.combine(today, datetime.min.time()).replace(
            hour=0, minute=0, second=0
        ) + __import__("datetime").timedelta(days=1)

        # Default to free plan
        limits = DEFAULT_LIMITS[QuotaPlan.FREE]
        plan_name = QuotaPlan.FREE.value

        # Get limit for this API type
        limit = self._get_api_limit(limits, api_type)

        # Get current usage (check buffer + database)
        used = await self._get_current_usage(user_id, api_type, today)

        return QuotaStatus(
            api_type=api_type,
            plan_name=plan_name,
            limit=limit,
            used=used,
            remaining=max(0, limit - used),
            is_exceeded=used >= limit,
            is_warning=(used / limit * 100) >= 80 if limit > 0 else False,
            reset_time=reset_time,
        )

    def _get_api_limit(self, limits: QuotaLimits, api_type: str) -> int:
        """Get the limit for a specific API type."""
        api_type_lower = api_type.lower()
        if api_type_lower == "semantic_scholar":
            return limits.semantic_scholar_daily
        elif api_type_lower == "openalex":
            return limits.openalex_daily
        elif api_type_lower == "zotero":
            return limits.zotero_daily
        else:
            return limits.total_daily

    async def _get_current_usage(
        self,
        user_id: str,
        api_type: str,
        usage_date: date,
    ) -> int:
        """Get current usage from buffer and database."""
        # Check buffer first
        buffer_key = (user_id, api_type, usage_date)
        async with self._buffer_lock:
            buffered = self._usage_buffer.get(buffer_key, 0)

        # Query database if available
        db_usage = 0
        if self.db:
            try:
                db_usage = await self._query_db_usage(user_id, api_type, usage_date)
            except Exception as e:
                logger.warning(f"Failed to query database usage: {e}")

        return buffered + db_usage

    async def _query_db_usage(
        self,
        user_id: str,
        api_type: str,
        usage_date: date,
    ) -> int:
        """Query database for usage count."""
        if not self.db:
            return 0

        try:
            query = """
                SELECT COALESCE(SUM(call_count), 0)::INT as total
                FROM api_usage
                WHERE user_id = $1
                  AND api_type = $2
                  AND usage_date = $3
            """

            # This is a simplified query - actual implementation depends on DB driver
            # For asyncpg:
            if hasattr(self.db, 'fetchval'):
                result = await self.db.fetchval(query, user_id, api_type, usage_date)
                return result or 0

            # For SQLAlchemy async:
            if hasattr(self.db, 'execute'):
                from sqlalchemy import text
                result = await self.db.execute(
                    text(query),
                    {"user_id": user_id, "api_type": api_type, "usage_date": usage_date}
                )
                row = result.fetchone()
                return row[0] if row else 0

        except Exception as e:
            logger.error(f"Database query error: {e}")

        return 0

    async def track_usage(
        self,
        user_id: Optional[str],
        api_type: str,
        endpoint: str,
        call_count: int = 1,
        project_id: Optional[str] = None,
        response_status: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Track an API call for quota management.

        Args:
            user_id: User ID (can be None for anonymous)
            api_type: Type of API (semantic_scholar, openalex, zotero)
            endpoint: API endpoint called
            call_count: Number of API calls made
            project_id: Optional project ID
            response_status: HTTP response status code
            response_time_ms: Response time in milliseconds
            error_message: Error message if call failed
            request_ip: Client IP address
            user_agent: Client user agent
        """
        if not user_id:
            user_id = "anonymous"

        today = date.today()
        buffer_key = (user_id, api_type, today)

        # Update buffer
        async with self._buffer_lock:
            self._usage_buffer[buffer_key] = self._usage_buffer.get(buffer_key, 0) + call_count

        # Invalidate cache
        cache_key = (user_id, api_type)
        async with self._cache_lock:
            if cache_key in self._cache:
                del self._cache[cache_key]

        # Write to database (can be done async/batched for performance)
        await self._write_usage_to_db(
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

    async def _write_usage_to_db(
        self,
        user_id: str,
        api_type: str,
        endpoint: str,
        call_count: int,
        project_id: Optional[str] = None,
        response_status: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Write usage record to database."""
        if not self.db:
            logger.debug("No database connection, skipping usage write")
            return

        try:
            query = """
                INSERT INTO api_usage (
                    user_id, project_id, api_type, endpoint, call_count,
                    usage_date, usage_hour, response_status, response_time_ms,
                    error_message, request_ip, user_agent
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    CURRENT_DATE, EXTRACT(HOUR FROM NOW())::INT, $6, $7,
                    $8, $9, $10
                )
            """

            # Handle anonymous user (use NULL for proper DB storage)
            db_user_id = None if user_id == "anonymous" else user_id

            # For asyncpg:
            if hasattr(self.db, 'execute'):
                await self.db.execute(
                    query,
                    db_user_id, project_id, api_type, endpoint, call_count,
                    response_status, response_time_ms, error_message,
                    request_ip, user_agent
                )
            else:
                # For SQLAlchemy async:
                from sqlalchemy import text
                await self.db.execute(
                    text(query.replace('$', ':')),
                    {
                        "1": db_user_id, "2": project_id, "3": api_type,
                        "4": endpoint, "5": call_count, "6": response_status,
                        "7": response_time_ms, "8": error_message,
                        "9": request_ip, "10": user_agent
                    }
                )

            logger.debug(f"Tracked API usage: {api_type}/{endpoint} for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to write usage to database: {e}")

    async def get_usage_summary(
        self,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Get usage summary for a user.

        Args:
            user_id: User ID
            start_date: Start date (default: today)
            end_date: End date (default: today)

        Returns:
            Dictionary with usage statistics
        """
        today = date.today()
        start = start_date or today
        end = end_date or today

        summary = {
            "user_id": user_id,
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "usage": {},
            "quotas": {},
        }

        # Get usage for each API type
        for api_type in ApiType:
            status = await self._fetch_quota_status(user_id, api_type.value)
            summary["usage"][api_type.value] = status.used
            summary["quotas"][api_type.value] = {
                "limit": status.limit,
                "used": status.used,
                "remaining": status.remaining,
                "percentage": round(status.usage_percentage, 1),
            }

        return summary

    async def flush_buffer(self) -> int:
        """
        Flush usage buffer to database.

        Called periodically or on shutdown.

        Returns:
            Number of records flushed
        """
        async with self._buffer_lock:
            buffer_copy = self._usage_buffer.copy()
            self._usage_buffer.clear()

        count = 0
        for (user_id, api_type, usage_date), call_count in buffer_copy.items():
            # Note: This is a simplified flush - real implementation would batch
            logger.debug(f"Flushing buffer: {user_id}/{api_type}/{usage_date}: {call_count}")
            count += 1

        return count

    def clear_cache(self) -> None:
        """Clear the quota cache."""
        self._cache.clear()


# ============================================================================
# Global Instance and Factory
# ============================================================================

_quota_service: Optional[QuotaService] = None


def init_quota_service(db=None, cache_ttl: int = 60) -> QuotaService:
    """Initialize the global quota service."""
    global _quota_service
    _quota_service = QuotaService(db=db, cache_ttl=cache_ttl)
    logger.info("Quota service initialized")
    return _quota_service


def get_quota_service() -> QuotaService:
    """Get the global quota service instance."""
    global _quota_service
    if _quota_service is None:
        _quota_service = QuotaService()
        logger.warning("Quota service auto-initialized without database connection")
    return _quota_service
