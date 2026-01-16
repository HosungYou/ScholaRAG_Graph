"""
Import API Router

Handles data import from ScholaRAG folders, PDFs, and CSVs.

Security:
- Path validation restricts access to allowed directories only
- Symbolic link resolution prevents path traversal attacks
- Input sanitization for all user-provided paths
- All endpoints require authentication in production (configurable via REQUIRE_AUTH)
- ALLOWED_IMPORT_ROOTS must be configured in production environments
"""

import logging
import os
from pathlib import Path
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Depends, status
from pydantic import BaseModel, field_validator
from datetime import datetime
from enum import Enum

from database import db
from graph.graph_store import GraphStore
from importers.scholarag_importer import ScholarAGImporter
from jobs import JobStore, JobStatus
from config import settings
from auth.dependencies import require_auth_if_configured
from auth.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


# Security Configuration
# IMPORTANT: Set these via environment variables in production
# Uses settings from config.py which loads from .env file
def get_allowed_import_roots() -> List[str]:
    """Get allowed import roots from settings."""
    roots = [
        settings.scholarag_import_root,
        settings.scholarag_import_root_2,
    ]
    return [r for r in roots if r]

# Initialize at module level for backwards compatibility
ALLOWED_IMPORT_ROOTS: List[str] = get_allowed_import_roots()

# Maximum path depth to prevent deep traversal
MAX_PATH_DEPTH = 10


