"""
Embedding Pipeline - Vector embedding creation and similarity search.

Extracted from GraphStore for Single Responsibility Principle.

BUG-040 (2026-01-21): Added fallback from Cohere to OpenAI on failure
PERF-012 (2026-01-21): Changed primary provider to OpenAI (6x cheaper, more stable)
"""

import json
import logging
from typing import Optional, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)


class EmbeddingPipeline:
    """
    Embedding Pipeline for vector operations.

    Handles:
    - Entity embedding creation (OpenAI/Cohere with fallback)
    - Chunk embedding creation (OpenAI/Cohere/SPECTER2 with fallback)
    - Vector similarity search

    Embedding Provider Priority (PERF-012: Changed 2026-01-21):
    1. OpenAI (if OPENAI_API_KEY set) - $0.02/1M tokens, most stable
    2. Cohere (if COHERE_API_KEY set) - $0.12/1M tokens, fallback
    3. Skip embeddings (if no provider available)

    Cost comparison: OpenAI is 6x cheaper than Cohere ($0.02 vs $0.12 per 1M tokens)
    """

    def __init__(self, db=None):
        """
        Initialize EmbeddingPipeline.

        Args:
            db: Database instance from backend/database.py
        """
        self.db = db

    # =========================================================================
    # Embedding Provider Selection
    # =========================================================================

    def _get_embedding_provider(self, prefer_cohere: bool = False):
        """
        Get the best available embedding provider with fallback logic.

        Priority order (PERF-012: Changed 2026-01-21):
        1. OpenAI (if OPENAI_API_KEY available) - $0.02/1M tokens, most stable
        2. Cohere (if COHERE_API_KEY available) - $0.12/1M tokens, fallback
        3. None (skip embeddings)

        Args:
            prefer_cohere: If True, skip OpenAI and use Cohere directly (for fallback)

        Returns:
            Embedding provider instance or None if no provider available
        """
        from config import settings

        # PERF-012: Priority 1: OpenAI (cheaper and more stable)
        if settings.openai_api_key and not prefer_cohere:
            from llm.openai_embeddings import OpenAIEmbeddingProvider
            logger.info("Using OpenAI for embeddings (primary provider, $0.02/1M tokens)")
            return OpenAIEmbeddingProvider(api_key=settings.openai_api_key)

        # Priority 2: Cohere (fallback)
        if settings.cohere_api_key:
            from llm.cohere_embeddings import CohereEmbeddingProvider
            if prefer_cohere:
                logger.info("Using Cohere for embeddings (fallback from OpenAI)")
            else:
                logger.info("Using Cohere for embeddings (OpenAI not available)")
            return CohereEmbeddingProvider(api_key=settings.cohere_api_key)

        # No provider available
        logger.warning(
            "No embedding provider available - skipping embedding creation. "
            "Set OPENAI_API_KEY (recommended) or COHERE_API_KEY to enable embeddings."
        )
        return None

    def _get_embedding_providers(self) -> Tuple[Optional[object], Optional[object]]:
        """
        BUG-040/PERF-012: Get primary and fallback embedding providers.

        PERF-012: Changed provider priority (2026-01-21)
        - OpenAI: $0.02/1M tokens (6x cheaper), more stable
        - Cohere: $0.12/1M tokens, used as fallback

        Returns:
            Tuple of (primary_provider, fallback_provider)
            Either can be None if not available
        """
        from config import settings

        primary = None
        fallback = None

        # PERF-012: Primary: OpenAI (cheaper and more stable)
        if settings.openai_api_key:
            from llm.openai_embeddings import OpenAIEmbeddingProvider
            primary = OpenAIEmbeddingProvider(api_key=settings.openai_api_key)
            logger.info("Primary embedding provider: OpenAI ($0.02/1M tokens)")

        # Fallback: Cohere
        if settings.cohere_api_key:
            from llm.cohere_embeddings import CohereEmbeddingProvider
            fallback = CohereEmbeddingProvider(api_key=settings.cohere_api_key)
            if primary:
                logger.info("Fallback embedding provider: Cohere")

        # If no OpenAI, use Cohere as primary
        if primary is None and fallback is not None:
            primary = fallback
            fallback = None
            logger.info("Primary embedding provider: Cohere (OpenAI not available)")

        return primary, fallback

    # =========================================================================
    # Entity Embeddings
    # =========================================================================

    async def create_embeddings(
        self,
        project_id: str,
        embedding_provider=None,
    ) -> int:
        """
        Create embeddings for all entities in a project.

        Supports multiple embedding providers with fallback:
        1. Cohere (if COHERE_API_KEY available) - FREE tier available
        2. OpenAI (if OPENAI_API_KEY available) - Paid fallback
        3. Skip embeddings if no provider available

        Args:
            project_id: UUID of the project
            embedding_provider: Pre-configured embedding provider instance (optional)

        Returns:
            Number of entities that received embeddings
        """
        logger.info(f"Embeddings creation requested for project {project_id}")

        if not self.db:
            logger.warning("No database connection - skipping embedding creation")
            return 0

        # Get or create embedding provider with fallback logic
        if embedding_provider is None:
            embedding_provider = self._get_embedding_provider()
            if embedding_provider is None:
                return 0

        project_uuid = UUID(project_id) if isinstance(project_id, str) else project_id

        try:
            # Fetch entities without embeddings
            rows = await self.db.fetch(
                """
                SELECT id, name, entity_type, properties
                FROM entities
                WHERE project_id = $1 AND embedding IS NULL
                ORDER BY created_at
                """,
                project_uuid,
            )

            if not rows:
                logger.info(f"No entities need embeddings in project {project_id}")
                return 0

            logger.info(f"Generating embeddings for {len(rows)} entities")

            # Prepare texts for embedding
            texts = []
            entity_ids = []
            for row in rows:
                name = row["name"]
                props = row["properties"] or {}
                if isinstance(props, str):
                    try:
                        props = json.loads(props)
                    except (json.JSONDecodeError, TypeError):
                        props = {}
                definition = props.get("definition", props.get("description", ""))
                entity_type = row["entity_type"]

                text = f"{entity_type}: {name}"
                if definition:
                    text += f" - {definition}"

                texts.append(text)
                entity_ids.append(row["id"])

            # Generate embeddings in batches
            embeddings = await embedding_provider.get_embeddings(
                texts,
                input_type="search_document",
            )

            # PERF-008: Batch update entities with embeddings using executemany
            batch_data = []
            for entity_id, embedding in zip(entity_ids, embeddings):
                embedding_str = "[" + ",".join(map(str, embedding)) + "]"
                batch_data.append((embedding_str, entity_id))

            try:
                await self.db.executemany(
                    """
                    UPDATE entities
                    SET embedding = $1::vector, updated_at = NOW()
                    WHERE id = $2
                    """,
                    batch_data,
                )
                updated_count = len(batch_data)
            except Exception as e:
                logger.error(f"Batch embedding update failed: {e}")
                # Fallback to individual updates
                updated_count = 0
                for embedding_str, entity_id in batch_data:
                    try:
                        await self.db.execute(
                            """
                            UPDATE entities
                            SET embedding = $1::vector, updated_at = NOW()
                            WHERE id = $2
                            """,
                            embedding_str,
                            entity_id,
                        )
                        updated_count += 1
                    except Exception as inner_e:
                        logger.error(f"Failed to update embedding for entity {entity_id}: {inner_e}")

            logger.info(f"Successfully created embeddings for {updated_count}/{len(rows)} entities")
            return updated_count

        except Exception as e:
            # BUG-038: Better error logging - capture exception type
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else "(no message)"
            logger.error(f"Failed to create embeddings ({error_type}): {error_msg}")
            return 0

    # =========================================================================
    # Chunk Embeddings
    # =========================================================================

    async def create_chunk_embeddings(
        self,
        project_id: str,
        embedding_provider=None,
        batch_size: int = 5,  # PERF-010: Further reduced for 512MB memory limit
        use_specter: bool = False,
    ) -> int:
        """
        Create embeddings for chunks without embeddings.

        Args:
            project_id: Project UUID
            embedding_provider: Optional custom embedding provider
            batch_size: Number of chunks to embed at once
            use_specter: If True, use SPECTER2 for academic embeddings

        Returns:
            Number of embeddings created
        """
        if not self.db:
            return 0

        project_uuid = UUID(project_id) if isinstance(project_id, str) else project_id

        # Get chunks without embeddings
        rows = await self.db.fetch(
            """
            SELECT id, text
            FROM semantic_chunks
            WHERE project_id = $1 AND embedding IS NULL
            ORDER BY created_at
            """,
            project_uuid,
        )

        if not rows:
            logger.info("No chunks need embeddings")
            return 0

        # BUG-040: Get primary and fallback providers
        primary_provider = None
        fallback_provider = None

        if not embedding_provider:
            if use_specter:
                try:
                    from llm.embedding_factory import get_embedding_factory, EmbeddingProvider
                    factory = get_embedding_factory()
                except ImportError:
                    logger.warning("SPECTER2 not available, falling back to standard embeddings")
                    use_specter = False

            if not use_specter:
                primary_provider, fallback_provider = self._get_embedding_providers()
                if primary_provider is None:
                    logger.warning("No embedding provider available - skipping chunk embeddings")
                    return 0
                embedding_provider = primary_provider
        else:
            primary_provider = embedding_provider

        embeddings_created = 0
        provider_failed = False  # BUG-040: Track if primary provider failed

        # Process in batches
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            texts = [row["text"] for row in batch]
            ids = [row["id"] for row in batch]

            try:
                if use_specter and not embedding_provider:
                    from llm.embedding_factory import get_embedding_factory, EmbeddingProvider
                    factory = get_embedding_factory()
                    result = await factory.get_embeddings(
                        texts, provider=EmbeddingProvider.SPECTER
                    )
                    embeddings = result.embeddings
                else:
                    embeddings = await embedding_provider.get_embeddings(
                        texts, input_type="search_document"
                    )

                # PERF-008: Batch update chunks with embeddings
                # Convert embedding list to string format for pgvector
                batch_data = []
                for chunk_id, embedding in zip(ids, embeddings):
                    embedding_str = "[" + ",".join(map(str, embedding)) + "]"
                    batch_data.append((embedding_str, chunk_id))
                try:
                    await self.db.executemany(
                        """
                        UPDATE semantic_chunks
                        SET embedding = $1::vector
                        WHERE id = $2
                        """,
                        batch_data,
                    )
                    embeddings_created += len(batch_data)
                except Exception as batch_e:
                    logger.warning(f"Batch chunk embedding update failed: {batch_e}, falling back")
                    for embedding_str, chunk_id in batch_data:
                        try:
                            await self.db.execute(
                                """
                                UPDATE semantic_chunks
                                SET embedding = $1::vector
                                WHERE id = $2
                                """,
                                embedding_str,
                                chunk_id,
                            )
                            embeddings_created += 1
                        except Exception as inner_e:
                            logger.error(f"Failed to update embedding for chunk {chunk_id}: {inner_e}")

            except Exception as e:
                # BUG-038/040: Better error logging - capture exception type
                error_type = type(e).__name__
                error_msg = str(e) if str(e) else "(no message)"
                logger.error(f"Failed to create chunk embeddings ({error_type}): {error_msg}")

                # BUG-040: Try fallback provider if available and not already using it
                if fallback_provider and embedding_provider is not fallback_provider and not provider_failed:
                    logger.warning(f"BUG-040: Primary embedding provider failed, switching to fallback")
                    embedding_provider = fallback_provider
                    provider_failed = True  # Only try fallback once

                    # Retry this batch with fallback provider
                    try:
                        embeddings = await embedding_provider.get_embeddings(
                            texts, input_type="search_document"
                        )
                        batch_data = []
                        for chunk_id, embedding in zip(ids, embeddings):
                            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
                            batch_data.append((embedding_str, chunk_id))
                        await self.db.executemany(
                            """
                            UPDATE semantic_chunks
                            SET embedding = $1::vector
                            WHERE id = $2
                            """,
                            batch_data,
                        )
                        embeddings_created += len(batch_data)
                        logger.info(f"BUG-040: Fallback provider succeeded for batch {i // batch_size + 1}")
                    except Exception as fallback_e:
                        fallback_error_type = type(fallback_e).__name__
                        fallback_error_msg = str(fallback_e) if str(fallback_e) else "(no message)"
                        logger.error(f"BUG-040: Fallback provider also failed ({fallback_error_type}): {fallback_error_msg}")

        logger.info(f"Created {embeddings_created} chunk embeddings (specter={use_specter})")
        return embeddings_created

    # =========================================================================
    # Vector Similarity Search
    # =========================================================================

    async def find_similar_entities(
        self,
        embedding: list[float],
        project_id: str,
        entity_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Find similar entities using vector similarity (pgvector).

        Args:
            embedding: Query embedding vector
            project_id: Project to search in
            entity_type: Optional filter by entity type
            limit: Maximum results

        Returns:
            List of similar entities with similarity scores
        """
        if self.db:
            return await self._db_find_similar(
                embedding, project_id, entity_type, limit
            )

        # Fallback: no similarity search without pgvector
        return []

    async def _db_find_similar(
        self,
        embedding: list[float],
        project_id: str,
        entity_type: Optional[str],
        limit: int,
    ) -> list[dict]:
        """Find similar entities using pgvector."""
        embedding_str = f"[{','.join(map(str, embedding))}]"

        if entity_type:
            query = """
                SELECT id, entity_type, name, properties,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM entities
                WHERE project_id = $2
                  AND entity_type = $3::entity_type
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> $1::vector
                LIMIT $4
            """
            rows = await self.db.fetch(query, embedding_str, project_id, entity_type, limit)
        else:
            query = """
                SELECT id, entity_type, name, properties,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM entities
                WHERE project_id = $2
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> $1::vector
                LIMIT $3
            """
            rows = await self.db.fetch(query, embedding_str, project_id, limit)

        return [
            {
                "id": str(row["id"]),
                "entity_type": row["entity_type"],
                "name": row["name"],
                "properties": row["properties"] or {},
                "similarity": float(row["similarity"]),
            }
            for row in rows
        ]
