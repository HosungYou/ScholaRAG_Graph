"""
Projects API Router

Handles project CRUD operations with PostgreSQL persistence.

Security:
- All endpoints require authentication in production (configurable via REQUIRE_AUTH)
- Project ownership is enforced via owner_id field
- Team members can access shared projects via team_projects junction table
"""

import logging
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime

from database import db
from auth.dependencies import require_auth_if_configured
from auth.models import User

logger = logging.getLogger(__name__)
router = APIRouter()


async def check_project_access(database, project_id: UUID, user_id: str) -> bool:
    """
    Check if a user has access to a project.
    Access is granted if:
    1. User is the owner of the project
    2. User is a collaborator on the project
    3. User is a member of a team that has access to the project
    4. Project is public

    Returns True if access is allowed, False otherwise.
    """
    # Check ownership, collaboration, team membership, or public visibility
    row = await database.fetchrow(
        """
        SELECT EXISTS(
            SELECT 1 FROM projects p
            WHERE p.id = $1 AND (
                p.owner_id = $2
                OR p.visibility = 'public'
                OR EXISTS (
                    SELECT 1 FROM project_collaborators pc
                    WHERE pc.project_id = p.id AND pc.user_id = $2
                )
                OR EXISTS (
                    SELECT 1 FROM team_projects tp
                    JOIN team_members tm ON tp.team_id = tm.team_id
                    WHERE tp.project_id = p.id AND tm.user_id = $2
                )
            )
        ) as has_access
        """,
        project_id,
        user_id,
    )
    return row["has_access"] if row else False


async def check_project_ownership(database, project_id: UUID, user_id: str) -> bool:
    """
    Check if a user is the owner of a project.
    Only owners can delete or modify certain project settings.
    """
    row = await database.fetchrow(
        "SELECT owner_id FROM projects WHERE id = $1",
        project_id,
    )
    return row and str(row["owner_id"]) == user_id


# Pydantic Models
class ProjectCreate(BaseModel):
    name: str
    research_question: Optional[str] = None
    source_path: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    research_question: Optional[str] = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    research_question: Optional[str]
    source_path: Optional[str]
    created_at: datetime
    updated_at: datetime
    stats: Optional[dict] = None


class ProjectStats(BaseModel):
    total_nodes: int = 0
    total_edges: int = 0
    total_papers: int = 0
    total_authors: int = 0
    total_concepts: int = 0
    total_methods: int = 0
    total_findings: int = 0


