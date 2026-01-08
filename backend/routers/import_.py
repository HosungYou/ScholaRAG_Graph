"""
Import API Router

Handles data import from ScholaRAG folders, PDFs, and CSVs.
"""

import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

from database import db
from graph.graph_store import GraphStore
from importers.scholarag_importer import ScholarAGImporter

logger = logging.getLogger(__name__)

router = APIRouter()


# Enums
class ImportStatus(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    EXTRACTING = "extracting"
    PROCESSING = "processing"
    BUILDING_GRAPH = "building_graph"
    COMPLETED = "completed"
    FAILED = "failed"


# Pydantic Models
class ScholaRAGImportRequest(BaseModel):
    folder_path: str
    project_name: Optional[str] = None
    extract_entities: bool = True  # Use LLM to extract Concept, Method, Finding


class ImportJobResponse(BaseModel):
    job_id: str
    status: ImportStatus
    progress: float  # 0.0 to 1.0
    message: str
    project_id: Optional[UUID] = None
    stats: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class ImportValidationResponse(BaseModel):
    valid: bool
    folder_path: str
    config_found: bool
    scholarag_metadata_found: bool
    papers_csv_found: bool
    papers_count: int
    pdfs_count: int
    chroma_db_found: bool
    errors: list = []
    warnings: list = []


# In-memory storage
_import_jobs: dict = {}


@router.post("/scholarag/validate", response_model=ImportValidationResponse)
async def validate_scholarag_folder(request: ScholaRAGImportRequest):
    """
    Validate a ScholaRAG project folder before import.

    Checks:
    - config.yaml exists
    - .scholarag metadata exists
    - data/02_screening/relevant_papers.csv exists
    - data/03_pdfs/ contains PDFs
    - data/04_rag/chroma_db/ exists (optional)
    """
    from pathlib import Path

    folder = Path(request.folder_path)

    validation = ImportValidationResponse(
        valid=True,
        folder_path=request.folder_path,
        config_found=False,
        scholarag_metadata_found=False,
        papers_csv_found=False,
        papers_count=0,
        pdfs_count=0,
        chroma_db_found=False,
        errors=[],
        warnings=[],
    )

    # Check folder exists
    if not folder.exists():
        validation.valid = False
        validation.errors.append(f"Folder not found: {request.folder_path}")
        return validation

    # Check config.yaml
    config_path = folder / "config.yaml"
    validation.config_found = config_path.exists()
    if not validation.config_found:
        validation.errors.append("config.yaml not found")
        validation.valid = False

    # Check .scholarag
    metadata_path = folder / ".scholarag"
    validation.scholarag_metadata_found = metadata_path.exists()
    if not validation.scholarag_metadata_found:
        validation.warnings.append(".scholarag metadata not found (optional)")

    # Check papers CSV
    papers_csv = folder / "data" / "02_screening" / "relevant_papers.csv"
    validation.papers_csv_found = papers_csv.exists()
    if validation.papers_csv_found:
        # Count rows (excluding header)
        try:
            with open(papers_csv, "r", encoding="utf-8") as f:
                validation.papers_count = sum(1 for _ in f) - 1
        except Exception as e:
            validation.warnings.append(f"Could not count papers: {e}")
    else:
        # Try alternative path
        alt_csv = folder / "data" / "02_screening" / "all_screened_papers.csv"
        if alt_csv.exists():
            validation.papers_csv_found = True
            validation.warnings.append("Using all_screened_papers.csv instead")

    if not validation.papers_csv_found:
        validation.errors.append("No papers CSV found in data/02_screening/")
        validation.valid = False

    # Check PDFs
    pdfs_dir = folder / "data" / "03_pdfs"
    if pdfs_dir.exists():
        validation.pdfs_count = len(list(pdfs_dir.rglob("*.pdf")))
    else:
        validation.warnings.append("No PDFs directory found")

    # Check ChromaDB
    chroma_dir = folder / "data" / "04_rag" / "chroma_db"
    validation.chroma_db_found = chroma_dir.exists() and any(chroma_dir.iterdir()) if chroma_dir.exists() else False

    return validation


@router.post("/scholarag", response_model=ImportJobResponse)
async def import_scholarag_folder(
    request: ScholaRAGImportRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start importing a ScholaRAG project folder.

    Process:
    1. Validate folder structure
    2. Parse config.yaml → Create Project
    3. Parse relevant_papers.csv → Create Paper entities
    4. Extract Authors from papers
    5. (If extract_entities=True) Use LLM to extract Concept, Method, Finding
    6. Build relationships (AUTHORED_BY, DISCUSSES_CONCEPT, etc.)
    7. Store in PostgreSQL + pgvector
    """
    from uuid import uuid4

    # Create import job
    job_id = str(uuid4())
    now = datetime.now()

    job = ImportJobResponse(
        job_id=job_id,
        status=ImportStatus.PENDING,
        progress=0.0,
        message="Import job created",
        project_id=None,
        stats=None,
        created_at=now,
        updated_at=now,
    )

    _import_jobs[job_id] = job.model_dump()

    # Start background import task
    background_tasks.add_task(
        _run_scholarag_import,
        job_id=job_id,
        folder_path=request.folder_path,
        project_name=request.project_name,
        extract_entities=request.extract_entities,
    )

    return job


async def _run_scholarag_import(
    job_id: str,
    folder_path: str,
    project_name: Optional[str],
    extract_entities: bool,
):
    """Background task to run ScholaRAG import."""
    logger.info(f"[Import {job_id}] Starting import from: {folder_path}")

    def progress_callback(progress):
        """Update job status from importer progress."""
        status_map = {
            "validating": ImportStatus.VALIDATING,
            "extracting": ImportStatus.EXTRACTING,
            "processing": ImportStatus.PROCESSING,
            "building_graph": ImportStatus.BUILDING_GRAPH,
            "completed": ImportStatus.COMPLETED,
            "failed": ImportStatus.FAILED,
        }
        _import_jobs[job_id]["status"] = status_map.get(progress.status, ImportStatus.PROCESSING)
        _import_jobs[job_id]["progress"] = progress.progress
        _import_jobs[job_id]["message"] = progress.message
        _import_jobs[job_id]["updated_at"] = datetime.now()
        logger.info(f"[Import {job_id}] {progress.status}: {progress.progress:.1%} - {progress.message}")

    try:
        # Create importer with database connection and GraphStore
        graph_store = GraphStore(db=db)
        importer = ScholarAGImporter(
            db_connection=db,
            graph_store=graph_store,
            progress_callback=progress_callback,
        )

        # Run the import
        result = await importer.import_folder(
            folder_path=folder_path,
            project_name=project_name,
            extract_entities=extract_entities,
        )

        if result["success"]:
            # Update job with results
            _import_jobs[job_id]["status"] = ImportStatus.COMPLETED
            _import_jobs[job_id]["progress"] = 1.0
            _import_jobs[job_id]["message"] = "Import completed successfully!"
            _import_jobs[job_id]["project_id"] = result.get("project_id")
            _import_jobs[job_id]["stats"] = result.get("stats", {})
            _import_jobs[job_id]["updated_at"] = datetime.now()

            logger.info(f"[Import {job_id}] Completed successfully: {result.get('stats', {})}")
        else:
            # Import failed
            _import_jobs[job_id]["status"] = ImportStatus.FAILED
            _import_jobs[job_id]["message"] = f"Import failed: {result.get('error', 'Unknown error')}"
            _import_jobs[job_id]["updated_at"] = datetime.now()
            _import_jobs[job_id]["stats"] = {
                "papers_imported": 0,
                "authors_extracted": 0,
                "concepts_extracted": 0,
                "relationships_created": 0,
            }

            logger.error(f"[Import {job_id}] Failed: {result.get('error')}")

    except Exception as e:
        logger.exception(f"[Import {job_id}] Exception during import: {e}")
        _import_jobs[job_id]["status"] = ImportStatus.FAILED
        _import_jobs[job_id]["message"] = f"Import failed: {str(e)}"
        _import_jobs[job_id]["updated_at"] = datetime.now()
        _import_jobs[job_id]["stats"] = {
            "papers_imported": 0,
            "authors_extracted": 0,
            "concepts_extracted": 0,
            "relationships_created": 0,
        }


@router.get("/status/{job_id}", response_model=ImportJobResponse)
async def get_import_status(job_id: str):
    """Get the status of an import job."""
    job = _import_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    return ImportJobResponse(**job)


@router.post("/pdf")
async def import_pdf(
    project_id: UUID,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    """Import a single PDF file."""
    from uuid import uuid4

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    job_id = str(uuid4())

    # TODO: Implement PDF import
    return {
        "job_id": job_id,
        "status": "pending",
        "filename": file.filename,
        "message": "PDF import not yet implemented",
    }


@router.post("/csv")
async def import_csv(
    project_id: UUID,
    file: UploadFile = File(...),
):
    """Import papers from a CSV file."""
    from uuid import uuid4

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    job_id = str(uuid4())

    # TODO: Implement CSV import
    return {
        "job_id": job_id,
        "status": "pending",
        "filename": file.filename,
        "message": "CSV import not yet implemented",
    }
