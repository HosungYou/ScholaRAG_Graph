"""
Settings router for ScholaRAG_Graph.

Handles API key management, LLM provider configuration, and user preferences.
"""

import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel

from fastapi import APIRouter, Body, Depends, HTTPException, status
import httpx

from auth.dependencies import require_auth_if_configured
from auth.models import User
from config import settings
from database import db

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# Provider Definitions
# ============================================

API_KEY_PROVIDERS = [
    {"id": "groq", "display_name": "Groq", "env_key": "groq_api_key", "usage": "LLM (기본 provider)"},
    {"id": "anthropic", "display_name": "Anthropic (Claude)", "env_key": "anthropic_api_key", "usage": "LLM"},
    {"id": "openai", "display_name": "OpenAI", "env_key": "openai_api_key", "usage": "LLM + Embeddings"},
    {"id": "google", "display_name": "Google (Gemini)", "env_key": "google_api_key", "usage": "LLM"},
    {"id": "semantic_scholar", "display_name": "Semantic Scholar", "env_key": "semantic_scholar_api_key", "usage": "Citation Network"},
    {"id": "cohere", "display_name": "Cohere", "env_key": "cohere_api_key", "usage": "Embeddings"},
]


# ============================================
# Request/Response Models
# ============================================

class ApiKeyInfo(BaseModel):
    """API key information for a provider."""
    provider: str
    display_name: str
    is_set: bool
    masked_key: Optional[str]
    source: str  # "user" or "server"
    usage: str


class ApiKeyValidationRequest(BaseModel):
    """Request to validate an API key."""
    provider: str
    key: str


class ApiKeyValidationResponse(BaseModel):
    """Response from API key validation."""
    valid: bool
    message: str


# ============================================
# Utility Functions
# ============================================

def mask_api_key(key: str) -> str:
    """
    Mask an API key for display.
    Shows first 4 chars + **** + last 3 chars.
    If key < 8 chars, just shows ****.
    """
    if not key:
        return ""

    if len(key) < 8:
        return "****"

    return f"{key[:4]}****{key[-3:]}"


def get_server_api_key(provider: str) -> Optional[str]:
    """Get API key from server settings."""
    key_mapping = {
        "groq": settings.groq_api_key,
        "anthropic": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "google": settings.google_api_key,
        "semantic_scholar": settings.semantic_scholar_api_key,
        "cohere": settings.cohere_api_key,
    }
    return key_mapping.get(provider, "")


# ============================================
# API Endpoints
# ============================================

@router.get("/api-keys", response_model=list[ApiKeyInfo])
async def get_api_keys(
    current_user: Optional[User] = Depends(require_auth_if_configured)
):
    """
    Get API key information for all providers.

    Returns information about which keys are set (user vs server),
    with masked key values for security.
    """
    result = []

    # Get user preferences if authenticated
    user_preferences = {}
    if current_user:
        try:
            row = await db.fetch_one(
                "SELECT preferences FROM user_profiles WHERE id = $1",
                current_user.id
            )
            if row and row["preferences"]:
                user_preferences = row["preferences"].get("api_keys", {})
        except Exception as e:
            logger.error(f"Error fetching user preferences: {e}")

    # Build response for each provider
    for provider_info in API_KEY_PROVIDERS:
        provider_id = provider_info["id"]

        # Check user key first
        user_key = user_preferences.get(provider_id, "")
        server_key = get_server_api_key(provider_id)

        if user_key:
            # User has their own key
            result.append(ApiKeyInfo(
                provider=provider_id,
                display_name=provider_info["display_name"],
                is_set=True,
                masked_key=mask_api_key(user_key),
                source="user",
                usage=provider_info["usage"]
            ))
        elif server_key:
            # Using server default key
            result.append(ApiKeyInfo(
                provider=provider_id,
                display_name=provider_info["display_name"],
                is_set=True,
                masked_key=mask_api_key(server_key),
                source="server",
                usage=provider_info["usage"]
            ))
        else:
            # No key set
            result.append(ApiKeyInfo(
                provider=provider_id,
                display_name=provider_info["display_name"],
                is_set=False,
                masked_key=None,
                source="none",
                usage=provider_info["usage"]
            ))

    return result


