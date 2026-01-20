"""
Embedding Factory - Unified interface for creating embedding providers.

Supports:
- Cohere (default, general purpose)
- SPECTER2 (academic papers)
- Dual (both Cohere and SPECTER2)

Usage:
    factory = EmbeddingFactory()
    
    # Get Cohere embeddings (default)
    embeddings = await factory.get_embeddings(texts)
    
    # Get SPECTER2 embeddings for academic content
    embeddings = await factory.get_embeddings(texts, provider="specter")
    
    # Get dual embeddings (both)
    dual_result = await factory.get_dual_embeddings(texts)
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    """Available embedding providers."""
    COHERE = "cohere"
    SPECTER = "specter"
    DUAL = "dual"


@dataclass
class EmbeddingResult:
    """Result from embedding operation."""
    embeddings: List[List[float]]
    provider: EmbeddingProvider
    dimension: int
    model: str


@dataclass
class DualEmbeddingResult:
    """Result from dual embedding operation."""
    cohere_embeddings: List[List[float]]
    specter_embeddings: List[List[float]]
    cohere_dimension: int
    specter_dimension: int


class EmbeddingFactory:
    """
    Factory for creating and managing embedding providers.
    
    Provides a unified interface for different embedding models
    with automatic provider selection based on use case.
    """
    
    def __init__(
        self,
        default_provider: EmbeddingProvider = EmbeddingProvider.COHERE,
        cohere_model: str = "embed-english-v3.0",
        enable_specter: bool = True,
    ):
        """
        Initialize the embedding factory.
        
        Args:
            default_provider: Default provider to use
            cohere_model: Cohere model name
            enable_specter: Whether to enable SPECTER2 (requires sentence-transformers)
        """
        self.default_provider = default_provider
        self.cohere_model = cohere_model
        self.enable_specter = enable_specter
        
        self._cohere_provider = None
        self._specter_provider = None
        self._dual_provider = None
    
    async def _get_cohere_provider(self):
        """Lazy load Cohere provider."""
        if self._cohere_provider is None:
            try:
                from .cohere_embeddings import get_cohere_embeddings
                self._cohere_provider = get_cohere_embeddings()
            except Exception as e:
                logger.error(f"Failed to initialize Cohere embeddings: {e}")
                raise
        return self._cohere_provider
    
    async def _get_specter_provider(self):
        """Lazy load SPECTER2 provider."""
        if self._specter_provider is None:
            if not self.enable_specter:
                raise ValueError("SPECTER2 is disabled")
            try:
                from .specter_embeddings import SpecterEmbeddingProvider
                self._specter_provider = SpecterEmbeddingProvider()
            except ImportError as e:
                logger.warning(f"SPECTER2 not available (missing dependencies): {e}")
                raise ValueError("SPECTER2 requires sentence-transformers package")
            except Exception as e:
                logger.error(f"Failed to initialize SPECTER2: {e}")
                raise
        return self._specter_provider
    
    async def _get_dual_provider(self):
        """Lazy load Dual embedding provider."""
        if self._dual_provider is None:
            try:
                from .specter_embeddings import DualEmbeddingProvider
                self._dual_provider = DualEmbeddingProvider()
            except Exception as e:
                logger.error(f"Failed to initialize dual embeddings: {e}")
                raise
        return self._dual_provider
    
    async def get_embeddings(
        self,
        texts: List[str],
        provider: Optional[EmbeddingProvider] = None,
        input_type: str = "search_document",
    ) -> EmbeddingResult:
        """
        Get embeddings using the specified provider.
        
        Args:
            texts: List of texts to embed
            provider: Provider to use (default: self.default_provider)
            input_type: Type hint for Cohere (search_document, search_query, etc.)
            
        Returns:
            EmbeddingResult with embeddings and metadata
        """
        provider = provider or self.default_provider
        
        if provider == EmbeddingProvider.COHERE:
            embed_provider = await self._get_cohere_provider()
            embeddings = await embed_provider.get_embeddings(texts, input_type=input_type)
            return EmbeddingResult(
                embeddings=embeddings,
                provider=provider,
                dimension=1536,  # Cohere embed-v3.0 dimension
                model=self.cohere_model,
            )
        
        elif provider == EmbeddingProvider.SPECTER:
            embed_provider = await self._get_specter_provider()
            embeddings = await embed_provider.get_embeddings(texts)
            return EmbeddingResult(
                embeddings=embeddings,
                provider=provider,
                dimension=768,  # SPECTER2 dimension
                model="allenai/specter2",
            )
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def get_dual_embeddings(
        self,
        texts: List[str],
        input_type: str = "search_document",
    ) -> DualEmbeddingResult:
        """
        Get embeddings from both Cohere and SPECTER2.
        
        Useful for storing dual representations for different search needs.
        
        Args:
            texts: List of texts to embed
            input_type: Type hint for Cohere
            
        Returns:
            DualEmbeddingResult with both embeddings
        """
        dual_provider = await self._get_dual_provider()
        cohere_emb, specter_emb = await dual_provider.get_embeddings(
            texts, input_type=input_type
        )
        
        return DualEmbeddingResult(
            cohere_embeddings=cohere_emb,
            specter_embeddings=specter_emb,
            cohere_dimension=1536,
            specter_dimension=768,
        )
    
    async def get_query_embedding(
        self,
        query: str,
        provider: Optional[EmbeddingProvider] = None,
    ) -> List[float]:
        """
        Get embedding for a search query.
        
        Args:
            query: Query text
            provider: Provider to use
            
        Returns:
            Single embedding vector
        """
        result = await self.get_embeddings(
            [query],
            provider=provider,
            input_type="search_query",
        )
        return result.embeddings[0]
    
    def suggest_provider_for_use_case(self, use_case: str) -> EmbeddingProvider:
        """
        Suggest the best embedding provider for a given use case.
        
        Args:
            use_case: Description of the use case
                - "academic": Academic paper similarity
                - "semantic_search": General semantic search
                - "chunk_retrieval": Document chunk retrieval
                - "entity_matching": Knowledge graph entity matching
                
        Returns:
            Recommended EmbeddingProvider
        """
        academic_cases = {"academic", "paper", "research", "citation", "scientific"}
        general_cases = {"semantic_search", "entity", "concept", "general"}
        
        use_case_lower = use_case.lower()
        
        # Academic use cases benefit from SPECTER2
        if any(case in use_case_lower for case in academic_cases):
            if self.enable_specter:
                return EmbeddingProvider.SPECTER
            return EmbeddingProvider.COHERE
        
        # General use cases work better with Cohere
        if any(case in use_case_lower for case in general_cases):
            return EmbeddingProvider.COHERE
        
        # Document chunks can use either, default to Cohere for cost
        if "chunk" in use_case_lower:
            return EmbeddingProvider.COHERE
        
        return self.default_provider


# Global factory instance
_factory_instance: Optional[EmbeddingFactory] = None


def get_embedding_factory() -> EmbeddingFactory:
    """Get or create the global embedding factory instance."""
    global _factory_instance
    if _factory_instance is None:
        # Check if SPECTER2 should be enabled (based on env var or availability)
        enable_specter = os.environ.get("ENABLE_SPECTER2", "false").lower() == "true"
        _factory_instance = EmbeddingFactory(enable_specter=enable_specter)
    return _factory_instance


async def get_embeddings(
    texts: List[str],
    provider: str = "cohere",
    input_type: str = "search_document",
) -> List[List[float]]:
    """
    Convenience function to get embeddings.
    
    Args:
        texts: List of texts to embed
        provider: Provider name ("cohere", "specter", "dual")
        input_type: Type hint for Cohere
        
    Returns:
        List of embedding vectors
    """
    factory = get_embedding_factory()
    provider_enum = EmbeddingProvider(provider)
    result = await factory.get_embeddings(texts, provider=provider_enum, input_type=input_type)
    return result.embeddings
