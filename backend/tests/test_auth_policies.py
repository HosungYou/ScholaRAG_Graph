"""
Tests for centralized authentication policies.

Tests the auth policy configuration and pattern matching logic.
"""

import pytest
from auth.policies import (
    AuthLevel,
    get_auth_level,
    requires_owner_check,
    get_resource_type,
    get_policy_summary,
    _match_pattern,
    _get_pattern_specificity,
    PUBLIC_PATHS,
)


class TestAuthLevel:
    """Test AuthLevel enum."""
    
    def test_auth_levels_exist(self):
        """Verify all auth levels are defined."""
        assert AuthLevel.NONE == "none"
        assert AuthLevel.OPTIONAL == "optional"
        assert AuthLevel.REQUIRED == "required"
        assert AuthLevel.OWNER == "owner"
    
    def test_auth_level_is_string_enum(self):
        """Verify AuthLevel is a string enum for JSON serialization."""
        assert isinstance(AuthLevel.NONE.value, str)
        # String enum provides value directly
        assert AuthLevel.REQUIRED.value == "required"


class TestPatternMatching:
    """Test pattern matching utilities."""
    
    def test_exact_match(self):
        """Test exact path matching."""
        assert _match_pattern("/api/auth/login", "/api/auth/login") is True
        assert _match_pattern("/api/auth/login", "/api/auth/signup") is False
    
    def test_wildcard_suffix(self):
        """Test wildcard suffix patterns."""
        assert _match_pattern("/api/projects/*", "/api/projects/123") is True
        assert _match_pattern("/api/projects/*", "/api/projects/123/stats") is True
        assert _match_pattern("/api/projects/*", "/api/projects") is True
        assert _match_pattern("/api/projects/*", "/api/teams/123") is False
    
    def test_pattern_specificity(self):
        """Test pattern specificity calculation."""
        # More segments = higher specificity
        assert _get_pattern_specificity("/api/a/b/c") > _get_pattern_specificity("/api/a/b")
        
        # Wildcards reduce specificity
        assert _get_pattern_specificity("/api/projects/123") > _get_pattern_specificity("/api/projects/*")


class TestPublicPaths:
    """Test public paths configuration."""
    
    def test_root_is_public(self):
        """Root path should be public."""
        assert "/" in PUBLIC_PATHS
    
    def test_health_is_public(self):
        """Health check should be public."""
        assert "/health" in PUBLIC_PATHS
    
    def test_docs_are_public(self):
        """API documentation should be public."""
        assert "/docs" in PUBLIC_PATHS
        assert "/openapi.json" in PUBLIC_PATHS
        assert "/redoc" in PUBLIC_PATHS


