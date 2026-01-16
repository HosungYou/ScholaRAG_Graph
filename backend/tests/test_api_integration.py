"""
API Integration Tests

Tests actual API endpoints with mocked dependencies.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestProjectsAPI:
    """Test projects API endpoints."""

    @pytest.mark.asyncio
    async def test_list_projects_empty(self, async_client, mock_db):
        """Test listing projects when none exist."""
        with patch("routers.projects.db", mock_db):
            mock_db.fetch.return_value = []

            response = await async_client.get("/api/projects/")

            assert response.status_code == 200
            assert response.json() == []

    @pytest.mark.asyncio
    async def test_create_project(self, async_client, mock_db):
        """Test creating a new project."""
        with patch("routers.projects.db", mock_db):
            project_data = {
                "name": "Test Project",
                "research_question": "What is the impact of AI?",
            }

            response = await async_client.post("/api/projects/", json=project_data)

            assert response.status_code == 200
            result = response.json()
            assert result["name"] == "Test Project"
            assert "id" in result

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, async_client, mock_db):
        """Test getting a non-existent project."""
        with patch("routers.projects.db", mock_db):
            mock_db.fetchrow.return_value = None

            response = await async_client.get(
                "/api/projects/12345678-1234-1234-1234-123456789012"
            )

            assert response.status_code == 404


class TestGraphAPI:
    """Test graph API endpoints."""

    @pytest.mark.asyncio
    async def test_get_nodes(self, async_client, mock_db):
        """Test getting nodes for a project."""
        with patch("routers.graph.db", mock_db):
            mock_db.fetch.return_value = [
                {
                    "id": "node-1",
                    "entity_type": "Paper",
                    "name": "Test Paper",
                    "properties": {},
                }
            ]

            response = await async_client.get(
                "/api/graph/nodes?project_id=12345678-1234-1234-1234-123456789012"
            )

            assert response.status_code == 200
            nodes = response.json()
            assert isinstance(nodes, list)

    @pytest.mark.asyncio
    async def test_get_edges(self, async_client, mock_db):
        """Test getting edges for a project."""
        with patch("routers.graph.db", mock_db):
            mock_db.fetch.return_value = []

            response = await async_client.get(
                "/api/graph/edges?project_id=12345678-1234-1234-1234-123456789012"
            )

            assert response.status_code == 200
            assert response.json() == []

    @pytest.mark.asyncio
    async def test_search_nodes(self, async_client, mock_db):
        """Test searching nodes."""
        with patch("routers.graph.db", mock_db):
            mock_db.fetch.return_value = []

            response = await async_client.post(
                "/api/graph/search",
                json={
                    "query": "machine learning",
                    "limit": 10,
                },
            )

            assert response.status_code == 200


class TestImportAPI:
    """Test import API endpoints."""

    @pytest.mark.asyncio
    async def test_validate_folder_not_found(self, async_client):
        """Test validating non-existent folder."""
        response = await async_client.post(
            "/api/import/scholarag/validate",
            json={"folder_path": "/nonexistent/path"},
        )

        # Should return validation response with valid=False
        # (unless path security blocks it first)
        assert response.status_code in [200, 403]

    @pytest.mark.asyncio
    async def test_get_import_status_not_found(self, async_client):
        """Test getting status for non-existent job."""
        response = await async_client.get("/api/import/status/nonexistent-job-id")

        assert response.status_code == 404


class TestChatAPI:
    """Test chat API endpoints."""

    @pytest.mark.asyncio
    async def test_chat_requires_project_id(self, async_client):
        """Test that chat endpoint requires project_id."""
        # Chat endpoint is at /api/chat/query
        response = await async_client.post(
            "/api/chat/query",
            json={
                "message": "Hello",
                # Missing project_id
            },
        )

        assert response.status_code == 422  # Validation error


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, async_client):
        """Test root endpoint returns API info."""
        response = await async_client.get("/")

        assert response.status_code == 200
        result = response.json()
        assert "name" in result or "status" in result


class TestSecurityHeaders:
    """Test security-related headers and responses."""

    @pytest.mark.asyncio
    async def test_import_path_traversal_blocked(self, async_client):
        """Test that path traversal attempts are sanitized.

        The ScholaRAGImportRequest.sanitize_path validator removes '..' sequences,
        so the path becomes a valid (but non-existent) path. In development mode
        without ALLOWED_IMPORT_ROOTS, the validation returns valid=False with errors
        instead of blocking with 403.
        """
        # Attempt path traversal
        response = await async_client.post(
            "/api/import/scholarag/validate",
            json={"folder_path": "../../etc/passwd"},
        )

        # In development mode without ALLOWED_IMPORT_ROOTS:
        # - Path is sanitized (.. becomes .)
        # - Validation returns 200 with valid=False (folder not found)
        # In production with ALLOWED_IMPORT_ROOTS:
        # - Path is blocked with 403
        assert response.status_code in [200, 400, 403]
        if response.status_code == 200:
            result = response.json()
            # Path sanitization means the folder won't exist
            assert result["valid"] is False
            # Ensure the path was sanitized (.. replaced with .)
            assert ".." not in result.get("folder_path", "")

    @pytest.mark.asyncio
    async def test_sanitized_error_messages(self, async_client, mock_db):
        """Test that error messages don't leak sensitive info."""
        with patch("routers.projects.db", mock_db):
            # Simulate database error with path in message
            mock_db.fetchrow.side_effect = Exception(
                "Connection failed for /secret/db/path"
            )

            response = await async_client.get(
                "/api/projects/12345678-1234-1234-1234-123456789012"
            )

            # Error response should not contain the path
            if response.status_code >= 400:
                error_text = response.text
                assert "/secret/db/path" not in error_text
