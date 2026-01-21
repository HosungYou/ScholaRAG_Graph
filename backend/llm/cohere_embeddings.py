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
        """Lazy load the Cohere V2 client (required for output_dimension support)."""
        if self._client is None:
            try:
                import cohere
                # Use AsyncClientV2 for embed-v4.0 output_dimension support
                self._client = cohere.AsyncClientV2(api_key=self.api_key)
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
            # PERF-010: Further reduced batch size for 512MB Render instances
            # PERF-009 had batch_size=20, but still caused memory overflow
            # Cohere API allows up to 96, but we use 5 to stay under memory limit
            batch_size = 5
            all_embeddings = []
            # BUG-038: Track slow API calls
            slow_call_count = 0
            max_slow_calls = 3  # If 3+ calls take >10s, something is wrong

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                # Clean texts (Cohere doesn't like empty strings)
                cleaned_batch = [t.strip() if t.strip() else "empty" for t in batch]

                # Build embed kwargs for V2 API - embed-v4.0 supports output_dimension
                embed_kwargs = {
                    "texts": cleaned_batch,
                    "model": model_to_use,
                    "input_type": input_type,
                    "embedding_types": ["float"],  # Required for V2 API
                }

                # Add output_dimension for v4 models (V2 API feature)
                if "v4" in model_to_use:
                    embed_kwargs["output_dimension"] = self.dimension

                # BUG-038: Add timeout to prevent blocking during rate limits
                import time
                start_time = time.time()
                try:
                    response = await asyncio.wait_for(
                        self.client.embed(**embed_kwargs),
                        timeout=30.0  # 30 second timeout per batch
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Cohere API timeout after 30s for batch {i//batch_size + 1}")
                    raise RuntimeError(f"Cohere API timeout (batch {i//batch_size + 1})")

                elapsed = time.time() - start_time
                if elapsed > 10.0:
                    slow_call_count += 1
                    logger.warning(f"Cohere API slow: {elapsed:.1f}s for batch {i//batch_size + 1}")
                    if slow_call_count >= max_slow_calls:
                        logger.error(f"Too many slow Cohere API calls ({slow_call_count}), stopping")
                        raise RuntimeError(f"Cohere API rate limited or unavailable ({slow_call_count} slow calls)")

                # V2 API returns embeddings via response.embeddings.float
                all_embeddings.extend(response.embeddings.float)

                # Small delay between batches to avoid rate limits
                if i + batch_size < len(texts):
                    # BUG-038: Increase delay if API is slow
                    delay = 0.5 if slow_call_count > 0 else 0.1
                    await asyncio.sleep(delay)

            logger.info(f"Generated {len(all_embeddings)} embeddings using Cohere {model_to_use}")
            return all_embeddings

        except Exception as e:
            # BUG-038: Better error logging - capture exception type and message
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else "(no message)"
            # Sanitize API key from error messages
            if self.api_key and len(self.api_key) > 10:
                error_msg = error_msg.replace(self.api_key, "[REDACTED]")
            logger.error(f"Cohere embedding error ({error_type}): {error_msg}")
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