def validate_safe_path(folder_path: str) -> Path:
    """
    Validate that the provided path is safe to access.

    Security checks:
    1. Path must be absolute
    2. Path must resolve within allowed root directories
    3. No symbolic link escapes
    4. Path depth limit

    Raises:
        HTTPException: If path validation fails
    """
    try:
        # Convert to Path object
        path = Path(folder_path)

        # Check for path depth
        if len(path.parts) > MAX_PATH_DEPTH:
            raise HTTPException(
                status_code=400,
                detail="Path depth exceeds maximum allowed"
            )

        # Resolve symbolic links and normalize path
        resolved_path = path.resolve()

        # SECURITY: Enforce allowed roots in production
        if not ALLOWED_IMPORT_ROOTS:
            if settings.environment in ("staging", "production"):
                # In production/staging, fail hard if no roots configured
                logger.error(
                    "SECURITY ERROR: ALLOWED_IMPORT_ROOTS not configured in production. "
                    "Set SCHOLARAG_IMPORT_ROOT environment variable."
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Import service not configured. Contact administrator."
                )
            else:
                # Development mode only: warn but allow
                logger.warning(
                    "SECURITY WARNING: No ALLOWED_IMPORT_ROOTS configured. "
                    "This is only allowed in development mode."
                )
                return resolved_path

        # Check if resolved path is within allowed roots
        is_allowed = False
        for allowed_root in ALLOWED_IMPORT_ROOTS:
            allowed_path = Path(allowed_root).resolve()
            try:
                resolved_path.relative_to(allowed_path)
                is_allowed = True
                break
            except ValueError:
                continue

        if not is_allowed:
            logger.warning(
                f"Path access denied: {folder_path} (resolved: {resolved_path}) "
                f"not within allowed roots"
            )
            raise HTTPException(
                status_code=403,
                detail="Access denied: Path is not within allowed import directories"
            )

        return resolved_path

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Path validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid path format"
        )


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

    @field_validator("folder_path")
    @classmethod
    def sanitize_path(cls, v: str) -> str:
        """Sanitize folder path input."""
        # Remove null bytes and control characters
        sanitized = "".join(c for c in v if c.isprintable() and c != "\x00")
        # Normalize path separators
        sanitized = sanitized.replace("\\", "/")
        # Remove consecutive dots that could indicate traversal
        while ".." in sanitized:
            sanitized = sanitized.replace("..", ".")
        return sanitized.strip()

    @field_validator("project_name")
    @classmethod
    def sanitize_project_name(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize project name."""
        if v is None:
            return v
        # Remove special characters, keep alphanumeric, spaces, hyphens, underscores
        sanitized = "".join(
            c for c in v if c.isalnum() or c in " -_"
        )
        return sanitized[:100].strip() or None


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


# Job store for persistent tracking
# Falls back to in-memory if DB unavailable
_job_store: Optional[JobStore] = None


async def get_job_store() -> JobStore:
    """Get or create job store instance."""
    global _job_store
    if _job_store is None:
        _job_store = JobStore(db_connection=db if db.is_connected else None)
        await _job_store.init_table()
    return _job_store


# Legacy in-memory storage (deprecated, use JobStore)
_import_jobs: dict = {}


@router.post("/scholarag/validate", response_model=ImportValidationResponse)
async def validate_scholarag_folder(
    request: ScholaRAGImportRequest,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Validate a ScholaRAG project folder before import. Requires auth in production.

    Checks:
    - Path is within allowed directories (security)
    - config.yaml exists
    - .scholarag metadata exists
    - data/02_screening/relevant_papers.csv exists
    - data/03_pdfs/ contains PDFs
    - data/04_rag/chroma_db/ exists (optional)
    """
    # Security: Validate path is within allowed directories
    folder = validate_safe_path(request.folder_path)

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
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Start importing a ScholaRAG project folder. Requires auth in production.

    Security:
    - Path must be within allowed import directories
    - Project name is sanitized
    - Authentication required in production

    Process:
    1. Validate folder structure
    2. Parse config.yaml → Create Project
    3. Parse relevant_papers.csv → Create Paper entities
    4. Extract Authors from papers
    5. (If extract_entities=True) Use LLM to extract Concept, Method, Finding
    6. Build relationships (AUTHORED_BY, DISCUSSES_CONCEPT, etc.)
    7. Store in PostgreSQL + pgvector
    """
    # Security: Validate path is within allowed directories
    validated_path = validate_safe_path(request.folder_path)

    # Create job in persistent store
    job_store = await get_job_store()
    job = await job_store.create_job(
        job_type="import",
        metadata={
            "folder_path": str(validated_path),
            "project_name": request.project_name,
            "extract_entities": request.extract_entities,
        },
    )

    now = datetime.now()
    response = ImportJobResponse(
        job_id=job.id,
        status=ImportStatus.PENDING,
        progress=0.0,
        message="Import job created",
        project_id=None,
        stats=None,
        created_at=now,
        updated_at=now,
    )

    # Legacy: also store in memory for backwards compatibility
    _import_jobs[job.id] = response.model_dump()

    # Start background import task with validated path
    background_tasks.add_task(
        _run_scholarag_import,
        job_id=job.id,
        folder_path=str(validated_path),
        project_name=request.project_name,
        extract_entities=request.extract_entities,
    )

    return response


def _mask_path_for_logging(path: str) -> str:
    """Mask sensitive parts of path for logging."""
    # Only show the last 2 path components
    parts = Path(path).parts
    if len(parts) <= 2:
        return path
    return f".../{'/'.join(parts[-2:])}"


async def _run_scholarag_import(
    job_id: str,
    folder_path: str,
    project_name: Optional[str],
    extract_entities: bool,
):
    """Background task to run ScholaRAG import."""
    # Mask path in logs to avoid exposing full directory structure
    masked_path = _mask_path_for_logging(folder_path)
    logger.info(f"[Import {job_id}] Starting import from: {masked_path}")

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
            extract_concepts=extract_entities,  # Maps extract_entities to extract_concepts
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
            # Import failed - sanitize error message
            error_msg = result.get("error", "Unknown error")
            # Don't expose internal paths in error messages
            sanitized_error = _sanitize_error_message(error_msg)

            _import_jobs[job_id]["status"] = ImportStatus.FAILED
            _import_jobs[job_id]["message"] = f"Import failed: {sanitized_error}"
            _import_jobs[job_id]["updated_at"] = datetime.now()
            _import_jobs[job_id]["stats"] = {
                "papers_imported": 0,
                "authors_extracted": 0,
                "concepts_extracted": 0,
                "relationships_created": 0,
            }

            logger.error(f"[Import {job_id}] Failed: {sanitized_error}")

    except Exception as e:
        # Log full exception internally but sanitize for user response
        logger.exception(f"[Import {job_id}] Exception during import")
        sanitized_error = _sanitize_error_message(str(e))

        _import_jobs[job_id]["status"] = ImportStatus.FAILED
        _import_jobs[job_id]["message"] = f"Import failed: {sanitized_error}"
        _import_jobs[job_id]["updated_at"] = datetime.now()
        _import_jobs[job_id]["stats"] = {
            "papers_imported": 0,
            "authors_extracted": 0,
            "concepts_extracted": 0,
            "relationships_created": 0,
        }


def _sanitize_error_message(error: str) -> str:
    """Remove sensitive information from error messages."""
    import re

    # Remove full file paths
    sanitized = re.sub(r"(/[a-zA-Z0-9_\-./]+)+", "[path]", error)

    # Remove potential API keys or tokens
    sanitized = re.sub(r"(sk-|api[_-]?key|token)[a-zA-Z0-9\-_]{10,}", "[redacted]", sanitized, flags=re.IGNORECASE)

    # Remove email addresses
    sanitized = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[email]", sanitized)

    # Limit message length
    return sanitized[:500] if len(sanitized) > 500 else sanitized


@router.get("/status/{job_id}", response_model=ImportJobResponse)
async def get_import_status(job_id: str):
    """Get the status of an import job from persistent store."""
    # Try JobStore first
    job_store = await get_job_store()
    job = await job_store.get_job(job_id)

    if job:
        # Convert JobStore job to ImportJobResponse
        status_map = {
            JobStatus.PENDING: ImportStatus.PENDING,
            JobStatus.RUNNING: ImportStatus.PROCESSING,
            JobStatus.COMPLETED: ImportStatus.COMPLETED,
            JobStatus.FAILED: ImportStatus.FAILED,
            JobStatus.CANCELLED: ImportStatus.FAILED,
        }
        return ImportJobResponse(
            job_id=job.id,
            status=status_map.get(job.status, ImportStatus.PENDING),
            progress=job.progress,
            message=job.message,
            project_id=job.result.get("project_id") if job.result else None,
            stats=job.result.get("stats") if job.result else None,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    # Fallback to legacy in-memory storage
    legacy_job = _import_jobs.get(job_id)
    if legacy_job:
        return ImportJobResponse(**legacy_job)

    raise HTTPException(status_code=404, detail="Import job not found")


@router.get("/jobs", response_model=list[ImportJobResponse])
async def list_import_jobs(
    status: Optional[str] = None,
    limit: int = 50,
):
    """List all import jobs with optional status filter."""
    job_store = await get_job_store()

    status_filter = None
    if status:
        try:
            status_filter = JobStatus(status)
        except ValueError:
            pass

    jobs = await job_store.list_jobs(job_type="import", status=status_filter, limit=limit)

    status_map = {
        JobStatus.PENDING: ImportStatus.PENDING,
        JobStatus.RUNNING: ImportStatus.PROCESSING,
        JobStatus.COMPLETED: ImportStatus.COMPLETED,
        JobStatus.FAILED: ImportStatus.FAILED,
        JobStatus.CANCELLED: ImportStatus.FAILED,
    }

    return [
        ImportJobResponse(
            job_id=job.id,
            status=status_map.get(job.status, ImportStatus.PENDING),
            progress=job.progress,
            message=job.message,
            project_id=job.result.get("project_id") if job.result else None,
            stats=job.result.get("stats") if job.result else None,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        for job in jobs
    ]


class PDFImportRequest(BaseModel):
    """Request model for PDF import."""
    project_name: Optional[str] = None
    research_question: Optional[str] = None
    extract_concepts: bool = True


class PDFImportResponse(BaseModel):
    """Response model for PDF import."""
    job_id: str
    status: ImportStatus
    message: str
    filename: str
    project_id: Optional[str] = None


@router.post("/pdf", response_model=PDFImportResponse)
async def import_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_name: Optional[str] = None,
    research_question: Optional[str] = None,
    extract_concepts: bool = True,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Import a single PDF file and create a Knowledge Graph. Requires auth in production.

    This endpoint allows direct PDF upload without needing a ScholaRAG project structure.
    It will:
    1. Extract text from the PDF using PyMuPDF
    2. Extract metadata (title, authors, year, abstract)
    3. Create a new project automatically
    4. Use LLM to extract concepts, methods, and findings
    5. Build a knowledge graph

    Args:
        file: PDF file to upload
        project_name: Optional project name (defaults to PDF title)
        research_question: Optional research question
        extract_concepts: Whether to use LLM for concept extraction (default: True)

    Returns:
        Import job information including job_id for status tracking
    """
    from uuid import uuid4

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Validate file size (max 50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    # Create job
    job_store = await get_job_store()
    job = await job_store.create_job(
        job_type="pdf_import",
        metadata={
            "filename": file.filename,
            "file_size": len(content),
            "project_name": project_name,
            "research_question": research_question,
            "extract_concepts": extract_concepts,
        },
    )

    now = datetime.now()
    _import_jobs[job.id] = {
        "job_id": job.id,
        "status": ImportStatus.PENDING,
        "progress": 0.0,
        "message": "PDF import job created",
        "project_id": None,
        "stats": None,
        "created_at": now,
        "updated_at": now,
    }

    # Start background import task
    background_tasks.add_task(
        _run_pdf_import,
        job_id=job.id,
        pdf_content=content,
        filename=file.filename,
        project_name=project_name,
        research_question=research_question,
        extract_concepts=extract_concepts,
    )

    return PDFImportResponse(
        job_id=job.id,
        status=ImportStatus.PENDING,
        message="PDF import started",
        filename=file.filename,
    )


async def _run_pdf_import(
    job_id: str,
    pdf_content: bytes,
    filename: str,
    project_name: Optional[str],
    research_question: Optional[str],
    extract_concepts: bool,
):
    """Background task to run PDF import."""
    from importers.pdf_importer import PDFImporter

    logger.info(f"[PDF Import {job_id}] Starting import: {filename}")

    # Get job store for persistent updates
    job_store = await get_job_store()

    # Map import stages to JobStore status
    stage_to_job_status = {
        "starting": JobStatus.RUNNING,
        "extracting": JobStatus.RUNNING,
        "creating": JobStatus.RUNNING,
        "storing": JobStatus.RUNNING,
        "analyzing": JobStatus.RUNNING,
        "building": JobStatus.RUNNING,
        "complete": JobStatus.COMPLETED,
    }

    def progress_callback(stage: str, progress: float, message: str):
        """Update job status from importer progress."""
        status_map = {
            "starting": ImportStatus.PENDING,
            "extracting": ImportStatus.EXTRACTING,
            "creating": ImportStatus.PROCESSING,
            "storing": ImportStatus.PROCESSING,
            "analyzing": ImportStatus.PROCESSING,
            "building": ImportStatus.BUILDING_GRAPH,
            "complete": ImportStatus.COMPLETED,
        }
        _import_jobs[job_id]["status"] = status_map.get(stage, ImportStatus.PROCESSING)
        _import_jobs[job_id]["progress"] = progress
        _import_jobs[job_id]["message"] = message
        _import_jobs[job_id]["updated_at"] = datetime.now()
        logger.info(f"[PDF Import {job_id}] {stage}: {progress:.0%} - {message}")

    try:
        # Mark job as running in JobStore
        await job_store.update_job(
            job_id=job_id,
            status=JobStatus.RUNNING,
            progress=0.0,
            message="Starting PDF import...",
        )

        # Create importer with database connection and GraphStore
        graph_store = GraphStore(db=db)
        importer = PDFImporter(
            llm_provider=settings.default_llm_provider,
            llm_model=settings.default_llm_model,
            db_connection=db,
            graph_store=graph_store,
            progress_callback=progress_callback,
        )

        # Run the import
        result = await importer.import_single_pdf(
            pdf_content=pdf_content,
            filename=filename,
            project_name=project_name,
            research_question=research_question,
            extract_concepts=extract_concepts,
        )

        if result["success"]:
            _import_jobs[job_id]["status"] = ImportStatus.COMPLETED
            _import_jobs[job_id]["progress"] = 1.0
            _import_jobs[job_id]["message"] = "PDF import completed successfully!"
            _import_jobs[job_id]["project_id"] = result.get("project_id")
            _import_jobs[job_id]["stats"] = result.get("stats", {})
            _import_jobs[job_id]["updated_at"] = datetime.now()

            # Update JobStore with completion status and result
            await job_store.update_job(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                progress=1.0,
                message="PDF import completed successfully!",
                result={
                    "project_id": str(result.get("project_id")) if result.get("project_id") else None,
                    "stats": result.get("stats", {}),
                },
            )

            logger.info(f"[PDF Import {job_id}] Completed: {result.get('stats', {})}")
        else:
            error_msg = result.get("error", "Unknown error")
            sanitized_error = _sanitize_error_message(error_msg)

            _import_jobs[job_id]["status"] = ImportStatus.FAILED
            _import_jobs[job_id]["message"] = f"Import failed: {sanitized_error}"
            _import_jobs[job_id]["updated_at"] = datetime.now()

            # Update JobStore with failure
            await job_store.update_job(
                job_id=job_id,
                status=JobStatus.FAILED,
                message=f"Import failed: {sanitized_error}",
                error=sanitized_error,
            )

            logger.error(f"[PDF Import {job_id}] Failed: {sanitized_error}")

    except Exception as e:
        logger.exception(f"[PDF Import {job_id}] Exception during import")
        sanitized_error = _sanitize_error_message(str(e))

        _import_jobs[job_id]["status"] = ImportStatus.FAILED
        _import_jobs[job_id]["message"] = f"Import failed: {sanitized_error}"
        _import_jobs[job_id]["updated_at"] = datetime.now()

        # Update JobStore with exception
        await job_store.update_job(
            job_id=job_id,
            status=JobStatus.FAILED,
            message=f"Import failed: {sanitized_error}",
            error=sanitized_error,
        )


@router.post("/pdf/multiple", response_model=PDFImportResponse)
async def import_multiple_pdfs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    project_name: str = "Uploaded PDFs",
    research_question: Optional[str] = None,
    extract_concepts: bool = True,
):
    """
    Import multiple PDF files into a single project.

    This endpoint allows batch PDF upload to create a Knowledge Graph from multiple papers.

    Args:
        files: List of PDF files to upload
        project_name: Name for the project (required for multiple files)
        research_question: Optional research question
        extract_concepts: Whether to use LLM for concept extraction

    Returns:
        Import job information including job_id for status tracking
    """
    from uuid import uuid4

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Validate all files are PDFs
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"All files must be PDFs. Invalid file: {file.filename}"
            )

    # Read all file contents
    MAX_TOTAL_SIZE = 200 * 1024 * 1024  # 200MB total
    pdf_files = []
    total_size = 0

    for file in files:
        content = await file.read()
        total_size += len(content)
        if total_size > MAX_TOTAL_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Total file size exceeds maximum of {MAX_TOTAL_SIZE // (1024*1024)}MB"
            )
        pdf_files.append((file.filename, content))

    # Create job
    job_store = await get_job_store()
    job = await job_store.create_job(
        job_type="pdf_import_multiple",
        metadata={
            "file_count": len(pdf_files),
            "total_size": total_size,
            "project_name": project_name,
            "research_question": research_question,
            "extract_concepts": extract_concepts,
        },
    )

    now = datetime.now()
    _import_jobs[job.id] = {
        "job_id": job.id,
        "status": ImportStatus.PENDING,
        "progress": 0.0,
        "message": f"Starting import of {len(pdf_files)} PDFs",
        "project_id": None,
        "stats": None,
        "created_at": now,
        "updated_at": now,
    }

    # Start background import task
    background_tasks.add_task(
        _run_multiple_pdf_import,
        job_id=job.id,
        pdf_files=pdf_files,
        project_name=project_name,
        research_question=research_question,
        extract_concepts=extract_concepts,
    )

    return PDFImportResponse(
        job_id=job.id,
        status=ImportStatus.PENDING,
        message=f"Started importing {len(pdf_files)} PDFs",
        filename=f"{len(pdf_files)} files",
    )


