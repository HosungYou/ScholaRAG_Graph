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
