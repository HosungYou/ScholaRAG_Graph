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
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from enum import Enum
import asyncpg.exceptions
from datetime import datetime
import io

from database import db
from graph.graph_store import GraphStore
from graph.metrics_cache import metrics_cache
from auth.dependencies import require_auth_if_configured
from auth.models import User
from routers.projects import check_project_access
from routers.integrations import get_effective_api_key
from config import settings

logger = logging.getLogger(__name__)


# ============================================
# Relationship Evidence Models (Phase 1: Contextual Edge Exploration)
# ============================================

class EvidenceChunkResponse(BaseModel):
    """Single evidence chunk supporting a relationship."""
    evidence_id: str
    chunk_id: str
    text: str
    section_type: str
    paper_id: Optional[str] = None
    paper_title: Optional[str] = None
    paper_authors: Optional[str] = None
    paper_year: Optional[int] = None
    relevance_score: float = 0.5
    context_snippet: Optional[str] = None


class RelationshipEvidenceResponse(BaseModel):
    """Response containing all evidence for a relationship."""
    relationship_id: str
    source_name: str
    target_name: str
    relationship_type: str
    evidence_chunks: List[EvidenceChunkResponse]
    total_evidence: int
    # v0.9.0: Error code for graceful degradation
    error_code: Optional[str] = None  # "table_missing", "permission_denied", "query_failed"
    # v0.11.0: AI-generated explanation when no text evidence
    ai_explanation: Optional[str] = None


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


def escape_sql_like(s: str) -> str:
    """Escape special characters for SQL LIKE queries."""
    if not s:
        return s
    return s.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_').replace("'", "''")


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
    max_nodes: int = Query(1000, le=5000),
    max_edges: int = Query(15000, ge=1000, le=50000),
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
                    WHEN 'Paper' THEN 5
                    WHEN 'Author' THEN 5
                    ELSE 1
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
                LIMIT $3
            """
            edge_rows = await database.fetch(
                edges_query,
                str(project_id),
                node_ids,
                max_edges,
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
    cluster_id: Optional[int] = None
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
    # v0.9.0: Reason code when gaps is empty
    no_gaps_reason: Optional[str] = None  # "no_clusters", "not_analyzed", "well_connected"


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
                concepts=[str(c) for c in (row["concepts"] or [])],  # Convert UUIDs to strings
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

        # v0.9.0: Determine reason when no gaps found
        no_gaps_reason = None
        if len(gaps) == 0:
            if len(clusters) < 2:
                no_gaps_reason = "no_clusters"
            else:
                no_gaps_reason = "well_connected"  # Clusters exist but all are well-connected

        return GapAnalysisResponse(
            clusters=clusters,
            gaps=gaps,
            centrality_metrics=centrality_metrics,
            total_concepts=concept_count or 0,
            total_relationships=relationship_count or 0,
            no_gaps_reason=no_gaps_reason,
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
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer

        min_concepts_for_embedding_path = 10
        max_concepts_for_gap = 1200
        max_tfidf_features = 64

        # Get all concepts with embeddings
        # Try to get concepts with embeddings first
        concept_rows = await database.fetch(
            """
            SELECT id, name, properties, embedding
            FROM entities
            WHERE project_id = $1
            AND entity_type IN ('Concept', 'Method', 'Finding', 'Problem', 'Dataset', 'Metric', 'Innovation', 'Limitation')
            AND embedding IS NOT NULL
            ORDER BY id
            LIMIT $2
            """,
            str(project_id),
            max_concepts_for_gap,
        )

        use_tfidf_fallback = False

        if not concept_rows or len(concept_rows) < min_concepts_for_embedding_path:
            # TF-IDF fallback: fetch all concepts regardless of embedding status
            logger.warning(
                "Only %d concepts with embeddings (need %d+). Using TF-IDF fallback.",
                len(concept_rows) if concept_rows else 0,
                min_concepts_for_embedding_path,
            )
            all_concept_rows = await database.fetch(
                """
                SELECT id, name, properties
                FROM entities
                WHERE project_id = $1
                AND entity_type IN ('Concept', 'Method', 'Finding', 'Problem', 'Dataset', 'Metric', 'Innovation', 'Limitation')
                ORDER BY id
                LIMIT $2
                """,
                str(project_id),
                max_concepts_for_gap,
            )

            if not all_concept_rows or len(all_concept_rows) < 3:
                return GapAnalysisResponse(
                    clusters=[],
                    gaps=[],
                    centrality_metrics=[],
                    total_concepts=len(all_concept_rows) if all_concept_rows else 0,
                    total_relationships=0,
                    no_gaps_reason="insufficient_concepts",
                )

            # Generate TF-IDF pseudo-embeddings
            try:
                concept_names = [(r["name"] or "").strip() for r in all_concept_rows]
                concept_names = [n if n else "unknown concept" for n in concept_names]
                vectorizer = TfidfVectorizer(
                    max_features=max_tfidf_features,
                    stop_words='english',
                    dtype=np.float32,
                )
                tfidf_matrix = vectorizer.fit_transform(concept_names)
                feature_count = tfidf_matrix.shape[1]
                if feature_count == 0:
                    raise ValueError("TF-IDF produced zero features")

                # Create synthetic concept_rows with TF-IDF embeddings
                concept_rows = []
                for i, row in enumerate(all_concept_rows):
                    concept_rows.append({
                        "id": row["id"],
                        "name": row["name"],
                        "properties": row["properties"],
                        "embedding": tfidf_matrix.getrow(i).toarray().astype(np.float32, copy=False).ravel().tolist(),
                    })
                use_tfidf_fallback = True
                logger.info(
                    "TF-IDF fallback: generated pseudo-embeddings for %d concepts "
                    "(features=%d, concept_cap=%d)",
                    len(concept_rows),
                    feature_count,
                    max_concepts_for_gap,
                )
            except Exception as e:
                logger.error(f"TF-IDF fallback failed: {e}")
                return GapAnalysisResponse(
                    clusters=[],
                    gaps=[],
                    centrality_metrics=[],
                    total_concepts=len(all_concept_rows),
                    total_relationships=0,
                    no_gaps_reason="embedding_unavailable",
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
        concepts = []
        for row in concept_rows:
            if use_tfidf_fallback:
                embedding = row["embedding"]  # Already a list from TF-IDF
            else:
                embedding = _parse_embedding(row["embedding"]) or None
            concepts.append({
                "id": str(row["id"]),
                "name": row["name"],
                "embedding": embedding,
                "properties": row.get("properties") or {},
            })

        relationships = [
            {
                "id": str(row["id"]),
                "source_id": str(row["source_id"]),  # Fixed: was "source", gap_detector expects "source_id"
                "target_id": str(row["target_id"]),  # Fixed: was "target", gap_detector expects "target_id"
                "type": row["relationship_type"],
                "properties": row["properties"] or {},
            }
            for row in relationship_rows
        ]

        # Run gap detection
        from dependencies import get_llm_provider
        llm = get_llm_provider()
        gap_detector = GapDetector(llm_provider=llm)
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
        # Build concept id -> name mapping for lookup
        concept_name_map = {c["id"]: c["name"] for c in concepts}

        for cluster in analysis.get("clusters", []):
            # Get concept names from the mapping
            cluster_concept_names = [
                concept_name_map.get(cid, "")
                for cid in cluster.concept_ids
            ]

            # Generate meaningful label using LLM (with fallback)
            if cluster.keywords:
                label = await gap_detector._generate_cluster_label(cluster.keywords)
            elif cluster_concept_names:
                filtered_names = [n for n in cluster_concept_names if n and n.strip()]
                label = ", ".join(filtered_names[:3]) if filtered_names else f"Cluster {cluster.id + 1}"
            else:
                label = f"Cluster {cluster.id + 1}"

            logger.info(f"Storing cluster {cluster.id}: {len(cluster.concept_ids)} concepts, name={cluster.name}, label={label}")

            await database.execute(
                """
                INSERT INTO concept_clusters (project_id, cluster_id, concepts, concept_names, size, density, label)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                str(project_id),
                cluster.id,  # ConceptCluster uses 'id' not 'cluster_id'
                [str(cid) for cid in cluster.concept_ids],  # Convert to strings for TEXT[]
                cluster_concept_names,  # Derived from concept_ids
                len(cluster.concept_ids),  # Computed size
                0.0,  # Default density (can be calculated if needed)
                label,
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

            # Convert concept IDs to sets for efficient lookup
            concept_ids_a = set(str(cid) for cid in gap.concept_a_ids)
            concept_ids_b = set(str(cid) for cid in gap.concept_b_ids)
            a_names = [c["name"] for c in concepts if c["id"] in concept_ids_a and c["name"]][:5]
            b_names = [c["name"] for c in concepts if c["id"] in concept_ids_b and c["name"]][:5]

            # Fallback 1: cluster keywords
            if not a_names:
                cl_a = next((cl for cl in analysis.get("clusters", [])
                             if cl.id == gap.cluster_a_id), None)
                if cl_a and cl_a.keywords:
                    a_names = [k for k in cl_a.keywords[:3] if k and k.strip()]
            if not b_names:
                cl_b = next((cl for cl in analysis.get("clusters", [])
                             if cl.id == gap.cluster_b_id), None)
                if cl_b and cl_b.keywords:
                    b_names = [k for k in cl_b.keywords[:3] if k and k.strip()]

            # Fallback 2: default label
            if not a_names:
                a_names = [f"Cluster {gap.cluster_a_id + 1}"]
            if not b_names:
                b_names = [f"Cluster {gap.cluster_b_id + 1}"]

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
                list(concept_ids_a),
                list(concept_ids_b),
                a_names,
                b_names,
                gap.gap_strength,
                gap.bridge_concepts or [],
                gap.suggested_research_questions or [],
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

        await metrics_cache.invalidate_project(str(project_id))

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