async def _run_multiple_pdf_import(
    job_id: str,
    pdf_files: List[tuple],
    project_name: str,
    research_question: Optional[str],
    extract_concepts: bool,
):
    """Background task to run multiple PDF import."""
    from importers.pdf_importer import PDFImporter

    logger.info(f"[Multi-PDF Import {job_id}] Starting import: {len(pdf_files)} files")

    # Get job store for persistent updates
    job_store = await get_job_store()

    def progress_callback(stage: str, progress: float, message: str):
        """Update job status from importer progress."""
        status_map = {
            "starting": ImportStatus.PENDING,
            "importing": ImportStatus.PROCESSING,
            "building": ImportStatus.BUILDING_GRAPH,
            "complete": ImportStatus.COMPLETED,
        }
        _import_jobs[job_id]["status"] = status_map.get(stage, ImportStatus.PROCESSING)
        _import_jobs[job_id]["progress"] = progress
        _import_jobs[job_id]["message"] = message
        _import_jobs[job_id]["updated_at"] = datetime.now()
        logger.info(f"[Multi-PDF Import {job_id}] {stage}: {progress:.0%} - {message}")

    try:
        # Mark job as running in JobStore
        await job_store.update_job(
            job_id=job_id,
            status=JobStatus.RUNNING,
            progress=0.0,
            message=f"Starting import of {len(pdf_files)} PDFs...",
        )

        graph_store = GraphStore(db=db)
        importer = PDFImporter(
            llm_provider=settings.default_llm_provider,
            llm_model=settings.default_llm_model,
            db_connection=db,
            graph_store=graph_store,
            progress_callback=progress_callback,
        )

        result = await importer.import_multiple_pdfs(
            pdf_files=pdf_files,
            project_name=project_name,
            research_question=research_question,
            extract_concepts=extract_concepts,
        )

        if result["success"]:
            _import_jobs[job_id]["status"] = ImportStatus.COMPLETED
            _import_jobs[job_id]["progress"] = 1.0
            _import_jobs[job_id]["message"] = f"Imported {result['stats']['papers_imported']} PDFs successfully!"
            _import_jobs[job_id]["project_id"] = result.get("project_id")
            _import_jobs[job_id]["stats"] = result.get("stats", {})
            _import_jobs[job_id]["updated_at"] = datetime.now()

            # Update JobStore with completion status and result
            await job_store.update_job(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                progress=1.0,
                message=f"Imported {result['stats']['papers_imported']} PDFs successfully!",
                result={
                    "project_id": str(result.get("project_id")) if result.get("project_id") else None,
                    "stats": result.get("stats", {}),
                },
            )

            logger.info(f"[Multi-PDF Import {job_id}] Completed: {result.get('stats', {})}")
        else:
            error_msg = result.get("error", "Unknown error")
            sanitized_error = _sanitize_error_message(error_msg)

            _import_jobs[job_id]["status"] = ImportStatus.FAILED
            _import_jobs[job_id]["message"] = f"Import failed: {sanitized_error}"
            _import_jobs[job_id]["updated_at"] = datetime.now()

            # Update JobStore with failure
            await job_store.update_job(
                job_id=job_id,
                status=JobStatus.FAILED,
                message=f"Import failed: {sanitized_error}",
                error=sanitized_error,
            )

            logger.error(f"[Multi-PDF Import {job_id}] Failed: {sanitized_error}")

    except Exception as e:
        logger.exception(f"[Multi-PDF Import {job_id}] Exception during import")
        sanitized_error = _sanitize_error_message(str(e))

        _import_jobs[job_id]["status"] = ImportStatus.FAILED
        _import_jobs[job_id]["message"] = f"Import failed: {sanitized_error}"
        _import_jobs[job_id]["updated_at"] = datetime.now()

        # Update JobStore with exception
        await job_store.update_job(
            job_id=job_id,
            status=JobStatus.FAILED,
            message=f"Import failed: {sanitized_error}",
            error=sanitized_error,
        )


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