@router.put("/api-keys")
async def update_api_keys(
    request_body: Dict[str, Any] = Body(...),
    current_user: Optional[User] = Depends(require_auth_if_configured)
):
    """
    Update API keys for the current user.

    Empty string for a key means delete that key (fallback to server default).
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to update API keys"
        )

    try:
        # Extract LLM settings from flat body
        llm_provider = request_body.pop("llm_provider", None)
        llm_model = request_body.pop("llm_model", None)
        api_keys = request_body  # Remaining keys are API keys

        # Build preferences update
        preferences_update: Dict[str, Any] = {}

        # Process API keys
        # Track which keys to delete (empty string = delete)
        keys_to_delete = []
        if api_keys:
            api_keys_update = {}
            for provider, key in api_keys.items():
                if key:  # Non-empty string = set key
                    api_keys_update[provider] = key
                else:  # Empty string = mark for deletion
                    keys_to_delete.append(provider)

            if api_keys_update:
                preferences_update["api_keys"] = api_keys_update

        # Process LLM provider/model
        if llm_provider:
            preferences_update["llm_provider"] = llm_provider

        if llm_model:
            preferences_update["llm_model"] = llm_model

        # Handle key deletions (empty strings)
        # We need to read current preferences and selectively update
        current_prefs = {}
        row = await db.fetch_one(
            "SELECT preferences FROM user_profiles WHERE id = $1",
            current_user.id
        )
        if row and row["preferences"]:
            current_prefs = row["preferences"]

        # Merge updates
        merged_prefs = {**current_prefs}

        # Update API keys (handle both additions and deletions)
        if "api_keys" in preferences_update or keys_to_delete:
            current_api_keys = current_prefs.get("api_keys", {})
            new_keys = preferences_update.get("api_keys", {})
            updated_api_keys = {**current_api_keys, **new_keys}

            # Remove keys that were set to empty string
            for provider in keys_to_delete:
                if provider in updated_api_keys:
                    del updated_api_keys[provider]

            merged_prefs["api_keys"] = updated_api_keys

        # Update LLM settings
        if "llm_provider" in preferences_update:
            merged_prefs["llm_provider"] = preferences_update["llm_provider"]
        if "llm_model" in preferences_update:
            merged_prefs["llm_model"] = preferences_update["llm_model"]

        # Save to database
        await db.execute(
            """
            UPDATE user_profiles
            SET preferences = $2::jsonb
            WHERE id = $1
            """,
            current_user.id,
            merged_prefs
        )

        return {"status": "success", "message": "API keys updated successfully"}

    except Exception as e:
        logger.error(f"Error updating API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update API keys: {str(e)}"
        )


@router.post("/api-keys/validate", response_model=ApiKeyValidationResponse)
async def validate_api_key(
    request: ApiKeyValidationRequest,
    current_user: Optional[User] = Depends(require_auth_if_configured)
):
    """
    Validate an API key for a specific provider.

    Makes a lightweight test request to verify the key works.
    """
    provider = request.provider
    key = request.key

    if not key:
        return ApiKeyValidationResponse(
            valid=False,
            message="API key cannot be empty"
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:

            # Semantic Scholar validation
            if provider == "semantic_scholar":
                response = await client.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params={"query": "test", "limit": 1},
                    headers={"x-api-key": key}
                )
                if response.status_code == 200:
                    return ApiKeyValidationResponse(
                        valid=True,
                        message="Semantic Scholar API key is valid"
                    )
                else:
                    return ApiKeyValidationResponse(
                        valid=False,
                        message=f"Invalid API key (status {response.status_code})"
                    )

            # Groq validation (basic format check)
            elif provider == "groq":
                if key.startswith("gsk_"):
                    return ApiKeyValidationResponse(
                        valid=True,
                        message="Groq API key format is valid"
                    )
                else:
                    return ApiKeyValidationResponse(
                        valid=False,
                        message="Groq API key should start with 'gsk_'"
                    )

            # Anthropic validation (basic format check)
            elif provider == "anthropic":
                if key.startswith("sk-ant-"):
                    return ApiKeyValidationResponse(
                        valid=True,
                        message="Anthropic API key format is valid"
                    )
                else:
                    return ApiKeyValidationResponse(
                        valid=False,
                        message="Anthropic API key should start with 'sk-ant-'"
                    )

            # OpenAI validation (basic format check)
            elif provider == "openai":
                if key.startswith("sk-"):
                    return ApiKeyValidationResponse(
                        valid=True,
                        message="OpenAI API key format is valid"
                    )
                else:
                    return ApiKeyValidationResponse(
                        valid=False,
                        message="OpenAI API key should start with 'sk-'"
                    )

            # Google validation (basic format check)
            elif provider == "google":
                if len(key) > 20:  # Google API keys are typically long
                    return ApiKeyValidationResponse(
                        valid=True,
                        message="Google API key format is valid"
                    )
                else:
                    return ApiKeyValidationResponse(
                        valid=False,
                        message="Google API key appears too short"
                    )

            # Cohere validation (basic format check)
            elif provider == "cohere":
                if len(key) > 20:
                    return ApiKeyValidationResponse(
                        valid=True,
                        message="Cohere API key format is valid"
                    )
                else:
                    return ApiKeyValidationResponse(
                        valid=False,
                        message="Cohere API key appears too short"
                    )

            else:
                return ApiKeyValidationResponse(
                    valid=False,
                    message=f"Unknown provider: {provider}"
                )

    except httpx.TimeoutException:
        return ApiKeyValidationResponse(
            valid=False,
            message="Request timed out - please try again"
        )
    except Exception as e:
        logger.error(f"Error validating API key for {provider}: {e}")
        return ApiKeyValidationResponse(
            valid=False,
            message=f"Validation error: {str(e)}"
        )
