"""
Graph API Router

Handles knowledge graph queries and visualization data with PostgreSQL persistence.
"""

import json
import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from enum import Enum

from database import db
from graph.graph_store import GraphStore

logger = logging.getLogger(__name__)


def _parse_json_field(value) -> dict:
    """Parse a JSON field that might be a string or already a dict."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}
router = APIRouter()


# Enums
class EntityType(str, Enum):
    PAPER = "Paper"
    AUTHOR = "Author"
    CONCEPT = "Concept"
    METHOD = "Method"
    FINDING = "Finding"


class RelationshipType(str, Enum):
    AUTHORED_BY = "AUTHORED_BY"
    CITES = "CITES"
    DISCUSSES_CONCEPT = "DISCUSSES_CONCEPT"
    USES_METHOD = "USES_METHOD"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    RELATED_TO = "RELATED_TO"


# Pydantic Models
class NodeResponse(BaseModel):
    id: str
    entity_type: str  # Changed from EntityType to str for flexibility
    name: str
    properties: dict = {}


class EdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    relationship_type: str  # Changed from RelationshipType to str
    properties: dict = {}
    weight: float = 1.0


class GraphDataResponse(BaseModel):
    nodes: List[NodeResponse]
    edges: List[EdgeResponse]


class SearchRequest(BaseModel):
    query: str
    entity_types: Optional[List[str]] = None
    limit: int = 20
    project_id: Optional[str] = None


# Database dependency
async def get_db():
    """Dependency to get database connection."""
    if not db.is_connected:
        await db.connect()
    return db


async def get_graph_store(database=Depends(get_db)) -> GraphStore:
    """Dependency to get GraphStore instance."""
    return GraphStore(db_connection=database)


@router.get("/nodes", response_model=List[NodeResponse])
async def get_nodes(
    project_id: UUID,
    entity_type: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    database=Depends(get_db),
):
    """Get all nodes for a project from PostgreSQL."""
    try:
        if entity_type:
            rows = await database.fetch(
                """
                SELECT id, entity_type::text, name, properties
                FROM entities
                WHERE project_id = $1 AND entity_type::text = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
                """,
                str(project_id),
                entity_type,
                limit,
                offset,
            )
        else:
            rows = await database.fetch(
                """
                SELECT id, entity_type::text, name, properties
                FROM entities
                WHERE project_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                str(project_id),
                limit,
                offset,
            )

        return [
            NodeResponse(
                id=str(row["id"]),
                entity_type=row["entity_type"],
                name=row["name"],
                properties=_parse_json_field(row["properties"]),
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to get nodes: {e}")
        return []


@router.get("/edges", response_model=List[EdgeResponse])
async def get_edges(
    project_id: UUID,
    relationship_type: Optional[str] = None,
    limit: int = Query(500, le=5000),
    offset: int = 0,
    database=Depends(get_db),
):
    """Get all edges for a project from PostgreSQL."""
    try:
        if relationship_type:
            rows = await database.fetch(
                """
                SELECT id, source_id, target_id, relationship_type::text, properties, weight
                FROM relationships
                WHERE project_id = $1 AND relationship_type::text = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
                """,
                str(project_id),
                relationship_type,
                limit,
                offset,
            )
        else:
            rows = await database.fetch(
                """
                SELECT id, source_id, target_id, relationship_type::text, properties, weight
                FROM relationships
                WHERE project_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                str(project_id),
                limit,
                offset,
            )

        return [
            EdgeResponse(
                id=str(row["id"]),
                source=str(row["source_id"]),
                target=str(row["target_id"]),
                relationship_type=row["relationship_type"],
                properties=_parse_json_field(row["properties"]),
                weight=row["weight"] or 1.0,
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to get edges: {e}")
        return []


@router.get("/visualization/{project_id}", response_model=GraphDataResponse)
async def get_visualization_data(
    project_id: UUID,
    entity_types: Optional[List[str]] = Query(None),
    max_nodes: int = Query(200, le=500),
    database=Depends(get_db),
):
    """Get graph data optimized for visualization (React Flow format)."""
    try:
        # Build entity type filter
        type_filter = ""
        params = [str(project_id), max_nodes]

        if entity_types:
            type_placeholders = ", ".join(f"${i+3}" for i in range(len(entity_types)))
            type_filter = f"AND entity_type::text IN ({type_placeholders})"
            params.extend(entity_types)

        # Get nodes
        nodes_query = f"""
            SELECT id, entity_type::text, name, properties
            FROM entities
            WHERE project_id = $1 {type_filter}
            ORDER BY
                CASE entity_type::text
                    WHEN 'Paper' THEN 1
                    WHEN 'Concept' THEN 2
                    WHEN 'Author' THEN 3
                    ELSE 4
                END,
                created_at DESC
            LIMIT $2
        """
        node_rows = await database.fetch(nodes_query, *params)

        nodes = [
            NodeResponse(
                id=str(row["id"]),
                entity_type=row["entity_type"],
                name=row["name"],
                properties=_parse_json_field(row["properties"]),
            )
            for row in node_rows
        ]

        # Get edges connecting visible nodes
        node_ids = [str(row["id"]) for row in node_rows]

        if node_ids:
            edges_query = """
                SELECT id, source_id, target_id, relationship_type::text, properties, weight
                FROM relationships
                WHERE project_id = $1
                AND source_id = ANY($2::uuid[])
                AND target_id = ANY($2::uuid[])
            """
            edge_rows = await database.fetch(
                edges_query,
                str(project_id),
                node_ids,
            )

            edges = [
                EdgeResponse(
                    id=str(row["id"]),
                    source=str(row["source_id"]),
                    target=str(row["target_id"]),
                    relationship_type=row["relationship_type"],
                    properties=_parse_json_field(row["properties"]),
                    weight=row["weight"] or 1.0,
                )
                for row in edge_rows
            ]
        else:
            edges = []

        return GraphDataResponse(nodes=nodes, edges=edges)
    except Exception as e:
        logger.error(f"Failed to get visualization data: {e}")
        return GraphDataResponse(nodes=[], edges=[])


@router.get("/subgraph/{node_id}", response_model=GraphDataResponse)
async def get_subgraph(
    node_id: str,
    depth: int = Query(1, le=3),
    max_nodes: int = Query(50, le=200),
    database=Depends(get_db),
):
    """Get subgraph centered around a specific node using BFS traversal."""
    try:
        # Validate node exists
        center_node = await database.fetchrow(
            """
            SELECT id, entity_type::text, name, properties, project_id
            FROM entities
            WHERE id = $1
            """,
            node_id,
        )

        if not center_node:
            raise HTTPException(status_code=404, detail="Node not found")

        project_id = str(center_node["project_id"])

        # BFS to find connected nodes
        visited_ids = {node_id}
        current_level = [node_id]

        for _ in range(depth):
            if len(visited_ids) >= max_nodes:
                break

            # Find neighbors
            neighbors_query = """
                SELECT DISTINCT
                    CASE WHEN source_id::text = ANY($1) THEN target_id ELSE source_id END as neighbor_id
                FROM relationships
                WHERE project_id = $2
                AND (source_id::text = ANY($1) OR target_id::text = ANY($1))
            """
            neighbor_rows = await database.fetch(
                neighbors_query,
                current_level,
                project_id,
            )

            next_level = []
            for row in neighbor_rows:
                neighbor_id = str(row["neighbor_id"])
                if neighbor_id not in visited_ids:
                    visited_ids.add(neighbor_id)
                    next_level.append(neighbor_id)
                    if len(visited_ids) >= max_nodes:
                        break

            current_level = next_level

        # Get all nodes
        node_rows = await database.fetch(
            """
            SELECT id, entity_type::text, name, properties
            FROM entities
            WHERE id = ANY($1::uuid[])
            """,
            list(visited_ids),
        )

        nodes = [
            NodeResponse(
                id=str(row["id"]),
                entity_type=row["entity_type"],
                name=row["name"],
                properties=_parse_json_field(row["properties"]),
            )
            for row in node_rows
        ]

        # Get edges between visited nodes
        edge_rows = await database.fetch(
            """
            SELECT id, source_id, target_id, relationship_type::text, properties, weight
            FROM relationships
            WHERE project_id = $1
            AND source_id = ANY($2::uuid[])
            AND target_id = ANY($2::uuid[])
            """,
            project_id,
            list(visited_ids),
        )

        edges = [
            EdgeResponse(
                id=str(row["id"]),
                source=str(row["source_id"]),
                target=str(row["target_id"]),
                relationship_type=row["relationship_type"],
                properties=_parse_json_field(row["properties"]),
                weight=row["weight"] or 1.0,
            )
            for row in edge_rows
        ]

        return GraphDataResponse(nodes=nodes, edges=edges)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get subgraph: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subgraph")


@router.post("/search", response_model=List[NodeResponse])
async def search_nodes(
    request: SearchRequest,
    database=Depends(get_db),
):
    """Search nodes by query string using trigram similarity."""
    try:
        query_lower = request.query.lower()
        params = [f"%{query_lower}%", request.limit]

        if request.project_id:
            project_filter = "AND project_id = $3"
            params.append(request.project_id)
        else:
            project_filter = ""

        if request.entity_types:
            type_offset = len(params) + 1
            type_placeholders = ", ".join(f"${i}" for i in range(type_offset, type_offset + len(request.entity_types)))
            type_filter = f"AND entity_type::text IN ({type_placeholders})"
            params.extend(request.entity_types)
        else:
            type_filter = ""

        rows = await database.fetch(
            f"""
            SELECT id, entity_type::text, name, properties
            FROM entities
            WHERE LOWER(name) LIKE $1 {project_filter} {type_filter}
            ORDER BY
                CASE WHEN LOWER(name) = $1 THEN 0 ELSE 1 END,
                LENGTH(name)
            LIMIT $2
            """,
            *params,
        )

        return [
            NodeResponse(
                id=str(row["id"]),
                entity_type=row["entity_type"],
                name=row["name"],
                properties=_parse_json_field(row["properties"]),
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to search nodes: {e}")
        return []


@router.get("/similar/{node_id}", response_model=List[NodeResponse])
async def get_similar_nodes(
    node_id: str,
    limit: int = Query(10, le=50),
    database=Depends(get_db),
):
    """Get similar nodes using pgvector similarity search."""
    try:
        # Get the source node and its embedding
        source_node = await database.fetchrow(
            """
            SELECT id, entity_type::text, name, properties, embedding, project_id
            FROM entities
            WHERE id = $1
            """,
            node_id,
        )

        if not source_node:
            raise HTTPException(status_code=404, detail="Node not found")

        if source_node["embedding"] is None:
            # Fallback: return nodes of same type
            rows = await database.fetch(
                """
                SELECT id, entity_type::text, name, properties
                FROM entities
                WHERE project_id = $1
                AND entity_type::text = $2
                AND id != $3
                LIMIT $4
                """,
                str(source_node["project_id"]),
                source_node["entity_type"],
                node_id,
                limit,
            )
        else:
            # Use pgvector cosine similarity
            rows = await database.fetch(
                """
                SELECT id, entity_type::text, name, properties,
                       1 - (embedding <=> $1) as similarity
                FROM entities
                WHERE project_id = $2
                AND id != $3
                AND embedding IS NOT NULL
                ORDER BY embedding <=> $1
                LIMIT $4
                """,
                source_node["embedding"],
                str(source_node["project_id"]),
                node_id,
                limit,
            )

        return [
            NodeResponse(
                id=str(row["id"]),
                entity_type=row["entity_type"],
                name=row["name"],
                properties=_parse_json_field(row["properties"]),
            )
            for row in rows
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get similar nodes: {e}")
        return []


@router.get("/gaps/{project_id}", response_model=List[NodeResponse])
async def get_research_gaps(
    project_id: UUID,
    min_papers: int = Query(3, description="Concepts with fewer papers are gaps"),
    database=Depends(get_db),
):
    """Identify research gaps - concepts with few connected papers."""
    try:
        # Find concepts with few paper connections
        rows = await database.fetch(
            """
            SELECT e.id, e.entity_type::text, e.name, e.properties,
                   COUNT(r.id) as paper_count
            FROM entities e
            LEFT JOIN relationships r ON (
                r.source_id = e.id OR r.target_id = e.id
            )
            LEFT JOIN entities paper ON (
                (paper.id = r.source_id OR paper.id = r.target_id)
                AND paper.id != e.id
                AND paper.entity_type = 'Paper'
            )
            WHERE e.project_id = $1
            AND e.entity_type = 'Concept'
            GROUP BY e.id, e.entity_type, e.name, e.properties
            HAVING COUNT(paper.id) < $2
            ORDER BY COUNT(paper.id) ASC, e.name
            LIMIT 20
            """,
            str(project_id),
            min_papers,
        )

        return [
            NodeResponse(
                id=str(row["id"]),
                entity_type=row["entity_type"],
                name=row["name"],
                properties={
                    **(row["properties"] or {}),
                    "paper_count": row["paper_count"],
                    "is_gap": True,
                },
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to get research gaps: {e}")
        return []


@router.get("/entity/{entity_id}", response_model=NodeResponse)
async def get_entity(
    entity_id: str,
    database=Depends(get_db),
):
    """Get a single entity by ID."""
    try:
        row = await database.fetchrow(
            """
            SELECT id, entity_type::text, name, properties
            FROM entities
            WHERE id = $1
            """,
            entity_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Entity not found")

        return NodeResponse(
            id=str(row["id"]),
            entity_type=row["entity_type"],
            name=row["name"],
            properties=_parse_json_field(row["properties"]),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entity: {e}")
        raise HTTPException(status_code=500, detail="Failed to get entity")


# ============================================
# Gap Detection API (InfraNodus-style)
# ============================================

class ConceptClusterResponse(BaseModel):
    cluster_id: int
    concepts: List[str]
    concept_names: List[str]
    size: int
    density: float
    label: Optional[str] = None


class StructuralGapResponse(BaseModel):
    id: str
    cluster_a_id: int
    cluster_b_id: int
    cluster_a_concepts: List[str]
    cluster_b_concepts: List[str]
    cluster_a_names: List[str]
    cluster_b_names: List[str]
    gap_strength: float
    bridge_candidates: List[str]
    research_questions: List[str]


class CentralityMetricsResponse(BaseModel):
    concept_id: str
    concept_name: str
    degree_centrality: float
    betweenness_centrality: float
    pagerank: float
    cluster_id: Optional[int] = None


class GapAnalysisResponse(BaseModel):
    clusters: List[ConceptClusterResponse]
    gaps: List[StructuralGapResponse]
    centrality_metrics: List[CentralityMetricsResponse]
    total_concepts: int
    total_relationships: int


@router.get("/gaps/{project_id}/analysis", response_model=GapAnalysisResponse)
async def get_gap_analysis(
    project_id: UUID,
    database=Depends(get_db),
):
    """Get full gap analysis including clusters, gaps, and centrality metrics."""
    try:
        # Get clusters
        cluster_rows = await database.fetch(
            """
            SELECT cluster_id, concepts, concept_names, size, density, label
            FROM concept_clusters
            WHERE project_id = $1
            ORDER BY cluster_id
            """,
            str(project_id),
        )

        clusters = [
            ConceptClusterResponse(
                cluster_id=row["cluster_id"],
                concepts=row["concepts"] or [],
                concept_names=row["concept_names"] or [],
                size=row["size"],
                density=row["density"] or 0.0,
                label=row["label"],
            )
            for row in cluster_rows
        ]

        # Get structural gaps
        gap_rows = await database.fetch(
            """
            SELECT id, cluster_a_id, cluster_b_id,
                   cluster_a_concepts, cluster_b_concepts,
                   cluster_a_names, cluster_b_names,
                   gap_strength, bridge_candidates, research_questions
            FROM structural_gaps
            WHERE project_id = $1
            ORDER BY gap_strength DESC
            """,
            str(project_id),
        )

        gaps = [
            StructuralGapResponse(
                id=str(row["id"]),
                cluster_a_id=row["cluster_a_id"],
                cluster_b_id=row["cluster_b_id"],
                cluster_a_concepts=row["cluster_a_concepts"] or [],
                cluster_b_concepts=row["cluster_b_concepts"] or [],
                cluster_a_names=row["cluster_a_names"] or [],
                cluster_b_names=row["cluster_b_names"] or [],
                gap_strength=row["gap_strength"] or 0.0,
                bridge_candidates=row["bridge_candidates"] or [],
                research_questions=row["research_questions"] or [],
            )
            for row in gap_rows
        ]

        # Get centrality metrics from entities
        centrality_rows = await database.fetch(
            """
            SELECT id, name, properties
            FROM entities
            WHERE project_id = $1
            AND entity_type IN ('Concept', 'Method', 'Finding', 'Problem', 'Dataset', 'Metric', 'Innovation', 'Limitation')
            AND properties->>'centrality_degree' IS NOT NULL
            ORDER BY (properties->>'centrality_pagerank')::float DESC NULLS LAST
            LIMIT 100
            """,
            str(project_id),
        )

        centrality_metrics = [
            CentralityMetricsResponse(
                concept_id=str(row["id"]),
                concept_name=row["name"],
                degree_centrality=float(row["properties"].get("centrality_degree", 0)),
                betweenness_centrality=float(row["properties"].get("centrality_betweenness", 0)),
                pagerank=float(row["properties"].get("centrality_pagerank", 0)),
                cluster_id=row["properties"].get("cluster_id"),
            )
            for row in centrality_rows
        ]

        # Get totals
        concept_count = await database.fetchval(
            """
            SELECT COUNT(*) FROM entities
            WHERE project_id = $1
            AND entity_type IN ('Concept', 'Method', 'Finding', 'Problem', 'Dataset', 'Metric', 'Innovation', 'Limitation')
            """,
            str(project_id),
        )

        relationship_count = await database.fetchval(
            """
            SELECT COUNT(*) FROM relationships
            WHERE project_id = $1
            """,
            str(project_id),
        )

        return GapAnalysisResponse(
            clusters=clusters,
            gaps=gaps,
            centrality_metrics=centrality_metrics,
            total_concepts=concept_count or 0,
            total_relationships=relationship_count or 0,
        )

    except Exception as e:
        logger.error(f"Failed to get gap analysis: {e}")
        return GapAnalysisResponse(
            clusters=[],
            gaps=[],
            centrality_metrics=[],
            total_concepts=0,
            total_relationships=0,
        )


@router.post("/gaps/{project_id}/refresh", response_model=GapAnalysisResponse)
async def refresh_gap_analysis(
    project_id: UUID,
    database=Depends(get_db),
):
    """Re-run gap detection on the project's concept graph."""
    try:
        from graph.gap_detector import GapDetector

        # Get all concepts with embeddings
        concept_rows = await database.fetch(
            """
            SELECT id, name, properties, embedding
            FROM entities
            WHERE project_id = $1
            AND entity_type IN ('Concept', 'Method', 'Finding', 'Problem', 'Dataset', 'Metric', 'Innovation', 'Limitation')
            AND embedding IS NOT NULL
            """,
            str(project_id),
        )

        if not concept_rows:
            return GapAnalysisResponse(
                clusters=[],
                gaps=[],
                centrality_metrics=[],
                total_concepts=0,
                total_relationships=0,
            )

        # Get relationships
        relationship_rows = await database.fetch(
            """
            SELECT id, source_id, target_id, relationship_type::text, properties
            FROM relationships
            WHERE project_id = $1
            """,
            str(project_id),
        )

        # Convert to format expected by GapDetector
        concepts = [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "embedding": list(row["embedding"]) if row["embedding"] else None,
                "properties": row["properties"] or {},
            }
            for row in concept_rows
        ]

        relationships = [
            {
                "id": str(row["id"]),
                "source": str(row["source_id"]),
                "target": str(row["target_id"]),
                "type": row["relationship_type"],
                "properties": row["properties"] or {},
            }
            for row in relationship_rows
        ]

        # Run gap detection
        gap_detector = GapDetector()
        analysis = await gap_detector.analyze_graph(concepts, relationships)

        # Store results
        # Clear old data
        await database.execute(
            "DELETE FROM concept_clusters WHERE project_id = $1",
            str(project_id),
        )
        await database.execute(
            "DELETE FROM structural_gaps WHERE project_id = $1",
            str(project_id),
        )

        # Store clusters
        for cluster in analysis.get("clusters", []):
            await database.execute(
                """
                INSERT INTO concept_clusters (project_id, cluster_id, concepts, concept_names, size, density, label)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                str(project_id),
                cluster.cluster_id,
                cluster.concepts,
                cluster.concept_names,
                cluster.size,
                cluster.density,
                cluster.label,
            )

        # Store gaps
        for gap in analysis.get("gaps", []):
            await database.execute(
                """
                INSERT INTO structural_gaps (
                    project_id, cluster_a_id, cluster_b_id,
                    cluster_a_concepts, cluster_b_concepts,
                    cluster_a_names, cluster_b_names,
                    gap_strength, bridge_candidates, research_questions
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                str(project_id),
                gap.cluster_a_id,
                gap.cluster_b_id,
                gap.cluster_a_concepts,
                gap.cluster_b_concepts,
                gap.cluster_a_names,
                gap.cluster_b_names,
                gap.gap_strength,
                gap.bridge_candidates,
                gap.research_questions,
            )

        # Update entity centrality
        for metric in analysis.get("centrality_metrics", []):
            await database.execute(
                """
                UPDATE entities
                SET properties = properties || $1::jsonb
                WHERE id = $2
                """,
                {
                    "centrality_degree": metric.degree_centrality,
                    "centrality_betweenness": metric.betweenness_centrality,
                    "centrality_pagerank": metric.pagerank,
                },
                metric.concept_id,
            )

        # Return updated analysis
        return await get_gap_analysis(project_id, database)

    except Exception as e:
        logger.error(f"Failed to refresh gap analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh gap analysis: {str(e)}")


@router.get("/gaps/detail/{gap_id}", response_model=StructuralGapResponse)
async def get_gap_detail(
    gap_id: UUID,
    database=Depends(get_db),
):
    """Get detailed information about a specific structural gap."""
    try:
        row = await database.fetchrow(
            """
            SELECT id, cluster_a_id, cluster_b_id,
                   cluster_a_concepts, cluster_b_concepts,
                   cluster_a_names, cluster_b_names,
                   gap_strength, bridge_candidates, research_questions
            FROM structural_gaps
            WHERE id = $1
            """,
            str(gap_id),
        )

        if not row:
            raise HTTPException(status_code=404, detail="Gap not found")

        return StructuralGapResponse(
            id=str(row["id"]),
            cluster_a_id=row["cluster_a_id"],
            cluster_b_id=row["cluster_b_id"],
            cluster_a_concepts=row["cluster_a_concepts"] or [],
            cluster_b_concepts=row["cluster_b_concepts"] or [],
            cluster_a_names=row["cluster_a_names"] or [],
            cluster_b_names=row["cluster_b_names"] or [],
            gap_strength=row["gap_strength"] or 0.0,
            bridge_candidates=row["bridge_candidates"] or [],
            research_questions=row["research_questions"] or [],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get gap detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to get gap detail")


@router.post("/gaps/{gap_id}/questions")
async def generate_gap_questions(
    gap_id: UUID,
    regenerate: bool = False,
    database=Depends(get_db),
):
    """Generate or regenerate AI research questions for a gap."""
    try:
        # Get gap
        row = await database.fetchrow(
            """
            SELECT id, cluster_a_names, cluster_b_names, research_questions, project_id
            FROM structural_gaps
            WHERE id = $1
            """,
            str(gap_id),
        )

        if not row:
            raise HTTPException(status_code=404, detail="Gap not found")

        # Return existing if not regenerating
        if not regenerate and row["research_questions"]:
            return {"questions": row["research_questions"]}

        # Generate new questions
        from graph.gap_detector import GapDetector

        gap_detector = GapDetector()

        # Create a minimal StructuralGap object for question generation
        from dataclasses import dataclass

        @dataclass
        class MinimalGap:
            cluster_a_id: int = 0
            cluster_b_id: int = 1
            gap_strength: float = 0.5

        questions = await gap_detector.generate_research_questions(
            MinimalGap(),
            row["cluster_a_names"],
            row["cluster_b_names"],
        )

        # Store questions
        await database.execute(
            """
            UPDATE structural_gaps
            SET research_questions = $1
            WHERE id = $2
            """,
            questions,
            str(gap_id),
        )

        return {"questions": questions}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate gap questions: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate questions")
