"""
OpenAI Embedding Provider

Fallback embedding provider when Cohere is not available.
Uses text-embedding-3-small (1536 dimensions) for compatibility with Cohere embed-v4.0.

Note: OpenAI embeddings are NOT free - pricing at https://openai.com/pricing
"""

import logging
from typing import List, Optional
import asyncio

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider:
    """
    OpenAI embedding provider for vector embeddings.

    Uses text-embedding-3-small model which supports 1536 dimensions,
    matching Cohere embed-v4.0 for compatibility.
    """

    # OpenAI text-embedding-3-small: 1536 dimensions (matches Cohere v4)
    # OpenAI text-embedding-3-large: 3072 dimensions
    DEFAULT_DIMENSION = 1536
    DEFAULT_MODEL = "text-embedding-3-small"

    def __init__(self, api_key: str, dimension: int = DEFAULT_DIMENSION):
        self.api_key = api_key
        self.dimension = dimension
        self._client = None

    @property
    def client(self):
        """Lazy load the OpenAI async client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package required: pip install openai")
        return self._client

    async def get_embeddings(
        self,
        texts: List[str],
        input_type: str = "search_document",  # Ignored for OpenAI, kept for API compatibility
        model: Optional[str] = None,
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of texts to embed
            input_type: Type of input (ignored for OpenAI, kept for Cohere API compatibility)
            model: Model to use (default: text-embedding-3-small)

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        model_to_use = model or self.DEFAULT_MODEL

        try:
            # PERF-010: Further reduced batch size for 512MB Render instances
            # PERF-009 had batch_size=20, but still caused memory overflow
            # OpenAI allows ~8191 tokens, but we use 5 to stay under memory limit
            batch_size = 5
            all_embeddings = []

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                # Clean texts (OpenAI doesn't like empty strings)
                cleaned_batch = [t.strip() if t.strip() else "empty" for t in batch]

                response = await self.client.embeddings.create(
                    input=cleaned_batch,
                    model=model_to_use,
                    dimensions=self.dimension,  # text-embedding-3 models support custom dimensions
                )

                # Extract embeddings from response
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                # Small delay between batches to avoid rate limits
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)

            logger.info(f"Generated {len(all_embeddings)} embeddings using OpenAI {model_to_use}")
            return all_embeddings

        except Exception as e:
            error_msg = str(e)
            # Sanitize API key from error messages
            if self.api_key and len(self.api_key) > 10:
                error_msg = error_msg.replace(self.api_key, "[REDACTED]")
            logger.error(f"OpenAI embedding error: {error_msg}")
            raise

    async def get_embedding(self, text: str, input_type: str = "search_document") -> List[float]:
        """Get embedding for a single text."""
        embeddings = await self.get_embeddings([text], input_type=input_type)
        return embeddings[0] if embeddings else []


# Singleton instance for easy access
_embedding_provider: Optional[OpenAIEmbeddingProvider] = None


def get_openai_embeddings(api_key: str) -> OpenAIEmbeddingProvider:
    """Get or create an OpenAI embedding provider instance."""
    global _embedding_provider
    if _embedding_provider is None or _embedding_provider.api_key != api_key:
        _embedding_provider = OpenAIEmbeddingProvider(api_key=api_key)
    return _embedding_provider
