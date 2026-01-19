"""
Graph API Router

Handles knowledge graph queries and visualization data with PostgreSQL persistence.

Security:
- All endpoints require authentication in production (configurable via REQUIRE_AUTH)
- Project-level access control is enforced for all operations
- Users can only access projects they own, collaborate on, or that are public
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
from auth.dependencies import require_auth_if_configured
from auth.models import User
from routers.projects import check_project_access

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


def _parse_embedding(value) -> list:
    """Parse a pgvector embedding that might be a string, list, or vector type."""
    if value is None:
        return []
    # Already a list of floats
    if isinstance(value, list):
        return value
    # String format from pgvector: "[0.1, 0.2, ...]"
    if isinstance(value, str):
        try:
            # Remove brackets and split
            clean = value.strip("[]")
            if not clean:
                return []
            return [float(x.strip()) for x in clean.split(",")]
        except (ValueError, AttributeError):
            return []
    # Try to convert directly (some drivers return native types)
    try:
        return list(value)
    except (TypeError, ValueError):
        return []


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
    return GraphStore(db=database)


async def verify_project_access(
    database,
    project_id: UUID,
    current_user: Optional[User],
    action: str = "access"
) -> None:
    """
    Verify that the current user has access to the project.

    Args:
        database: Database connection
        project_id: UUID of the project
        current_user: Current authenticated user (None if auth not configured)
        action: Description of the action for error messages

    Raises:
        HTTPException: 403 if access denied, 404 if project not found
    """
    # Check project exists
    exists = await database.fetchval(
        "SELECT EXISTS(SELECT 1 FROM projects WHERE id = $1)",
        project_id,
    )
    if not exists:
        raise HTTPException(status_code=404, detail="Project not found")

    # If auth is configured, verify access
    if current_user is not None:
        has_access = await check_project_access(database, project_id, current_user.id)
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail=f"You don't have permission to {action} this project"
            )


async def get_project_id_from_node(database, node_id: str) -> Optional[UUID]:
    """
    Get the project_id for a node.

    Args:
        database: Database connection
        node_id: UUID of the node

    Returns:
        Project UUID or None if node not found
    """
    row = await database.fetchrow(
        "SELECT project_id FROM entities WHERE id = $1",
        node_id,
    )
    return UUID(str(row["project_id"])) if row else None


async def get_project_id_from_gap(database, gap_id: str) -> Optional[UUID]:
    """
    Get the project_id for a structural gap.

    Args:
        database: Database connection
        gap_id: UUID of the gap

    Returns:
        Project UUID or None if gap not found
    """
    row = await database.fetchrow(
        "SELECT project_id FROM structural_gaps WHERE id = $1",
        str(gap_id),
    )
    return UUID(str(row["project_id"])) if row else None


@router.get("/nodes", response_model=List[NodeResponse])
async def get_nodes(
    project_id: UUID,
    entity_type: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get all nodes for a project from PostgreSQL. Requires auth in production."""
    # Verify project access
    await verify_project_access(database, project_id, current_user, "access")

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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get nodes: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please try again later."
        )


@router.get("/edges", response_model=List[EdgeResponse])
async def get_edges(
    project_id: UUID,
    relationship_type: Optional[str] = None,
    limit: int = Query(500, le=5000),
    offset: int = 0,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get all edges for a project from PostgreSQL. Requires auth in production."""
    # Verify project access
    await verify_project_access(database, project_id, current_user, "access")

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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get edges: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please try again later."
        )


@router.get("/visualization/{project_id}", response_model=GraphDataResponse)
async def get_visualization_data(
    project_id: UUID,
    entity_types: Optional[List[str]] = Query(None),
    max_nodes: int = Query(200, le=500),
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get graph data optimized for visualization. Requires auth in production."""
    # Verify project access
    await verify_project_access(database, project_id, current_user, "access")

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

        # Get edges connecting visible nodes (Hybrid Mode: include if BOTH endpoints visible)
        node_ids = [str(row["id"]) for row in node_rows]
        node_id_set = set(node_ids)

        if node_ids:
            # Fetch edges where both endpoints are visible
            # This ensures the graph is coherent (no dangling edges)
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

            logger.info(f"Visualization: {len(nodes)} nodes, {len(edges)} edges (both endpoints visible)")
        else:
            edges = []

        return GraphDataResponse(nodes=nodes, edges=edges)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get visualization data: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please try again later."
        )


