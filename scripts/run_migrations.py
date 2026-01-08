#!/usr/bin/env python3
"""
Database Migration Runner

Runs SQL migration files in order against the PostgreSQL database.

Usage:
    python scripts/run_migrations.py

Environment:
    DATABASE_URL: PostgreSQL connection string (with SSL)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import asyncpg


async def run_migrations():
    """Run all migration files in order."""
    # Get database URL from environment
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("\nSet it with:")
        print("  export DATABASE_URL='postgresql://user:pass@host:5432/db?sslmode=require'")
        sys.exit(1)

    # Ensure SSL for Render
    if "sslmode" not in database_url:
        database_url += "?sslmode=require"

    # Migration files directory
    migrations_dir = Path(__file__).parent.parent / "database" / "migrations"

    if not migrations_dir.exists():
        print(f"ERROR: Migrations directory not found: {migrations_dir}")
        sys.exit(1)

    # Get migration files sorted by name
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        print("No migration files found")
        return

    print(f"Found {len(migration_files)} migration files")
    print(f"Database: {database_url[:50]}...")
    print()

    # Connect to database
    try:
        conn = await asyncpg.connect(database_url)
        print("Connected to database")
    except Exception as e:
        print(f"ERROR: Failed to connect: {e}")
        sys.exit(1)

    # Create migrations tracking table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    # Get already applied migrations
    applied = set(
        row["name"]
        for row in await conn.fetch("SELECT name FROM _migrations")
    )

    # Run each migration
    for migration_file in migration_files:
        name = migration_file.name

        if name in applied:
            print(f"  [SKIP] {name} (already applied)")
            continue

        print(f"  [RUN]  {name}...")

        try:
            # Read and execute migration
            sql = migration_file.read_text()

            # Execute in transaction
            async with conn.transaction():
                await conn.execute(sql)

                # Record migration
                await conn.execute(
                    "INSERT INTO _migrations (name) VALUES ($1)",
                    name
                )

            print(f"         OK")

        except Exception as e:
            print(f"         FAILED: {e}")
            await conn.close()
            sys.exit(1)

    await conn.close()
    print()
    print("All migrations completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_migrations())
