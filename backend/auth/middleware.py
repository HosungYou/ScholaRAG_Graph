"""
Authentication middleware for FastAPI.

Provides request-level authentication policy enforcement based on centralized
policy configuration.

This middleware automatically applies authentication requirements based on
the route being accessed, eliminating the need for manual dependency injection
in each route handler (though route-level dependencies can still override).

Usage:
    from fastapi import FastAPI
    from auth.middleware import AuthMiddleware
    
    app = FastAPI()
    app.add_middleware(AuthMiddleware)
"""

import logging
from typing import Optional, Callable, Awaitable

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .policies import get_auth_level, AuthLevel
from .supabase_client import verify_jwt, supabase_client

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces authentication policies at the request level.
    
    This middleware:
    1. Checks the auth policy for the requested route
    2. Extracts and validates the JWT token if present
    3. Attaches user info to request.state for downstream handlers
    4. Returns 401/403 errors for unauthorized requests
    
    The middleware respects the REQUIRE_AUTH setting for OPTIONAL routes,
    allowing development mode without authentication.
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and enforce authentication policies."""
        path = request.url.path
        method = request.method
        
        # Skip OPTIONS requests (CORS preflight)
        if method == "OPTIONS":
            return await call_next(request)
        
        # Get the auth level for this route
        auth_level = get_auth_level(path)
        
        # Initialize user state
        request.state.user = None
        request.state.user_id = None
        request.state.auth_level = auth_level
        
        # NONE level - no authentication needed
        if auth_level == AuthLevel.NONE:
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        token = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Verify token if present
        user_data = None
        if token:
            try:
                user_data = await verify_jwt(token)
                if user_data:
                    request.state.user = user_data
                    request.state.user_id = user_data.get("id")
            except Exception as e:
                logger.warning(f"Token verification failed: {e}")
        
        # Check authentication requirements
        if auth_level == AuthLevel.REQUIRED:
            if not user_data:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Authentication required"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        elif auth_level == AuthLevel.OPTIONAL:
            # Check if auth is required by configuration
            from config import settings
            
            if settings.require_auth and not user_data:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Authentication required"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # Otherwise, proceed with or without auth
        
        elif auth_level == AuthLevel.OWNER:
            # OWNER level requires both auth and ownership verification
            # Ownership verification is handled by route handlers
            if not user_data:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Authentication required for this resource"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Continue to the route handler
        return await call_next(request)


class AuthPolicyEnforcer:
    """
    Alternative to middleware: a dependency factory that enforces auth policies.
    
    Use this when you need more control over authentication handling in specific
    routes, or when you want to combine with other dependencies.
    
    Usage:
        from auth.middleware import AuthPolicyEnforcer
        
        enforcer = AuthPolicyEnforcer()
        
        @app.get("/api/resource")
        async def get_resource(user = Depends(enforcer.get_dependency("/api/resource"))):
            ...
    """
    
    def __init__(self):
        self._cache: dict = {}
    
    def get_dependency(self, path: str) -> Callable:
        """
        Get the appropriate authentication dependency for a path.
        
        Args:
            path: The route path
            
        Returns:
            A FastAPI dependency function
        """
        if path in self._cache:
            return self._cache[path]
        
        level = get_auth_level(path)
        
        if level == AuthLevel.NONE:
            dep = self._no_auth_dependency
        elif level == AuthLevel.REQUIRED:
            dep = self._require_auth_dependency
        elif level == AuthLevel.OWNER:
            dep = self._require_owner_dependency
        else:
            dep = self._optional_auth_dependency
        
        self._cache[path] = dep
        return dep
    
    async def _no_auth_dependency(self) -> None:
        """No authentication required."""
        return None
    
    async def _require_auth_dependency(self, request: Request):
        """Authentication always required."""
        from .dependencies import get_current_user
        from fastapi import Depends
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        
        security = HTTPBearer(auto_error=True)
        credentials = await security(request)
        return await get_current_user(credentials)
    
    async def _optional_auth_dependency(self, request: Request):
        """Authentication based on configuration."""
        from .dependencies import get_current_user_if_required
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        
        security = HTTPBearer(auto_error=False)
        credentials = await security(request)
        return await get_current_user_if_required(credentials)
    
    async def _require_owner_dependency(self, request: Request):
        """Authentication required with ownership verification pending."""
        # First ensure authentication
        user = await self._require_auth_dependency(request)
        # Ownership verification must be done in the route handler
        # as it requires knowledge of the resource being accessed
        return user


def get_user_from_request(request: Request) -> Optional[dict]:
    """
    Get the authenticated user from request state.
    
    Use this in route handlers after the middleware has processed the request.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        User data dict or None if not authenticated
    """
    return getattr(request.state, "user", None)


def get_user_id_from_request(request: Request) -> Optional[str]:
    """
    Get the authenticated user's ID from request state.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        User ID string or None if not authenticated
    """
    return getattr(request.state, "user_id", None)


def require_auth_from_request(request: Request) -> dict:
    """
    Get the authenticated user from request state, raising if not authenticated.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        User data dict
        
    Raises:
        HTTPException: If user is not authenticated
    """
    user = get_user_from_request(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
