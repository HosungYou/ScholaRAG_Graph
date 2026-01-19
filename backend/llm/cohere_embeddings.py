"""
Cohere Embedding Provider

FREE TIER: 1,000 API calls/month
Supports 1536 dimensions (matches OpenAI text-embedding-3-small)

Get API key: https://dashboard.cohere.com/api-keys
"""

import logging
from typing import List, Optional
import asyncio

logger = logging.getLogger(__name__)


class CohereEmbeddingProvider:
    """
    Cohere embedding provider for vector embeddings.

    Uses embed-v4.0 model which supports 1536 dimensions.
    """

    # Cohere embed-v4.0 supports: 256, 512, 1024, 1536
    DEFAULT_DIMENSION = 1536
    DEFAULT_MODEL = "embed-v4.0"  # Use v4 for 1536 dimension support

    def __init__(self, api_key: str, dimension: int = DEFAULT_DIMENSION):
        self.api_key = api_key
        self.dimension = dimension
        self._client = None

    @property
    def client(self):
        """Lazy load the Cohere client."""
        if self._client is None:
            try:
                import cohere
                self._client = cohere.AsyncClient(api_key=self.api_key)
            except ImportError:
                raise ImportError("cohere package required: pip install cohere")
        return self._client

    async def get_embeddings(
        self,
        texts: List[str],
        input_type: str = "search_document",
        model: Optional[str] = None,
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of texts to embed
            input_type: Type of input - "search_document", "search_query",
                       "classification", or "clustering"
            model: Model to use (default: embed-english-v3.0)

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        model_to_use = model or self.DEFAULT_MODEL

        try:
            # Cohere has a limit of 96 texts per request
            batch_size = 96
            all_embeddings = []

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                # Clean texts (Cohere doesn't like empty strings)
                cleaned_batch = [t.strip() if t.strip() else "empty" for t in batch]

                # Build embed kwargs - embed-v4.0 supports output_dimensions
                embed_kwargs = {
                    "texts": cleaned_batch,
                    "model": model_to_use,
                    "input_type": input_type,
                    "truncate": "END",  # Truncate long texts from end
                }

                # Only add output_dimension for v4 models that support it
                # Note: parameter is singular "output_dimension", not plural
                if "v4" in model_to_use:
                    embed_kwargs["output_dimension"] = self.dimension

                response = await self.client.embed(**embed_kwargs)

                all_embeddings.extend(response.embeddings)

                # Small delay between batches to avoid rate limits
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)

            logger.info(f"Generated {len(all_embeddings)} embeddings using Cohere {model_to_use}")
            return all_embeddings

        except Exception as e:
            error_msg = str(e)
            # Sanitize API key from error messages
            if self.api_key and len(self.api_key) > 10:
                error_msg = error_msg.replace(self.api_key, "[REDACTED]")
            logger.error(f"Cohere embedding error: {error_msg}")
            raise

    async def get_embedding(self, text: str, input_type: str = "search_document") -> List[float]:
        """Get embedding for a single text."""
        embeddings = await self.get_embeddings([text], input_type=input_type)
        return embeddings[0] if embeddings else []


# Singleton instance for easy access
_embedding_provider: Optional[CohereEmbeddingProvider] = None


def get_cohere_embeddings(api_key: str) -> CohereEmbeddingProvider:
    """Get or create a Cohere embedding provider instance."""
    global _embedding_provider
    if _embedding_provider is None or _embedding_provider.api_key != api_key:
        _embedding_provider = CohereEmbeddingProvider(api_key=api_key)
    return _embedding_provider
