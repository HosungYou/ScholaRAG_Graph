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

    # Default LLM Configuration
    default_llm_provider: Literal["anthropic", "openai", "google", "groq"] = "anthropic"
    default_llm_model: str = "claude-3-5-haiku-20241022"

    # Embedding Configuration
    embedding_model: str = "embed-english-v3.0"  # Cohere model
    embedding_dimension: int = 1024  # Cohere v3 dimension

    # CORS - comma-separated list of allowed origins
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003,https://scholarag-graph.vercel.app"
    frontend_url: str = "http://localhost:3000"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Debug
    debug: bool = False
    
    # Supabase Auth
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""  # For admin operations

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
    llm_cache_max_size: int = 1000  # Maximum cache entries

    # Performance: Redis (for rate limiting and caching in production)
    redis_url: str = ""  # Redis connection URL (e.g., redis://localhost:6379)
    redis_rate_limit_enabled: bool = False  # Use Redis for rate limiting

    # Security: Rate Limiting
    # Enabled by default in production, disabled in development
    # Can be overridden with RATE_LIMIT_ENABLED environment variable
    rate_limit_enabled: bool = True  # Enable API rate limiting

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience exports
settings = get_settings()