# ============================================
# Bridge Hypothesis Generation API (Phase 3)
# ============================================

class BridgeHypothesisResponse(BaseModel):
    """Single bridge hypothesis."""
    title: str
    description: str
    methodology: str
    connecting_concepts: List[str]
    confidence: float


class BridgeGenerationResponse(BaseModel):
    """Response for bridge hypothesis generation."""
    hypotheses: List[BridgeHypothesisResponse]
    bridge_type: str  # "theoretical", "methodological", "empirical"
    key_insight: str
    gap_id: str


@router.post("/gaps/{gap_id}/generate-bridge", response_model=BridgeGenerationResponse)
async def generate_bridge_hypotheses(
    gap_id: UUID,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Generate AI-powered bridge hypotheses to connect two concept clusters.

    This is the core "Generate Bridge Idea" feature - uses LLM to propose
    novel research hypotheses that could bridge the structural gap.

    Returns:
        - hypotheses: List of 3-5 specific, testable research hypotheses
        - bridge_type: "theoretical", "methodological", or "empirical"
        - key_insight: One-sentence summary of the opportunity

    Requires auth in production.
    """
    try:
        # Get gap details
        row = await database.fetchrow(
            """
            SELECT id, cluster_a_id, cluster_b_id,
                   cluster_a_names, cluster_b_names,
                   gap_strength, project_id
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

        # Get LLM provider
        from dependencies import get_llm_provider

        llm = get_llm_provider()

        # Initialize gap detector with LLM
        from graph.gap_detector import GapDetector, StructuralGap as GapModel

        gap_detector = GapDetector(llm_provider=llm)

        # Create gap model
        gap_model = GapModel(
            id=str(gap_id),
            cluster_a_id=row["cluster_a_id"],
            cluster_b_id=row["cluster_b_id"],
            gap_strength=row["gap_strength"],
        )

        # Generate hypotheses
        result = await gap_detector.generate_bridge_hypotheses(
            gap_model,
            row["cluster_a_names"] or [],
            row["cluster_b_names"] or [],
        )

        # Convert to response model
        hypotheses = [
            BridgeHypothesisResponse(
                title=h["title"],
                description=h["description"],
                methodology=h["methodology"],
                connecting_concepts=h["connecting_concepts"],
                confidence=h["confidence"],
            )
            for h in result.get("hypotheses", [])
        ]

        return BridgeGenerationResponse(
            hypotheses=hypotheses,
            bridge_type=result.get("bridge_type", "theoretical"),
            key_insight=result.get("key_insight", "Connection opportunity detected."),
            gap_id=str(gap_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate bridge hypotheses: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate bridge hypotheses")


# ============================================
# Bridge Creation API (Phase 6 - Accept Hypothesis)
# ============================================

class BridgeCreationRequest(BaseModel):
    """Request to create a bridge relationship from an accepted hypothesis."""
    hypothesis_title: str
    hypothesis_description: str
    connecting_concepts: List[str]  # List of concept names to connect
    confidence: float = 0.5


class BridgeCreationResponse(BaseModel):
    """Response after creating bridge relationships."""
    success: bool
    relationships_created: int
    relationship_ids: List[str]
    message: str


@router.post("/gaps/{gap_id}/create-bridge", response_model=BridgeCreationResponse)
async def create_bridge_from_hypothesis(
    gap_id: UUID,
    request: BridgeCreationRequest,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Create BRIDGES_GAP relationships between concepts from an accepted hypothesis.

    This endpoint is called when a user accepts a bridge hypothesis. It creates
    new relationships in the knowledge graph connecting concepts from the two
    clusters identified in the structural gap.

    Args:
        gap_id: The structural gap ID
        request: BridgeCreationRequest with hypothesis details and concepts to connect

    Returns:
        BridgeCreationResponse with created relationship IDs

    Requires auth in production.
    """
    try:
        # Get gap details including project_id
        gap_row = await database.fetchrow(
            """
            SELECT id, project_id, cluster_a_concepts, cluster_b_concepts
            FROM structural_gaps
            WHERE id = $1
            """,
            str(gap_id),
        )

        if not gap_row:
            raise HTTPException(status_code=404, detail="Gap not found")

        project_id = UUID(str(gap_row["project_id"]))

        # Verify project access (write access needed)
        await verify_project_access(database, project_id, current_user, "write")

        # Find concept entities by name
        concept_ids = []
        for concept_name in request.connecting_concepts:
            row = await database.fetchrow(
                """
                SELECT id FROM entities
                WHERE project_id = $1 AND name ILIKE $2 AND entity_type IN ('Concept', 'Method', 'Finding')
                LIMIT 1
                """,
                str(project_id),
                concept_name,
            )
            if row:
                concept_ids.append(str(row["id"]))

        if len(concept_ids) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Need at least 2 valid concepts to create bridge. Found: {len(concept_ids)}"
            )

        # Create BRIDGES_GAP relationships between consecutive pairs
        import uuid
        relationship_ids = []

        for i in range(len(concept_ids) - 1):
            source_id = concept_ids[i]
            target_id = concept_ids[i + 1]

            # Check if relationship already exists
            existing = await database.fetchrow(
                """
                SELECT id FROM relationships
                WHERE project_id = $1
                  AND source_id = $2 AND target_id = $3
                  AND relationship_type = 'BRIDGES_GAP'
                """,
                str(project_id),
                source_id,
                target_id,
            )

            if existing:
                relationship_ids.append(str(existing["id"]))
                continue

            # Create new relationship
            rel_id = str(uuid.uuid4())
            properties = {
                "gap_id": str(gap_id),
                "hypothesis_title": request.hypothesis_title,
                "hypothesis_description": request.hypothesis_description,
                "confidence": request.confidence,
                "ai_generated": True,
            }

            await database.execute(
                """
                INSERT INTO relationships (id, project_id, source_id, target_id, relationship_type, weight, properties)
                VALUES ($1, $2, $3, $4, 'BRIDGES_GAP', $5, $6)
                """,
                rel_id,
                str(project_id),
                source_id,
                target_id,
                request.confidence,
                json.dumps(properties),
            )

            relationship_ids.append(rel_id)

        logger.info(f"Created {len(relationship_ids)} bridge relationships for gap {gap_id}")

        return BridgeCreationResponse(
            success=True,
            relationships_created=len(relationship_ids),
            relationship_ids=relationship_ids,
            message=f"Successfully created {len(relationship_ids)} bridge relationship(s) based on hypothesis: {request.hypothesis_title}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create bridge relationships: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create bridge relationships: {str(e)}")


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
# Gap-Based Paper Recommendations
# ============================================================

class RecommendedPaperResponse(BaseModel):
    title: str
    year: Optional[int] = None
    citation_count: int = 0
    url: Optional[str] = None
    abstract_snippet: str = ""

class GapRecommendationsResponse(BaseModel):
    gap_id: str
    query_used: str
    papers: List[RecommendedPaperResponse]


@router.get("/gaps/{project_id}/recommendations/{gap_id}",
            response_model=GapRecommendationsResponse)
async def get_gap_recommendations(
    project_id: UUID,
    gap_id: UUID,
    limit: int = Query(5, ge=1, le=10),
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get paper recommendations for a structural gap via Semantic Scholar."""
    await verify_project_access(database, project_id, current_user, "access")

    try:
        # Fetch gap with project ownership check
        row = await database.fetchrow(
            """
            SELECT bridge_candidates, cluster_a_names, cluster_b_names
            FROM structural_gaps
            WHERE id = $1 AND project_id = $2
            """,
            str(gap_id),
            str(project_id),
        )

        if not row:
            raise HTTPException(status_code=404, detail="Gap not found in this project")

        # Build search query from bridge candidates + cluster names
        bridge = row["bridge_candidates"] or []
        a_names = row["cluster_a_names"] or []
        b_names = row["cluster_b_names"] or []

        query_parts = bridge[:3] + a_names[:2] + b_names[:2]
        query = " ".join(query_parts) if query_parts else "research gap"

        # Search Semantic Scholar
        import asyncio
        from integrations.semantic_scholar import SemanticScholarClient

        papers = []
        try:
            s2_key = await get_effective_api_key(current_user, "semantic_scholar", settings.semantic_scholar_api_key)
            async with SemanticScholarClient(api_key=s2_key or None) as client:
                results = await asyncio.wait_for(
                    client.search_papers(query=query, limit=limit),
                    timeout=15.0,
                )
                for p in results:
                    url = None
                    if p.doi:
                        url = f"https://doi.org/{p.doi}"
                    elif p.arxiv_id:
                        url = f"https://arxiv.org/abs/{p.arxiv_id}"

                    snippet = ""
                    if p.abstract:
                        snippet = p.abstract[:200] + ("..." if len(p.abstract) > 200 else "")

                    papers.append(RecommendedPaperResponse(
                        title=p.title,
                        year=p.year,
                        citation_count=p.citation_count,
                        url=url,
                        abstract_snippet=snippet,
                    ))
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"Semantic Scholar search failed: {e}")
            # Return empty papers gracefully, not 500

        return GapRecommendationsResponse(
            gap_id=str(gap_id),
            query_used=query,
            papers=papers,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get gap recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations")


# ============================================================
# Gap Analysis Report Export
# ============================================================

@router.get("/gaps/{project_id}/export")
async def export_gap_report(
    project_id: UUID,
    format: str = Query("markdown", pattern="^(markdown)$"),
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Export gap analysis as a Markdown report."""
    await verify_project_access(database, project_id, current_user, "access")

    try:
        # Get project info
        project_row = await database.fetchrow(
            "SELECT name, research_question FROM projects WHERE id = $1",
            str(project_id),
        )
        project_name = project_row["name"] if project_row else "Unknown Project"
        research_question = project_row.get("research_question", "") if project_row else ""

        # Get clusters
        cluster_rows = await database.fetch(
            """
            SELECT cluster_id, label, size, concept_names
            FROM concept_clusters
            WHERE project_id = $1
            ORDER BY cluster_id
            """,
            str(project_id),
        )

        # Get gaps
        gap_rows = await database.fetch(
            """
            SELECT gap_strength, bridge_candidates, research_questions,
                   cluster_a_names, cluster_b_names
            FROM structural_gaps
            WHERE project_id = $1
            ORDER BY gap_strength DESC
            """,
            str(project_id),
        )

        if not cluster_rows and not gap_rows:
            raise HTTPException(
                status_code=404,
                detail="No gap analysis data. Run gap detection first."
            )

        # Build Markdown
        lines = [
            f"# Gap Analysis Report: {project_name}",
            f"",
            f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            "",
        ]

        if research_question:
            lines.extend([
                f"**Research Question**: {research_question}",
                "",
            ])

        # Clusters table
        if cluster_rows:
            lines.extend([
                "## Concept Clusters",
                "",
                "| Cluster | Label | Size | Top Concepts |",
                "|---------|-------|------|-------------|",
            ])
            for row in cluster_rows:
                names = row["concept_names"] or []
                top_concepts = ", ".join(names[:5])
                if len(names) > 5:
                    top_concepts += f" (+{len(names) - 5})"
                lines.append(
                    f"| {row['cluster_id']} | {row['label'] or 'N/A'} | {row['size']} | {top_concepts} |"
                )
            lines.append("")

        # Gaps section
        if gap_rows:
            lines.extend([
                "## Structural Gaps",
                "",
            ])
            for i, row in enumerate(gap_rows, 1):
                a_names = row["cluster_a_names"] or []
                b_names = row["cluster_b_names"] or []
                bridge = row["bridge_candidates"] or []
                questions = row["research_questions"] or []

                lines.extend([
                    f"### Gap {i} (Strength: {row['gap_strength']:.1%})",
                    "",
                    f"- **Cluster A**: {', '.join(a_names[:3])}",
                    f"- **Cluster B**: {', '.join(b_names[:3])}",
                ])

                if bridge:
                    lines.append(f"- **Bridge Candidates**: {', '.join(bridge[:5])}")

                if questions:
                    lines.extend(["", "**Research Questions**:", ""])
                    for q in questions:
                        lines.append(f"1. {q}")

                lines.append("")

        # Summary stats
        total_concepts = sum(row["size"] for row in cluster_rows)
        lines.extend([
            "---",
            "",
            f"*{total_concepts} concepts across {len(cluster_rows)} clusters, {len(gap_rows)} structural gaps identified.*",
        ])

        content = "\n".join(lines)
        buffer = io.BytesIO(content.encode("utf-8"))

        filename = f"gap_report_{project_name.replace(' ', '_')}.md"
        return StreamingResponse(
            buffer,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export gap report: {e}")
        raise HTTPException(status_code=500, detail="Failed to export report")


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
    cache_key = f"centrality:{project_id}:{metric}"
    cached = await metrics_cache.get(cache_key)
    if cached is not None:
        return cached

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
            payload = {
                "metric": metric,
                "centrality": {},
                "top_bridges": [],
            }
            await metrics_cache.set(cache_key, payload)
            return payload

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

        payload = {
            "metric": metric,
            "centrality": centrality,
            "top_bridges": top_bridges_with_names,
        }
        await metrics_cache.set(cache_key, payload)
        return payload

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compute centrality metrics: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute centrality metrics: {type(e).__name__}: {str(e)}"
        )


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


# ============================================
# Diversity Analysis API (Phase 4)
# ============================================

class DiversityMetricsResponse(BaseModel):
    """Response for diversity analysis."""
    shannon_entropy: float
    normalized_entropy: float
    modularity: float
    bias_score: float
    diversity_rating: str  # "high", "medium", "low"
    cluster_sizes: List[int]
    dominant_cluster_ratio: float
    gini_coefficient: float


@router.get("/diversity/{project_id}", response_model=DiversityMetricsResponse)
async def get_diversity_metrics(
    project_id: UUID,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Get diversity metrics for a project's knowledge graph.

    Analyzes how diverse/balanced the concept clusters are:
    - shannon_entropy: Evenness of cluster distribution (higher = more diverse)
    - modularity: How well-defined clusters are (-0.5 to 1.0)
    - bias_score: If one cluster dominates (0-1, lower = better)
    - diversity_rating: "high", "medium", or "low"
    - gini_coefficient: Inequality measure (0 = equal, 1 = unequal)

    Requires auth in production.
    """
    # Verify project access
    await verify_project_access(database, project_id, current_user, "access")

    cache_key = f"diversity:{project_id}"
    cached = await metrics_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        from graph.diversity_analyzer import diversity_analyzer

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
            SELECT id, source_id, target_id
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
            payload = {
                "shannon_entropy": 0.0,
                "normalized_entropy": 0.0,
                "modularity": 0.0,
                "bias_score": 1.0,
                "diversity_rating": "low",
                "cluster_sizes": [],
                "dominant_cluster_ratio": 1.0,
                "gini_coefficient": 1.0,
            }
            await metrics_cache.set(cache_key, payload)
            return payload

        # Convert to format for analyzer
        nodes = [{"id": str(row["id"])} for row in node_rows]
        edges = [
            {"source": str(row["source_id"]), "target": str(row["target_id"])}
            for row in edge_rows
        ]
        clusters = [
            {"node_ids": row["concepts"] or [], "size": row["size"]}
            for row in cluster_rows
        ]

        # If no clusters defined, create a single cluster with all nodes
        if not clusters:
            clusters = [{"node_ids": [n["id"] for n in nodes]}]

        # Compute metrics
        metrics = diversity_analyzer.analyze_from_data(nodes, edges, clusters)

        payload = {
            "shannon_entropy": metrics.shannon_entropy,
            "normalized_entropy": metrics.normalized_entropy,
            "modularity": metrics.modularity,
            "bias_score": metrics.bias_score,
            "diversity_rating": metrics.diversity_rating,
            "cluster_sizes": metrics.cluster_sizes,
            "dominant_cluster_ratio": metrics.dominant_cluster_ratio,
            "gini_coefficient": metrics.gini_coefficient,
        }
        await metrics_cache.set(cache_key, payload)
        return payload

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compute diversity metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute diversity metrics")


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

    cache_key = f"graph_metrics:{project_id}"
    cached = await metrics_cache.get(cache_key)
    if cached is not None:
        return cached

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
            payload = {
                "modularity": 0.0,
                "diversity": 0.0,
                "density": 0.0,
                "avg_clustering": 0.0,
                "num_components": 0,
                "node_count": 0,
                "edge_count": 0,
                "cluster_count": 0,
            }
            await metrics_cache.set(cache_key, payload)
            return payload

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

        payload = {
            "modularity": metrics["modularity"],
            "diversity": metrics["diversity"],
            "density": metrics["density"],
            "avg_clustering": metrics["avg_clustering"],
            "num_components": metrics["num_components"],
            "node_count": len(nodes),
            "edge_count": len(edges),
            "cluster_count": len(clusters),
        }
        await metrics_cache.set(cache_key, payload)
        return payload

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

        await metrics_cache.invalidate_project(str(project_id))

        return {
            "clusters": formatted_clusters,
            "optimal_k": optimal_k,
        }

    except Exception as e:
        logger.error(f"Failed to recompute clusters: {e}")
        raise HTTPException(status_code=500, detail="Failed to recompute clusters")


# ============================================
# Temporal Graph API (Phase 2: Graph Evolution)
# ============================================

class TemporalStatsResponse(BaseModel):
    """Temporal statistics for a project."""
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    year_count: int = 0
    entities_with_year: int = 0
    total_entities: int = 0


class TemporalGraphResponse(BaseModel):
    """Graph data with temporal filtering and year range."""
    nodes: List[NodeResponse]
    edges: List[EdgeResponse]
    year_range: dict  # {min: int, max: int}
    temporal_stats: TemporalStatsResponse


@router.get("/temporal/{project_id}", response_model=TemporalGraphResponse)
async def get_temporal_graph(
    project_id: UUID,
    year_start: Optional[int] = Query(None, description="Filter entities from this year"),
    year_end: Optional[int] = Query(None, description="Filter entities up to this year"),
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Get graph data filtered by year range for temporal evolution visualization.

    This enables the "time slider" feature - animate how the knowledge graph
    evolved over years as research progressed.

    Returns nodes/edges visible up to year_end, with opacity hints for
    nodes that appeared earlier vs recently.

    Requires auth in production.
    """
    # Verify project access
    await verify_project_access(database, project_id, current_user, "access")

    try:
        # Get temporal statistics
        stats_row = await database.fetchrow(
            """
            SELECT
                MIN(first_seen_year) as min_year,
                MAX(COALESCE(last_seen_year, first_seen_year)) as max_year,
                COUNT(DISTINCT first_seen_year) as year_count,
                COUNT(*) FILTER (WHERE first_seen_year IS NOT NULL) as entities_with_year,
                COUNT(*) as total_entities
            FROM entities
            WHERE project_id = $1
            """,
            str(project_id),
        )

        temporal_stats = TemporalStatsResponse(
            min_year=stats_row["min_year"],
            max_year=stats_row["max_year"],
            year_count=stats_row["year_count"] or 0,
            entities_with_year=stats_row["entities_with_year"] or 0,
            total_entities=stats_row["total_entities"] or 0,
        )

        # If no temporal data, fall back to year from properties
        if temporal_stats.min_year is None:
            # Try to get years from properties
            props_stats = await database.fetchrow(
                """
                SELECT
                    MIN((properties->>'year')::INTEGER) as min_year,
                    MAX((properties->>'year')::INTEGER) as max_year
                FROM entities
                WHERE project_id = $1
                AND properties->>'year' IS NOT NULL
                """,
                str(project_id),
            )
            if props_stats and props_stats["min_year"]:
                temporal_stats.min_year = props_stats["min_year"]
                temporal_stats.max_year = props_stats["max_year"]

        # Build year filter conditions
        year_filter = ""
        params = [str(project_id)]

        if year_start is not None and year_end is not None:
            year_filter = """
                AND (
                    first_seen_year IS NULL
                    OR (first_seen_year >= $2 AND first_seen_year <= $3)
                    OR (first_seen_year <= $3 AND (last_seen_year IS NULL OR last_seen_year >= $2))
                )
            """
            params.extend([year_start, year_end])
        elif year_end is not None:
            year_filter = """
                AND (first_seen_year IS NULL OR first_seen_year <= $2)
            """
            params.append(year_end)
        elif year_start is not None:
            year_filter = """
                AND (first_seen_year IS NULL OR first_seen_year >= $2)
            """
            params.append(year_start)

        # Get filtered nodes
        nodes_query = f"""
            SELECT id, entity_type::text, name, properties,
                   first_seen_year, last_seen_year, source_year
            FROM entities
            WHERE project_id = $1 {year_filter}
            ORDER BY
                CASE entity_type::text
                    WHEN 'Paper' THEN 1
                    WHEN 'Concept' THEN 2
                    WHEN 'Author' THEN 3
                    ELSE 4
                END,
                first_seen_year NULLS LAST,
                created_at DESC
            LIMIT 500
        """
        node_rows = await database.fetch(nodes_query, *params)

        # Add temporal properties to nodes
        nodes = []
        for row in node_rows:
            props = _parse_json_field(row["properties"])
            # Add temporal info to properties
            props["first_seen_year"] = row["first_seen_year"]
            props["last_seen_year"] = row["last_seen_year"]
            props["source_year"] = row["source_year"]

            nodes.append(
                NodeResponse(
                    id=str(row["id"]),
                    entity_type=row["entity_type"],
                    name=row["name"],
                    properties=props,
                )
            )

        # Get edges connecting visible nodes
        node_ids = [str(row["id"]) for row in node_rows]

        if node_ids:
            edges_query = """
                SELECT id, source_id, target_id, relationship_type::text,
                       properties, weight, first_seen_year
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

            edges = []
            for row in edge_rows:
                props = _parse_json_field(row["properties"])
                props["first_seen_year"] = row["first_seen_year"]

                edges.append(
                    EdgeResponse(
                        id=str(row["id"]),
                        source=str(row["source_id"]),
                        target=str(row["target_id"]),
                        relationship_type=row["relationship_type"],
                        properties=props,
                        weight=row["weight"] or 1.0,
                    )
                )
        else:
            edges = []

        return TemporalGraphResponse(
            nodes=nodes,
            edges=edges,
            year_range={
                "min": temporal_stats.min_year or 2000,
                "max": temporal_stats.max_year or 2025,
            },
            temporal_stats=temporal_stats,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get temporal graph: {e}")
        raise HTTPException(status_code=500, detail="Failed to get temporal graph data")


@router.post("/temporal/{project_id}/migrate")
async def migrate_temporal_data(
    project_id: UUID,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Migrate/backfill temporal data for existing entities in a project.

    This populates first_seen_year, last_seen_year from paper metadata.
    Run this after importing papers to enable temporal visualization.

    Requires auth in production.
    """
    # Verify project access
    await verify_project_access(database, project_id, current_user, "modify")

    try:
        # Run the migration function
        result = await database.fetchrow(
            "SELECT * FROM migrate_entity_temporal_data($1)",
            str(project_id),
        )

        return {
            "status": "success",
            "entities_updated": result["entities_updated"] if result else 0,
            "relationships_updated": result["relationships_updated"] if result else 0,
        }

    except Exception as e:
        logger.error(f"Failed to migrate temporal data: {e}")
        # If function doesn't exist, return a helpful message
        if "function migrate_entity_temporal_data" in str(e):
            raise HTTPException(
                status_code=500,
                detail="Temporal migration function not found. Please run database migration 013_entity_temporal.sql first."
            )
        raise HTTPException(status_code=500, detail="Failed to migrate temporal data")


# ============================================
# Temporal Timeline API (v0.12.1)
# ============================================

class YearBucket(BaseModel):
    year: int
    new_concepts: int
    total_concepts: int
    top_concepts: List[str]


class TemporalTimelineResponse(BaseModel):
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    buckets: List[YearBucket]
    total_with_year: int
    total_without_year: int


@router.get("/temporal/{project_id}/timeline", response_model=TemporalTimelineResponse)
async def get_temporal_timeline(
    project_id: UUID,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get aggregated timeline data for temporal visualization."""
    await verify_project_access(database, project_id, current_user, "access")

    # TTL cache reuse (metrics_cache singleton)
    cache_key = f"timeline:{project_id}"
    cached = await metrics_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        year_rows = await database.fetch(
            """
            SELECT
                first_seen_year as year,
                COUNT(*) as concept_count,
                (ARRAY_AGG(name ORDER BY
                    CASE WHEN properties->>'centrality_pagerank' ~ '^-?\\d+(\\.\\d+)?$'
                         THEN (properties->>'centrality_pagerank')::float
                         ELSE 0 END
                    DESC NULLS LAST
                ))[1:5] as top_names
            FROM entities
            WHERE project_id = $1
              AND entity_type IN ('Concept', 'Method', 'Finding', 'Problem',
                                  'Dataset', 'Metric', 'Innovation', 'Limitation')
              AND first_seen_year IS NOT NULL
            GROUP BY first_seen_year
            ORDER BY first_seen_year
            """,
            str(project_id),
        )

        if not year_rows:
            # Fallback to source_year
            year_rows = await database.fetch(
                """
                SELECT
                    source_year as year,
                    COUNT(*) as concept_count,
                    (ARRAY_AGG(name ORDER BY name))[1:5] as top_names
                FROM entities
                WHERE project_id = $1
                  AND entity_type IN ('Concept', 'Method', 'Finding', 'Problem',
                                      'Dataset', 'Metric', 'Innovation', 'Limitation')
                  AND source_year IS NOT NULL
                GROUP BY source_year
                ORDER BY source_year
                """,
                str(project_id),
            )

        total_without = await database.fetchval(
            """
            SELECT COUNT(*) FROM entities
            WHERE project_id = $1
              AND entity_type IN ('Concept', 'Method', 'Finding', 'Problem',
                                  'Dataset', 'Metric', 'Innovation', 'Limitation')
              AND first_seen_year IS NULL AND source_year IS NULL
            """,
            str(project_id),
        )

        if not year_rows:
            result = TemporalTimelineResponse(
                min_year=None, max_year=None,
                buckets=[], total_with_year=0,
                total_without_year=total_without or 0,
            )
            await metrics_cache.set(cache_key, result)
            return result

        buckets = []
        cumulative = 0
        for row in year_rows:
            cumulative += row["concept_count"]
            buckets.append(YearBucket(
                year=row["year"],
                new_concepts=row["concept_count"],
                total_concepts=cumulative,
                top_concepts=(row["top_names"] or [])[:5],
            ))

        result = TemporalTimelineResponse(
            min_year=year_rows[0]["year"],
            max_year=year_rows[-1]["year"],
            buckets=buckets,
            total_with_year=cumulative,
            total_without_year=total_without or 0,
        )
        await metrics_cache.set(cache_key, result)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get temporal timeline: {e}")
        raise HTTPException(500, "Failed to get temporal timeline data")


# ============================================
# Relationship Evidence API (Phase 1: Contextual Edge Exploration)
# ============================================

@router.get("/relationships/{relationship_id}/evidence", response_model=RelationshipEvidenceResponse)
async def get_relationship_evidence(
    relationship_id: str,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Get evidence chunks that support a specific relationship.

    This enables "contextual edge exploration" - clicking an edge shows
    the source text passages that justify the relationship.

    Requires auth in production.
    """
    try:
        # Get the relationship details
        relationship = await database.fetchrow(
            """
            SELECT r.id, r.source_id, r.target_id, r.relationship_type::text, r.project_id,
                   src.name as source_name, tgt.name as target_name
            FROM relationships r
            JOIN entities src ON r.source_id = src.id
            JOIN entities tgt ON r.target_id = tgt.id
            WHERE r.id = $1
            """,
            relationship_id,
        )

        if not relationship:
            raise HTTPException(status_code=404, detail="Relationship not found")

        project_id = UUID(str(relationship["project_id"]))

        # Verify project access
        await verify_project_access(database, project_id, current_user, "access")

        # v0.8.0: Check if relationship_evidence table exists before querying
        table_exists = await database.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'relationship_evidence'
            )
            """
        )

        evidence_rows = []
        ai_explanation = None

        if table_exists:
            # Try to get evidence from relationship_evidence table
            try:
                evidence_rows = await database.fetch(
                    """
                    SELECT
                        re.id as evidence_id,
                        re.chunk_id,
                        sc.text,
                        sc.section_type,
                        pm.id as paper_id,
                        pm.title as paper_title,
                        pm.authors as paper_authors,
                        pm.year as paper_year,
                        re.relevance_score,
                        re.context_snippet
                    FROM relationship_evidence re
                    JOIN semantic_chunks sc ON re.chunk_id = sc.id
                    JOIN paper_metadata pm ON sc.paper_id = pm.id
                    WHERE re.relationship_id = $1
                    ORDER BY re.relevance_score DESC
                    LIMIT 10
                    """,
                    relationship_id,
                )
            except Exception as e:
                # If query fails (e.g., RLS issues, missing columns), log and continue
                logger.warning(f"Failed to query relationship_evidence table: {e}")
                evidence_rows = []

        # If no evidence in dedicated table, try to find evidence from
        # semantic chunks that mention both entities
        if not evidence_rows:
            source_name = relationship["source_name"]
            target_name = relationship["target_name"]

            # Search for chunks containing both entity names
            evidence_rows = await database.fetch(
                """
                SELECT
                    sc.id as evidence_id,
                    sc.id as chunk_id,
                    sc.text,
                    sc.section_type,
                    pm.id as paper_id,
                    pm.title as paper_title,
                    pm.authors as paper_authors,
                    pm.year as paper_year,
                    0.5 as relevance_score,
                    NULL as context_snippet
                FROM semantic_chunks sc
                JOIN paper_metadata pm ON sc.paper_id = pm.id
                WHERE sc.project_id = $1
                AND sc.text ILIKE $2
                AND sc.text ILIKE $3
                ORDER BY sc.created_at DESC
                LIMIT 5
                """,
                str(project_id),
                f"%{escape_sql_like(source_name)}%",
                f"%{escape_sql_like(target_name)}%",
            )

        # v0.11.0: AI explanation fallback for CO_OCCURS_WITH and no-evidence relationships
        if not evidence_rows:
            rel_type = relationship["relationship_type"]
            source_name = relationship["source_name"]
            target_name = relationship["target_name"]

            # For CO_OCCURS_WITH, provide co-occurrence based explanation
            if rel_type == "CO_OCCURS_WITH":
                ai_explanation = (
                    f"'{source_name}' and '{target_name}' frequently co-occur across multiple papers "
                    f"in this collection. This co-occurrence relationship was detected through "
                    f"statistical analysis of concept mentions within the same documents."
                )
            else:
                # Try LLM-based explanation if available
                try:
                    from dependencies import get_llm_provider
                    llm = get_llm_provider()
                    if llm:
                        ai_explanation = await llm.generate(
                            f"Explain the academic relationship between '{source_name}' and '{target_name}' "
                            f"in the context of research. Keep it to 2-3 sentences."
                        )
                except Exception as e:
                    logger.warning(f"LLM explanation generation failed: {e}")

        evidence_chunks = [
            EvidenceChunkResponse(
                evidence_id=str(row["evidence_id"]),
                chunk_id=str(row["chunk_id"]),
                text=row["text"][:2000] if row["text"] else "",  # Limit text length
                section_type=row["section_type"] or "unknown",
                paper_id=str(row["paper_id"]) if row["paper_id"] else None,
                paper_title=row["paper_title"],
                paper_authors=row["paper_authors"],
                paper_year=row["paper_year"],
                relevance_score=float(row["relevance_score"]) if row["relevance_score"] else 0.5,
                context_snippet=row["context_snippet"],
            )
            for row in evidence_rows
        ]

        return RelationshipEvidenceResponse(
            relationship_id=relationship_id,
            source_name=relationship["source_name"],
            target_name=relationship["target_name"],
            relationship_type=relationship["relationship_type"],
            evidence_chunks=evidence_chunks,
            total_evidence=len(evidence_chunks),
            ai_explanation=ai_explanation,
        )

    except HTTPException:
        raise
    except asyncpg.exceptions.UndefinedTableError as e:
        logger.warning(f"Relationship evidence table missing: {e}")
        return RelationshipEvidenceResponse(
            relationship_id=relationship_id,
            source_name=relationship["source_name"] if relationship else "Unknown",
            target_name=relationship["target_name"] if relationship else "Unknown",
            relationship_type=relationship["relationship_type"] if relationship else "RELATED_TO",
            evidence_chunks=[],
            total_evidence=0,
            error_code="table_missing",
        )
    except asyncpg.exceptions.InsufficientPrivilegeError as e:
        logger.error(f"RLS permission denied for relationship evidence: {e}")
        return RelationshipEvidenceResponse(
            relationship_id=relationship_id,
            source_name=relationship["source_name"] if relationship else "Unknown",
            target_name=relationship["target_name"] if relationship else "Unknown",
            relationship_type=relationship["relationship_type"] if relationship else "RELATED_TO",
            evidence_chunks=[],
            total_evidence=0,
            error_code="permission_denied",
        )
    except Exception as e:
        logger.error(f"Failed to get relationship evidence: {e}")
        # Return empty response with error code instead of 500
        return RelationshipEvidenceResponse(
            relationship_id=relationship_id,
            source_name=relationship["source_name"] if relationship else "Unknown",
            target_name=relationship["target_name"] if relationship else "Unknown",
            relationship_type=relationship["relationship_type"] if relationship else "RELATED_TO",
            evidence_chunks=[],
            total_evidence=0,
            error_code="query_failed",
        )


# ============================================
# Graph Comparison API (Phase 5)
# ============================================

class ProjectComparisonNode(BaseModel):
    """Node with comparison metadata."""
    id: str
    name: str
    entity_type: str
    in_project_a: bool
    in_project_b: bool
    is_common: bool


class ProjectComparisonEdge(BaseModel):
    """Edge with comparison metadata."""
    id: str
    source: str
    target: str
    relationship_type: str
    in_project_a: bool
    in_project_b: bool
    is_common: bool


class GraphComparisonResponse(BaseModel):
    """Response for graph comparison."""
    project_a_id: str
    project_a_name: str
    project_b_id: str
    project_b_name: str
    # Statistics
    common_entities: int
    unique_to_a: int
    unique_to_b: int
    common_entity_names: List[str]
    # Comparison breakdown
    jaccard_similarity: float
    overlap_coefficient: float
    # Full data for visualization
    nodes: List[ProjectComparisonNode]
    edges: List[ProjectComparisonEdge]


@router.get("/compare/{project_a_id}/{project_b_id}", response_model=GraphComparisonResponse)
async def compare_graphs(
    project_a_id: UUID,
    project_b_id: UUID,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Compare two project knowledge graphs.

    Shows:
    - Common entities (intersection)
    - Unique to each project (difference)
    - Similarity metrics (Jaccard, overlap coefficient)

    Requires auth in production.
    """
    # Verify access to both projects
    await verify_project_access(database, project_a_id, current_user, "access")
    await verify_project_access(database, project_b_id, current_user, "access")

    try:
        # Get project names
        project_a = await database.fetchrow(
            "SELECT id, name FROM projects WHERE id = $1",
            str(project_a_id),
        )
        project_b = await database.fetchrow(
            "SELECT id, name FROM projects WHERE id = $1",
            str(project_b_id),
        )

        if not project_a or not project_b:
            raise HTTPException(status_code=404, detail="One or both projects not found")

        # Get entities from both projects
        entities_a = await database.fetch(
            """
            SELECT id, name, entity_type::text
            FROM entities
            WHERE project_id = $1
            AND entity_type IN ('Concept', 'Method', 'Finding', 'Problem', 'Dataset', 'Metric', 'Innovation', 'Limitation')
            """,
            str(project_a_id),
        )

        entities_b = await database.fetch(
            """
            SELECT id, name, entity_type::text
            FROM entities
            WHERE project_id = $1
            AND entity_type IN ('Concept', 'Method', 'Finding', 'Problem', 'Dataset', 'Metric', 'Innovation', 'Limitation')
            """,
            str(project_b_id),
        )

        # Build name-based lookup for comparison (case-insensitive)
        names_a = {row["name"].lower(): row for row in entities_a}
        names_b = {row["name"].lower(): row for row in entities_b}

        # Find common and unique entities
        common_names = set(names_a.keys()) & set(names_b.keys())
        unique_a_names = set(names_a.keys()) - common_names
        unique_b_names = set(names_b.keys()) - common_names

        # Calculate similarity metrics
        total_unique = len(set(names_a.keys()) | set(names_b.keys()))
        jaccard_similarity = len(common_names) / total_unique if total_unique > 0 else 0

        min_size = min(len(names_a), len(names_b))
        overlap_coefficient = len(common_names) / min_size if min_size > 0 else 0

        # Build comparison nodes
        nodes = []

        # Common entities
        for name in common_names:
            entity = names_a[name]
            nodes.append(ProjectComparisonNode(
                id=f"common_{name}",
                name=entity["name"],
                entity_type=entity["entity_type"],
                in_project_a=True,
                in_project_b=True,
                is_common=True,
            ))

        # Unique to A
        for name in unique_a_names:
            entity = names_a[name]
            nodes.append(ProjectComparisonNode(
                id=f"a_{str(entity['id'])}",
                name=entity["name"],
                entity_type=entity["entity_type"],
                in_project_a=True,
                in_project_b=False,
                is_common=False,
            ))

        # Unique to B
        for name in unique_b_names:
            entity = names_b[name]
            nodes.append(ProjectComparisonNode(
                id=f"b_{str(entity['id'])}",
                name=entity["name"],
                entity_type=entity["entity_type"],
                in_project_a=False,
                in_project_b=True,
                is_common=False,
            ))

        # Get edges from both projects
        edges_a = await database.fetch(
            """
            SELECT r.id, src.name as source_name, tgt.name as target_name, r.relationship_type::text
            FROM relationships r
            JOIN entities src ON r.source_id = src.id
            JOIN entities tgt ON r.target_id = tgt.id
            WHERE r.project_id = $1
            """,
            str(project_a_id),
        )

        edges_b = await database.fetch(
            """
            SELECT r.id, src.name as source_name, tgt.name as target_name, r.relationship_type::text
            FROM relationships r
            JOIN entities src ON r.source_id = src.id
            JOIN entities tgt ON r.target_id = tgt.id
            WHERE r.project_id = $1
            """,
            str(project_b_id),
        )

        # Build edge comparison (by source-target name pairs)
        edge_key_a = {(r["source_name"].lower(), r["target_name"].lower(), r["relationship_type"]): r for r in edges_a}
        edge_key_b = {(r["source_name"].lower(), r["target_name"].lower(), r["relationship_type"]): r for r in edges_b}

        common_edge_keys = set(edge_key_a.keys()) & set(edge_key_b.keys())

        edges = []
        seen_edges = set()

        # Common edges
        for key in common_edge_keys:
            edge = edge_key_a[key]
            edge_id = f"common_{key[0]}_{key[1]}"
            if edge_id not in seen_edges:
                edges.append(ProjectComparisonEdge(
                    id=edge_id,
                    source=f"common_{key[0]}",
                    target=f"common_{key[1]}",
                    relationship_type=edge["relationship_type"],
                    in_project_a=True,
                    in_project_b=True,
                    is_common=True,
                ))
                seen_edges.add(edge_id)

        # Get common entity names for display
        common_entity_names = sorted([names_a[n]["name"] for n in list(common_names)[:20]])

        return GraphComparisonResponse(
            project_a_id=str(project_a_id),
            project_a_name=project_a["name"],
            project_b_id=str(project_b_id),
            project_b_name=project_b["name"],
            common_entities=len(common_names),
            unique_to_a=len(unique_a_names),
            unique_to_b=len(unique_b_names),
            common_entity_names=common_entity_names,
            jaccard_similarity=round(jaccard_similarity, 4),
            overlap_coefficient=round(overlap_coefficient, 4),
            nodes=nodes,
            edges=edges,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare graphs: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare graphs")


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