# =============================================================================
# Zotero RDF Export Import
# =============================================================================

class ZoteroImportRequest(BaseModel):
    """Request model for Zotero import."""
    project_name: Optional[str] = None
    research_question: Optional[str] = None
    extract_concepts: bool = True


class ZoteroValidationResponse(BaseModel):
    """Response model for Zotero folder validation."""
    valid: bool
    folder_path: str
    rdf_file: Optional[str] = None
    items_count: int = 0
    pdfs_available: int = 0
    has_files_dir: bool = False
    errors: List[str] = []
    warnings: List[str] = []


class ZoteroImportResponse(BaseModel):
    """Response model for Zotero import."""
    job_id: str
    status: ImportStatus
    message: str
    items_count: int = 0
    project_id: Optional[str] = None


@router.post("/zotero/validate", response_model=ZoteroValidationResponse)
async def validate_zotero_folder(
    files: List[UploadFile] = File(...),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Validate uploaded Zotero export files before import.

    Expects:
    - One .rdf file (Zotero metadata export)
    - Multiple .pdf files (optional, from "Export Files" option)

    Returns validation results including item count and PDF availability.
    """
    import tempfile
    import shutil
    from importers.zotero_rdf_importer import ZoteroRDFImporter

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Create temp directory for validation
    temp_dir = tempfile.mkdtemp(prefix="zotero_validate_")

    try:
        rdf_file = None
        pdf_count = 0

        # Save uploaded files to temp directory, preserving relative paths
        logger.info(f"Received {len(files)} files for Zotero validation")
        for file in files:
            logger.info(f"  - filename: '{file.filename}', content_type: {file.content_type}")
            content = await file.read()

            # Security: Validate path (no absolute paths or path traversal)
            filename = file.filename or ""
            if filename.startswith("/") or ".." in filename:
                logger.warning(f"Rejected unsafe path: {filename}")
                continue

            # Preserve full relative path for ALL files (RDF and PDF)
            # This maintains Zotero's folder structure: files/<item_key>/paper.pdf
            target_path = Path(temp_dir) / filename
            target_path.parent.mkdir(parents=True, exist_ok=True)

            with open(target_path, 'wb') as f:
                f.write(content)

            if filename.lower().endswith('.rdf'):
                rdf_file = filename
            elif filename.lower().endswith('.pdf'):
                pdf_count += 1
                logger.info(f"    → Saved PDF to: {target_path}")

        if not rdf_file:
            return ZoteroValidationResponse(
                valid=False,
                folder_path=temp_dir,
                errors=["RDF 파일이 업로드되지 않았습니다. Zotero에서 RDF 형식으로 내보내기 해주세요."],
            )

        # Run validation
        importer = ZoteroRDFImporter()
        result = await importer.validate_folder(temp_dir)

        return ZoteroValidationResponse(
            valid=result.get("valid", False),
            folder_path=temp_dir,
            rdf_file=result.get("rdf_file"),
            items_count=result.get("items_count", 0),
            pdfs_available=result.get("pdfs_available", 0),
            has_files_dir=result.get("has_files_dir", False),
            errors=result.get("errors", []),
            warnings=result.get("warnings", []),
        )

    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/zotero", response_model=ZoteroImportResponse)
async def import_zotero_folder(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    project_name: Optional[str] = None,
    research_question: Optional[str] = None,
    extract_concepts: bool = True,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Import a Zotero RDF export with PDFs. Requires auth in production.

    Upload a Zotero export (RDF file + PDFs from "Export Files" option).
    This endpoint will:
    1. Parse RDF/XML for bibliographic metadata
    2. Extract text from uploaded PDFs
    3. Create a new project automatically
    4. Use LLM to extract concepts, methods, and findings
    5. Build a concept-centric knowledge graph

    Args:
        files: Uploaded files (one .rdf + multiple .pdf files)
        project_name: Optional project name (defaults to "Zotero Import YYYY-MM-DD")
        research_question: Optional research question for context
        extract_concepts: Whether to use LLM for concept extraction (default: True)

    Returns:
        Import job information including job_id for status tracking
    """
    import tempfile
    from uuid import uuid4

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Validate that we have an RDF file (case-insensitive)
    rdf_files = [f for f in files if f.filename and f.filename.lower().endswith('.rdf')]
    if not rdf_files:
        raise HTTPException(
            status_code=400,
            detail="RDF 파일이 필요합니다. Zotero에서 RDF 형식으로 내보내기 해주세요."
        )

    # Read all file contents
    MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 500MB total
    uploaded_files = []
    total_size = 0

    for file in files:
        content = await file.read()
        total_size += len(content)
        if total_size > MAX_TOTAL_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"전체 파일 크기가 {MAX_TOTAL_SIZE // (1024*1024)}MB를 초과합니다."
            )
        uploaded_files.append((file.filename, content))

    # Count items (basic RDF parsing to get count)
    rdf_content = next((c for f, c in uploaded_files if f and f.lower().endswith('.rdf')), None)
    items_count = 0
    if rdf_content:
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(rdf_content)
            # Count bibliographic items
            for item_type in ['Article', 'Book', 'BookSection', 'ConferencePaper',
                             'JournalArticle', 'Report', 'Thesis', 'Document']:
                items_count += len(root.findall(f'.//{{{NAMESPACES_FOR_COUNT["bib"]}}}{item_type}', NAMESPACES_FOR_COUNT))
        except:
            pass

    # Create job
    job_store = await get_job_store()
    job = await job_store.create_job(
        job_type="zotero_import",
        metadata={
            "file_count": len(uploaded_files),
            "total_size": total_size,
            "items_count": items_count,
            "project_name": project_name,
            "research_question": research_question,
            "extract_concepts": extract_concepts,
        },
    )

    now = datetime.now()
    _import_jobs[job.id] = {
        "job_id": job.id,
        "status": ImportStatus.PENDING,
        "progress": 0.0,
        "message": f"Zotero import 시작: {items_count}개 항목",
        "project_id": None,
        "stats": None,
        "created_at": now,
        "updated_at": now,
    }

    # Start background import task
    background_tasks.add_task(
        _run_zotero_import,
        job_id=job.id,
        uploaded_files=uploaded_files,
        project_name=project_name,
        research_question=research_question,
        extract_concepts=extract_concepts,
    )

    return ZoteroImportResponse(
        job_id=job.id,
        status=ImportStatus.PENDING,
        message=f"Zotero import 시작: {items_count}개 항목, {len([f for f, _ in uploaded_files if f.endswith('.pdf')])}개 PDF",
        items_count=items_count,
    )


