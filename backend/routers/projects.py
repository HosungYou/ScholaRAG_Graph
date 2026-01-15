"""
Projects API Router

Handles project CRUD operations with PostgreSQL persistence.
"""

import logging
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime

from database import db

logger = logging.getLogger(__name__)
router = APIRouter()


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
async def list_projects(database=Depends(get_db)):
    """List all projects from PostgreSQL."""
    try:
        rows = await database.fetch(
            """
            SELECT id, name, research_question, source_path, created_at, updated_at
            FROM projects
            ORDER BY created_at DESC
            """
        )

        projects = []
        for row in rows:
            # Get stats for each project
            stats = await _get_project_stats(database, str(row["id"]))
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
        # Fallback to empty list if DB not available
        return []


@router.post("/", response_model=ProjectResponse)
async def create_project(project: ProjectCreate, database=Depends(get_db)):
    """Create a new project in PostgreSQL."""
    project_id = uuid4()
    now = datetime.now()

    try:
        await database.execute(
            """
            INSERT INTO projects (id, name, research_question, source_path, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            project_id,
            project.name,
            project.research_question,
            project.source_path,
            now,
            now,
        )

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
async def get_project(project_id: UUID, database=Depends(get_db)):
    """Get project by ID from PostgreSQL."""
    try:
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
    database=Depends(get_db)
):
    """Update project details."""
    try:
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

        return await get_project(project_id, database)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update project")


@router.delete("/{project_id}")
async def delete_project(project_id: UUID, database=Depends(get_db)):
    """Delete project and all associated data."""
    try:
        # Check project exists
        row = await database.fetchrow(
            "SELECT id FROM projects WHERE id = $1",
            project_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

        # Delete in order: relationships, entities, project
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

        return {"status": "deleted", "project_id": str(project_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete project")


@router.get("/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats_endpoint(project_id: UUID, database=Depends(get_db)):
    """Get project statistics from PostgreSQL."""
    return await _get_project_stats(database, str(project_id))


async def _get_project_stats(database, project_id: str) -> ProjectStats:
    """Calculate actual stats from database."""
    try:
        # Count entities by type
        entity_counts = await database.fetch(
            """
            SELECT entity_type, COUNT(*) as count
            FROM entities
            WHERE project_id = $1
            GROUP BY entity_type
            """,
            project_id,
        )

        counts = {row["entity_type"]: row["count"] for row in entity_counts}

        # Count relationships
        rel_count = await database.fetchval(
            "SELECT COUNT(*) FROM relationships WHERE project_id = $1",
            project_id,
        )

        total_nodes = sum(counts.values())

        return ProjectStats(
            total_nodes=total_nodes,
            total_edges=rel_count or 0,
            total_papers=counts.get("Paper", 0),
            total_authors=counts.get("Author", 0),
            total_concepts=counts.get("Concept", 0),
            total_methods=counts.get("Method", 0),
            total_findings=counts.get("Finding", 0),
        )
    except Exception as e:
        logger.warning(f"Failed to get stats for project {project_id}: {e}")
        return ProjectStats()
