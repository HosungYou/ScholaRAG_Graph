"""
Database connection management using asyncpg.

Provides connection pooling and helper methods for PostgreSQL operations.
"""

import logging
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
        except Exception as e:
            # Don't log DSN or connection details in error
            logger.error("Failed to connect to database (check DATABASE_URL configuration)")
            raise RuntimeError("Database connection failed") from e

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("Database disconnected")

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
        try:
            result = await self.fetchval("SELECT 1")
            return result == 1
        except Exception:
            logger.error("Database health check failed")
            return False

    async def check_pgvector(self) -> bool:
        """Check if pgvector extension is available."""
        try:
            result = await self.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            return result
        except Exception:
            logger.error("pgvector extension check failed")
            return False


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


async def init_db() -> None:
    """Initialize database connection (call on startup)."""
    await db.connect()
    logger.info("Database initialized")


async def close_db() -> None:
    """Close database connection (call on shutdown)."""
    await db.disconnect()
    logger.info("Database closed")
