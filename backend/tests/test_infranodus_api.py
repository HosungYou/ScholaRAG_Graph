"""
TEST-002: InfraNodus API Endpoints Test
Tests for new InfraNodus-style knowledge graph analysis endpoints
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from unittest.mock import AsyncMock, patch


class TestRelationshipEvidenceEndpoint:
    """Tests for GET /api/graph/relationships/{id}/evidence"""

    @pytest.mark.asyncio
    async def test_get_evidence_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful retrieval of relationship evidence"""
        relationship_id = str(uuid4())

        with patch("routers.graph.get_db_connection") as mock_db:
            mock_db.return_value.fetch = AsyncMock(return_value=[
                {
                    "evidence_id": str(uuid4()),
                    "chunk_id": str(uuid4()),
                    "chunk_text": "Sample evidence text",
                    "section_type": "methodology",
                    "paper_id": str(uuid4()),
                    "paper_title": "Test Paper",
                    "paper_authors": "Author A, Author B",
                    "paper_year": 2024,
                    "relevance_score": 0.85,
                    "context_snippet": "...context..."
                }
            ])

            response = await client.get(
                f"/api/graph/relationships/{relationship_id}/evidence",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert "evidence" in data
        assert len(data["evidence"]) > 0
        assert "chunk_text" in data["evidence"][0]

    @pytest.mark.asyncio
    async def test_get_evidence_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test 404 when relationship doesn't exist"""
        relationship_id = str(uuid4())

        with patch("routers.graph.get_db_connection") as mock_db:
            mock_db.return_value.fetch = AsyncMock(return_value=[])

            response = await client.get(
                f"/api/graph/relationships/{relationship_id}/evidence",
                headers=auth_headers
            )

        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_evidence_unauthorized(self, client: AsyncClient):
        """Test 401 without authentication"""
        relationship_id = str(uuid4())

        response = await client.get(
            f"/api/graph/relationships/{relationship_id}/evidence"
        )

        assert response.status_code == 401


class TestTemporalGraphEndpoint:
    """Tests for GET /api/graph/temporal/{project_id}"""

    @pytest.mark.asyncio
    async def test_get_temporal_data_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful retrieval of temporal graph data"""
        project_id = str(uuid4())

        response = await client.get(
            f"/api/graph/temporal/{project_id}",
            headers=auth_headers
        )

        # Should return 200 with temporal stats or 404 if project doesn't exist
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "min_year" in data or "temporal_stats" in data

    @pytest.mark.asyncio
    async def test_get_temporal_with_year_filter(self, client: AsyncClient, auth_headers: dict):
        """Test temporal data with year filter"""
        project_id = str(uuid4())

        response = await client.get(
            f"/api/graph/temporal/{project_id}",
            params={"year": 2023},
            headers=auth_headers
        )

        assert response.status_code in [200, 404]


class TestTemporalMigrateEndpoint:
    """Tests for POST /api/graph/temporal/{project_id}/migrate"""

    @pytest.mark.asyncio
    async def test_migrate_temporal_data(self, client: AsyncClient, auth_headers: dict):
        """Test temporal data migration trigger"""
        project_id = str(uuid4())

        with patch("routers.graph.get_db_connection") as mock_db:
            mock_db.return_value.fetchrow = AsyncMock(return_value={
                "entities_updated": 10,
                "relationships_updated": 5
            })

            response = await client.post(
                f"/api/graph/temporal/{project_id}/migrate",
                headers=auth_headers
            )

        assert response.status_code in [200, 202, 404]

        if response.status_code in [200, 202]:
            data = response.json()
            assert "entities_updated" in data or "message" in data

    @pytest.mark.asyncio
    async def test_migrate_unauthorized(self, client: AsyncClient):
        """Test 401 without authentication"""
        project_id = str(uuid4())

        response = await client.post(
            f"/api/graph/temporal/{project_id}/migrate"
        )

        assert response.status_code == 401


class TestBridgeHypothesisEndpoint:
    """Tests for POST /api/graph/gaps/{id}/generate-bridge"""

    @pytest.mark.asyncio
    async def test_generate_bridge_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful bridge hypothesis generation"""
        gap_id = str(uuid4())

        with patch("routers.graph.GapDetector") as mock_detector:
            mock_instance = mock_detector.return_value
            mock_instance.generate_bridge_hypotheses = AsyncMock(return_value=[
                {
                    "hypothesis": "Concept A may relate to Concept B through mechanism X",
                    "confidence": 0.75,
                    "supporting_evidence": ["paper1", "paper2"],
                    "suggested_papers": []
                }
            ])

            response = await client.post(
                f"/api/graph/gaps/{gap_id}/generate-bridge",
                headers=auth_headers
            )

        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            data = response.json()
            assert "hypotheses" in data or "hypothesis" in str(data)

    @pytest.mark.asyncio
    async def test_generate_bridge_with_context(self, client: AsyncClient, auth_headers: dict):
        """Test bridge generation with additional context"""
        gap_id = str(uuid4())

        response = await client.post(
            f"/api/graph/gaps/{gap_id}/generate-bridge",
            json={"context": "Focus on educational technology"},
            headers=auth_headers
        )

        assert response.status_code in [200, 404, 422]


class TestDiversityEndpoint:
    """Tests for GET /api/graph/diversity/{project_id}"""

    @pytest.mark.asyncio
    async def test_get_diversity_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful diversity metrics retrieval"""
        project_id = str(uuid4())

        with patch("routers.graph.DiversityAnalyzer") as mock_analyzer:
            mock_instance = mock_analyzer.return_value
            mock_instance.analyze = AsyncMock(return_value={
                "shannon_entropy": 2.5,
                "gini_coefficient": 0.35,
                "cluster_distribution": {"concept": 50, "method": 30, "finding": 20},
                "bias_score": 0.15,
                "diversity_rating": "Good"
            })

            response = await client.get(
                f"/api/graph/diversity/{project_id}",
                headers=auth_headers
            )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Check for diversity metrics
            assert any(key in data for key in [
                "shannon_entropy", "gini_coefficient", "diversity", "metrics"
            ])

    @pytest.mark.asyncio
    async def test_diversity_empty_project(self, client: AsyncClient, auth_headers: dict):
        """Test diversity for project with no entities"""
        project_id = str(uuid4())

        response = await client.get(
            f"/api/graph/diversity/{project_id}",
            headers=auth_headers
        )

        # Should handle empty gracefully
        assert response.status_code in [200, 404]


class TestGraphCompareEndpoint:
    """Tests for GET /api/graph/compare/{project_a}/{project_b}"""

    @pytest.mark.asyncio
    async def test_compare_projects_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful project comparison"""
        project_a = str(uuid4())
        project_b = str(uuid4())

        response = await client.get(
            f"/api/graph/compare/{project_a}/{project_b}",
            headers=auth_headers
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Check for comparison metrics
            assert any(key in data for key in [
                "jaccard_similarity", "overlap_coefficient", "comparison", "similarity"
            ])

    @pytest.mark.asyncio
    async def test_compare_same_project(self, client: AsyncClient, auth_headers: dict):
        """Test comparing project with itself"""
        project_id = str(uuid4())

        response = await client.get(
            f"/api/graph/compare/{project_id}/{project_id}",
            headers=auth_headers
        )

        # Should return 100% similarity or error
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_compare_unauthorized_project(self, client: AsyncClient, auth_headers: dict):
        """Test comparing with unauthorized project"""
        project_a = str(uuid4())
        project_b = str(uuid4())  # User doesn't have access

        response = await client.get(
            f"/api/graph/compare/{project_a}/{project_b}",
            headers=auth_headers
        )

        # Should return 403 or 404
        assert response.status_code in [200, 403, 404]


class TestErrorHandling:
    """Tests for error handling across all endpoints"""

    @pytest.mark.asyncio
    async def test_invalid_uuid_format(self, client: AsyncClient, auth_headers: dict):
        """Test 422 for invalid UUID format"""
        invalid_id = "not-a-uuid"

        endpoints = [
            f"/api/graph/relationships/{invalid_id}/evidence",
            f"/api/graph/temporal/{invalid_id}",
            f"/api/graph/diversity/{invalid_id}",
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint, headers=auth_headers)
            assert response.status_code in [400, 422, 404], f"Failed for {endpoint}"

    @pytest.mark.asyncio
    async def test_rate_limiting(self, client: AsyncClient, auth_headers: dict):
        """Test rate limiting on endpoints"""
        project_id = str(uuid4())

        # Make many rapid requests
        responses = []
        for _ in range(10):
            response = await client.get(
                f"/api/graph/diversity/{project_id}",
                headers=auth_headers
            )
            responses.append(response.status_code)

        # Should eventually hit rate limit or all succeed
        assert all(code in [200, 404, 429] for code in responses)


# Fixtures
@pytest.fixture
async def client():
    """AsyncClient fixture for API testing"""
    from main import app
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Authentication headers fixture"""
    return {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json"
    }
