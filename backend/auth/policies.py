"""
Centralized authentication policy configuration.

Defines which routes require authentication and what level.
This module provides a single source of truth for authentication requirements
across all API endpoints.

Usage:
    from auth.policies import get_auth_level, AuthLevel

    # In middleware or dependencies
    level = get_auth_level("/api/projects/123")
    if level == AuthLevel.REQUIRED:
        # Enforce authentication
"""

import fnmatch
import logging
from enum import Enum
from typing import Dict, Set, List, Tuple

logger = logging.getLogger(__name__)


class AuthLevel(str, Enum):
    """
    Authentication levels for API endpoints.
    
    NONE: No authentication required (health check, login, signup)
    OPTIONAL: Authentication optional, behavior may differ based on auth state
              (development mode or guest-accessible features)
    REQUIRED: Always requires authentication
    OWNER: Requires authentication AND ownership verification
    """
    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"
    OWNER = "owner"


# =============================================================================
# Public Paths (no authentication needed)
# =============================================================================

PUBLIC_PATHS: Set[str] = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}


# =============================================================================
# Authentication Policies by Route Pattern
# =============================================================================
# 
# Patterns support:
#   - Exact match: "/api/auth/login"
#   - Wildcard suffix: "/api/projects/*" (matches /api/projects/123, /api/projects/123/stats)
#   - Glob patterns: "/api/*/public" (matches /api/graph/public, /api/teams/public)
#
# More specific patterns take precedence over general patterns.
# Default level is OPTIONAL if no pattern matches.

AUTH_POLICIES: List[Tuple[str, AuthLevel]] = [
    # ===========================================
    # Auth routes - no auth required for login/signup
    # ===========================================
    ("/api/auth/signup", AuthLevel.NONE),
    ("/api/auth/login", AuthLevel.NONE),
    ("/api/auth/refresh", AuthLevel.NONE),
    ("/api/auth/password/reset", AuthLevel.NONE),
    ("/api/auth/providers", AuthLevel.NONE),
    ("/api/auth/oauth/*", AuthLevel.NONE),
    
    # Auth routes - require authentication
    ("/api/auth/me", AuthLevel.REQUIRED),
    ("/api/auth/logout", AuthLevel.REQUIRED),
    ("/api/auth/password/update", AuthLevel.REQUIRED),
    
    # ===========================================
    # Projects - configurable (dev vs prod)
    # ===========================================
    ("/api/projects", AuthLevel.OPTIONAL),
    ("/api/projects/*", AuthLevel.OPTIONAL),
    
    # ===========================================
    # Graph operations - configurable
    # ===========================================
    ("/api/graph", AuthLevel.OPTIONAL),
    ("/api/graph/*", AuthLevel.OPTIONAL),
    
    # ===========================================
    # Chat - configurable
    # ===========================================
    ("/api/chat", AuthLevel.OPTIONAL),
    ("/api/chat/*", AuthLevel.OPTIONAL),
    
    # ===========================================
    # Import - configurable
    # ===========================================
    ("/api/import", AuthLevel.OPTIONAL),
    ("/api/import/*", AuthLevel.OPTIONAL),
    
    # ===========================================
    # Integrations - configurable
    # ===========================================
    ("/api/integrations", AuthLevel.OPTIONAL),
    ("/api/integrations/*", AuthLevel.OPTIONAL),
    
    # ===========================================
    # PRISMA - configurable
    # ===========================================
    ("/api/prisma", AuthLevel.OPTIONAL),
    ("/api/prisma/*", AuthLevel.OPTIONAL),
    
    # ===========================================
    # Teams - always require authentication
    # ===========================================
    ("/api/teams", AuthLevel.REQUIRED),
    ("/api/teams/*", AuthLevel.REQUIRED),
    ("/api/teams/*/members", AuthLevel.REQUIRED),
    ("/api/teams/*/members/*", AuthLevel.REQUIRED),
    ("/api/teams/projects/*", AuthLevel.REQUIRED),
]


# =============================================================================
# Owner-level Routes (require ownership verification)
# =============================================================================
# These routes not only require authentication but also verify that the
# authenticated user owns the resource being accessed.

OWNER_ROUTES: Dict[str, str] = {
    # Pattern -> Resource type
    "/api/projects/*/delete": "project",
    "/api/teams/*/delete": "team",
}


