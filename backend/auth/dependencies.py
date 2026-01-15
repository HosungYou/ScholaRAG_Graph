"""
Authentication dependencies for FastAPI.

Provides dependency injection for user authentication in route handlers.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .supabase_client import supabase_client, verify_jwt
from .models import User

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """
    Get the current authenticated user.
    
    Raises HTTPException 401 if not authenticated.
    """
    if not supabase_client.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_data = await verify_jwt(credentials.credentials)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return User(
        id=user_data["id"],
        email=user_data["email"],
        email_confirmed=user_data["email_confirmed"],
        created_at=user_data.get("created_at"),
        full_name=user_data.get("user_metadata", {}).get("full_name"),
        avatar_url=user_data.get("user_metadata", {}).get("avatar_url"),
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Get the current user if authenticated, None otherwise.
    
    Does not raise exceptions for missing/invalid tokens.
    """
    if not supabase_client.is_configured():
        return None
    
    if not credentials:
        return None
    
    user_data = await verify_jwt(credentials.credentials)
    
    if not user_data:
        return None
    
    return User(
        id=user_data["id"],
        email=user_data["email"],
        email_confirmed=user_data["email_confirmed"],
        created_at=user_data.get("created_at"),
        full_name=user_data.get("user_metadata", {}).get("full_name"),
        avatar_url=user_data.get("user_metadata", {}).get("avatar_url"),
    )


def require_auth(user: User = Depends(get_current_user)) -> User:
    """
    Dependency that requires authentication.
    
    Alias for get_current_user for semantic clarity.
    """
    return user


def require_verified_email(user: User = Depends(get_current_user)) -> User:
    """
    Dependency that requires a verified email address.
    """
    if not user.email_confirmed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return user


# =============================================================================
# Configurable Auth Dependencies (based on settings.require_auth)
# =============================================================================

async def get_current_user_if_required(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Get current user if authentication is required by settings.

    In development mode with require_auth=False, returns None.
    In production mode, enforces authentication.
    """
    from config import settings

    if not settings.require_auth:
        # Development mode: auth optional
        if credentials:
            return await get_optional_user(credentials)
        return None

    # Production mode: auth required
    return await get_current_user(credentials)


def require_auth_if_configured(
    user: Optional[User] = Depends(get_current_user_if_required)
) -> Optional[User]:
    """
    Dependency that requires auth based on configuration.

    Use this for endpoints that should be protected in production
    but accessible without auth in development.
    """
    from config import settings

    if settings.require_auth and user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# =============================================================================
# Policy-Based Auth Dependencies
# =============================================================================

def get_auth_dependency_for_route(path: str):
    """
    Returns appropriate auth dependency based on route policy.
    
    This function provides a factory for creating route-specific authentication
    dependencies based on the centralized policy configuration.
    
    Args:
        path: The route path (e.g., "/api/projects")
        
    Returns:
        A FastAPI dependency function appropriate for the route's auth level.
        
    Example:
        @router.get("/custom-endpoint")
        async def custom_endpoint(
            user = Depends(get_auth_dependency_for_route("/api/custom-endpoint"))
        ):
            ...
    """
    from .policies import get_auth_level, AuthLevel
    
    level = get_auth_level(path)
    
    if level == AuthLevel.NONE:
        return _no_auth
    elif level == AuthLevel.REQUIRED:
        return require_auth
    elif level == AuthLevel.OWNER:
        return require_auth  # Ownership check done separately
    else:  # OPTIONAL
        return require_auth_if_configured


async def _no_auth() -> None:
    """No authentication required - returns None."""
    return None


def get_policy_based_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    path: str = None
) -> Optional[User]:
    """
    Get user based on the auth policy for the current route.
    
    Note: This is a lower-level function. For most use cases,
    use the specific dependency functions or get_auth_dependency_for_route().
    """
    from .policies import get_auth_level, AuthLevel
    
    if path is None:
        # Fall back to optional behavior if path not provided
        return require_auth_if_configured
    
    level = get_auth_level(path)
    
    if level == AuthLevel.NONE:
        return None
    elif level == AuthLevel.REQUIRED or level == AuthLevel.OWNER:
        return require_auth
    else:
        return require_auth_if_configured


# =============================================================================
# Request State Helpers (for use with AuthMiddleware)
# =============================================================================

def get_user_from_state(request) -> Optional[User]:
    """
    Get authenticated user from request state (set by AuthMiddleware).
    
    This is useful when the middleware has already validated the token
    and you just need to access the user data.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        User object or None if not authenticated
    """
    user_data = getattr(request.state, "user", None)
    
    if not user_data:
        return None
    
    return User(
        id=user_data["id"],
        email=user_data["email"],
        email_confirmed=user_data.get("email_confirmed", False),
        created_at=user_data.get("created_at"),
        full_name=user_data.get("user_metadata", {}).get("full_name"),
        avatar_url=user_data.get("user_metadata", {}).get("avatar_url"),
    )


def require_user_from_state(request) -> User:
    """
    Get authenticated user from request state, raising if not present.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        User object
        
    Raises:
        HTTPException 401 if user not in state
    """
    user = get_user_from_state(request)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user