async def get_db():
    """Dependency to get database connection."""
    if not db.is_connected:
        await db.connect()
    return db


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    List projects accessible to the current user.

    Returns projects where the user is:
    - The owner
    - A collaborator
    - A member of a team with access to the project
    - Or the project is public

    Requires authentication in production.
    """
    try:
        # If no auth is configured (development mode), return all projects
        if current_user is None:
            rows = await database.fetch(
                """
                SELECT id, name, research_question, source_path, created_at, updated_at
                FROM projects
                ORDER BY created_at DESC
                """
            )
        else:
            # Filter by user access: owned, collaborated, team-shared, or public
            rows = await database.fetch(
                """
                SELECT DISTINCT p.id, p.name, p.research_question, p.source_path,
                       p.created_at, p.updated_at
                FROM projects p
                LEFT JOIN project_collaborators pc ON p.id = pc.project_id
                LEFT JOIN team_projects tp ON p.id = tp.project_id
                LEFT JOIN team_members tm ON tp.team_id = tm.team_id
                WHERE p.owner_id = $1
                   OR pc.user_id = $1
                   OR tm.user_id = $1
                   OR p.visibility = 'public'
                ORDER BY p.created_at DESC
                """,
                current_user.id,
            )

        # Get stats for all projects in a single batch query (prevents N+1)
        project_ids = [str(row["id"]) for row in rows]
        stats_batch = await _get_project_stats_batch(database, project_ids)

        projects = []
        for row in rows:
            project_id = str(row["id"])
            stats = stats_batch.get(project_id, ProjectStats())
            projects.append(
                ProjectResponse(
                    id=row["id"],
                    name=row["name"],
                    research_question=row["research_question"],
                    source_path=row["source_path"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    stats=stats.model_dump(),
                )
            )

        return projects
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please try again later."
        )


@router.post("/", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Create a new project in PostgreSQL.

    The current authenticated user becomes the owner of the project.
    Requires authentication in production.
    """
    project_id = uuid4()
    now = datetime.now()

    # Set owner_id from authenticated user (None if auth not configured)
    owner_id = current_user.id if current_user else None

    try:
        await database.execute(
            """
            INSERT INTO projects (id, name, research_question, source_path, owner_id, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            project_id,
            project.name,
            project.research_question,
            project.source_path,
            owner_id,
            now,
            now,
        )

        logger.info(f"Created project {project_id} for owner {owner_id}")

        return ProjectResponse(
            id=project_id,
            name=project.name,
            research_question=project.research_question,
            source_path=project.source_path,
            created_at=now,
            updated_at=now,
            stats=ProjectStats().model_dump(),
        )
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail="Failed to create project")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Get project by ID from PostgreSQL.

    Access control:
    - Owner can always access
    - Collaborators can access
    - Team members can access if team has project access
    - Anyone can access public projects

    Requires authentication in production.
    """
    try:
        # Verify access if auth is configured
        if current_user is not None:
            has_access = await check_project_access(database, project_id, current_user.id)
            if not has_access:
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to access this project"
                )

        row = await database.fetchrow(
            """
            SELECT id, name, research_question, source_path, created_at, updated_at
            FROM projects
            WHERE id = $1
            """,
            project_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

        stats = await _get_project_stats(database, str(project_id))

        return ProjectResponse(
            id=row["id"],
            name=row["name"],
            research_question=row["research_question"],
            source_path=row["source_path"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            stats=stats.model_dump(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project")


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    update: ProjectUpdate,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Update project details.

    Access control:
    - Only the owner can update a project
    - Team admins with 'admin' role can also update

    Requires authentication in production.
    """
    try:
        # Verify ownership if auth is configured
        if current_user is not None:
            # Check if user is owner or has admin role on the project
            is_owner = await check_project_ownership(database, project_id, current_user.id)

            # Also check if user is an admin collaborator
            is_admin = await database.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM project_collaborators
                    WHERE project_id = $1 AND user_id = $2 AND role IN ('admin', 'owner')
                )
                """,
                project_id,
                current_user.id,
            )

            if not is_owner and not is_admin:
                raise HTTPException(
                    status_code=403,
                    detail="Only the project owner or admin can update this project"
                )

        # Build dynamic update query
        updates = []
        values = []
        param_idx = 1

        if update.name is not None:
            updates.append(f"name = ${param_idx}")
            values.append(update.name)
            param_idx += 1

        if update.research_question is not None:
            updates.append(f"research_question = ${param_idx}")
            values.append(update.research_question)
            param_idx += 1

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates.append(f"updated_at = ${param_idx}")
        values.append(datetime.now())
        param_idx += 1

        values.append(project_id)

        await database.execute(
            f"""
            UPDATE projects
            SET {', '.join(updates)}
            WHERE id = ${param_idx}
            """,
            *values,
        )

        return await get_project(project_id, database, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update project")


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Delete project and all associated data.

    Access control:
    - Only the project owner can delete a project
    - This action is irreversible

    Requires authentication in production.
    """
    try:
        # Check project exists
        row = await database.fetchrow(
            "SELECT id, owner_id FROM projects WHERE id = $1",
            project_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

        # Verify ownership if auth is configured - only owner can delete
        if current_user is not None:
            is_owner = await check_project_ownership(database, project_id, current_user.id)
            if not is_owner:
                raise HTTPException(
                    status_code=403,
                    detail="Only the project owner can delete this project"
                )

        # Delete in order: team_projects, project_collaborators, relationships, entities, project
        await database.execute(
            "DELETE FROM team_projects WHERE project_id = $1",
            project_id,
        )
        await database.execute(
            "DELETE FROM project_collaborators WHERE project_id = $1",
            project_id,
        )
        await database.execute(
            "DELETE FROM relationships WHERE project_id = $1",
            project_id,
        )
        await database.execute(
            "DELETE FROM entities WHERE project_id = $1",
            project_id,
        )
        await database.execute(
            "DELETE FROM projects WHERE id = $1",
            project_id,
        )

        logger.info(f"Deleted project {project_id} by user {current_user.id if current_user else 'anonymous'}")

        return {"status": "deleted", "project_id": str(project_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete project")


@router.get("/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats_endpoint(
    project_id: UUID,
    database=Depends(get_db),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Get project statistics from PostgreSQL.

    Access control:
    - Same as get_project (owner, collaborator, team member, or public)

    Requires authentication in production.
    """
    # Verify access if auth is configured
    if current_user is not None:
        has_access = await check_project_access(database, project_id, current_user.id)
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this project"
            )

    return await _get_project_stats(database, str(project_id))


async def _get_project_stats(database, project_id: str) -> ProjectStats:
    """Calculate actual stats from database for a single project."""
    stats_batch = await _get_project_stats_batch(database, [project_id])
    return stats_batch.get(project_id, ProjectStats())


async def _get_project_stats_batch(database, project_ids: List[str]) -> dict[str, ProjectStats]:
    """
    Calculate stats for multiple projects in a single batch query.

    Prevents N+1 queries when listing projects.

    Returns:
        Dict mapping project_id to ProjectStats
    """
    if not project_ids:
        return {}

    try:
        # Single query to get entity counts for all projects
        entity_counts = await database.fetch(
            """
            SELECT project_id::text, entity_type, COUNT(*) as count
            FROM entities
            WHERE project_id = ANY($1::uuid[])
            GROUP BY project_id, entity_type
            """,
            project_ids,
        )

        # Single query to get relationship counts for all projects
        rel_counts = await database.fetch(
            """
            SELECT project_id::text, COUNT(*) as count
            FROM relationships
            WHERE project_id = ANY($1::uuid[])
            GROUP BY project_id
            """,
            project_ids,
        )

        # BUG-029 FIX: Query paper_metadata table for paper counts
        # Papers are stored in paper_metadata (ADR-001), not in entities table
        paper_counts = await database.fetch(
            """
            SELECT project_id::text, COUNT(*) as count
            FROM paper_metadata
            WHERE project_id = ANY($1::uuid[])
            GROUP BY project_id
            """,
            project_ids,
        )

        # Build paper lookup: {project_id: count}
        paper_lookup = {row["project_id"]: row["count"] for row in paper_counts}

        # Build counts lookup: {project_id: {entity_type: count}}
        entity_lookup: dict[str, dict[str, int]] = {pid: {} for pid in project_ids}
        for row in entity_counts:
            pid = row["project_id"]
            entity_lookup[pid][row["entity_type"]] = row["count"]

        # Build relationship lookup: {project_id: count}
        rel_lookup = {row["project_id"]: row["count"] for row in rel_counts}

        # Build result
        result = {}
        for pid in project_ids:
            counts = entity_lookup.get(pid, {})
            total_nodes = sum(counts.values())

            result[pid] = ProjectStats(
                total_nodes=total_nodes,
                total_edges=rel_lookup.get(pid, 0),
                # BUG-029 FIX: Use paper_metadata table count (ADR-001: Papers are metadata, not entities)
                total_papers=paper_lookup.get(pid, 0),
                total_authors=counts.get("Author", 0),
                total_concepts=counts.get("Concept", 0),
                total_methods=counts.get("Method", 0),
                total_findings=counts.get("Finding", 0),
            )

        return result

    except Exception as e:
        logger.warning(f"Failed to get batch stats for projects: {e}")
        # Return empty stats for all projects
        return {pid: ProjectStats() for pid in project_ids}
