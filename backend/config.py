"""
Configuration management for ScholaRAG_Graph backend.
"""

import os
from functools import lru_cache
from typing import Literal, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://localhost:5432/scholarag_graph"

    # LLM Providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""  # FREE! Get key at https://console.groq.com
    cohere_api_key: str = ""  # FREE! For embeddings - https://dashboard.cohere.com/api-keys

    # BUG-032 Fix: Groq Rate Limiting Configuration
    groq_requests_per_second: float = 2.0  # Max requests per second to Groq API
    groq_max_retries: int = 3  # Max retry attempts for Groq API errors
    groq_timeout: float = 60.0  # Timeout in seconds for Groq API calls

    # Default LLM Configuration
    # Changed default to groq (free tier, fastest inference)
    default_llm_provider: Literal["anthropic", "openai", "google", "groq"] = "groq"
    default_llm_model: str = "llama-3.3-70b-versatile"

    # Embedding Configuration
    embedding_model: str = "embed-english-v3.0"  # Cohere model
    embedding_dimension: int = 1024  # Cohere v3 dimension

    # CORS - comma-separated list of allowed origins
    # Vercel Preview URLs are allowed via regex in main.py:
    #   Pattern: ^https://schola-rag-graph-[a-z0-9]+-hosung-yous-projects\.vercel\.app$
    # IMPORTANT: schola-rag-graph.vercel.app is the production frontend URL
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003,https://schola-rag-graph.vercel.app,https://scholarag-graph.vercel.app"
    frontend_url: str = "http://localhost:3000"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Debug
    debug: bool = False
    
    # Supabase Auth
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""  # Service role key for admin operations
    supabase_service_role_key: str = ""  # Alias for service_key (deprecated)
    supabase_project_id: str = ""  # Supabase project ID

    # External API Integrations
    semantic_scholar_api_key: str = ""  # Optional: for higher rate limits
    openalex_email: str = ""  # For polite pool access (higher rate limits)
    zotero_api_key: str = ""  # User's Zotero API key (can also be provided per-request)
    zotero_user_id: str = ""  # User's Zotero user ID

    # Import Security Configuration
    scholarag_import_root: str = ""  # Primary allowed import directory
    scholarag_import_root_2: str = ""  # Secondary allowed import directory

    # Security: Authentication & Authorization
    require_auth: bool = True  # Set to False only for local development
    environment: Literal["development", "staging", "production"] = "development"

    # Performance: LLM Caching
    llm_cache_enabled: bool = True  # Enable LLM response caching
    llm_cache_ttl: int = 3600  # Default cache TTL in seconds (1 hour)
    llm_cache_max_size: int = 50  # PERF-010: Further reduced for 512MB memory limit

    # Performance: Redis (for rate limiting and caching in production)
    redis_url: str = ""  # Redis connection URL (e.g., redis://localhost:6379)
    redis_rate_limit_enabled: bool = False  # Use Redis for rate limiting

    # Security: Rate Limiting
    # Enabled by default in production, disabled in development
    # Can be overridden with RATE_LIMIT_ENABLED environment variable
    rate_limit_enabled: bool = True  # Enable API rate limiting

    # Security: Trusted Proxy Configuration
    # Controls whether to trust X-Forwarded-For header for client IP detection
    # - "auto": Trust in production (behind Render LB), don't trust in development
    # - "always": Always trust X-Forwarded-For (use if behind known proxy)
    # - "never": Never trust, always use direct connection IP
    # WARNING: Setting "always" when not behind a trusted proxy allows IP spoofing!
    trusted_proxy_mode: Literal["auto", "always", "never"] = "auto"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_required_settings(self) -> List[str]:
        """
        Validate required settings for production.
        Returns list of missing/invalid setting names.
        """
        missing = []

        # Database is always required
        if not self.database_url or self.database_url == "postgresql://localhost:5432/scholarag_graph":
            if self.environment == "production":
                missing.append("DATABASE_URL")

        # At least one LLM API key required
        if not any([
            self.anthropic_api_key,
            self.openai_api_key,
            self.google_api_key,
            self.groq_api_key,
        ]):
            missing.append("LLM_API_KEY (ANTHROPIC/OPENAI/GOOGLE/GROQ 중 하나 필요)")

        # Validate LLM provider matches available key
        provider_key_map = {
            "anthropic": self.anthropic_api_key,
            "openai": self.openai_api_key,
            "google": self.google_api_key,
            "groq": self.groq_api_key,
        }
        if self.default_llm_provider and not provider_key_map.get(self.default_llm_provider):
            missing.append(f"{self.default_llm_provider.upper()}_API_KEY (DEFAULT_LLM_PROVIDER={self.default_llm_provider}이지만 해당 API 키 없음)")

        return missing

    def get_available_llm_provider(self) -> str:
        """
        Get an available LLM provider based on configured API keys.
        Returns the default provider if its key exists, otherwise falls back.
        """
        provider_key_map = {
            "anthropic": self.anthropic_api_key,
            "openai": self.openai_api_key,
            "google": self.google_api_key,
            "groq": self.groq_api_key,
        }

        # Check if default provider has key
        if provider_key_map.get(self.default_llm_provider):
            return self.default_llm_provider

        # Fallback to any available provider
        for provider, key in provider_key_map.items():
            if key:
                return provider

        return self.default_llm_provider  # Return default even if no key (will fail at runtime)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience exports
settings = get_settings()
