"""
Graph Analytics - Graph analysis, statistics, and research gap detection.

Extracted from GraphStore for Single Responsibility Principle.
"""

import logging
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class GraphAnalytics:
    """
    Graph Analytics for analysis operations.

    Handles:
    - Graph statistics
    - Subgraph extraction
    - Entity text search
    - Research gap detection
    - Concept relationship building
    - Visualization data preparation
    """

    def __init__(self, db=None, entity_dao=None):
        """
        Initialize GraphAnalytics.

        Args:
            db: Database instance from backend/database.py
            entity_dao: EntityDAO instance for in-memory fallback
        """
        self.db = db
        self.entity_dao = entity_dao

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self, project_id: str) -> dict:
        """Get graph statistics for a project."""
        if self.db:
            return await self._db_get_stats(project_id)

        # In-memory fallback
        if not self.entity_dao:
            return {"total_nodes": 0, "total_edges": 0, "entity_counts": {}, "relationship_counts": {}}

        nodes = [n for n in self.entity_dao.nodes.values() if n.project_id == project_id]
        edges = [e for e in self.entity_dao.edges.values() if e.project_id == project_id]

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

    async def _db_get_stats(self, project_id: str) -> dict:
        """Get graph statistics from PostgreSQL."""
        node_count = await self.db.fetchval(
            "SELECT COUNT(*) FROM entities WHERE project_id = $1",
            project_id
        )
        edge_count = await self.db.fetchval(
            "SELECT COUNT(*) FROM relationships WHERE project_id = $1",
            project_id
        )

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

    # =========================================================================
    # Subgraph Extraction
    # =========================================================================

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
        if not self.entity_dao:
            return {"nodes": [], "edges": []}

        visited_nodes = {node_id}
        frontier = [node_id]
        result_edges = []

        for _ in range(depth):
            next_frontier = []
            for current_id in frontier:
                for edge in self.entity_dao.edges.values():
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

        result_nodes = [
            {
                "id": n.id,
                "entity_type": n.entity_type,
                "name": n.name,
                "properties": n.properties,
            }
            for n in self.entity_dao.nodes.values()
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

    async def _db_get_subgraph(
        self, node_id: str, depth: int, max_nodes: int
    ) -> dict:
        """Get subgraph from PostgreSQL using recursive CTE."""
        query = """
            WITH RECURSIVE subgraph AS (
                SELECT id, entity_type, name, properties, 0 AS depth
                FROM entities
                WHERE id = $1

                UNION

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

        node_ids = [str(row["id"]) for row in node_rows]

        if not node_ids:
            return {"nodes": [], "edges": []}

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

    # =========================================================================
    # Entity Search
    # =========================================================================

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
        if not self.entity_dao:
            return []

        query_lower = query.lower()
        results = []
        for node in self.entity_dao.nodes.values():
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

    # =========================================================================
    # Research Gap Detection
    # =========================================================================

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
        if not self.entity_dao:
            return []

        concept_paper_count = {}

        for edge in self.entity_dao.edges.values():
            if (
                edge.project_id == project_id
                and edge.relationship_type == "DISCUSSES_CONCEPT"
            ):
                concept_id = edge.target_id
                concept_paper_count[concept_id] = (
                    concept_paper_count.get(concept_id, 0) + 1
                )

        gaps = []
        for node in self.entity_dao.nodes.values():
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

    # =========================================================================
    # Concept Relationship Building
    # =========================================================================

    async def build_concept_relationships(
        self,
        project_id: str,
        similarity_threshold: float = 0.7,
        llm_provider=None,
        entity_dao=None,
    ) -> int:
        """
        Build semantic relationships between concepts in a project.

        Uses embedding similarity to create RELATED_TO relationships
        between concepts that are semantically similar.

        Args:
            project_id: Project ID
            similarity_threshold: Minimum cosine similarity for relationship (0-1)
            llm_provider: Optional LLM provider for advanced relationship detection
            entity_dao: EntityDAO instance for adding relationships

        Returns:
            Number of relationships created
        """
        from graph.relationship_builder import ConceptCentricRelationshipBuilder

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
                logger.info(f"Not enough concepts with embeddings: {len(rows)}")
                return 0

            # Convert to format expected by RelationshipBuilder
            concepts = []
            for row in rows:
                embedding = row["embedding"]
                if isinstance(embedding, str):
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

            # Store relationships using entity_dao if provided
            dao = entity_dao or self.entity_dao
            if not dao:
                logger.warning("No entity_dao provided for relationship storage")
                return 0

            relationships_created = 0
            for candidate in candidates:
                try:
                    await dao.add_relationship(
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

    # =========================================================================
    # Visualization Data
    # =========================================================================

    async def get_visualization_data(
        self,
        project_id: str,
        max_nodes: int = 200,
        entity_dao=None,
    ) -> dict:
        """
        Get graph data optimized for visualization.

        Returns nodes and edges in a format suitable for React Flow.
        """
        dao = entity_dao or self.entity_dao
        if not dao:
            return {"nodes": [], "edges": []}

        nodes = await dao.get_entities(project_id, limit=max_nodes)
        edges = await dao.get_relationships(project_id, limit=max_nodes * 5)

        # Filter edges to only include those connecting visible nodes
        node_ids = {n["id"] for n in nodes}
        edges = [
            e for e in edges if e["source"] in node_ids and e["target"] in node_ids
        ]

        return {"nodes": nodes, "edges": edges}
