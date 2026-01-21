"""
Graph Store - Facade for Knowledge Graph Operations

This module provides a unified interface to the refactored graph storage system.
It delegates to specialized modules while maintaining backward compatibility.

ARCH-002: Refactored from 1500+ line God Object to Facade Pattern
- Persistence: EntityDAO, ChunkDAO
- Embedding: EmbeddingPipeline
- Analytics: GraphAnalytics
"""

import logging
from typing import Any, Optional, List

# Re-export dataclasses for backward compatibility
from graph.persistence.entity_dao import Node, Edge, EntityDAO
from graph.persistence.chunk_dao import ChunkDAO
from graph.embedding.embedding_pipeline import EmbeddingPipeline
from graph.analytics.graph_analytics import GraphAnalytics

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = ["GraphStore", "Node", "Edge"]


class GraphStore:
    """
    Facade for PostgreSQL-based graph storage.

    This class provides a unified interface to:
    - Entity (node) storage and retrieval (via EntityDAO)
    - Relationship (edge) storage and retrieval (via EntityDAO)
    - Vector similarity search via pgvector (via EmbeddingPipeline)
    - Graph traversal and analytics (via GraphAnalytics)
    - Semantic chunk storage (via ChunkDAO)

    The original 1500+ line implementation has been split into:
    - persistence/entity_dao.py: Entity/Relationship CRUD
    - persistence/chunk_dao.py: Chunk storage/retrieval
    - embedding/embedding_pipeline.py: Embedding operations
    - analytics/graph_analytics.py: Graph analysis
    """

    def __init__(self, db=None):
        """
        Initialize GraphStore with all sub-components.

        Args:
            db: Database instance from backend/database.py
        """
        self.db = db

        # Initialize sub-components
        self._entity_dao = EntityDAO(db)
        self._chunk_dao = ChunkDAO(db)
        self._embedding_pipeline = EmbeddingPipeline(db)
        self._analytics = GraphAnalytics(db, self._entity_dao)

    # =========================================================================
    # Entity Operations (delegated to EntityDAO)
    # =========================================================================

    async def add_entity(
        self,
        project_id: str,
        entity_type: str,
        name: str,
        properties: dict = None,
        embedding: list[float] = None,
    ) -> str:
        """Add an entity to the graph. Returns the entity ID."""
        return await self._entity_dao.add_entity(
            project_id, entity_type, name, properties, embedding
        )

    async def get_entity(self, entity_id: str) -> Optional[dict]:
        """Get a single entity by ID."""
        return await self._entity_dao.get_entity(entity_id)

    async def get_entities(
        self,
        project_id: str,
        entity_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Get entities for a project, optionally filtered by type."""
        return await self._entity_dao.get_entities(project_id, entity_type, limit, offset)

    async def store_entity(
        self,
        project_id: str,
        name: str,
        entity_type: str,
        description: str = "",
        source_paper_id: str = None,
        confidence: float = 0.5,
        properties: dict = None,
    ) -> str:
        """Store an entity in the knowledge graph (wrapper for importers)."""
        return await self._entity_dao.store_entity(
            project_id, name, entity_type, description, source_paper_id, confidence, properties
        )

    # =========================================================================
    # Relationship Operations (delegated to EntityDAO)
    # =========================================================================

    async def add_relationship(
        self,
        project_id: str,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: dict = None,
        weight: float = 1.0,
    ) -> str:
        """Add a relationship between entities. Returns the relationship ID."""
        return await self._entity_dao.add_relationship(
            project_id, source_id, target_id, relationship_type, properties, weight
        )

    async def get_relationships(
        self,
        project_id: str,
        relationship_type: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict]:
        """Get relationships for a project, optionally filtered by type."""
        return await self._entity_dao.get_relationships(
            project_id, relationship_type, limit, offset
        )

    # =========================================================================
    # Project & Paper Operations (delegated to EntityDAO)
    # =========================================================================

    async def create_project(
        self,
        name: str,
        description: str = None,
        config: dict = None,
    ) -> str:
        """Create a new project in the database. Returns the project UUID."""
        return await self._entity_dao.create_project(name, description, config)

    async def store_paper_metadata(
        self,
        project_id: str,
        title: str,
        abstract: str = "",
        authors: List[str] = None,
        year: int = None,
        doi: str = None,
        source: str = None,
        properties: dict = None,
    ) -> str:
        """Store paper metadata in the database. Returns the paper UUID."""
        return await self._entity_dao.store_paper_metadata(
            project_id, title, abstract, authors, year, doi, source, properties
        )

    # =========================================================================
    # Embedding Operations (delegated to EmbeddingPipeline)
    # =========================================================================

    async def create_embeddings(
        self,
        project_id: str,
        embedding_provider=None,
    ) -> int:
        """Create embeddings for all entities in a project."""
        return await self._embedding_pipeline.create_embeddings(project_id, embedding_provider)

    async def find_similar_entities(
        self,
        embedding: list[float],
        project_id: str,
        entity_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Find similar entities using vector similarity (pgvector)."""
        return await self._embedding_pipeline.find_similar_entities(
            embedding, project_id, entity_type, limit
        )

    # =========================================================================
    # Analytics Operations (delegated to GraphAnalytics)
    # =========================================================================

    async def get_subgraph(
        self,
        node_id: str,
        depth: int = 1,
        max_nodes: int = 50,
    ) -> dict:
        """Get subgraph centered on a node."""
        return await self._analytics.get_subgraph(node_id, depth, max_nodes)

    async def search_entities(
        self,
        query: str,
        project_id: str,
        entity_types: Optional[list[str]] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Search entities by text (fuzzy matching)."""
        return await self._analytics.search_entities(query, project_id, entity_types, limit)

    async def find_research_gaps(
        self,
        project_id: str,
        min_papers: int = 3,
    ) -> list[dict]:
        """Find research gaps - concepts with few connected papers."""
        return await self._analytics.find_research_gaps(project_id, min_papers)

    async def get_visualization_data(
        self,
        project_id: str,
        max_nodes: int = 200,
    ) -> dict:
        """Get graph data optimized for visualization."""
        return await self._analytics.get_visualization_data(
            project_id, max_nodes, self._entity_dao
        )

    async def get_stats(self, project_id: str) -> dict:
        """Get graph statistics for a project."""
        return await self._analytics.get_stats(project_id)

    async def build_concept_relationships(
        self,
        project_id: str,
        similarity_threshold: float = 0.7,
        llm_provider=None,
    ) -> int:
        """Build semantic relationships between concepts in a project."""
        return await self._analytics.build_concept_relationships(
            project_id, similarity_threshold, llm_provider, self._entity_dao
        )

    # =========================================================================
    # Chunk Operations (delegated to ChunkDAO)
    # =========================================================================

    async def store_chunks(
        self,
        project_id: str,
        paper_id: str,
        chunks: list,
        create_embeddings: bool = True,
    ) -> int:
        """Store semantic chunks from a paper."""
        return await self._chunk_dao.store_chunks(
            project_id, paper_id, chunks, create_embeddings, self._embedding_pipeline
        )

    async def create_chunk_embeddings(
        self,
        project_id: str,
        embedding_provider=None,
        batch_size: int = 50,
        use_specter: bool = False,
    ) -> int:
        """Create embeddings for chunks without embeddings."""
        return await self._embedding_pipeline.create_chunk_embeddings(
            project_id, embedding_provider, batch_size, use_specter
        )

    async def search_chunks(
        self,
        project_id: str,
        query_embedding: list,
        top_k: int = 5,
        section_filter: list = None,
        min_score: float = 0.5,
    ) -> list:
        """Search chunks by vector similarity."""
        return await self._chunk_dao.search_chunks(
            project_id, query_embedding, top_k, section_filter, min_score
        )

    async def get_chunk_with_context(
        self,
        chunk_id: str,
    ) -> dict:
        """Get a chunk with its parent context."""
        return await self._chunk_dao.get_chunk_with_context(chunk_id)

    async def get_chunks_by_paper(
        self,
        paper_id: str,
        section_type: str = None,
    ) -> list:
        """Get all chunks for a paper, optionally filtered by section."""
        return await self._chunk_dao.get_chunks_by_paper(paper_id, section_type)

    # =========================================================================
    # Backward Compatibility - Private DB Methods
    # These are kept for any external code that might be using them directly
    # =========================================================================

    async def _db_add_entity(self, node: Node) -> None:
        """Add entity to PostgreSQL. Deprecated: use add_entity() instead."""
        return await self._entity_dao._db_add_entity(node)

    async def _db_add_relationship(self, edge: Edge) -> None:
        """Add relationship to PostgreSQL. Deprecated: use add_relationship() instead."""
        return await self._entity_dao._db_add_relationship(edge)

    async def _db_get_entity(self, entity_id: str) -> Optional[dict]:
        """Get single entity from PostgreSQL. Deprecated: use get_entity() instead."""
        return await self._entity_dao._db_get_entity(entity_id)

    async def _db_get_entities(
        self, project_id: str, entity_type: Optional[str], limit: int, offset: int
    ) -> list[dict]:
        """Get entities from PostgreSQL. Deprecated: use get_entities() instead."""
        return await self._entity_dao._db_get_entities(project_id, entity_type, limit, offset)

    async def _db_get_relationships(
        self,
        project_id: str,
        relationship_type: Optional[str],
        limit: int,
        offset: int,
    ) -> list[dict]:
        """Get relationships from PostgreSQL. Deprecated: use get_relationships() instead."""
        return await self._entity_dao._db_get_relationships(
            project_id, relationship_type, limit, offset
        )

    async def _db_get_subgraph(
        self, node_id: str, depth: int, max_nodes: int
    ) -> dict:
        """Get subgraph from PostgreSQL. Deprecated: use get_subgraph() instead."""
        return await self._analytics._db_get_subgraph(node_id, depth, max_nodes)

    async def _db_search_entities(
        self,
        query_text: str,
        project_id: str,
        entity_types: Optional[list[str]],
        limit: int,
    ) -> list[dict]:
        """Search entities. Deprecated: use search_entities() instead."""
        return await self._analytics._db_search_entities(
            query_text, project_id, entity_types, limit
        )

    async def _db_find_similar(
        self,
        embedding: list[float],
        project_id: str,
        entity_type: Optional[str],
        limit: int,
    ) -> list[dict]:
        """Find similar entities. Deprecated: use find_similar_entities() instead."""
        return await self._embedding_pipeline._db_find_similar(
            embedding, project_id, entity_type, limit
        )

    async def _db_find_gaps(self, project_id: str, min_papers: int) -> list[dict]:
        """Find research gaps. Deprecated: use find_research_gaps() instead."""
        return await self._analytics._db_find_gaps(project_id, min_papers)

    async def _db_get_stats(self, project_id: str) -> dict:
        """Get graph statistics. Deprecated: use get_stats() instead."""
        return await self._analytics._db_get_stats(project_id)

    # =========================================================================
    # In-Memory Accessors (for backward compatibility)
    # =========================================================================

    @property
    def _nodes(self) -> dict[str, Node]:
        """Access in-memory nodes. Deprecated: use EntityDAO directly."""
        return self._entity_dao._nodes

    @property
    def _edges(self) -> dict[str, Edge]:
        """Access in-memory edges. Deprecated: use EntityDAO directly."""
        return self._entity_dao._edges
