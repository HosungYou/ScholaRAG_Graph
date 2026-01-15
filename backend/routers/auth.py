"""
Authentication router for ScholaRAG_Graph.

Handles user registration, login, logout, and profile management.
"""

import logging
import os
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status, Response
from gotrue.errors import AuthApiError

from auth.supabase_client import get_supabase
from auth.dependencies import get_current_user, get_optional_user
from auth.models import (
    User,
    UserCreate,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordUpdateRequest,
    ProfileUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Security: Allowed redirect domains for OAuth
# =============================================================================

def get_allowed_redirect_hosts() -> set:
    """
    Get the set of allowed redirect hosts for OAuth.

    Includes localhost for development and configured frontend URLs.
    """
    allowed = {
        "localhost",
        "127.0.0.1",
    }

    # Add frontend URL from environment if configured
    frontend_url = os.getenv("FRONTEND_URL", "")
    if frontend_url:
        try:
            parsed = urlparse(frontend_url)
            if parsed.netloc:
                allowed.add(parsed.netloc.split(":")[0])  # Strip port
        except Exception:
            pass

    # Add additional allowed hosts from environment (comma-separated)
    extra_hosts = os.getenv("ALLOWED_REDIRECT_HOSTS", "")
    if extra_hosts:
        for host in extra_hosts.split(","):
            host = host.strip()
            if host:
                allowed.add(host)

    return allowed


def validate_redirect_url(redirect_to: Optional[str]) -> Optional[str]:
    """
    Validate and sanitize a redirect URL to prevent open redirect attacks.

    Returns:
        - The original URL if it's a safe relative path or allowed host
        - None if the URL is invalid or points to an untrusted host
    """
    if not redirect_to:
        return None

    # Allow relative paths (must start with /)
    if redirect_to.startswith("/") and not redirect_to.startswith("//"):
        return redirect_to

    # Parse the URL for absolute URLs
    try:
        parsed = urlparse(redirect_to)

        # Reject URLs without scheme (could be protocol-relative like //evil.com)
        if not parsed.scheme:
            return None

        # Only allow http and https schemes
        if parsed.scheme not in ("http", "https"):
            return None

        # Extract host without port
        host = parsed.netloc.split(":")[0].lower()

        # Check against allowed hosts
        allowed_hosts = get_allowed_redirect_hosts()

        if host in allowed_hosts:
            return redirect_to

        # Also allow subdomains of allowed hosts (e.g., app.example.com if example.com is allowed)
        for allowed_host in allowed_hosts:
            if host.endswith(f".{allowed_host}"):
                return redirect_to

        logger.warning(f"Rejected redirect to untrusted host: {host}")
        return None

    except Exception as e:
        logger.warning(f"Failed to parse redirect URL: {e}")
        return None


@router.post("/signup", response_model=TokenResponse)
async def signup(user_data: UserCreate, supabase=Depends(get_supabase)):
    """
    Register a new user.
    
    Creates a new user account with email and password.
    Sends a verification email to the user.
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )
    
    try:
        # Create user with Supabase Auth
        response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "full_name": user_data.full_name,
                }
            }
        })
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )
        
        # Return tokens if auto-confirmed, otherwise indicate email verification needed
        if response.session:
            return TokenResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                expires_in=response.session.expires_in or 3600,
                user=User(
                    id=response.user.id,
                    email=response.user.email,
                    email_confirmed=response.user.email_confirmed_at is not None,
                    created_at=response.user.created_at,
                    full_name=user_data.full_name,
                )
            )
        else:
            # Email confirmation required
            return TokenResponse(
                access_token="",
                refresh_token="",
                expires_in=0,
                user=User(
                    id=response.user.id,
                    email=response.user.email,
                    email_confirmed=False,
                    created_at=response.user.created_at,
                    full_name=user_data.full_name,
                )
            )
            
    except AuthApiError as e:
        logger.error(f"Signup error: {e}")
        if "already registered" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create account. Please check your information and try again."
        )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, supabase=Depends(get_supabase)):
    """
    Log in with email and password.
    
    Returns access and refresh tokens on success.
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )
    
    try:
        response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password,
        })
        
        if not response.session or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        user_metadata = response.user.user_metadata or {}
        
        return TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            expires_in=response.session.expires_in or 3600,
            user=User(
                id=response.user.id,
                email=response.user.email,
                email_confirmed=response.user.email_confirmed_at is not None,
                created_at=response.user.created_at,
                full_name=user_metadata.get("full_name"),
                avatar_url=user_metadata.get("avatar_url"),
            )
        )
        
    except AuthApiError as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    supabase=Depends(get_supabase)
):
    """
    Log out the current user.
    
    Invalidates the current session.
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )
    
    try:
        supabase.auth.sign_out()
        return {"message": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Still return success - client should clear tokens anyway
        return {"message": "Logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    supabase=Depends(get_supabase)
):
    """
    Refresh an access token using a refresh token.
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )
    
    try:
        response = supabase.auth.refresh_session(request.refresh_token)
        
        if not response.session or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_metadata = response.user.user_metadata or {}
        
        return TokenResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            expires_in=response.session.expires_in or 3600,
            user=User(
                id=response.user.id,
                email=response.user.email,
                email_confirmed=response.user.email_confirmed_at is not None,
                created_at=response.user.created_at,
                full_name=user_metadata.get("full_name"),
                avatar_url=user_metadata.get("avatar_url"),
            )
        )
        
    except AuthApiError as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the current user's information.
    """
    return current_user


@router.patch("/me", response_model=User)
async def update_profile(
    profile: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    supabase=Depends(get_supabase)
):
    """
    Update the current user's profile.
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )
    
    try:
        # Build update data
        update_data = {}
        if profile.full_name is not None:
            update_data["full_name"] = profile.full_name
        if profile.avatar_url is not None:
            update_data["avatar_url"] = profile.avatar_url
        
        if update_data:
            response = supabase.auth.update_user({
                "data": update_data
            })
            
            if response.user:
                user_metadata = response.user.user_metadata or {}
                return User(
                    id=response.user.id,
                    email=response.user.email,
                    email_confirmed=response.user.email_confirmed_at is not None,
                    created_at=response.user.created_at,
                    full_name=user_metadata.get("full_name"),
                    avatar_url=user_metadata.get("avatar_url"),
                )
        
        return current_user
        
    except AuthApiError as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update profile. Please try again."
        )


