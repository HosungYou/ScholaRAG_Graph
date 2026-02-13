"""
Supabase client initialization for ScholaRAG_Graph.

Handles connection to Supabase for authentication and database operations.
"""

import logging
import base64
import json
import time
from typing import Optional

from supabase import create_client, Client

logger = logging.getLogger(__name__)


def _extract_jwt_payload(token: str) -> dict:
    """Decode JWT payload without signature verification for diagnostics only."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload + padding)
        return json.loads(decoded.decode("utf-8"))
    except Exception:
        return {}


class SupabaseClient:
    """Singleton wrapper for Supabase client."""
    
    _client: Optional[Client] = None
    _url: Optional[str] = None
    _key: Optional[str] = None
    
    @classmethod
    def initialize(cls, url: str, key: str) -> None:
        """Initialize the Supabase client."""
        if not url or not key:
            logger.warning("Supabase credentials not provided. Auth will be disabled.")
            return

        cls._url = url
        cls._key = key
        cls._client = create_client(url, key)
        logger.info(f"Supabase client initialized: {url[:30]}...")

        # Pre-validate the anon key by making a lightweight auth call
        try:
            cls._client.auth.get_user("dummy-token-for-key-validation")
        except Exception as e:
            err_msg = str(e)
            if "Invalid API key" in err_msg:
                logger.critical(
                    "SUPABASE_ANON_KEY is INVALID — Supabase rejected the API key itself. "
                    "All auth requests will fail until the correct key is set. "
                    "Key prefix: %s...",
                    key[:20],
                )
            else:
                # Expected: dummy token will fail with auth error, not API key error
                logger.debug("Anon key validation passed (dummy token rejected as expected)")
    
    @classmethod
    def get_client(cls) -> Optional[Client]:
        """Get the Supabase client instance."""
        return cls._client
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if Supabase is properly configured."""
        return cls._client is not None


# Global instance
supabase_client = SupabaseClient()


def get_supabase() -> Optional[Client]:
    """Dependency to get Supabase client."""
    return supabase_client.get_client()


async def verify_jwt(token: str) -> Optional[dict]:
    """
    Verify a JWT token with Supabase.
    
    Args:
        token: The JWT token to verify
        
    Returns:
        User data if valid, None otherwise
    """
    client = supabase_client.get_client()
    if not client:
        return None
    
    try:
        # Get user from token
        response = client.auth.get_user(token)
        if response and response.user:
            return {
                "id": response.user.id,
                "email": response.user.email,
                "email_confirmed": response.user.email_confirmed_at is not None,
                "created_at": response.user.created_at,
                "user_metadata": response.user.user_metadata or {},
            }
    except Exception as e:
        err_msg = str(e)
        if "Invalid API key" in err_msg:
            logger.critical(
                "JWT verification failed: Invalid API key — the SUPABASE_ANON_KEY "
                "used to initialize the client is rejected by Supabase. "
                "This is NOT a user token issue. Fix the backend env var. "
                "Key prefix: %s...",
                (supabase_client._key or "")[:20],
            )
        else:
            payload = _extract_jwt_payload(token)
            token_iss = payload.get("iss")
            token_exp = payload.get("exp")

            configured_url = getattr(supabase_client, "_url", None)
            expected_iss_prefix = f"{configured_url.rstrip('/')}/auth/v1" if configured_url else None

            if token_iss and expected_iss_prefix and not str(token_iss).startswith(expected_iss_prefix):
                logger.warning(
                    "JWT verification failed: token issuer mismatch "
                    "(token_iss=%s, expected_prefix=%s)",
                    token_iss,
                    expected_iss_prefix,
                )
            elif isinstance(token_exp, (int, float)) and int(token_exp) < int(time.time()):
                logger.info(
                    "JWT verification failed: token expired (exp=%s, now=%s)",
                    int(token_exp),
                    int(time.time()),
                )
            else:
                logger.warning("JWT verification failed: %s", e)
    
    return None
