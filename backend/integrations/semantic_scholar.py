"""
Semantic Scholar API Integration for ScholaRAG_Graph.

Enhanced integration providing:
- Paper search and metadata enrichment
- Citation graph queries (references and citations)
- Author disambiguation
- SPECTER2 embeddings
- Rate limiting and retry logic
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)


class SemanticScholarRateLimitError(Exception):
    """Raised when Semantic Scholar keeps returning 429 after retries."""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Semantic Scholar rate limit exceeded (retry_after={retry_after}s)")


@dataclass
class SemanticScholarPaper:
    """Semantic Scholar paper data model."""

    paper_id: str
    title: str
    abstract: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    citation_count: int = 0
    influential_citation_count: int = 0
    reference_count: int = 0
    is_open_access: bool = False
    open_access_pdf_url: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    authors: List[Dict[str, Any]] = field(default_factory=list)
    fields_of_study: List[str] = field(default_factory=list)
    publication_types: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    tldr: Optional[str] = None
    external_ids: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "SemanticScholarPaper":
        """Create paper from API response."""
        open_access = data.get("openAccessPdf") or {}
        external_ids = data.get("externalIds") or {}

        return cls(
            paper_id=data.get("paperId", ""),
            title=data.get("title", ""),
            abstract=data.get("abstract"),
            year=data.get("year"),
            venue=data.get("venue"),
            citation_count=data.get("citationCount", 0),
            influential_citation_count=data.get("influentialCitationCount", 0),
            reference_count=data.get("referenceCount", 0),
            is_open_access=bool(open_access.get("url")),
            open_access_pdf_url=open_access.get("url"),
            doi=external_ids.get("DOI"),
            arxiv_id=external_ids.get("ArXiv"),
            authors=[
                {
                    "author_id": a.get("authorId"),
                    "name": a.get("name"),
                    "affiliations": a.get("affiliations", []),
                }
                for a in data.get("authors", [])
            ],
            fields_of_study=data.get("fieldsOfStudy") or [],
            publication_types=data.get("publicationTypes") or [],
            embedding=data.get("embedding", {}).get("vector"),
            tldr=data.get("tldr", {}).get("text") if data.get("tldr") else None,
            external_ids=external_ids,
        )


@dataclass
class SemanticScholarAuthor:
    """Semantic Scholar author data model."""

    author_id: str
    name: str
    affiliations: List[str] = field(default_factory=list)
    paper_count: int = 0
    citation_count: int = 0
    h_index: int = 0

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "SemanticScholarAuthor":
        """Create author from API response."""
        return cls(
            author_id=data.get("authorId", ""),
            name=data.get("name", ""),
            affiliations=data.get("affiliations") or [],
            paper_count=data.get("paperCount", 0),
            citation_count=data.get("citationCount", 0),
            h_index=data.get("hIndex", 0),
        )


@dataclass
class CitationContext:
    """Citation context with snippet and intent."""

    citing_paper_id: str
    citing_paper_title: str
    context: Optional[str] = None
    intent: Optional[str] = None  # methodology, background, result_comparison, etc.
    is_influential: bool = False


class SemanticScholarClient:
    """
    Enhanced Semantic Scholar API client.

    Features:
    - Automatic rate limiting (100 requests per 5 minutes without API key)
    - Retry logic with exponential backoff
    - Batch paper retrieval
    - Citation graph traversal
    - SPECTER2 embedding retrieval
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    RECOMMENDATIONS_URL = "https://api.semanticscholar.org/recommendations/v1"

    # Default fields for paper queries
    PAPER_FIELDS = [
        "paperId", "title", "abstract", "year", "venue",
        "citationCount", "influentialCitationCount", "referenceCount",
        "openAccessPdf", "externalIds", "authors", "fieldsOfStudy",
        "publicationTypes", "tldr"
    ]

    PAPER_FIELDS_WITH_EMBEDDING = PAPER_FIELDS + ["embedding"]

    AUTHOR_FIELDS = [
        "authorId", "name", "affiliations", "paperCount",
        "citationCount", "hIndex"
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        requests_per_interval: int = 100,
        interval_seconds: int = 300,
    ):
        """
        Initialize the client.

        Args:
            api_key: Optional API key for higher rate limits
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            requests_per_interval: Rate limit requests per interval
            interval_seconds: Rate limit interval in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.requests_per_interval = requests_per_interval
        self.interval_seconds = interval_seconds

        # Rate limiting state
        self._request_times: List[float] = []
        self._lock = asyncio.Lock()

        # HTTP client
        headers = {"Accept": "application/json"}
        if api_key:
            headers["x-api-key"] = api_key

        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers=headers,
        )

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _rate_limit(self):
        """Enforce rate limiting."""
        async with self._lock:
            now = datetime.now().timestamp()
            cutoff = now - self.interval_seconds

            # Remove old requests
            self._request_times = [t for t in self._request_times if t > cutoff]

            if len(self._request_times) >= self.requests_per_interval:
                # Wait until oldest request expires
                sleep_time = self._request_times[0] - cutoff + 0.1
                logger.warning(f"Rate limit reached, waiting {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)
                self._request_times = self._request_times[1:]

            self._request_times.append(now)

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make an API request with retry logic."""
        await self._rate_limit()

        last_retry_after = 60
        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(method, url, **kwargs)

                if response.status_code == 429:
                    # Rate limited
                    retry_after = int(response.headers.get("Retry-After", 60))
                    last_retry_after = retry_after
                    if attempt == self.max_retries - 1:
                        raise SemanticScholarRateLimitError(retry_after=retry_after)
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response.json()

            except SemanticScholarRateLimitError:
                raise
            except httpx.HTTPStatusError as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"HTTP error after {self.max_retries} attempts: {e}")
                    raise
                await asyncio.sleep(2 ** attempt)

            except httpx.RequestError as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Request error after {self.max_retries} attempts: {e}")
                    raise
                await asyncio.sleep(2 ** attempt)

        raise SemanticScholarRateLimitError(retry_after=last_retry_after)

    # ==================== Paper Search ====================

    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        offset: int = 0,
        year_range: Optional[tuple] = None,
        fields_of_study: Optional[List[str]] = None,
        open_access_only: bool = False,
        include_embedding: bool = False,
    ) -> List[SemanticScholarPaper]:
        """
        Search for papers.

        Args:
            query: Search query string
            limit: Maximum number of results (max 100)
            offset: Result offset for pagination
            year_range: Optional (start_year, end_year) filter
            fields_of_study: Optional field of study filter
            open_access_only: Only return open access papers
            include_embedding: Include SPECTER embeddings

        Returns:
            List of papers matching the query
        """
        fields = self.PAPER_FIELDS_WITH_EMBEDDING if include_embedding else self.PAPER_FIELDS

        params = {
            "query": query,
            "limit": min(limit, 100),
            "offset": offset,
            "fields": ",".join(fields),
        }

        if year_range:
            params["year"] = f"{year_range[0]}-{year_range[1]}"

        if fields_of_study:
            params["fieldsOfStudy"] = ",".join(fields_of_study)

        if open_access_only:
            params["openAccessPdf"] = ""

        url = f"{self.BASE_URL}/paper/search"
        data = await self._request("GET", url, params=params)

        papers = []
        for item in data.get("data", []):
            try:
                papers.append(SemanticScholarPaper.from_api_response(item))
            except Exception as e:
                logger.warning(f"Failed to parse paper: {e}")

        return papers

    async def search_papers_bulk(
        self,
        query: str,
        max_results: int = 1000,
        **kwargs
    ) -> List[SemanticScholarPaper]:
        """
        Search for papers with pagination for large result sets.

        Args:
            query: Search query string
            max_results: Maximum total results to retrieve
            **kwargs: Additional arguments passed to search_papers

        Returns:
            List of all papers found
        """
        all_papers = []
        offset = 0

        while len(all_papers) < max_results:
            batch_size = min(100, max_results - len(all_papers))
            papers = await self.search_papers(
                query=query,
                limit=batch_size,
                offset=offset,
                **kwargs
            )

            if not papers:
                break

            all_papers.extend(papers)
            offset += len(papers)

            if len(papers) < batch_size:
                break

        return all_papers

    # ==================== Paper Details ====================

    async def get_paper(
        self,
        paper_id: str,
        include_embedding: bool = False,
    ) -> Optional[SemanticScholarPaper]:
        """
        Get detailed information about a paper.

        Args:
            paper_id: Semantic Scholar paper ID, DOI, arXiv ID, etc.
            include_embedding: Include SPECTER embedding

        Returns:
            Paper details or None if not found
        """
        fields = self.PAPER_FIELDS_WITH_EMBEDDING if include_embedding else self.PAPER_FIELDS

        # URL encode the paper ID (handles DOI, arXiv, etc.)
        encoded_id = quote_plus(paper_id)
        url = f"{self.BASE_URL}/paper/{encoded_id}"

        try:
            data = await self._request("GET", url, params={"fields": ",".join(fields)})
            return SemanticScholarPaper.from_api_response(data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def get_papers_batch(
        self,
        paper_ids: List[str],
        include_embedding: bool = False,
    ) -> List[SemanticScholarPaper]:
        """
        Get multiple papers in a single request (max 500).

        Args:
            paper_ids: List of paper IDs
            include_embedding: Include SPECTER embeddings

        Returns:
            List of papers found
        """
        if not paper_ids:
            return []

        fields = self.PAPER_FIELDS_WITH_EMBEDDING if include_embedding else self.PAPER_FIELDS

        # Batch endpoint accepts up to 500 IDs
        all_papers = []
        for i in range(0, len(paper_ids), 500):
            batch = paper_ids[i:i + 500]

            url = f"{self.BASE_URL}/paper/batch"
            data = await self._request(
                "POST",
                url,
                params={"fields": ",".join(fields)},
                json={"ids": batch},
            )

            for item in data:
                if item:  # Skip None for not found papers
                    try:
                        all_papers.append(SemanticScholarPaper.from_api_response(item))
                    except Exception as e:
                        logger.warning(f"Failed to parse paper: {e}")

        return all_papers

    async def enrich_paper_metadata(
        self,
        doi: Optional[str] = None,
        title: Optional[str] = None,
        include_embedding: bool = True,
    ) -> Optional[SemanticScholarPaper]:
        """
        Enrich paper metadata using DOI or title search.

        Args:
            doi: Paper DOI
            title: Paper title (used if DOI not provided)
            include_embedding: Include SPECTER embedding

        Returns:
            Enriched paper data or None if not found
        """
        if doi:
            paper = await self.get_paper(f"DOI:{doi}", include_embedding=include_embedding)
            if paper:
                return paper

        if title:
            papers = await self.search_papers(
                query=title,
                limit=5,
                include_embedding=include_embedding,
            )

            # Find best match by title similarity
            title_lower = title.lower()
            for paper in papers:
                if paper.title.lower() == title_lower:
                    return paper

            # Return first result if no exact match
            if papers:
                return papers[0]

        return None

    # ==================== Citation Graph ====================

    async def get_references(
        self,
        paper_id: str,
        limit: int = 100,
        include_embedding: bool = False,
    ) -> List[SemanticScholarPaper]:
        """
        Get papers that this paper references.

        Args:
            paper_id: Source paper ID
            limit: Maximum number of references
            include_embedding: Include SPECTER embeddings

        Returns:
            List of referenced papers
        """
        fields = self.PAPER_FIELDS_WITH_EMBEDDING if include_embedding else self.PAPER_FIELDS

        encoded_id = quote_plus(paper_id)
        url = f"{self.BASE_URL}/paper/{encoded_id}/references"

        data = await self._request(
            "GET",
            url,
            params={
                "fields": ",".join([f"citedPaper.{f}" for f in fields]),
                "limit": min(limit, 1000),
            }
        )

        papers = []
        for item in data.get("data", []):
            cited_paper = item.get("citedPaper")
            if cited_paper:
                try:
                    papers.append(SemanticScholarPaper.from_api_response(cited_paper))
                except Exception as e:
                    logger.warning(f"Failed to parse reference: {e}")

        return papers

    async def get_citations(
        self,
        paper_id: str,
        limit: int = 100,
        include_embedding: bool = False,
    ) -> List[SemanticScholarPaper]:
        """
        Get papers that cite this paper.

        Args:
            paper_id: Source paper ID
            limit: Maximum number of citations
            include_embedding: Include SPECTER embeddings

        Returns:
            List of citing papers
        """
        fields = self.PAPER_FIELDS_WITH_EMBEDDING if include_embedding else self.PAPER_FIELDS

        encoded_id = quote_plus(paper_id)
        url = f"{self.BASE_URL}/paper/{encoded_id}/citations"

        data = await self._request(
            "GET",
            url,
            params={
                "fields": ",".join([f"citingPaper.{f}" for f in fields]),
                "limit": min(limit, 1000),
            }
        )

        papers = []
        for item in data.get("data", []):
            citing_paper = item.get("citingPaper")
            if citing_paper:
                try:
                    papers.append(SemanticScholarPaper.from_api_response(citing_paper))
                except Exception as e:
                    logger.warning(f"Failed to parse citation: {e}")

        return papers

    async def get_citation_graph(
        self,
        paper_id: str,
        depth: int = 2,
        max_per_level: int = 20,
        include_embedding: bool = False,
    ) -> Dict[str, Any]:
        """
        Build a citation graph around a paper.

        Args:
            paper_id: Center paper ID
            depth: How many hops to traverse (1 or 2)
            max_per_level: Maximum papers per level
            include_embedding: Include SPECTER embeddings

        Returns:
            Citation graph with nodes and edges
        """
        nodes: Dict[str, SemanticScholarPaper] = {}
        edges: List[Dict[str, str]] = []
        visited: Set[str] = set()

        # Get center paper
        center = await self.get_paper(paper_id, include_embedding=include_embedding)
        if not center:
            return {"nodes": [], "edges": []}

        nodes[center.paper_id] = center
        visited.add(center.paper_id)

        async def process_level(paper_ids: List[str], level: int):
            if level > depth:
                return

            for pid in paper_ids:
                if pid in visited:
                    continue
                visited.add(pid)

                # Get references and citations
                refs = await self.get_references(pid, limit=max_per_level, include_embedding=include_embedding)
                cites = await self.get_citations(pid, limit=max_per_level, include_embedding=include_embedding)

                next_level = []

                for ref in refs:
                    if ref.paper_id not in nodes:
                        nodes[ref.paper_id] = ref
                        next_level.append(ref.paper_id)
                    edges.append({"source": pid, "target": ref.paper_id, "type": "references"})

                for cite in cites:
                    if cite.paper_id not in nodes:
                        nodes[cite.paper_id] = cite
                        next_level.append(cite.paper_id)
                    edges.append({"source": cite.paper_id, "target": pid, "type": "cites"})

                if level < depth:
                    await process_level(next_level[:max_per_level], level + 1)

        await process_level([center.paper_id], 1)

        return {
            "center_paper_id": paper_id,
            "nodes": [
                {
                    "id": p.paper_id,
                    "title": p.title,
                    "year": p.year,
                    "citation_count": p.citation_count,
                    "is_center": p.paper_id == paper_id,
                }
                for p in nodes.values()
            ],
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }

    # ==================== Author Operations ====================

    async def get_author(
        self,
        author_id: str,
    ) -> Optional[SemanticScholarAuthor]:
        """
        Get author details.

        Args:
            author_id: Semantic Scholar author ID

        Returns:
            Author details or None if not found
        """
        url = f"{self.BASE_URL}/author/{author_id}"

        try:
            data = await self._request("GET", url, params={"fields": ",".join(self.AUTHOR_FIELDS)})
            return SemanticScholarAuthor.from_api_response(data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def search_authors(
        self,
        query: str,
        limit: int = 10,
    ) -> List[SemanticScholarAuthor]:
        """
        Search for authors by name.

        Args:
            query: Author name to search
            limit: Maximum results

        Returns:
            List of matching authors
        """
        url = f"{self.BASE_URL}/author/search"

        data = await self._request(
            "GET",
            url,
            params={
                "query": query,
                "limit": min(limit, 100),
                "fields": ",".join(self.AUTHOR_FIELDS),
            }
        )

        return [
            SemanticScholarAuthor.from_api_response(item)
            for item in data.get("data", [])
        ]

    async def get_author_papers(
        self,
        author_id: str,
        limit: int = 100,
        include_embedding: bool = False,
    ) -> List[SemanticScholarPaper]:
        """
        Get papers by an author.

        Args:
            author_id: Author ID
            limit: Maximum papers to retrieve
            include_embedding: Include SPECTER embeddings

        Returns:
            List of papers by the author
        """
        fields = self.PAPER_FIELDS_WITH_EMBEDDING if include_embedding else self.PAPER_FIELDS

        url = f"{self.BASE_URL}/author/{author_id}/papers"

        data = await self._request(
            "GET",
            url,
            params={
                "fields": ",".join(fields),
                "limit": min(limit, 1000),
            }
        )

        return [
            SemanticScholarPaper.from_api_response(item)
            for item in data.get("data", [])
        ]

    # ==================== Recommendations ====================

    async def get_recommendations(
        self,
        paper_ids: List[str],
        limit: int = 100,
    ) -> List[SemanticScholarPaper]:
        """
        Get paper recommendations based on a list of papers.

        Args:
            paper_ids: List of paper IDs to base recommendations on
            limit: Maximum recommendations

        Returns:
            List of recommended papers
        """
        url = f"{self.RECOMMENDATIONS_URL}/papers"

        data = await self._request(
            "POST",
            url,
            params={"fields": ",".join(self.PAPER_FIELDS), "limit": min(limit, 500)},
            json={"positivePaperIds": paper_ids[:500]},  # Max 500 seed papers
        )

        return [
            SemanticScholarPaper.from_api_response(item)
            for item in data.get("recommendedPapers", [])
        ]