def _match_pattern(pattern: str, path: str) -> bool:
    """
    Check if a path matches a pattern.
    
    Supports:
    - Exact match
    - Wildcard suffix (*): /api/projects/* matches /api/projects/123
    - Glob patterns via fnmatch
    """
    # Exact match
    if pattern == path:
        return True
    
    # Wildcard suffix pattern
    if pattern.endswith("/*"):
        prefix = pattern[:-1]  # Keep trailing slash: /api/projects/
        if path.startswith(prefix) or path == prefix[:-1]:  # Match with or without trailing slash
            return True
    
    # Glob pattern matching
    if "*" in pattern:
        return fnmatch.fnmatch(path, pattern)
    
    return False


def _get_pattern_specificity(pattern: str) -> int:
    """
    Calculate pattern specificity for precedence ordering.
    
    More specific patterns (longer, more segments) get higher scores.
    Exact matches score higher than wildcard patterns.
    """
    # Base score from path segments
    segments = pattern.count("/")
    
    # Penalty for wildcards
    wildcards = pattern.count("*")
    
    # Length bonus
    length_bonus = len(pattern) // 10
    
    return (segments * 10) + length_bonus - (wildcards * 5)


def get_auth_level(path: str) -> AuthLevel:
    """
    Get the authentication level required for a given path.
    
    Args:
        path: The request path (e.g., "/api/projects/123")
        
    Returns:
        AuthLevel enum value indicating the required authentication level.
        
    Example:
        >>> get_auth_level("/api/auth/login")
        AuthLevel.NONE
        >>> get_auth_level("/api/teams/123")
        AuthLevel.REQUIRED
        >>> get_auth_level("/api/projects/456")
        AuthLevel.OPTIONAL
    """
    # Normalize path
    path = path.rstrip("/")
    if not path:
        path = "/"
    
    # Check public paths first
    if path in PUBLIC_PATHS:
        return AuthLevel.NONE
    
    # Find all matching patterns and their levels
    matches: List[Tuple[str, AuthLevel, int]] = []
    
    for pattern, level in AUTH_POLICIES:
        if _match_pattern(pattern, path):
            specificity = _get_pattern_specificity(pattern)
            matches.append((pattern, level, specificity))
    
    if matches:
        # Sort by specificity (highest first) and return most specific match
        matches.sort(key=lambda x: x[2], reverse=True)
        best_match = matches[0]
        logger.debug(f"Auth policy for '{path}': {best_match[1].value} (matched '{best_match[0]}')")
        return best_match[1]
    
    # Default to OPTIONAL for unspecified routes
    logger.debug(f"Auth policy for '{path}': OPTIONAL (no matching policy)")
    return AuthLevel.OPTIONAL


def requires_owner_check(path: str) -> bool:
    """
    Check if a path requires ownership verification.
    
    Args:
        path: The request path
        
    Returns:
        True if ownership verification is required
    """
    for pattern in OWNER_ROUTES:
        if _match_pattern(pattern, path):
            return True
    return False


def get_resource_type(path: str) -> str | None:
    """
    Get the resource type for owner verification.
    
    Args:
        path: The request path
        
    Returns:
        Resource type string (e.g., "project", "team") or None
    """
    for pattern, resource_type in OWNER_ROUTES.items():
        if _match_pattern(pattern, path):
            return resource_type
    return None


# =============================================================================
# Policy Summary Functions (for documentation/debugging)
# =============================================================================

def get_policy_summary() -> Dict[str, List[str]]:
    """
    Get a summary of all policies grouped by auth level.
    
    Returns:
        Dictionary mapping auth level to list of patterns
    """
    summary: Dict[str, List[str]] = {
        AuthLevel.NONE.value: list(PUBLIC_PATHS),
        AuthLevel.OPTIONAL.value: [],
        AuthLevel.REQUIRED.value: [],
        AuthLevel.OWNER.value: [],
    }
    
    for pattern, level in AUTH_POLICIES:
        summary[level.value].append(pattern)
    
    for pattern in OWNER_ROUTES:
        summary[AuthLevel.OWNER.value].append(pattern)
    
    return summary


def print_policy_summary() -> None:
    """Print a human-readable summary of all auth policies."""
    summary = get_policy_summary()
    
    print("\n" + "=" * 60)
    print("AUTHENTICATION POLICY SUMMARY")
    print("=" * 60)
    
    for level_name, patterns in summary.items():
        print(f"\n{level_name.upper()} ({len(patterns)} routes):")
        for pattern in sorted(patterns):
            print(f"  - {pattern}")
    
    print("\n" + "=" * 60)
