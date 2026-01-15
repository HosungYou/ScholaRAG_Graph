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

    # Default LLM Configuration
    default_llm_provider: Literal["anthropic", "openai", "google"] = "anthropic"
    default_llm_model: str = "claude-3-5-haiku-20241022"

    # Embedding Configuration
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # CORS - comma-separated list of allowed origins
    cors_origins: str = "http://localhost:3000,https://scholarag-graph.vercel.app"
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
