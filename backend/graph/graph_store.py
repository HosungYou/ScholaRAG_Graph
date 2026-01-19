"""
Graph Store

PostgreSQL-based graph storage with pgvector support.
Provides methods for storing, querying, and traversing the knowledge graph.
"""

import json
import logging
from typing import Any, Optional, List
from uuid import UUID, uuid4
from dataclasses import dataclass

from graph.relationship_builder import ConceptCentricRelationshipBuilder

logger = logging.getLogger(__name__)


@dataclass
class Node:
    """Graph node representing an entity."""

    id: str
    project_id: str
    entity_type: str
    name: str
    properties: dict
    embedding: Optional[list[float]] = None


@dataclass
class Edge:
    """Graph edge representing a relationship."""

    id: str
    project_id: str
    source_id: str
    target_id: str
    relationship_type: str
    properties: dict
    weight: float = 1.0


class GraphStore:
    """
    PostgreSQL-based graph storage.

    Provides:
    - Entity (node) storage and retrieval
    - Relationship (edge) storage and retrieval
    - Vector similarity search via pgvector
    - Graph traversal queries
    """

    def __init__(self, db=None):
        """
        Initialize GraphStore.

        Args:
            db: Database instance from backend/database.py
        """
        self.db = db
        # In-memory fallback for development
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, Edge] = {}

    async def add_entity(
        self,
        project_id: str,
        entity_type: str,
        name: str,
        properties: dict = None,
        embedding: list[float] = None,
    ) -> str:
        """
        Add an entity to the graph.

        Returns the entity ID.
        """
        entity_id = str(uuid4())
        node = Node(
            id=entity_id,
            project_id=project_id,
            entity_type=entity_type,
            name=name,
            properties=properties or {},
            embedding=embedding,
        )

        if self.db:
            await self._db_add_entity(node)
        else:
            self._nodes[entity_id] = node

        return entity_id

    async def add_relationship(
        self,
        project_id: str,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: dict = None,
        weight: float = 1.0,
    ) -> str:
        """
        Add a relationship between entities.

        Returns the relationship ID.
        """
        rel_id = str(uuid4())
        edge = Edge(
            id=rel_id,
            project_id=project_id,
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            properties=properties or {},
            weight=weight,
        )

        if self.db:
            await self._db_add_relationship(edge)
        else:
            self._edges[rel_id] = edge

        return rel_id

    async def get_entity(self, entity_id: str) -> Optional[dict]:
        """Get a single entity by ID."""
        if self.db:
            return await self._db_get_entity(entity_id)

        node = self._nodes.get(entity_id)
        if node:
            return {
                "id": node.id,
                "entity_type": node.entity_type,
                "name": node.name,
                "properties": node.properties,
            }
        return None

    async def get_entities(
        self,
        project_id: str,
        entity_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Get entities for a project, optionally filtered by type."""
        if self.db:
            return await self._db_get_entities(project_id, entity_type, limit, offset)

        # In-memory fallback
        nodes = [
            n for n in self._nodes.values()
            if n.project_id == project_id
            and (entity_type is None or n.entity_type == entity_type)
        ]
        return [
            {
                "id": n.id,
                "entity_type": n.entity_type,
                "name": n.name,
                "properties": n.properties,
            }
            for n in nodes[offset : offset + limit]
        ]

    async def get_relationships(
        self,
        project_id: str,
        relationship_type: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict]:
        """Get relationships for a project, optionally filtered by type."""
        if self.db:
            return await self._db_get_relationships(
                project_id, relationship_type, limit, offset
            )

        # In-memory fallback
        edges = [
            e for e in self._edges.values()
            if e.project_id == project_id
            and (relationship_type is None or e.relationship_type == relationship_type)
        ]
        return [
            {
                "id": e.id,
                "source": e.source_id,
                "target": e.target_id,
                "relationship_type": e.relationship_type,
                "properties": e.properties,
                "weight": e.weight,
            }
            for e in edges[offset : offset + limit]
        ]

    async def get_subgraph(
        self,
        node_id: str,
        depth: int = 1,
        max_nodes: int = 50,
    ) -> dict:
        """
        Get subgraph centered on a node.

        Args:
            node_id: Center node ID
            depth: How many hops from center (1-3)
            max_nodes: Maximum nodes to return

        Returns:
            Dict with 'nodes' and 'edges' lists
        """
        if self.db:
            return await self._db_get_subgraph(node_id, depth, max_nodes)

        # In-memory BFS traversal
        visited_nodes = {node_id}
        frontier = [node_id]
        result_edges = []

        for _ in range(depth):
            next_frontier = []
            for current_id in frontier:
                # Find connected edges
                for edge in self._edges.values():
                    if edge.source_id == current_id:
                        result_edges.append(edge)
                        if edge.target_id not in visited_nodes:
                            visited_nodes.add(edge.target_id)
                            next_frontier.append(edge.target_id)
                    elif edge.target_id == current_id:
                        result_edges.append(edge)
                        if edge.source_id not in visited_nodes:
                            visited_nodes.add(edge.source_id)
                            next_frontier.append(edge.source_id)

                if len(visited_nodes) >= max_nodes:
                    break

            frontier = next_frontier
            if len(visited_nodes) >= max_nodes:
                break

        # Get node details
        result_nodes = [
            {
                "id": n.id,
                "entity_type": n.entity_type,
                "name": n.name,
                "properties": n.properties,
            }
            for n in self._nodes.values()
            if n.id in visited_nodes
        ]

        return {
            "nodes": result_nodes[:max_nodes],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source_id,
                    "target": e.target_id,
                    "relationship_type": e.relationship_type,
                }
                for e in result_edges
            ],
        }

    async def search_entities(
        self,
        query: str,
        project_id: str,
        entity_types: Optional[list[str]] = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Search entities by text (fuzzy matching).

        Args:
            query: Search query text
            project_id: Project to search in
            entity_types: Optional filter by entity types
            limit: Maximum results

        Returns:
            List of matching entities
        """
        if self.db:
            return await self._db_search_entities(query, project_id, entity_types, limit)

        # In-memory fallback: simple substring matching
        query_lower = query.lower()
        results = []
        for node in self._nodes.values():
            if node.project_id == project_id:
                if entity_types and node.entity_type not in entity_types:
                    continue
                if query_lower in node.name.lower():
                    results.append({
                        "id": node.id,
                        "entity_type": node.entity_type,
                        "name": node.name,
                        "properties": node.properties,
                    })
        return results[:limit]

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

    async def find_research_gaps(
        self,
        project_id: str,
        min_papers: int = 3,
    ) -> list[dict]:
        """
        Find research gaps - concepts with few connected papers.

        Args:
            project_id: Project to analyze
            min_papers: Concepts with fewer papers are gaps

        Returns:
            List of gap concepts with paper counts
        """
        if self.db:
            return await self._db_find_gaps(project_id, min_papers)

        # In-memory fallback
        concept_paper_count = {}

        for edge in self._edges.values():
            if (
                edge.project_id == project_id
                and edge.relationship_type == "DISCUSSES_CONCEPT"
            ):
                concept_id = edge.target_id
                concept_paper_count[concept_id] = (
                    concept_paper_count.get(concept_id, 0) + 1
                )

        gaps = []
        for node in self._nodes.values():
            if node.entity_type == "Concept" and node.project_id == project_id:
                count = concept_paper_count.get(node.id, 0)
                if count < min_papers:
                    gaps.append(
                        {
                            "id": node.id,
                            "name": node.name,
                            "paper_count": count,
                        }
                    )

        return sorted(gaps, key=lambda x: x["paper_count"])

    async def get_visualization_data(
        self,
        project_id: str,
        max_nodes: int = 200,
    ) -> dict:
        """
        Get graph data optimized for visualization.

        Returns nodes and edges in a format suitable for React Flow.
        """
        nodes = await self.get_entities(project_id, limit=max_nodes)
        edges = await self.get_relationships(project_id, limit=max_nodes * 5)

        # Filter edges to only include those connecting visible nodes
        node_ids = {n["id"] for n in nodes}
        edges = [
            e for e in edges if e["source"] in node_ids and e["target"] in node_ids
        ]

        return {"nodes": nodes, "edges": edges}

    async def get_stats(self, project_id: str) -> dict:
        """Get graph statistics for a project."""
        if self.db:
            return await self._db_get_stats(project_id)

        # In-memory fallback
        nodes = [n for n in self._nodes.values() if n.project_id == project_id]
        edges = [e for e in self._edges.values() if e.project_id == project_id]

        entity_counts = {}
        for node in nodes:
            entity_counts[node.entity_type] = entity_counts.get(node.entity_type, 0) + 1

        relationship_counts = {}
        for edge in edges:
            relationship_counts[edge.relationship_type] = (
                relationship_counts.get(edge.relationship_type, 0) + 1
            )

        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "entity_counts": entity_counts,
            "relationship_counts": relationship_counts,
        }

    async def create_project(
        self,
        name: str,
        description: str = None,
        config: dict = None,
    ) -> str:
        """
        Create a new project in the database.

        Args:
            name: Project name
            description: Research question or description
            config: Additional configuration metadata (stored in research_question as JSON note)

        Returns:
            The UUID of the created project
        """
        from uuid import uuid4
        from datetime import datetime

        project_id = uuid4()
        now = datetime.now()

        if self.db:
            # Base schema (001_init.sql): id, name, research_question, source_path, created_at, updated_at
            # Note: owner_id is added in 005_user_profiles.sql migration - not required for import
            await self.db.execute(
                """
                INSERT INTO projects (id, name, research_question, source_path, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                project_id,
                name,
                description,
                None,  # source_path
                now,
                now,
            )
            logger.info(f"Created project {project_id}: {name}")
            return str(project_id)
        else:
            # In-memory fallback
            logger.warning(f"No database - returning temporary project ID for: {name}")
            return str(project_id)

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
        """
        Store paper metadata in the database.
        
        Args:
            project_id: UUID of the project
            title: Paper title (required)
            abstract: Paper abstract
            authors: List of author names
            year: Publication year
            doi: Digital Object Identifier
            source: Source of the paper (e.g., 'zotero', 'semantic_scholar')
            properties: Additional metadata as dict
            
        Returns:
            The UUID of the stored paper
        """
        from uuid import uuid4
        from datetime import datetime
        import json
        
        paper_id = uuid4()
        
        # Convert authors to JSONB format
        authors_json = json.dumps([{"name": a} for a in (authors or [])])
        
        if self.db:
            try:
                await self.db.execute(
                    """
                    INSERT INTO paper_metadata (
                        id, project_id, title, abstract, authors, year, doi, source, created_at
                    ) VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9)
                    """,
                    paper_id,
                    project_id if isinstance(project_id, type(paper_id)) else __import__('uuid').UUID(project_id),
                    title,
                    abstract,
                    authors_json,
                    year,
                    doi,
                    source,
                    datetime.now(),
                )
                logger.info(f"Stored paper metadata: {title[:50]}...")
                return str(paper_id)
            except Exception as e:
                logger.error(f"Failed to store paper metadata: {e}")
                raise
        else:
            logger.warning(f"No database - returning temporary paper ID for: {title[:50]}")
            return str(paper_id)

    async def create_embeddings(
        self,
        project_id: str,
        embedding_provider=None,
    ) -> int:
        """
        Create embeddings for all entities in a project using Cohere.

        Args:
            project_id: UUID of the project
            embedding_provider: CohereEmbeddingProvider instance (optional, will create from config if None)

        Returns:
            Number of entities that received embeddings
        """
        import uuid as uuid_module

        logger.info(f"Embeddings creation requested for project {project_id}")

        if not self.db:
            logger.warning("No database connection - skipping embedding creation")
            return 0

        # Get or create embedding provider
        if embedding_provider is None:
            from config import settings
            if settings.cohere_api_key:
                from llm.cohere_embeddings import CohereEmbeddingProvider
                embedding_provider = CohereEmbeddingProvider(api_key=settings.cohere_api_key)
            else:
                logger.warning("No Cohere API key configured - skipping embedding creation")
                return 0

        project_uuid = uuid_module.UUID(project_id) if isinstance(project_id, str) else project_id

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
                # Create rich text for embedding: name + description/definition
                name = row["name"]
                props = row["properties"] or {}
                # Handle case where properties is a JSON string instead of dict
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

            # Update entities with embeddings
            updated_count = 0
            for i, (entity_id, embedding) in enumerate(zip(entity_ids, embeddings)):
                try:
                    # Convert embedding list to string format for pgvector
                    # asyncpg requires string format: '[0.1, 0.2, ...]'
                    embedding_str = "[" + ",".join(map(str, embedding)) + "]"
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
                except Exception as e:
                    logger.error(f"Failed to update embedding for entity {entity_id}: {e}")

            logger.info(f"Successfully created embeddings for {updated_count}/{len(rows)} entities")
            return updated_count

        except Exception as e:
            logger.error(f"Failed to create embeddings: {e}")
            return 0

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
        """
        Store an entity in the knowledge graph (wrapper for importers).
        
        Args:
            project_id: UUID of the project
            name: Entity name
            entity_type: Type of entity (Concept, Method, Finding, etc.)
            description: Entity description
            source_paper_id: UUID of the source paper
            confidence: Extraction confidence score
            properties: Additional properties
            
        Returns:
            The UUID of the stored entity
        """
        # Merge description and metadata into properties
        entity_properties = properties or {}
        if description:
            entity_properties["description"] = description
        if source_paper_id:
            entity_properties["source_paper_id"] = source_paper_id
        entity_properties["confidence"] = confidence
        
        # Use existing add_entity method
        return await self.add_entity(
            project_id=project_id,
            entity_type=entity_type,
            name=name,
            properties=entity_properties,
        )

    # =========================================================================
    # Database methods (asyncpg implementation)
    # =========================================================================

    async def _db_add_entity(self, node: Node) -> None:
        """Add entity to PostgreSQL."""
        query = """
            INSERT INTO entities (id, project_id, entity_type, name, properties, embedding)
            VALUES ($1, $2, $3::entity_type, $4, $5, $6)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                properties = EXCLUDED.properties,
                embedding = EXCLUDED.embedding,
                updated_at = NOW()
        """
        embedding_str = None
        if node.embedding:
            embedding_str = f"[{','.join(map(str, node.embedding))}]"

        await self.db.execute(
            query,
            node.id,
            node.project_id,
            node.entity_type,
            node.name,
            json.dumps(node.properties),
            embedding_str,
        )

    async def _db_add_relationship(self, edge: Edge) -> None:
        """Add relationship to PostgreSQL."""
        query = """
            INSERT INTO relationships (id, project_id, source_id, target_id, relationship_type, properties, weight)
            VALUES ($1, $2, $3, $4, $5::relationship_type, $6, $7)
            ON CONFLICT (source_id, target_id, relationship_type) DO UPDATE SET
                properties = EXCLUDED.properties,
                weight = EXCLUDED.weight
        """
        await self.db.execute(
            query,
            edge.id,
            edge.project_id,
            edge.source_id,
            edge.target_id,
            edge.relationship_type,
            json.dumps(edge.properties),
            edge.weight,
        )

    async def _db_get_entity(self, entity_id: str) -> Optional[dict]:
        """Get single entity from PostgreSQL."""
        query = """
            SELECT id, project_id, entity_type, name, properties
            FROM entities
            WHERE id = $1
        """
        row = await self.db.fetchrow(query, entity_id)
        if row:
            return {
                "id": str(row["id"]),
                "project_id": str(row["project_id"]),
                "entity_type": row["entity_type"],
                "name": row["name"],
                "properties": row["properties"] or {},
            }
        return None

    async def _db_get_entities(
        self, project_id: str, entity_type: Optional[str], limit: int, offset: int
    ) -> list[dict]:
        """Get entities from PostgreSQL."""
        if entity_type:
            query = """
                SELECT id, entity_type, name, properties
                FROM entities
                WHERE project_id = $1 AND entity_type = $2::entity_type
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
            """
            rows = await self.db.fetch(query, project_id, entity_type, limit, offset)
        else:
            query = """
                SELECT id, entity_type, name, properties
                FROM entities
                WHERE project_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            rows = await self.db.fetch(query, project_id, limit, offset)

        return [
            {
                "id": str(row["id"]),
                "entity_type": row["entity_type"],
                "name": row["name"],
                "properties": row["properties"] or {},
            }
            for row in rows
        ]

    async def _db_get_relationships(
        self,
        project_id: str,
        relationship_type: Optional[str],
        limit: int,
        offset: int,
    ) -> list[dict]:
        """Get relationships from PostgreSQL."""
        if relationship_type:
            query = """
                SELECT id, source_id, target_id, relationship_type, properties, weight
                FROM relationships
                WHERE project_id = $1 AND relationship_type = $2::relationship_type
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
            """
            rows = await self.db.fetch(query, project_id, relationship_type, limit, offset)
        else:
            query = """
                SELECT id, source_id, target_id, relationship_type, properties, weight
                FROM relationships
                WHERE project_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            rows = await self.db.fetch(query, project_id, limit, offset)

        return [
            {
                "id": str(row["id"]),
                "source": str(row["source_id"]),
                "target": str(row["target_id"]),
                "relationship_type": row["relationship_type"],
                "properties": row["properties"] or {},
                "weight": row["weight"],
            }
            for row in rows
        ]

    async def _db_get_subgraph(
        self, node_id: str, depth: int, max_nodes: int
    ) -> dict:
        """Get subgraph from PostgreSQL using recursive CTE."""
        query = """
            WITH RECURSIVE subgraph AS (
                -- Base case: starting node
                SELECT id, entity_type, name, properties, 0 AS depth
                FROM entities
                WHERE id = $1

                UNION

                -- Recursive case: connected nodes
                SELECT DISTINCT e.id, e.entity_type, e.name, e.properties, sg.depth + 1
                FROM entities e
                JOIN relationships r ON (e.id = r.source_id OR e.id = r.target_id)
                JOIN subgraph sg ON (
                    (r.source_id = sg.id AND e.id = r.target_id) OR
                    (r.target_id = sg.id AND e.id = r.source_id)
                )
                WHERE sg.depth < $2
            )
            SELECT DISTINCT id, entity_type, name, properties
            FROM subgraph
            LIMIT $3
        """
        node_rows = await self.db.fetch(query, node_id, depth, max_nodes)

        # Get node IDs for edge filtering
        node_ids = [str(row["id"]) for row in node_rows]

        if not node_ids:
            return {"nodes": [], "edges": []}

        # Get edges between these nodes
        edge_query = """
            SELECT id, source_id, target_id, relationship_type, properties
            FROM relationships
            WHERE source_id = ANY($1::uuid[]) AND target_id = ANY($1::uuid[])
        """
        edge_rows = await self.db.fetch(edge_query, node_ids)

        return {
            "nodes": [
                {
                    "id": str(row["id"]),
                    "entity_type": row["entity_type"],
                    "name": row["name"],
                    "properties": row["properties"] or {},
                }
                for row in node_rows
            ],
            "edges": [
                {
                    "id": str(row["id"]),
                    "source": str(row["source_id"]),
                    "target": str(row["target_id"]),
                    "relationship_type": row["relationship_type"],
                }
                for row in edge_rows
            ],
        }

    async def _db_search_entities(
        self,
        query_text: str,
        project_id: str,
        entity_types: Optional[list[str]],
        limit: int,
    ) -> list[dict]:
        """Search entities using trigram similarity."""
        if entity_types:
            query = """
                SELECT id, entity_type, name, properties,
                       similarity(name, $1) AS sim
                FROM entities
                WHERE project_id = $2
                  AND entity_type = ANY($3::entity_type[])
                  AND (name ILIKE '%' || $1 || '%' OR similarity(name, $1) > 0.1)
                ORDER BY sim DESC
                LIMIT $4
            """
            rows = await self.db.fetch(query, query_text, project_id, entity_types, limit)
        else:
            query = """
                SELECT id, entity_type, name, properties,
                       similarity(name, $1) AS sim
                FROM entities
                WHERE project_id = $2
                  AND (name ILIKE '%' || $1 || '%' OR similarity(name, $1) > 0.1)
                ORDER BY sim DESC
                LIMIT $3
            """
            rows = await self.db.fetch(query, query_text, project_id, limit)

        return [
            {
                "id": str(row["id"]),
                "entity_type": row["entity_type"],
                "name": row["name"],
                "properties": row["properties"] or {},
                "score": float(row["sim"]) if row["sim"] else 0.0,
            }
            for row in rows
        ]

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

    async def _db_find_gaps(self, project_id: str, min_papers: int) -> list[dict]:
        """Find research gaps from PostgreSQL."""
        query = """
            SELECT * FROM find_research_gaps($1, $2)
        """
        rows = await self.db.fetch(query, project_id, min_papers)

        return [
            {
                "id": str(row["concept_id"]),
                "name": row["concept_name"],
                "paper_count": int(row["paper_count"]),
            }
            for row in rows
        ]

    async def _db_get_stats(self, project_id: str) -> dict:
        """Get graph statistics from PostgreSQL."""
        # Total counts
        node_count = await self.db.fetchval(
            "SELECT COUNT(*) FROM entities WHERE project_id = $1",
            project_id
        )
        edge_count = await self.db.fetchval(
            "SELECT COUNT(*) FROM relationships WHERE project_id = $1",
            project_id
        )

        # Entity type breakdown
        entity_rows = await self.db.fetch(
            """
            SELECT entity_type, COUNT(*) as count
            FROM entities
            WHERE project_id = $1
            GROUP BY entity_type
            """,
            project_id
        )
        entity_counts = {row["entity_type"]: int(row["count"]) for row in entity_rows}

        # Relationship type breakdown
        rel_rows = await self.db.fetch(
            """
            SELECT relationship_type, COUNT(*) as count
            FROM relationships
            WHERE project_id = $1
            GROUP BY relationship_type
            """,
            project_id
        )
        relationship_counts = {row["relationship_type"]: int(row["count"]) for row in rel_rows}

        return {
            "total_nodes": int(node_count) if node_count else 0,
            "total_edges": int(edge_count) if edge_count else 0,
            "entity_counts": entity_counts,
            "relationship_counts": relationship_counts,
        }

    async def build_concept_relationships(
        self,
        project_id: str,
        similarity_threshold: float = 0.7,
        llm_provider=None,
    ) -> int:
        """
        Build semantic relationships between concepts in a project.

        Uses embedding similarity to create RELATED_TO relationships
        between concepts that are semantically similar.

        Args:
            project_id: Project ID
            similarity_threshold: Minimum cosine similarity for relationship (0-1)
            llm_provider: Optional LLM provider for advanced relationship detection

        Returns:
            Number of relationships created
        """
        try:
            # Get all concepts with embeddings from the project
            query = """
                SELECT id, name, embedding
                FROM entities
                WHERE project_id = $1
                  AND entity_type = 'Concept'
                  AND embedding IS NOT NULL
            """
            project_uuid = UUID(project_id) if isinstance(project_id, str) else project_id
            rows = await self.db.fetch(query, project_uuid)

            if len(rows) < 2:
                logger.info(f"Not enough concepts with embeddings for relationship building: {len(rows)}")
                return 0

            # Convert to format expected by RelationshipBuilder
            concepts = []
            for row in rows:
                embedding = row["embedding"]
                # Handle embedding format (could be list or string)
                if isinstance(embedding, str):
                    # Parse pgvector format: "[0.1, 0.2, ...]"
                    embedding = [float(x) for x in embedding.strip("[]").split(",")]
                concepts.append({
                    "id": str(row["id"]),
                    "name": row["name"],
                    "embedding": embedding,
                })

            logger.info(f"Building relationships for {len(concepts)} concepts")

            # Use RelationshipBuilder for semantic relationships
            builder = ConceptCentricRelationshipBuilder(
                llm_provider=llm_provider,
                similarity_threshold=similarity_threshold,
            )
            candidates = builder.build_semantic_relationships(
                concepts=concepts,
                similarity_threshold=similarity_threshold,
            )

            # Store relationships
            relationships_created = 0
            for candidate in candidates:
                try:
                    await self.add_relationship(
                        project_id=project_id,
                        source_id=candidate.source_id,
                        target_id=candidate.target_id,
                        relationship_type=candidate.relationship_type,
                        properties={
                            "confidence": candidate.confidence,
                            "auto_generated": True,
                            **candidate.properties,
                        },
                        weight=candidate.confidence,
                    )
                    relationships_created += 1
                except Exception as e:
                    logger.warning(f"Failed to create relationship: {e}")

            logger.info(f"Created {relationships_created} semantic relationships")
            return relationships_created

        except Exception as e:
            logger.error(f"Error building concept relationships: {e}")
            return 0