@router.get("/subgraph/{node_id}", response_model=GraphDataResponse)
async def get_subgraph(
    node_id: str,
    depth: int = Query(1, le=3),
    max_nodes: int = Query(50, le=200),
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get subgraph centered around a specific node using BFS traversal. Requires auth in production."""
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

        project_id = UUID(str(center_node["project_id"]))

        # Verify project access
        await verify_project_access(database, project_id, current_user, "access")

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
                str(project_id),
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
            str(project_id),
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
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Search nodes by query string. Requires auth in production."""
    # If project_id is provided, verify access
    if request.project_id:
        await verify_project_access(
            database, UUID(request.project_id), current_user, "search"
        )

    try:
        query_lower = request.query.lower()
        params = [f"%{query_lower}%", request.limit]

        if request.project_id:
            project_filter = "AND project_id = $3"
            params.append(request.project_id)
        else:
            # If no project_id, only search in accessible projects
            if current_user is not None:
                project_filter = """
                AND project_id IN (
                    SELECT p.id FROM projects p
                    LEFT JOIN project_collaborators pc ON p.id = pc.project_id
                    LEFT JOIN team_projects tp ON p.id = tp.project_id
                    LEFT JOIN team_members tm ON tp.team_id = tm.team_id
                    WHERE p.owner_id = $3
                       OR pc.user_id = $3
                       OR tm.user_id = $3
                       OR p.visibility = 'public'
                )
                """
                params.append(current_user.id)
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search nodes: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please try again later."
        )


@router.get("/similar/{node_id}", response_model=List[NodeResponse])
async def get_similar_nodes(
    node_id: str,
    limit: int = Query(10, le=50),
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get similar nodes using pgvector similarity search. Requires auth in production."""
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

        project_id = UUID(str(source_node["project_id"]))

        # Verify project access
        await verify_project_access(database, project_id, current_user, "access")

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
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please try again later."
        )


@router.get("/gaps/{project_id}", response_model=List[NodeResponse])
async def get_research_gaps(
    project_id: UUID,
    min_papers: int = Query(3, description="Concepts with fewer papers are gaps"),
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Identify research gaps - concepts with few connected papers. Requires auth in production."""
    # Verify project access
    await verify_project_access(database, project_id, current_user, "access")

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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get research gaps: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please try again later."
        )


