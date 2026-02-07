"""
Comprehensive tests for settings router.

Tests API key management, LLM provider configuration, and validation endpoints.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

# Import specific functions to avoid shadowing config.settings
from routers import settings as settings_router


# ============================================
# Unit Tests: mask_api_key()
# ============================================

class TestMaskApiKey:
    """Test API key masking utility function."""

    def test_normal_key_long(self):
        """Test masking a normal length key (>8 chars)."""
        result = settings_router.mask_api_key("gsk_1234567890abcdef")
        assert result == "gsk_****def"

    def test_normal_key_exact_length(self):
        """Test masking a key with exactly enough length."""
        result = settings_router.mask_api_key("sk-ant-1234567890")
        assert result == "sk-a****890"

    def test_short_key(self):
        """Test masking a short key (<8 chars)."""
        result = settings_router.mask_api_key("short")
        assert result == "****"

    def test_empty_string(self):
        """Test masking an empty string."""
        result = settings_router.mask_api_key("")
        assert result == ""

    def test_exact_boundary_8_chars(self):
        """Test masking a key with exactly 8 characters."""
        result = settings_router.mask_api_key("12345678")
        assert result == "1234****678"

    def test_exact_boundary_7_chars(self):
        """Test masking a key with 7 characters (just below boundary)."""
        result = settings_router.mask_api_key("1234567")
        assert result == "****"

    def test_very_long_key(self):
        """Test masking a very long API key."""
        long_key = "sk-proj-" + "x" * 100
        result = settings_router.mask_api_key(long_key)
        assert result.startswith("sk-p")
        assert result.endswith("xxx")
        assert "****" in result


# ============================================
# Unit Tests: get_server_api_key()
# ============================================

class TestGetServerApiKey:
    """Test server API key retrieval utility."""

    @patch("routers.settings.settings")
    def test_groq_provider(self, mock_settings):
        """Test retrieving Groq API key."""
        mock_settings.groq_api_key = "gsk_test123"
        result = settings_router.get_server_api_key("groq")
        assert result == "gsk_test123"

    @patch("routers.settings.settings")
    def test_anthropic_provider(self, mock_settings):
        """Test retrieving Anthropic API key."""
        mock_settings.anthropic_api_key = "sk-ant-test"
        result = settings_router.get_server_api_key("anthropic")
        assert result == "sk-ant-test"

    @patch("routers.settings.settings")
    def test_openai_provider(self, mock_settings):
        """Test retrieving OpenAI API key."""
        mock_settings.openai_api_key = "sk-test123"
        result = settings_router.get_server_api_key("openai")
        assert result == "sk-test123"

    @patch("routers.settings.settings")
    def test_google_provider(self, mock_settings):
        """Test retrieving Google API key."""
        mock_settings.google_api_key = "google_test_key"
        result = settings_router.get_server_api_key("google")
        assert result == "google_test_key"

    @patch("routers.settings.settings")
    def test_semantic_scholar_provider(self, mock_settings):
        """Test retrieving Semantic Scholar API key."""
        mock_settings.semantic_scholar_api_key = "s2_test_key"
        result = settings_router.get_server_api_key("semantic_scholar")
        assert result == "s2_test_key"

    @patch("routers.settings.settings")
    def test_cohere_provider(self, mock_settings):
        """Test retrieving Cohere API key."""
        mock_settings.cohere_api_key = "cohere_test_key"
        result = settings_router.get_server_api_key("cohere")
        assert result == "cohere_test_key"

    @patch("routers.settings.settings")
    def test_unknown_provider(self, mock_settings):
        """Test retrieving API key for unknown provider returns empty string."""
        result = settings_router.get_server_api_key("unknown_provider")
        assert result == ""

    @patch("routers.settings.settings")
    def test_empty_provider(self, mock_settings):
        """Test retrieving API key with empty provider name."""
        result = settings_router.get_server_api_key("")
        assert result == ""


# ============================================
# Unit Tests: Pydantic Models
# ============================================

class TestPydanticModels:
    """Test Pydantic model validation."""

    def test_api_key_info_validation(self):
        """Test ApiKeyInfo model validation."""
        info = settings_router.ApiKeyInfo(
            provider="groq",
            display_name="Groq",
            is_set=True,
            masked_key="gsk_****123",
            source="user",
            usage="LLM"
        )
        assert info.provider == "groq"
        assert info.is_set is True
        assert info.source == "user"

    def test_api_key_info_none_masked_key(self):
        """Test ApiKeyInfo with None masked_key."""
        info = settings_router.ApiKeyInfo(
            provider="groq",
            display_name="Groq",
            is_set=False,
            masked_key=None,
            source="none",
            usage="LLM"
        )
        assert info.masked_key is None

    def test_api_key_validation_request(self):
        """Test ApiKeyValidationRequest model."""
        request = settings_router.ApiKeyValidationRequest(
            provider="groq",
            key="gsk_test123"
        )
        assert request.provider == "groq"
        assert request.key == "gsk_test123"

    def test_api_key_validation_response(self):
        """Test ApiKeyValidationResponse model."""
        response = settings_router.ApiKeyValidationResponse(
            valid=True,
            message="API key is valid"
        )
        assert response.valid is True
        assert response.message == "API key is valid"


# ============================================
# Integration Tests: GET /api/settings/api-keys
# ============================================

class TestGetApiKeys:
    """Test GET /api/settings/api-keys endpoint."""

    @pytest.mark.asyncio
    @patch("routers.settings.db")
    @patch("routers.settings.get_server_api_key")
    async def test_returns_all_providers(self, mock_get_server_key, mock_db, async_client_no_auth):
        """Test endpoint returns all 6 providers."""
        # Mock no user authentication
        mock_db.fetch_one = AsyncMock(return_value=None)
        mock_get_server_key.return_value = ""

        response = await async_client_no_auth.get("/api/settings/api-keys")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 6
        provider_ids = [item["provider"] for item in data]
        assert "groq" in provider_ids
        assert "anthropic" in provider_ids
        assert "openai" in provider_ids
        assert "semantic_scholar" in provider_ids

    @pytest.mark.asyncio
    @patch("routers.settings.db")
    @patch("routers.settings.get_server_api_key")
    async def test_user_key_priority(self, mock_get_server_key, mock_db, async_client_with_auth, mock_user):
        """Test user key takes priority over server key."""
        # Mock user with preferences
        mock_db.fetch_one = AsyncMock(return_value={
            "preferences": {
                "api_keys": {
                    "groq": "gsk_user_key"
                }
            }
        })
        mock_get_server_key.side_effect = lambda p: "gsk_server_key" if p == "groq" else ""

        response = await async_client_with_auth.get("/api/settings/api-keys")

        assert response.status_code == 200
        data = response.json()
        groq_entry = next(item for item in data if item["provider"] == "groq")
        assert groq_entry["source"] == "user"
        assert groq_entry["masked_key"] == "gsk_****key"

    @pytest.mark.asyncio
    @patch("routers.settings.db")
    @patch("routers.settings.get_server_api_key")
    async def test_server_only_key(self, mock_get_server_key, mock_db, async_client_with_auth, mock_user):
        """Test server-only key shows source='server'."""
        # Mock no user key
        mock_db.fetch_one = AsyncMock(return_value={
            "preferences": {"api_keys": {}}
        })
        mock_get_server_key.side_effect = lambda p: "gsk_server_key" if p == "groq" else ""

        response = await async_client_with_auth.get("/api/settings/api-keys")

        assert response.status_code == 200
        data = response.json()
        groq_entry = next(item for item in data if item["provider"] == "groq")
        assert groq_entry["source"] == "server"
        assert groq_entry["is_set"] is True

    @pytest.mark.asyncio
    @patch("routers.settings.db")
    @patch("routers.settings.get_server_api_key")
    async def test_no_key_set(self, mock_get_server_key, mock_db, async_client_with_auth, mock_user):
        """Test provider with no key shows is_set=False."""
        mock_db.fetch_one = AsyncMock(return_value={
            "preferences": {"api_keys": {}}
        })
        mock_get_server_key.return_value = ""

        response = await async_client_with_auth.get("/api/settings/api-keys")

        assert response.status_code == 200
        data = response.json()
        assert all(item["is_set"] is False for item in data)
        assert all(item["source"] == "none" for item in data)


# ============================================
# Integration Tests: PUT /api/settings/api-keys
# ============================================

class TestUpdateApiKeys:
    """Test PUT /api/settings/api-keys endpoint."""

    @pytest.mark.asyncio
    async def test_requires_authentication(self, async_client_no_auth):
        """Test endpoint requires authentication."""
        response = await async_client_no_auth.put(
            "/api/settings/api-keys",
            json={"groq": "gsk_test"}
        )

        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch("routers.settings.db")
    async def test_updates_api_keys(self, mock_db, async_client_with_auth, mock_user):
        """Test updating API keys in preferences."""
        # Mock current preferences
        mock_db.fetch_one = AsyncMock(return_value={
            "preferences": {"api_keys": {}}
        })
        mock_db.execute = AsyncMock()

        response = await async_client_with_auth.put(
            "/api/settings/api-keys",
            json={"groq": "gsk_new_key"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Verify database update was called
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        assert "UPDATE user_profiles" in call_args[0][0]
        assert call_args[0][1] == mock_user.id

    @pytest.mark.asyncio
    @patch("routers.settings.db")
    async def test_empty_string_deletes_key(self, mock_db, async_client_with_auth, mock_user):
        """Test empty string deletes API key."""
        # Mock existing key
        mock_db.fetch_one = AsyncMock(return_value={
            "preferences": {"api_keys": {"groq": "gsk_old_key"}}
        })
        mock_db.execute = AsyncMock()

        response = await async_client_with_auth.put(
            "/api/settings/api-keys",
            json={"groq": ""}
        )

        assert response.status_code == 200

        # Verify key was removed
        call_args = mock_db.execute.call_args
        saved_prefs = call_args[0][2]
        assert "groq" not in saved_prefs.get("api_keys", {})

    @pytest.mark.asyncio
    @patch("routers.settings.db")
    async def test_updates_llm_provider(self, mock_db, async_client_with_auth, mock_user):
        """Test updating LLM provider preference."""
        mock_db.fetch_one = AsyncMock(return_value={
            "preferences": {}
        })
        mock_db.execute = AsyncMock()

        response = await async_client_with_auth.put(
            "/api/settings/api-keys",
            json={
                "llm_provider": "anthropic",
                "llm_model": "claude-3-opus-20240229"
            }
        )

        assert response.status_code == 200

        # Verify LLM settings were saved
        call_args = mock_db.execute.call_args
        saved_prefs = call_args[0][2]
        assert saved_prefs["llm_provider"] == "anthropic"
        assert saved_prefs["llm_model"] == "claude-3-opus-20240229"

    @pytest.mark.asyncio
    @patch("routers.settings.db")
    async def test_database_error_handling(self, mock_db, async_client_with_auth, mock_user):
        """Test handling of database errors."""
        mock_db.fetch_one = AsyncMock(side_effect=Exception("Database error"))

        response = await async_client_with_auth.put(
            "/api/settings/api-keys",
            json={"groq": "gsk_test"}
        )

        assert response.status_code == 500
        assert "Failed to update API keys" in response.json()["detail"]


# ============================================
# Integration Tests: POST /api/settings/api-keys/validate
# ============================================

class TestValidateApiKey:
    """Test POST /api/settings/api-keys/validate endpoint."""

    @pytest.mark.asyncio
    async def test_empty_key_returns_invalid(self, async_client_no_auth):
        """Test empty key returns invalid response."""
        response = await async_client_no_auth.post(
            "/api/settings/api-keys/validate",
            json={"provider": "groq", "key": ""}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "cannot be empty" in data["message"]

    @pytest.mark.asyncio
    async def test_groq_valid_format(self, async_client_no_auth):
        """Test Groq key format validation (starts with gsk_)."""
        response = await async_client_no_auth.post(
            "/api/settings/api-keys/validate",
            json={"provider": "groq", "key": "gsk_test123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "valid" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_groq_invalid_format(self, async_client_no_auth):
        """Test Groq key with invalid format."""
        response = await async_client_no_auth.post(
            "/api/settings/api-keys/validate",
            json={"provider": "groq", "key": "invalid_key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "gsk_" in data["message"]

    @pytest.mark.asyncio
    async def test_anthropic_valid_format(self, async_client_no_auth):
        """Test Anthropic key format validation (starts with sk-ant-)."""
        response = await async_client_no_auth.post(
            "/api/settings/api-keys/validate",
            json={"provider": "anthropic", "key": "sk-ant-test123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_anthropic_invalid_format(self, async_client_no_auth):
        """Test Anthropic key with invalid format."""
        response = await async_client_no_auth.post(
            "/api/settings/api-keys/validate",
            json={"provider": "anthropic", "key": "invalid"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "sk-ant-" in data["message"]

    @pytest.mark.asyncio
    async def test_openai_valid_format(self, async_client_no_auth):
        """Test OpenAI key format validation (starts with sk-)."""
        response = await async_client_no_auth.post(
            "/api/settings/api-keys/validate",
            json={"provider": "openai", "key": "sk-test123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_openai_invalid_format(self, async_client_no_auth):
        """Test OpenAI key with invalid format."""
        response = await async_client_no_auth.post(
            "/api/settings/api-keys/validate",
            json={"provider": "openai", "key": "invalid"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "sk-" in data["message"]

    @pytest.mark.asyncio
    async def test_google_valid_format(self, async_client_no_auth):
        """Test Google key format validation (length check)."""
        long_key = "x" * 25
        response = await async_client_no_auth.post(
            "/api/settings/api-keys/validate",
            json={"provider": "google", "key": long_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_google_invalid_format(self, async_client_no_auth):
        """Test Google key with invalid format (too short)."""
        response = await async_client_no_auth.post(
            "/api/settings/api-keys/validate",
            json={"provider": "google", "key": "short"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "too short" in data["message"]

    @pytest.mark.asyncio
    async def test_cohere_valid_format(self, async_client_no_auth):
        """Test Cohere key format validation (length check)."""
        long_key = "x" * 25
        response = await async_client_no_auth.post(
            "/api/settings/api-keys/validate",
            json={"provider": "cohere", "key": long_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_unknown_provider(self, async_client_no_auth):
        """Test validation with unknown provider."""
        response = await async_client_no_auth.post(
            "/api/settings/api-keys/validate",
            json={"provider": "unknown", "key": "test"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "Unknown provider" in data["message"]

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_semantic_scholar_real_validation(self, mock_httpx_client, async_client_no_auth):
        """Test Semantic Scholar validation with real API call."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock()

        mock_httpx_client.return_value = mock_client_instance

        response = await async_client_no_auth.post(
            "/api/settings/api-keys/validate",
            json={"provider": "semantic_scholar", "key": "s2_test_key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_semantic_scholar_invalid_key(self, mock_httpx_client, async_client_no_auth):
        """Test Semantic Scholar validation with invalid key."""
        # Mock failed API response
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock()

        mock_httpx_client.return_value = mock_client_instance

        response = await async_client_no_auth.post(
            "/api/settings/api-keys/validate",
            json={"provider": "semantic_scholar", "key": "invalid_key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "status 401" in data["message"]

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_validation_timeout(self, mock_httpx_client, async_client_no_auth):
        """Test validation handles timeout errors."""
        from httpx import TimeoutException

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(side_effect=TimeoutException("Timeout"))
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        mock_httpx_client.return_value = mock_client_instance

        response = await async_client_no_auth.post(
            "/api/settings/api-keys/validate",
            json={"provider": "semantic_scholar", "key": "test_key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "timed out" in data["message"].lower()
