"""
TEST-001: InfraNodus DB Migrations Test
Tests for 012_relationship_evidence.sql and 013_entity_temporal.sql
"""
import pytest
from uuid import uuid4
from datetime import datetime


class TestRelationshipEvidenceMigration:
    """Tests for 012_relationship_evidence.sql migration"""

    @pytest.mark.asyncio
    async def test_relationship_evidence_table_exists(self, db):
        """Verify relationship_evidence table was created"""
        result = await db.fetchrow("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'relationship_evidence'
            ) as exists
        """)
        assert result["exists"], "relationship_evidence table should exist"

    @pytest.mark.asyncio
    async def test_relationship_evidence_columns(self, db):
        """Verify all required columns exist"""
        result = await db.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'relationship_evidence'
        """)
        columns = {row["column_name"]: row["data_type"] for row in result}

        expected_columns = {
            "id": "uuid",
            "relationship_id": "uuid",
            "chunk_id": "uuid",
            "relevance_score": "real",
            "extraction_method": "text",
            "context_snippet": "text",
            "created_at": "timestamp with time zone"
        }

        for col_name, col_type in expected_columns.items():
            assert col_name in columns, f"Column {col_name} should exist"
            assert col_type in columns[col_name], f"Column {col_name} should be {col_type}"

    @pytest.mark.asyncio
    async def test_relationship_evidence_indexes(self, db):
        """Verify indexes were created"""
        result = await db.fetch("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'relationship_evidence'
        """)
        index_names = [row["indexname"] for row in result]

        expected_indexes = [
            "idx_rel_evidence_relationship_id",
            "idx_rel_evidence_chunk_id",
            "idx_rel_evidence_relevance"
        ]

        for idx in expected_indexes:
            assert idx in index_names, f"Index {idx} should exist"

    @pytest.mark.asyncio
    async def test_get_relationship_evidence_function(self, db):
        """Verify get_relationship_evidence() function exists"""
        result = await db.fetchrow("""
            SELECT EXISTS (
                SELECT FROM pg_proc
                WHERE proname = 'get_relationship_evidence'
            ) as exists
        """)
        assert result["exists"], "get_relationship_evidence function should exist"

    @pytest.mark.asyncio
    async def test_rls_enabled(self, db):
        """Verify RLS is enabled on relationship_evidence"""
        result = await db.fetchrow("""
            SELECT relrowsecurity
            FROM pg_class
            WHERE relname = 'relationship_evidence'
        """)
        assert result["relrowsecurity"], "RLS should be enabled"


class TestEntityTemporalMigration:
    """Tests for 013_entity_temporal.sql migration"""

    @pytest.mark.asyncio
    async def test_entities_temporal_columns(self, db):
        """Verify temporal columns were added to entities table"""
        result = await db.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'entities'
            AND column_name IN ('source_year', 'first_seen_year', 'last_seen_year')
        """)
        columns = [row["column_name"] for row in result]

        assert "source_year" in columns, "source_year column should exist"
        assert "first_seen_year" in columns, "first_seen_year column should exist"
        assert "last_seen_year" in columns, "last_seen_year column should exist"

    @pytest.mark.asyncio
    async def test_relationships_temporal_column(self, db):
        """Verify first_seen_year column was added to relationships"""
        result = await db.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'relationships'
            AND column_name = 'first_seen_year'
        """)
        assert len(result) == 1, "first_seen_year column should exist in relationships"

    @pytest.mark.asyncio
    async def test_temporal_indexes(self, db):
        """Verify temporal indexes were created"""
        result = await db.fetch("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'entities'
            AND indexname LIKE '%year%'
        """)
        index_names = [row["indexname"] for row in result]

        expected_indexes = [
            "idx_entities_source_year",
            "idx_entities_first_seen_year",
            "idx_entities_temporal_range"
        ]

        for idx in expected_indexes:
            assert idx in index_names, f"Index {idx} should exist"

    @pytest.mark.asyncio
    async def test_migrate_entity_temporal_data_function(self, db):
        """Verify migrate_entity_temporal_data() function exists"""
        result = await db.fetchrow("""
            SELECT EXISTS (
                SELECT FROM pg_proc
                WHERE proname = 'migrate_entity_temporal_data'
            ) as exists
        """)
        assert result["exists"], "migrate_entity_temporal_data function should exist"

    @pytest.mark.asyncio
    async def test_get_project_temporal_stats_function(self, db):
        """Verify get_project_temporal_stats() function exists"""
        result = await db.fetchrow("""
            SELECT EXISTS (
                SELECT FROM pg_proc
                WHERE proname = 'get_project_temporal_stats'
            ) as exists
        """)
        assert result["exists"], "get_project_temporal_stats function should exist"


class TestMigrationDataBackfill:
    """Tests for data backfill after migration"""

    @pytest.mark.asyncio
    async def test_migrate_temporal_data_execution(self, db, test_project_id):
        """Test that migrate_entity_temporal_data() runs without errors"""
        result = await db.fetchrow("""
            SELECT * FROM migrate_entity_temporal_data($1)
        """, test_project_id)

        assert result is not None, "Function should return results"
        assert "entities_updated" in result.keys()
        assert "relationships_updated" in result.keys()

    @pytest.mark.asyncio
    async def test_temporal_stats_retrieval(self, db, test_project_id):
        """Test get_project_temporal_stats() returns valid data"""
        result = await db.fetchrow("""
            SELECT * FROM get_project_temporal_stats($1)
        """, test_project_id)

        assert result is not None
        assert "min_year" in result.keys()
        assert "max_year" in result.keys()
        assert "total_entities" in result.keys()


# Fixtures
@pytest.fixture
async def db():
    """Database connection fixture"""
    from database import get_db_connection
    conn = await get_db_connection()
    yield conn
    await conn.close()


@pytest.fixture
def test_project_id():
    """Test project ID fixture - replace with actual test project"""
    return uuid4()
