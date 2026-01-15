"""
Authentication module for ScholaRAG_Graph.

Uses Supabase Auth for user management and JWT verification.

This module provides:
- Supabase client for authentication operations
- FastAPI dependencies for route-level authentication
- Centralized authentication policies
- Middleware for request-level policy enforcement
"""

from .supabase_client import supabase_client, get_supabase
from .dependencies import (
    get_current_user,
    get_optional_user,
    require_auth,
    require_auth_if_configured,
    require_verified_email,
    get_auth_dependency_for_route,
    get_user_from_state,
    require_user_from_state,
)
from .models import User, UserCreate, UserProfile
from .policies import (
    AuthLevel,
    get_auth_level,
    requires_owner_check,
    get_resource_type,
    get_policy_summary,
    PUBLIC_PATHS,
    AUTH_POLICIES,
)
from .middleware import (
    AuthMiddleware,
    AuthPolicyEnforcer,
    get_user_from_request,
    get_user_id_from_request,
    require_auth_from_request,
)

__all__ = [
    # Supabase client
    "supabase_client",
    "get_supabase",
    # Dependencies
    "get_current_user",
    "get_optional_user",
    "require_auth",
    "require_auth_if_configured",
    "require_verified_email",
    "get_auth_dependency_for_route",
    "get_user_from_state",
    "require_user_from_state",
    # Models
    "User",
    "UserCreate", 
    "UserProfile",
    # Policies
    "AuthLevel",
    "get_auth_level",
    "requires_owner_check",
    "get_resource_type",
    "get_policy_summary",
    "PUBLIC_PATHS",
    "AUTH_POLICIES",
    # Middleware
    "AuthMiddleware",
    "AuthPolicyEnforcer",
    "get_user_from_request",
    "get_user_id_from_request",
    "require_auth_from_request",
]