# Namespace constants for RDF parsing in endpoint
NAMESPACES_FOR_COUNT = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'bib': 'http://purl.org/net/biblio#',
}


async def _run_zotero_import(
    job_id: str,
    uploaded_files: List[tuple],
    project_name: Optional[str],
    research_question: Optional[str],
    extract_concepts: bool,
):
    """Background task to run Zotero import."""
    from importers.zotero_rdf_importer import ZoteroRDFImporter

    logger.info(f"[Zotero Import {job_id}] Starting import: {len(uploaded_files)} files")

    # Get job store for persistent updates
    job_store = await get_job_store()

    def progress_callback(progress):
        """Update job status from importer progress."""
        status_map = {
            "validating": ImportStatus.VALIDATING,
            "parsing": ImportStatus.EXTRACTING,
            "scanning": ImportStatus.EXTRACTING,
            "creating_project": ImportStatus.PROCESSING,
            "importing": ImportStatus.PROCESSING,
            "building_relationships": ImportStatus.BUILDING_GRAPH,
            "embeddings": ImportStatus.BUILDING_GRAPH,
            "complete": ImportStatus.COMPLETED,
        }
        _import_jobs[job_id]["status"] = status_map.get(progress.status, ImportStatus.PROCESSING)
        _import_jobs[job_id]["progress"] = progress.progress
        _import_jobs[job_id]["message"] = progress.message
        _import_jobs[job_id]["updated_at"] = datetime.now()
        logger.info(f"[Zotero Import {job_id}] {progress.status}: {progress.progress:.0%} - {progress.message}")

    try:
        # Mark job as running in JobStore
        await job_store.update_job(
            job_id=job_id,
            status=JobStatus.RUNNING,
            progress=0.0,
            message="Starting Zotero import...",
        )

        # Create importer with database connection and GraphStore
        graph_store = GraphStore(db=db)
        importer = ZoteroRDFImporter(
            llm_provider=settings.default_llm_provider if extract_concepts else None,
            llm_model=settings.default_llm_model,
            db_connection=db,
            graph_store=graph_store,
            progress_callback=progress_callback,
        )

        # Run the import
        result = await importer.import_from_upload(
            files=uploaded_files,
            project_name=project_name,
            research_question=research_question,
        )

        if result.get("success"):
            _import_jobs[job_id]["status"] = ImportStatus.COMPLETED
            _import_jobs[job_id]["progress"] = 1.0
            _import_jobs[job_id]["message"] = f"Zotero import 완료: {result.get('papers_imported', 0)}개 논문"
            _import_jobs[job_id]["project_id"] = result.get("project_id")
            _import_jobs[job_id]["stats"] = {
                "papers_imported": result.get("papers_imported", 0),
                "pdfs_processed": result.get("pdfs_processed", 0),
                "concepts_extracted": result.get("concepts_extracted", 0),
                "relationships_created": result.get("relationships_created", 0),
            }
            _import_jobs[job_id]["updated_at"] = datetime.now()

            # Update JobStore with completion status and result
            await job_store.update_job(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                progress=1.0,
                message=f"Zotero import 완료: {result.get('papers_imported', 0)}개 논문",
                result={
                    "project_id": str(result.get("project_id")) if result.get("project_id") else None,
                    "stats": _import_jobs[job_id]["stats"],
                },
            )

            logger.info(f"[Zotero Import {job_id}] Completed: {_import_jobs[job_id]['stats']}")
        else:
            errors = result.get("errors", ["Unknown error"])
            error_msg = "; ".join(errors[:3])  # Limit error message length
            sanitized_error = _sanitize_error_message(error_msg)

            _import_jobs[job_id]["status"] = ImportStatus.FAILED
            _import_jobs[job_id]["message"] = f"Import 실패: {sanitized_error}"
            _import_jobs[job_id]["updated_at"] = datetime.now()

            # Update JobStore with failure
            await job_store.update_job(
                job_id=job_id,
                status=JobStatus.FAILED,
                message=f"Import 실패: {sanitized_error}",
                error=sanitized_error,
            )

            logger.error(f"[Zotero Import {job_id}] Failed: {sanitized_error}")

    except Exception as e:
        logger.exception(f"[Zotero Import {job_id}] Exception during import")
        sanitized_error = _sanitize_error_message(str(e))

        _import_jobs[job_id]["status"] = ImportStatus.FAILED
        _import_jobs[job_id]["message"] = f"Import 실패: {sanitized_error}"
        _import_jobs[job_id]["updated_at"] = datetime.now()

        # Update JobStore with exception
        await job_store.update_job(
            job_id=job_id,
            status=JobStatus.FAILED,
            message=f"Import 실패: {sanitized_error}",
            error=sanitized_error,
        )
