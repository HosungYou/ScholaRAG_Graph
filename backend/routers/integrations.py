"""
External integrations API router.

Provides endpoints for:
- Semantic Scholar: Paper search, metadata enrichment, citation graphs
- OpenAlex: Open academic knowledge base
- Zotero: Reference management synchronization

All endpoints include per-user/project API quota management.
Quota headers are included in all responses:
- X-Quota-Limit: Daily limit for this API
- X-Quota-Used: Current usage count
- X-Quota-Remaining: Remaining calls allowed
- X-Quota-Reset: ISO timestamp when quota resets
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from config import get_settings, Settings
from auth.dependencies import require_auth_if_configured
from auth.models import User
from integrations.semantic_scholar import SemanticScholarClient, SemanticScholarPaper
from integrations.openalex import OpenAlexClient, OpenAlexWork
from integrations.zotero import ZoteroClient, ZoteroItem, ZoteroCollection
from middleware.quota_middleware import QuotaDependency, add_quota_headers
from middleware.quota_service import QuotaStatus

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


# ==================== Request/Response Models ====================

class PaperSearchRequest(BaseModel):
    """Paper search request."""
    query: str = Field(..., description="Search query")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results")
    year_start: Optional[int] = Field(None, description="Start year filter")
    year_end: Optional[int] = Field(None, description="End year filter")
    open_access_only: bool = Field(False, description="Only open access papers")
    include_embedding: bool = Field(False, description="Include SPECTER embeddings")


class PaperEnrichRequest(BaseModel):
    """Paper metadata enrichment request."""
    doi: Optional[str] = Field(None, description="Paper DOI")
    title: Optional[str] = Field(None, description="Paper title")
    include_embedding: bool = Field(True, description="Include SPECTER embedding")


class CitationGraphRequest(BaseModel):
    """Citation graph request."""
    paper_id: str = Field(..., description="Center paper ID")
    depth: int = Field(2, ge=1, le=3, description="Graph depth")
    max_per_level: int = Field(20, ge=1, le=50, description="Max papers per level")


class ZoteroSyncRequest(BaseModel):
    """Zotero sync request."""
    api_key: str = Field(..., description="Zotero API key")
    user_id: Optional[str] = Field(None, description="User library ID")
    group_id: Optional[str] = Field(None, description="Group library ID")
    collection_key: str = Field(..., description="Collection to sync")
    last_sync_version: int = Field(0, description="Last sync version")


class ZoteroExportRequest(BaseModel):
    """Zotero export request."""
    api_key: str = Field(..., description="Zotero API key")
    user_id: Optional[str] = Field(None, description="User library ID")
    group_id: Optional[str] = Field(None, description="Group library ID")
    collection_name: str = Field(..., description="New collection name")
    papers: List[Dict[str, Any]] = Field(..., description="Papers to export")


class SemanticScholarPaperResponse(BaseModel):
    """Semantic Scholar paper response."""
    paper_id: str
    title: str
    abstract: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    citation_count: int = 0
    influential_citation_count: int = 0
    is_open_access: bool = False
    open_access_pdf_url: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    authors: List[Dict[str, Any]] = []
    fields_of_study: List[str] = []
    embedding: Optional[List[float]] = None
    tldr: Optional[str] = None

    @classmethod
    def from_paper(cls, paper: SemanticScholarPaper) -> "SemanticScholarPaperResponse":
        return cls(
            paper_id=paper.paper_id,
            title=paper.title,
            abstract=paper.abstract,
            year=paper.year,
            venue=paper.venue,
            citation_count=paper.citation_count,
            influential_citation_count=paper.influential_citation_count,
            is_open_access=paper.is_open_access,
            open_access_pdf_url=paper.open_access_pdf_url,
            doi=paper.doi,
            arxiv_id=paper.arxiv_id,
            authors=paper.authors,
            fields_of_study=paper.fields_of_study,
            embedding=paper.embedding,
            tldr=paper.tldr,
        )


class OpenAlexWorkResponse(BaseModel):
    """OpenAlex work response."""
    id: str
    title: str
    abstract: Optional[str] = None
    publication_year: Optional[int] = None
    type: Optional[str] = None
    doi: Optional[str] = None
    open_access_url: Optional[str] = None
    is_open_access: bool = False
    open_access_status: Optional[str] = None
    citation_count: int = 0
    authors: List[Dict[str, Any]] = []
    concepts: List[Dict[str, Any]] = []
    topics: List[Dict[str, Any]] = []

    @classmethod
    def from_work(cls, work: OpenAlexWork) -> "OpenAlexWorkResponse":
        return cls(
            id=work.id,
            title=work.title,
            abstract=work.abstract,
            publication_year=work.publication_year,
            type=work.type,
            doi=work.doi,
            open_access_url=work.open_access_url,
            is_open_access=work.is_open_access,
            open_access_status=work.open_access_status,
            citation_count=work.citation_count,
            authors=work.authors,
            concepts=work.concepts,
            topics=work.topics,
        )


# ==================== Semantic Scholar Endpoints ====================

@router.post("/semantic-scholar/search", response_model=List[SemanticScholarPaperResponse])
async def search_semantic_scholar(
    request: PaperSearchRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
    current_user: Optional[User] = Depends(require_auth_if_configured),
    quota: QuotaStatus = Depends(QuotaDependency(api_type="semantic_scholar")),
):
    """
    Search papers using Semantic Scholar API.

    Returns papers matching the query with metadata, citations, and optionally embeddings.

    **Quota**: This endpoint counts against your `semantic_scholar` daily quota.
    """
    async with SemanticScholarClient() as client:
        year_range = None
        if request.year_start or request.year_end:
            year_range = (
                request.year_start or 1900,
                request.year_end or 2100,
            )

        papers = await client.search_papers_bulk(
            query=request.query,
            max_results=request.limit,
            year_range=year_range,
            open_access_only=request.open_access_only,
            include_embedding=request.include_embedding,
        )

        # Add quota headers to response
        add_quota_headers(response, quota)

        return [SemanticScholarPaperResponse.from_paper(p) for p in papers]


@router.get("/semantic-scholar/paper/{paper_id}", response_model=SemanticScholarPaperResponse)
async def get_semantic_scholar_paper(
    paper_id: str,
    include_embedding: bool = Query(False),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Get detailed information about a paper.

    Paper ID can be:
    - Semantic Scholar ID
    - DOI (prefixed with "DOI:")
    - arXiv ID (prefixed with "arXiv:")
    - PMID (prefixed with "PMID:")
    """
    async with SemanticScholarClient() as client:
        paper = await client.get_paper(paper_id, include_embedding=include_embedding)

        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        return SemanticScholarPaperResponse.from_paper(paper)


