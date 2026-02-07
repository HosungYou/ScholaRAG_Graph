"""
Pytest fixtures for ScholaRAG_Graph tests.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, AsyncMock

# Import app lazily to avoid circular imports
@pytest.fixture
def app():
    """Get FastAPI app instance."""
    from main import app
    return app


@pytest_asyncio.fixture
async def async_client(app):
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_db():
    """Mock database connection."""
    db = MagicMock()
    db.is_connected = True
    db.fetch = AsyncMock(return_value=[])
    db.fetchrow = AsyncMock(return_value=None)
    db.fetchval = AsyncMock(return_value=None)
    db.execute = AsyncMock(return_value="INSERT 0 1")
    db.executemany = AsyncMock(return_value=None)
    return db


@pytest.fixture
def sample_project():
    """Sample project data for testing."""
    return {
        "id": "12345678-1234-1234-1234-123456789012",
        "name": "Test Project",
        "research_question": "How does AI affect education?",
        "source_path": "/test/path",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }


@pytest.fixture
def sample_node():
    """Sample graph node for testing."""
    return {
        "id": "node-12345678-1234-1234-1234-123456789012",
        "entity_type": "Paper",
        "name": "Test Paper Title",
        "properties": {
            "abstract": "This is a test abstract.",
            "year": 2024,
            "doi": "10.1234/test",
        },
    }


@pytest.fixture
def sample_edge():
    """Sample graph edge for testing."""
    return {
        "id": "edge-12345678-1234-1234-1234-123456789012",
        "source": "node-1",
        "target": "node-2",
        "relationship_type": "AUTHORED_BY",
        "properties": {},
        "weight": 1.0,
    }


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    from auth.models import User
    return User(
        id="test-user-123",
        email="test@example.com",
        email_confirmed=True,
        created_at="2024-01-01T00:00:00Z"
    )


@pytest_asyncio.fixture
async def async_client_no_auth(app):
    """Create async HTTP client with no authentication required."""
    from auth.dependencies import require_auth_if_configured
    from unittest.mock import patch

    # Patch settings to disable auth requirement at import time
    with patch("config.settings") as mock_settings:
        mock_settings.require_auth = False

        # Return None to simulate no user
        def no_auth():
            return None

        app.dependency_overrides[require_auth_if_configured] = no_auth

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client_with_auth(app, mock_user):
    """Create async HTTP client with a mock authenticated user."""
    from auth.dependencies import require_auth_if_configured
    from unittest.mock import patch

    # Patch settings but keep require_auth=True (since we have a user)
    with patch("config.settings") as mock_settings:
        mock_settings.require_auth = False  # Don't enforce auth since we're providing a user

        # Simply return the mock user, bypassing all auth checks
        def return_user():
            return mock_user

        app.dependency_overrides[require_auth_if_configured] = return_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        app.dependency_overrides.clear()
