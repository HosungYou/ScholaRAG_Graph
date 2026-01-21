"""
Cohere Embedding Provider

FREE TIER: 1,000 API calls/month
Supports 1536 dimensions (matches OpenAI text-embedding-3-small)

Get API key: https://dashboard.cohere.com/api-keys

BUG-040 (2026-01-21): Added retry logic with exponential backoff for network errors
"""

import logging
import time
from typing import List, Optional
import asyncio

logger = logging.getLogger(__name__)

# BUG-040: Retryable exception types (network-level errors)
RETRYABLE_EXCEPTIONS = (
    asyncio.TimeoutError,
    ConnectionError,
    OSError,  # Includes socket errors
)

# Try to import httpx exceptions if available
try:
    import httpx
    RETRYABLE_EXCEPTIONS = RETRYABLE_EXCEPTIONS + (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
    )
except ImportError:
    pass

# Try to import httpcore exceptions if available
try:
    import httpcore
    RETRYABLE_EXCEPTIONS = RETRYABLE_EXCEPTIONS + (
        httpcore.ConnectError,
        httpcore.ConnectTimeout,
        httpcore.ReadTimeout,
    )
except ImportError:
    pass


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

        # PERF-010: Further reduced batch size for 512MB Render instances
        # PERF-009 had batch_size=20, but still caused memory overflow
        # Cohere API allows up to 96, but we use 5 to stay under memory limit
        batch_size = 5
        all_embeddings = []
        # BUG-038: Track slow API calls
        slow_call_count = 0
        max_slow_calls = 3  # If 3+ calls take >10s, something is wrong
        # BUG-040: Retry configuration
        max_retries = 3
        total_retries = 0
        max_total_retries = 5  # Stop if too many retries across all batches

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = i // batch_size + 1

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

            # BUG-040: Retry loop with exponential backoff
            response = None
            last_error = None
            for attempt in range(max_retries):
                start_time = time.time()
                try:
                    # BUG-038: Add timeout to prevent blocking during rate limits
                    response = await asyncio.wait_for(
                        self.client.embed(**embed_kwargs),
                        timeout=30.0  # 30 second timeout per batch
                    )
                    break  # Success, exit retry loop

                except RETRYABLE_EXCEPTIONS as e:
                    # BUG-040: Network error - retry with exponential backoff
                    last_error = e
                    total_retries += 1
                    error_type = type(e).__name__
                    error_msg = str(e) if str(e) else "(no message)"

                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # 1s, 2s, 4s
                        logger.warning(
                            f"Cohere API {error_type} for batch {batch_num}, "
                            f"retry {attempt + 1}/{max_retries} after {wait_time}s: {error_msg}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"Cohere API {error_type} for batch {batch_num}, "
                            f"all {max_retries} retries exhausted: {error_msg}"
                        )

                    # BUG-040: Stop if too many retries across all batches
                    if total_retries >= max_total_retries:
                        logger.error(f"Too many total retries ({total_retries}), aborting embedding creation")
                        raise RuntimeError(
                            f"Cohere API unstable: {total_retries} retries exceeded. Last error: {error_type}"
                        ) from last_error

                except Exception as e:
                    # Non-retryable error (API error, validation error, etc.)
                    error_type = type(e).__name__
                    error_msg = str(e) if str(e) else "(no message)"
                    # Sanitize API key from error messages
                    if self.api_key and len(self.api_key) > 10:
                        error_msg = error_msg.replace(self.api_key, "[REDACTED]")
                    logger.error(f"Cohere embedding error ({error_type}): {error_msg}")
                    raise

            # Check if all retries failed
            if response is None:
                raise RuntimeError(
                    f"Cohere API failed for batch {batch_num} after {max_retries} retries"
                ) from last_error

            elapsed = time.time() - start_time
            if elapsed > 10.0:
                slow_call_count += 1
                logger.warning(f"Cohere API slow: {elapsed:.1f}s for batch {batch_num}")
                if slow_call_count >= max_slow_calls:
                    logger.error(f"Too many slow Cohere API calls ({slow_call_count}), stopping")
                    raise RuntimeError(f"Cohere API rate limited or unavailable ({slow_call_count} slow calls)")

            # V2 API returns embeddings via response.embeddings.float
            all_embeddings.extend(response.embeddings.float)

            # Small delay between batches to avoid rate limits
            if i + batch_size < len(texts):
                # BUG-038: Increase delay if API is slow or retries occurred
                delay = 0.5 if (slow_call_count > 0 or total_retries > 0) else 0.1
                await asyncio.sleep(delay)

        if total_retries > 0:
            logger.info(f"Generated {len(all_embeddings)} embeddings using Cohere {model_to_use} (with {total_retries} retries)")
        else:
            logger.info(f"Generated {len(all_embeddings)} embeddings using Cohere {model_to_use}")
        return all_embeddings

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