@router.post("/semantic-scholar/enrich", response_model=Optional[SemanticScholarPaperResponse])
async def enrich_paper_metadata(
    request: PaperEnrichRequest,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Enrich paper metadata using DOI or title search.

    Returns the best matching paper with full metadata and SPECTER embedding.
    """
    if not request.doi and not request.title:
        raise HTTPException(
            status_code=400,
            detail="Either doi or title must be provided"
        )

    async with SemanticScholarClient() as client:
        paper = await client.enrich_paper_metadata(
            doi=request.doi,
            title=request.title,
            include_embedding=request.include_embedding,
        )

        if not paper:
            return None

        return SemanticScholarPaperResponse.from_paper(paper)


@router.post("/semantic-scholar/citation-graph")
async def get_citation_graph(
    request: CitationGraphRequest,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Build a citation graph around a paper.

    Returns nodes (papers) and edges (citation relationships) for visualization.
    """
    async with SemanticScholarClient() as client:
        graph = await client.get_citation_graph(
            paper_id=request.paper_id,
            depth=request.depth,
            max_per_level=request.max_per_level,
        )

        return graph


@router.get("/semantic-scholar/paper/{paper_id}/references", response_model=List[SemanticScholarPaperResponse])
async def get_paper_references(
    paper_id: str,
    limit: int = Query(100, ge=1, le=500),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get papers that this paper references."""
    async with SemanticScholarClient() as client:
        papers = await client.get_references(paper_id, limit=limit)
        return [SemanticScholarPaperResponse.from_paper(p) for p in papers]


@router.get("/semantic-scholar/paper/{paper_id}/citations", response_model=List[SemanticScholarPaperResponse])
async def get_paper_citations(
    paper_id: str,
    limit: int = Query(100, ge=1, le=500),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get papers that cite this paper."""
    async with SemanticScholarClient() as client:
        papers = await client.get_citations(paper_id, limit=limit)
        return [SemanticScholarPaperResponse.from_paper(p) for p in papers]


@router.post("/semantic-scholar/recommendations", response_model=List[SemanticScholarPaperResponse])
async def get_recommendations(
    paper_ids: List[str],
    limit: int = Query(100, ge=1, le=500),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get paper recommendations based on a list of papers."""
    async with SemanticScholarClient() as client:
        papers = await client.get_recommendations(paper_ids, limit=limit)
        return [SemanticScholarPaperResponse.from_paper(p) for p in papers]


# ==================== OpenAlex Endpoints ====================

@router.post("/openalex/search", response_model=List[OpenAlexWorkResponse])
async def search_openalex(
    request: PaperSearchRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
    current_user: Optional[User] = Depends(require_auth_if_configured),
    quota: QuotaStatus = Depends(QuotaDependency(api_type="openalex")),
):
    """
    Search works using OpenAlex API.

    OpenAlex provides broader coverage including more international and open access works.

    **Quota**: This endpoint counts against your `openalex` daily quota.
    """
    async with OpenAlexClient() as client:
        filter_params = {}

        if request.year_start and request.year_end:
            filter_params["publication_year"] = f"{request.year_start}-{request.year_end}"
        elif request.year_start:
            filter_params["from_publication_date"] = f"{request.year_start}-01-01"
        elif request.year_end:
            filter_params["to_publication_date"] = f"{request.year_end}-12-31"

        if request.open_access_only:
            filter_params["is_oa"] = "true"

        works = await client.search_works_bulk(
            query=request.query,
            max_results=request.limit,
            filter_params=filter_params if filter_params else None,
        )

        # Add quota headers to response
        add_quota_headers(response, quota)

        return [OpenAlexWorkResponse.from_work(w) for w in works]


@router.get("/openalex/work/{work_id}", response_model=OpenAlexWorkResponse)
async def get_openalex_work(
    work_id: str,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Get detailed information about a work.

    Work ID can be OpenAlex ID, DOI, or PMID.
    """
    async with OpenAlexClient() as client:
        work = await client.get_work(work_id)

        if not work:
            raise HTTPException(status_code=404, detail="Work not found")

        return OpenAlexWorkResponse.from_work(work)


@router.post("/openalex/enrich", response_model=Optional[OpenAlexWorkResponse])
async def enrich_openalex_metadata(
    request: PaperEnrichRequest,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Enrich paper metadata using OpenAlex."""
    if not request.doi and not request.title:
        raise HTTPException(
            status_code=400,
            detail="Either doi or title must be provided"
        )

    async with OpenAlexClient() as client:
        work = await client.enrich_work_metadata(
            doi=request.doi,
            title=request.title,
        )

        if not work:
            return None

        return OpenAlexWorkResponse.from_work(work)


@router.get("/openalex/work/{work_id}/citations", response_model=List[OpenAlexWorkResponse])
async def get_openalex_citations(
    work_id: str,
    limit: int = Query(100, ge=1, le=200),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get works that cite this work."""
    async with OpenAlexClient() as client:
        works = await client.get_citations(work_id, limit=limit)
        return [OpenAlexWorkResponse.from_work(w) for w in works]


@router.get("/openalex/concepts/search")
async def search_openalex_concepts(
    query: str,
    limit: int = Query(25, ge=1, le=100),
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Search for concepts in OpenAlex taxonomy."""
    async with OpenAlexClient() as client:
        concepts = await client.search_concepts(query, per_page=limit)
        return [
            {
                "id": c.id,
                "display_name": c.display_name,
                "level": c.level,
                "description": c.description,
                "works_count": c.works_count,
            }
            for c in concepts
        ]


@router.get("/openalex/oa-statistics")
async def get_oa_statistics(
    query: Optional[str] = None,
    year: Optional[str] = None,
    concept_id: Optional[str] = None,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get open access statistics for works matching filters."""
    async with OpenAlexClient() as client:
        filter_params = {}
        if year:
            filter_params["publication_year"] = year
        if concept_id:
            filter_params["concepts.id"] = concept_id

        if query:
            # Search first, then get stats
            works = await client.search_works_bulk(query=query, max_results=1000)
            total = len(works)
            oa_count = sum(1 for w in works if w.is_open_access)
            return {
                "total_works": total,
                "open_access_count": oa_count,
                "open_access_percentage": (oa_count / total * 100) if total > 0 else 0,
            }
        else:
            return await client.get_oa_statistics(filter_params if filter_params else None)


# ==================== Zotero Endpoints ====================

@router.post("/zotero/collections")
async def get_zotero_collections(
    api_key: str,
    user_id: Optional[str] = None,
    group_id: Optional[str] = None,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get all collections in a Zotero library."""
    async with ZoteroClient(api_key, user_id, group_id) as client:
        collections = await client.get_collections()
        return [
            {
                "key": c.key,
                "name": c.name,
                "parent_collection": c.parent_collection,
                "num_items": c.num_items,
            }
            for c in collections
        ]


@router.post("/zotero/collection/{collection_key}/items")
async def get_zotero_collection_items(
    collection_key: str,
    api_key: str,
    user_id: Optional[str] = None,
    group_id: Optional[str] = None,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get all items in a Zotero collection."""
    async with ZoteroClient(api_key, user_id, group_id) as client:
        items = await client.get_items_all(collection_key=collection_key)
        return [
            {
                "key": item.key,
                "title": item.title,
                "abstract": item.abstract,
                "year": item.year,
                "doi": item.doi,
                "authors": [
                    c.get("firstName", "") + " " + c.get("lastName", c.get("name", ""))
                    for c in item.creators
                ],
                "journal": item.publication_title,
                "tags": [t.get("tag") for t in item.tags],
            }
            for item in items
        ]


@router.post("/zotero/import")
async def import_zotero_collection(
    api_key: str,
    collection_key: str,
    user_id: Optional[str] = None,
    group_id: Optional[str] = None,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Import a Zotero collection as ScholaRAG paper data.

    Returns paper data ready for project import.
    """
    async with ZoteroClient(api_key, user_id, group_id) as client:
        papers = await client.import_collection_to_project(collection_key)
        return {
            "status": "success",
            "papers_count": len(papers),
            "papers": papers,
        }


@router.post("/zotero/export")
async def export_to_zotero(
    request: ZoteroExportRequest,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Export ScholaRAG papers to a new Zotero collection.

    Creates a new collection and adds all papers as items.
    """
    async with ZoteroClient(
        request.api_key,
        request.user_id,
        request.group_id,
    ) as client:
        collection, items = await client.export_papers_to_collection(
            papers=request.papers,
            collection_name=request.collection_name,
        )

        return {
            "status": "success",
            "collection": {
                "key": collection.key,
                "name": collection.name,
            },
            "items_created": len(items),
        }


@router.post("/zotero/sync")
async def sync_zotero_collection(
    request: ZoteroSyncRequest,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Sync a Zotero collection with ScholaRAG.

    Returns new, modified, and deleted items since last sync.
    """
    async with ZoteroClient(
        request.api_key,
        request.user_id,
        request.group_id,
    ) as client:
        result = await client.sync_collection(
            collection_key=request.collection_key,
            last_sync_version=request.last_sync_version,
        )

        return result
