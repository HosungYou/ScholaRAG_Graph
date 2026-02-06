"""
Database connection management using asyncpg.

Provides connection pooling and helper methods for PostgreSQL operations.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Optional

import asyncpg

from config import settings

logger = logging.getLogger(__name__)


class Database:
    """
    Async PostgreSQL database connection manager using asyncpg.

    Usage:
        db = Database()
        await db.connect()

        # Use connection pool
        async with db.acquire() as conn:
            result = await conn.fetch("SELECT * FROM projects")

        await db.disconnect()
    """

    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or settings.database_url
        self._pool: Optional[asyncpg.Pool] = None
        # Health snapshot cache to avoid frequent DB probes from /health endpoint.
        self._health_cache_ttl = 15.0
        self._health_cache = {
            "checked_at": 0.0,
            "db_ok": False,
            "pgvector_ok": False,
        }
        self._health_lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._pool is not None

    @property
    def pool(self) -> asyncpg.Pool:
        """Get the connection pool, raise if not connected."""
        if self._pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._pool

    async def connect(
        self,
        min_size: int = 2,
        max_size: int = 5,
        command_timeout: float = 30.0,
    ) -> None:
        """
        Create connection pool.

        Args:
            min_size: Minimum pool connections (reduced for free tier DB limits)
            max_size: Maximum pool connections (reduced for free tier DB limits)
            command_timeout: Default query timeout in seconds

        Note:
            Free tier databases (Supabase, Render) have ~20 connection limits.
            Keep pool small to avoid exhausting connections.
        """
        if self._pool is not None:
            logger.warning("Database already connected")
            return

        try:
            self._pool = await asyncpg.create_pool(
                dsn=self.dsn,
                min_size=min_size,
                max_size=max_size,
                command_timeout=command_timeout,
                # Connection health settings for free tier stability
                max_inactive_connection_lifetime=300.0,  # Close idle connections after 5 min
                # pgbouncer compatibility: disable prepared statements
                # Supabase uses pgbouncer in transaction mode which doesn't support prepared statements
                statement_cache_size=0,
            )
            logger.info(f"Database connected (pool: {min_size}-{max_size})")
            # Force fresh health probe after reconnect.
            self._health_cache["checked_at"] = 0.0
        except Exception as e:
            # Log exception type and message for debugging (DSN is not logged)
            logger.error(f"Failed to connect to database: {type(e).__name__}: {e}")
            raise RuntimeError("Database connection failed") from e

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            self._health_cache = {
                "checked_at": time.monotonic(),
                "db_ok": False,
                "pgvector_ok": False,
            }
            logger.info("Database disconnected")

    async def get_health_snapshot(self, force_refresh: bool = False) -> dict[str, bool]:
        """
        Return cached DB health + pgvector status.

        Uses a short TTL cache because infrastructure health checks can call
        this endpoint very frequently (e.g., every 15-30s on hosting platforms).
        """
        now = time.monotonic()
        cache_age = now - float(self._health_cache["checked_at"])
        if not force_refresh and cache_age < self._health_cache_ttl:
            return {
                "db_ok": bool(self._health_cache["db_ok"]),
                "pgvector_ok": bool(self._health_cache["pgvector_ok"]),
            }

        async with self._health_lock:
            # Re-check cache inside lock to prevent thundering-herd refreshes.
            now = time.monotonic()
            cache_age = now - float(self._health_cache["checked_at"])
            if not force_refresh and cache_age < self._health_cache_ttl:
                return {
                    "db_ok": bool(self._health_cache["db_ok"]),
                    "pgvector_ok": bool(self._health_cache["pgvector_ok"]),
                }

            if self._pool is None:
                self._health_cache = {
                    "checked_at": now,
                    "db_ok": False,
                    "pgvector_ok": False,
                }
                return {"db_ok": False, "pgvector_ok": False}

            try:
                async with self.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT
                            1 AS db_ok,
                            EXISTS(
                                SELECT 1
                                FROM pg_extension
                                WHERE extname = 'vector'
                            ) AS pgvector_ok
                        """
                    )

                db_ok = bool(row and row["db_ok"] == 1)
                pgvector_ok = bool(row and row["pgvector_ok"])
                self._health_cache = {
                    "checked_at": now,
                    "db_ok": db_ok,
                    "pgvector_ok": pgvector_ok,
                }
            except Exception:
                logger.error("Database health snapshot check failed")
                self._health_cache = {
                    "checked_at": now,
                    "db_ok": False,
                    "pgvector_ok": False,
                }

            return {
                "db_ok": bool(self._health_cache["db_ok"]),
                "pgvector_ok": bool(self._health_cache["pgvector_ok"]),
            }

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire a connection from the pool.

        Usage:
            async with db.acquire() as conn:
                await conn.fetch("SELECT * FROM table")
        """
        async with self.pool.acquire() as connection:
            yield connection

    @asynccontextmanager
    async def transaction(self):
        """
        Acquire a connection and start a transaction.

        Usage:
            async with db.transaction() as conn:
                await conn.execute("INSERT INTO ...")
                await conn.execute("UPDATE ...")
        """
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                yield connection

    async def execute(self, query: str, *args) -> str:
        """Execute a query and return status."""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        """Fetch all rows from a query."""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch a single row from a query."""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args) -> Any:
        """Fetch a single value from a query."""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def executemany(self, query: str, args: list) -> None:
        """Execute a query with multiple argument sets."""
        async with self.acquire() as conn:
            await conn.executemany(query, args)

    async def health_check(self) -> bool:
        """Check if database is accessible."""
        status = await self.get_health_snapshot()
        return status["db_ok"]

    async def check_pgvector(self) -> bool:
        """Check if pgvector extension is available."""
        status = await self.get_health_snapshot()
        return status["pgvector_ok"]


# Global database instance
db = Database()


async def get_db() -> Database:
    """
    FastAPI dependency for database access.

    Usage:
        @app.get("/items")
        async def get_items(db: Database = Depends(get_db)):
            return await db.fetch("SELECT * FROM items")
    """
    return db


async def require_db() -> Database:
    """
    FastAPI dependency that requires database to be connected.

    Returns 503 Service Unavailable if database is not available.
    Use this for endpoints that cannot function without a database.

    See: ARCH-001 - Consistent behavior when DB connection fails

    Usage:
        @app.get("/items")
        async def get_items(db: Database = Depends(require_db)):
            return await db.fetch("SELECT * FROM items")
    """
    from fastapi import HTTPException

    if not db.is_connected:
        logger.warning("Database not connected - returning 503")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable: database connection not established",
            headers={"Retry-After": "30"}
        )
    return db


async def init_db() -> None:
    """Initialize database connection (call on startup)."""
    await db.connect()
    logger.info("Database initialized")


async def close_db() -> None:
    """Close database connection (call on shutdown)."""
    await db.disconnect()
    logger.info("Database closed")