@router.post("/password/reset")
async def request_password_reset(
    request: PasswordResetRequest,
    supabase=Depends(get_supabase)
):
    """
    Request a password reset email.
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )
    
    try:
        supabase.auth.reset_password_email(request.email)
        # Always return success to prevent email enumeration
        return {"message": "If an account exists, a reset email has been sent"}
        
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        # Still return success to prevent email enumeration
        return {"message": "If an account exists, a reset email has been sent"}


@router.post("/password/update")
async def update_password(
    request: PasswordUpdateRequest,
    current_user: User = Depends(get_current_user),
    supabase=Depends(get_supabase)
):
    """
    Update the current user's password.
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )
    
    try:
        supabase.auth.update_user({
            "password": request.password
        })
        return {"message": "Password updated successfully"}
        
    except AuthApiError as e:
        logger.error(f"Password update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update password. Please ensure your new password meets the requirements."
        )


@router.get("/providers")
async def get_oauth_providers():
    """
    Get available OAuth providers.
    """
    return {
        "providers": [
            {"name": "google", "enabled": True},
            {"name": "github", "enabled": True},
            {"name": "orcid", "enabled": False},  # Planned for researchers
        ]
    }


@router.get("/oauth/{provider}/url")
async def get_oauth_url(
    provider: str,
    redirect_to: Optional[str] = None,
    supabase=Depends(get_supabase)
):
    """
    Get OAuth authorization URL for a provider.

    Security: redirect_to is validated against an allowlist to prevent open redirect attacks.
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured"
        )

    valid_providers = ["google", "github"]
    if provider not in valid_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider. Must be one of: {valid_providers}"
        )

    # Validate redirect_to to prevent open redirect attacks
    validated_redirect = validate_redirect_url(redirect_to)
    if redirect_to and not validated_redirect:
        logger.warning(f"Invalid redirect_to rejected: {redirect_to}")
        # Don't expose that the redirect was rejected for security reasons
        # Just use the default redirect behavior

    try:
        options = {}
        if validated_redirect:
            options["redirect_to"] = validated_redirect

        response = supabase.auth.sign_in_with_oauth({
            "provider": provider,
            "options": options
        })

        return {"url": response.url}

    except Exception as e:
        logger.error(f"OAuth URL error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate OAuth URL"
        )