@router.get("/entity/{entity_id}", response_model=NodeResponse)
async def get_entity(
    entity_id: str,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get a single entity by ID. Requires auth in production."""
    try:
        row = await database.fetchrow(
            """
            SELECT id, entity_type::text, name, properties, project_id
            FROM entities
            WHERE id = $1
            """,
            entity_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Entity not found")

        project_id = UUID(str(row["project_id"]))

        # Verify project access
        await verify_project_access(database, project_id, current_user, "access")

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


class PotentialEdgeResponse(BaseModel):
    """Potential (ghost) edge between clusters for visualization."""
    source_id: str
    target_id: str
    similarity: float
    gap_id: str
    source_name: Optional[str] = None
    target_name: Optional[str] = None


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
    potential_edges: List[PotentialEdgeResponse] = []  # Ghost edges for visualization


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
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get full gap analysis including clusters, gaps, and centrality metrics. Requires auth in production."""
    # Verify project access
    await verify_project_access(database, project_id, current_user, "access")

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
                   gap_strength, bridge_candidates, research_questions, potential_edges
            FROM structural_gaps
            WHERE project_id = $1
            ORDER BY gap_strength DESC
            """,
            str(project_id),
        )

        gaps = []
        for row in gap_rows:
            # Parse potential_edges from JSON
            potential_edges_data = row.get("potential_edges")
            if potential_edges_data:
                if isinstance(potential_edges_data, str):
                    potential_edges_data = json.loads(potential_edges_data)
                potential_edges = [
                    PotentialEdgeResponse(**pe) for pe in (potential_edges_data or [])
                ]
            else:
                potential_edges = []

            gaps.append(
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
                    potential_edges=potential_edges,
                )
            )

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get gap analysis: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please try again later."
        )


@router.post("/gaps/{project_id}/refresh", response_model=GapAnalysisResponse)
async def refresh_gap_analysis(
    project_id: UUID,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Re-run gap detection on the project's concept graph. Requires auth in production."""
    # Verify project access
    await verify_project_access(database, project_id, current_user, "modify")

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
                "embedding": _parse_embedding(row["embedding"]) or None,
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
            # Convert potential_edges to JSON-serializable format
            potential_edges_json = [
                {
                    "source_id": pe.source_id,
                    "target_id": pe.target_id,
                    "similarity": pe.similarity,
                    "gap_id": pe.gap_id,
                    "source_name": pe.source_name,
                    "target_name": pe.target_name,
                }
                for pe in (gap.potential_edges or [])
            ]

            await database.execute(
                """
                INSERT INTO structural_gaps (
                    project_id, cluster_a_id, cluster_b_id,
                    cluster_a_concepts, cluster_b_concepts,
                    cluster_a_names, cluster_b_names,
                    gap_strength, bridge_candidates, research_questions, potential_edges
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                str(project_id),
                gap.cluster_a_id,
                gap.cluster_b_id,
                gap.concept_a_ids,
                gap.concept_b_ids,
                [c["name"] for c in concepts if c["id"] in gap.concept_a_ids][:5],
                [c["name"] for c in concepts if c["id"] in gap.concept_b_ids][:5],
                gap.gap_strength,
                gap.bridge_concepts,
                gap.suggested_research_questions,
                json.dumps(potential_edges_json),
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
        return await get_gap_analysis(project_id, database, current_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh gap analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh gap analysis. Please try again later.")


@router.get("/gaps/detail/{gap_id}", response_model=StructuralGapResponse)
async def get_gap_detail(
    gap_id: UUID,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get detailed information about a specific structural gap. Requires auth in production."""
    try:
        row = await database.fetchrow(
            """
            SELECT id, cluster_a_id, cluster_b_id,
                   cluster_a_concepts, cluster_b_concepts,
                   cluster_a_names, cluster_b_names,
                   gap_strength, bridge_candidates, research_questions,
                   potential_edges, project_id
            FROM structural_gaps
            WHERE id = $1
            """,
            str(gap_id),
        )

        if not row:
            raise HTTPException(status_code=404, detail="Gap not found")

        project_id = UUID(str(row["project_id"]))

        # Verify project access
        await verify_project_access(database, project_id, current_user, "access")

        # Parse potential_edges from JSON
        potential_edges_data = row.get("potential_edges")
        if potential_edges_data:
            if isinstance(potential_edges_data, str):
                potential_edges_data = json.loads(potential_edges_data)
            potential_edges = [
                PotentialEdgeResponse(**pe) for pe in (potential_edges_data or [])
            ]
        else:
            potential_edges = []

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
            potential_edges=potential_edges,
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
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Generate or regenerate AI research questions for a gap. Requires auth in production."""
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

        project_id = UUID(str(row["project_id"]))

        # Verify project access
        await verify_project_access(database, project_id, current_user, "modify")

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


# ============================================================
# Centrality Analysis & Slicing Endpoints
# ============================================================

class CentralityResponse(BaseModel):
    """Response model for centrality analysis."""
    metric: str
    centrality: dict  # node_id -> score
    top_bridges: List[tuple]  # [(node_id, score), ...]


class SliceRequest(BaseModel):
    """Request model for graph slicing."""
    remove_top_n: int = 5
    metric: str = "betweenness"


class SliceResponse(BaseModel):
    """Response model for sliced graph."""
    nodes: List[NodeResponse]
    edges: List[EdgeResponse]
    removed_node_ids: List[str]
    top_bridges: List[dict]
    original_count: int
    filtered_count: int


class ClusterRequest(BaseModel):
    """Request model for clustering."""
    cluster_count: int = 5


class ClusterResponse(BaseModel):
    """Response model for clustering."""
    clusters: List[dict]
    optimal_k: int


@router.get("/centrality/{project_id}")
async def get_centrality(
    project_id: UUID,
    metric: str = "betweenness",
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Get centrality metrics for all nodes in the project.

    Supported metrics: betweenness, degree, eigenvector

    Returns:
        - centrality: dict mapping node_id to centrality score
        - top_bridges: list of (node_id, score) for top 10 nodes
    """
    try:
        from graph.centrality_analyzer import centrality_analyzer

        # Get nodes
        node_rows = await database.fetch(
            """
            SELECT id, entity_type, name, properties
            FROM entities
            WHERE project_id = $1
            """,
            str(project_id),
        )

        # Get edges
        edge_rows = await database.fetch(
            """
            SELECT id, source_id, target_id, relationship_type::text, properties,
                   COALESCE((properties->>'weight')::float, 1.0) as weight
            FROM relationships
            WHERE project_id = $1
            """,
            str(project_id),
        )

        if not node_rows:
            return {
                "metric": metric,
                "centrality": {},
                "top_bridges": [],
            }

        # Convert to format expected by analyzer
        nodes = [
            {
                "id": str(row["id"]),
                "entity_type": row["entity_type"],
                "name": row["name"],
                "properties": _parse_json_field(row["properties"]),
            }
            for row in node_rows
        ]

        edges = [
            {
                "id": str(row["id"]),
                "source": str(row["source_id"]),
                "target": str(row["target_id"]),
                "relationship_type": row["relationship_type"],
                "weight": float(row["weight"]) if row["weight"] else 1.0,
            }
            for row in edge_rows
        ]

        # Compute centrality
        metrics = centrality_analyzer.compute_all_centrality(
            nodes, edges, cache_key=str(project_id)
        )

        # Get requested metric
        if metric == "betweenness":
            centrality = metrics.betweenness
        elif metric == "degree":
            centrality = metrics.degree
        elif metric == "eigenvector":
            centrality = metrics.eigenvector
        else:
            centrality = metrics.betweenness

        # Get top bridges
        top_bridges = centrality_analyzer.get_top_bridges(centrality, 10)

        # Add names to top bridges
        top_bridges_with_names = [
            (node_id, score, centrality_analyzer.get_node_name(node_id, nodes))
            for node_id, score in top_bridges
        ]

        return {
            "metric": metric,
            "centrality": centrality,
            "top_bridges": top_bridges_with_names,
        }

    except Exception as e:
        logger.error(f"Failed to compute centrality: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute centrality metrics")


class GraphMetricsResponse(BaseModel):
    """Response model for graph quality metrics (Insight HUD)."""
    modularity: float  # Cluster separation quality (0-1)
    diversity: float   # Cluster size balance (0-1)
    density: float     # Connection density (0-1)
    avg_clustering: float  # Average clustering coefficient
    num_components: int    # Number of connected components
    node_count: int
    edge_count: int
    cluster_count: int


@router.get("/metrics/{project_id}", response_model=GraphMetricsResponse)
async def get_graph_metrics(
    project_id: UUID,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Get graph quality metrics for Insight HUD display (InfraNodus-style).

    Returns:
        - modularity: Cluster separation quality (0-1, higher = better separated)
        - diversity: Cluster size balance (0-1, higher = more even distribution)
        - density: Connection density (0-1)
        - avg_clustering: Average clustering coefficient
        - num_components: Number of connected components
        - node_count: Total number of nodes
        - edge_count: Total number of edges
        - cluster_count: Number of clusters
    """
    # Verify project access
    await verify_project_access(database, project_id, current_user, "access")

    try:
        from graph.centrality_analyzer import centrality_analyzer, ClusterResult

        # Get nodes
        node_rows = await database.fetch(
            """
            SELECT id, entity_type::text, name, properties
            FROM entities
            WHERE project_id = $1
            AND entity_type IN ('Concept', 'Method', 'Finding', 'Problem', 'Dataset', 'Metric', 'Innovation', 'Limitation')
            """,
            str(project_id),
        )

        # Get edges
        edge_rows = await database.fetch(
            """
            SELECT id, source_id, target_id, relationship_type::text,
                   COALESCE((properties->>'weight')::float, 1.0) as weight
            FROM relationships
            WHERE project_id = $1
            """,
            str(project_id),
        )

        # Get clusters
        cluster_rows = await database.fetch(
            """
            SELECT cluster_id, concepts, size
            FROM concept_clusters
            WHERE project_id = $1
            ORDER BY cluster_id
            """,
            str(project_id),
        )

        if not node_rows:
            return GraphMetricsResponse(
                modularity=0.0,
                diversity=0.0,
                density=0.0,
                avg_clustering=0.0,
                num_components=0,
                node_count=0,
                edge_count=0,
                cluster_count=0,
            )

        # Convert to format expected by analyzer
        nodes = [
            {
                "id": str(row["id"]),
                "entity_type": row["entity_type"],
                "name": row["name"],
                "properties": _parse_json_field(row["properties"]),
            }
            for row in node_rows
        ]

        edges = [
            {
                "id": str(row["id"]),
                "source": str(row["source_id"]),
                "target": str(row["target_id"]),
                "weight": float(row["weight"]) if row["weight"] else 1.0,
            }
            for row in edge_rows
        ]

        # Convert clusters to ClusterResult objects
        clusters = [
            ClusterResult(
                cluster_id=row["cluster_id"],
                node_ids=row["concepts"] or [],
                node_names=[],
                centroid=None,
                size=row["size"],
            )
            for row in cluster_rows
        ]

        # Compute graph metrics
        metrics = centrality_analyzer.compute_graph_metrics(nodes, edges, clusters)

        return GraphMetricsResponse(
            modularity=metrics["modularity"],
            diversity=metrics["diversity"],
            density=metrics["density"],
            avg_clustering=metrics["avg_clustering"],
            num_components=metrics["num_components"],
            node_count=len(nodes),
            edge_count=len(edges),
            cluster_count=len(clusters),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compute graph metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute graph metrics")


@router.post("/slice/{project_id}")
async def slice_graph(
    project_id: UUID,
    request: SliceRequest,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Remove top N nodes by centrality to reveal hidden cluster structures.

    This is the "slicing" operation from InfraNodus that helps discover
    overlooked connections by temporarily removing bridge nodes.

    Args:
        remove_top_n: Number of top nodes to remove (default: 5)
        metric: Centrality metric to use (betweenness, degree, eigenvector)

    Returns:
        Filtered graph with removed nodes and top bridges info
    """
    try:
        from graph.centrality_analyzer import centrality_analyzer

        # Get nodes
        node_rows = await database.fetch(
            """
            SELECT id, entity_type, name, properties
            FROM entities
            WHERE project_id = $1
            """,
            str(project_id),
        )

        # Get edges
        edge_rows = await database.fetch(
            """
            SELECT id, source_id, target_id, relationship_type::text, properties,
                   COALESCE((properties->>'weight')::float, 1.0) as weight
            FROM relationships
            WHERE project_id = $1
            """,
            str(project_id),
        )

        if not node_rows:
            return {
                "nodes": [],
                "edges": [],
                "removed_node_ids": [],
                "top_bridges": [],
                "original_count": 0,
                "filtered_count": 0,
            }

        # Convert to format expected by analyzer
        nodes = [
            {
                "id": str(row["id"]),
                "entity_type": row["entity_type"],
                "name": row["name"],
                "properties": _parse_json_field(row["properties"]),
            }
            for row in node_rows
        ]

        edges = [
            {
                "id": str(row["id"]),
                "source": str(row["source_id"]),
                "target": str(row["target_id"]),
                "relationship_type": row["relationship_type"],
                "weight": float(row["weight"]) if row["weight"] else 1.0,
            }
            for row in edge_rows
        ]

        # Perform slicing
        filtered_nodes, filtered_edges, removed_ids, top_bridges = centrality_analyzer.slice_graph(
            nodes,
            edges,
            request.remove_top_n,
            request.metric,
        )

        # Format response
        response_nodes = [
            NodeResponse(
                id=n["id"],
                entity_type=n["entity_type"],
                name=n["name"],
                properties=n["properties"],
            )
            for n in filtered_nodes
        ]

        response_edges = [
            EdgeResponse(
                id=e["id"],
                source=e["source"],
                target=e["target"],
                relationship_type=e["relationship_type"],
                weight=e.get("weight", 1.0),
            )
            for e in filtered_edges
        ]

        top_bridges_formatted = [
            {
                "id": node_id,
                "name": centrality_analyzer.get_node_name(node_id, nodes),
                "score": score,
            }
            for node_id, score in top_bridges
        ]

        return {
            "nodes": response_nodes,
            "edges": response_edges,
            "removed_node_ids": removed_ids,
            "top_bridges": top_bridges_formatted,
            "original_count": len(nodes),
            "filtered_count": len(filtered_nodes),
        }

    except Exception as e:
        logger.error(f"Failed to slice graph: {e}")
        raise HTTPException(status_code=500, detail="Failed to slice graph")


@router.post("/clusters/{project_id}")
async def recompute_clusters(
    project_id: UUID,
    request: ClusterRequest,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Recompute K-means clusters for the project's concept graph.

    Args:
        cluster_count: Desired number of clusters

    Returns:
        Updated cluster assignments and optimal K value
    """
    try:
        from graph.centrality_analyzer import centrality_analyzer
        import numpy as np

        # Get nodes with embeddings
        node_rows = await database.fetch(
            """
            SELECT id, entity_type, name, properties, embedding
            FROM entities
            WHERE project_id = $1
            AND entity_type IN ('Concept', 'Method', 'Finding', 'Problem', 'Dataset', 'Metric', 'Innovation', 'Limitation')
            AND embedding IS NOT NULL
            """,
            str(project_id),
        )

        if not node_rows:
            return {
                "clusters": [],
                "optimal_k": 2,
            }

        # Prepare data
        nodes = [
            {
                "id": str(row["id"]),
                "entity_type": row["entity_type"],
                "name": row["name"],
                "properties": _parse_json_field(row["properties"]),
            }
            for row in node_rows
        ]

        embeddings = np.array([_parse_embedding(row["embedding"]) for row in node_rows], dtype=np.float32)

        # Compute optimal K if not specified
        optimal_k = centrality_analyzer.compute_optimal_k(embeddings, min_k=2, max_k=min(10, len(nodes) - 1))

        # Perform clustering
        clusters = centrality_analyzer.cluster_nodes(
            nodes,
            embeddings,
            n_clusters=request.cluster_count,
        )

        # Cluster color palette
        colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
            '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
            '#BB8FCE', '#85C1E9', '#F8B500', '#82E0AA',
        ]

        # Format clusters
        formatted_clusters = [
            {
                "cluster_id": c.cluster_id,
                "concepts": c.node_ids,
                "concept_names": c.node_names,
                "label": c.label or f"Cluster {c.cluster_id + 1}",
                "size": c.size,
                "color": colors[c.cluster_id % len(colors)],
            }
            for c in clusters
        ]

        # Update entities with new cluster assignments
        for cluster in clusters:
            for node_id in cluster.node_ids:
                await database.execute(
                    """
                    UPDATE entities
                    SET properties = properties || $1::jsonb
                    WHERE id = $2
                    """,
                    json.dumps({"cluster_id": cluster.cluster_id}),
                    node_id,
                )

        return {
            "clusters": formatted_clusters,
            "optimal_k": optimal_k,
        }

    except Exception as e:
        logger.error(f"Failed to recompute clusters: {e}")
        raise HTTPException(status_code=500, detail="Failed to recompute clusters")


@router.post("/rebuild/{project_id}")
async def rebuild_embeddings_and_relationships(
    project_id: UUID,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Rebuild embeddings and relationships for an existing project.

    This is useful when:
    - The original import failed to create embeddings (missing API key)
    - You want to regenerate relationships with different parameters
    - Embeddings need to be updated after entity changes

    Requires authentication in production.
    """
    try:
        # Verify project access
        await verify_project_access(database, project_id, current_user, "edit")

        graph_store = GraphStore(database)

        # Step 1: Create embeddings for entities without them
        logger.info(f"Creating embeddings for project {project_id}")
        embeddings_created = await graph_store.create_embeddings(str(project_id))
        logger.info(f"Created {embeddings_created} embeddings")

        if embeddings_created == 0:
            # Check if it's because no entities need embeddings or API key issue
            entity_count = await database.fetchval(
                "SELECT COUNT(*) FROM entities WHERE project_id = $1",
                project_id,
            )
            entities_with_embeddings = await database.fetchval(
                "SELECT COUNT(*) FROM entities WHERE project_id = $1 AND embedding IS NOT NULL",
                project_id,
            )

            if entity_count == 0:
                return {
                    "status": "warning",
                    "message": "No entities found in project",
                    "embeddings_created": 0,
                    "relationships_created": 0,
                }
            elif entities_with_embeddings == entity_count:
                logger.info("All entities already have embeddings")
            else:
                # Some entities exist but no embeddings created - likely API key issue
                return {
                    "status": "warning",
                    "message": "No embeddings created. Check COHERE_API_KEY configuration.",
                    "entities_count": entity_count,
                    "embeddings_created": 0,
                    "relationships_created": 0,
                }

        # Step 2: Build relationships
        logger.info(f"Building relationships for project {project_id}")
        relationships_created = await graph_store.build_concept_relationships(str(project_id))
        logger.info(f"Created {relationships_created} relationships")

        return {
            "status": "success",
            "message": f"Rebuilt {embeddings_created} embeddings and {relationships_created} relationships",
            "embeddings_created": embeddings_created,
            "relationships_created": relationships_created,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rebuild embeddings/relationships: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rebuild: {str(e)}"
        )