class TestGetAuthLevel:
    """Test get_auth_level function."""
    
    def test_public_paths_return_none(self):
        """Public paths should return AuthLevel.NONE."""
        assert get_auth_level("/") == AuthLevel.NONE
        assert get_auth_level("/health") == AuthLevel.NONE
        assert get_auth_level("/docs") == AuthLevel.NONE
    
    def test_auth_login_no_auth_required(self):
        """Login/signup shouldn't require auth."""
        assert get_auth_level("/api/auth/login") == AuthLevel.NONE
        assert get_auth_level("/api/auth/signup") == AuthLevel.NONE
        assert get_auth_level("/api/auth/refresh") == AuthLevel.NONE
    
    def test_auth_me_requires_auth(self):
        """Protected auth routes should require auth."""
        assert get_auth_level("/api/auth/me") == AuthLevel.REQUIRED
        assert get_auth_level("/api/auth/logout") == AuthLevel.REQUIRED
    
    def test_teams_always_requires_auth(self):
        """Team routes should always require authentication."""
        assert get_auth_level("/api/teams") == AuthLevel.REQUIRED
        assert get_auth_level("/api/teams/123") == AuthLevel.REQUIRED
        assert get_auth_level("/api/teams/123/members") == AuthLevel.REQUIRED
    
    def test_projects_optional_auth(self):
        """Project routes should have optional auth."""
        assert get_auth_level("/api/projects") == AuthLevel.OPTIONAL
        assert get_auth_level("/api/projects/123") == AuthLevel.OPTIONAL
        assert get_auth_level("/api/projects/123/stats") == AuthLevel.OPTIONAL
    
    def test_graph_optional_auth(self):
        """Graph routes should have optional auth."""
        assert get_auth_level("/api/graph") == AuthLevel.OPTIONAL
        assert get_auth_level("/api/graph/nodes") == AuthLevel.OPTIONAL
    
    def test_chat_optional_auth(self):
        """Chat routes should have optional auth."""
        assert get_auth_level("/api/chat") == AuthLevel.OPTIONAL
        assert get_auth_level("/api/chat/123") == AuthLevel.OPTIONAL
    
    def test_unknown_paths_return_optional(self):
        """Unknown paths should default to OPTIONAL."""
        assert get_auth_level("/api/unknown/endpoint") == AuthLevel.OPTIONAL
        assert get_auth_level("/some/random/path") == AuthLevel.OPTIONAL
    
    def test_trailing_slash_handling(self):
        """Paths with trailing slashes should be normalized."""
        assert get_auth_level("/api/projects/") == get_auth_level("/api/projects")
        assert get_auth_level("/api/teams/") == get_auth_level("/api/teams")
    
    def test_oauth_routes_no_auth(self):
        """OAuth routes should not require auth."""
        assert get_auth_level("/api/auth/oauth/google") == AuthLevel.NONE
        assert get_auth_level("/api/auth/oauth/github/url") == AuthLevel.NONE


class TestOwnerRoutes:
    """Test owner verification routes."""
    
    def test_project_delete_requires_owner(self):
        """Project deletion should require owner verification."""
        assert requires_owner_check("/api/projects/123/delete") is True
        assert get_resource_type("/api/projects/123/delete") == "project"
    
    def test_team_delete_requires_owner(self):
        """Team deletion should require owner verification."""
        assert requires_owner_check("/api/teams/123/delete") is True
        assert get_resource_type("/api/teams/123/delete") == "team"
    
    def test_regular_paths_dont_require_owner(self):
        """Regular paths should not require owner verification."""
        assert requires_owner_check("/api/projects/123") is False
        assert requires_owner_check("/api/teams") is False
        assert get_resource_type("/api/projects/123") is None


class TestPolicySummary:
    """Test policy summary utilities."""
    
    def test_get_policy_summary_returns_dict(self):
        """Policy summary should return a dictionary."""
        summary = get_policy_summary()
        assert isinstance(summary, dict)
    
    def test_summary_has_all_levels(self):
        """Summary should include all auth levels."""
        summary = get_policy_summary()
        assert AuthLevel.NONE.value in summary
        assert AuthLevel.OPTIONAL.value in summary
        assert AuthLevel.REQUIRED.value in summary
        assert AuthLevel.OWNER.value in summary
    
    def test_summary_includes_public_paths(self):
        """Summary should include public paths under NONE."""
        summary = get_policy_summary()
        assert "/" in summary[AuthLevel.NONE.value]
        assert "/health" in summary[AuthLevel.NONE.value]


class TestSpecificityPrecedence:
    """Test that more specific patterns take precedence."""
    
    def test_specific_pattern_wins(self):
        """More specific pattern should override general pattern."""
        # /api/auth/me (REQUIRED) should override /api/auth/* if it existed as NONE
        assert get_auth_level("/api/auth/me") == AuthLevel.REQUIRED
    
    def test_nested_team_routes(self):
        """Nested team routes should all require auth."""
        assert get_auth_level("/api/teams") == AuthLevel.REQUIRED
        assert get_auth_level("/api/teams/123") == AuthLevel.REQUIRED
        assert get_auth_level("/api/teams/123/members") == AuthLevel.REQUIRED
        assert get_auth_level("/api/teams/123/members/456") == AuthLevel.REQUIRED
