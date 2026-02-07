"""
Tests for external API integrations.

These tests mock external API calls to avoid rate limits and ensure
consistent test behavior.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from integrations.semantic_scholar import (
    SemanticScholarClient,
    SemanticScholarPaper,
    SemanticScholarAuthor,
)
from integrations.openalex import (
    OpenAlexClient,
    OpenAlexWork,
    OpenAlexAuthor,
    OpenAlexConcept,
)
from integrations.zotero import (
    ZoteroClient,
    ZoteroItem,
    ZoteroCollection,
    ZoteroItemType,
)


# ==================== Semantic Scholar Tests ====================

class TestSemanticScholarPaper:
    """Test SemanticScholarPaper model."""

    def test_from_api_response(self):
        """Test parsing API response."""
        data = {
            "paperId": "abc123",
            "title": "Test Paper",
            "abstract": "This is a test abstract.",
            "year": 2024,
            "venue": "Test Journal",
            "citationCount": 10,
            "influentialCitationCount": 2,
            "referenceCount": 5,
            "openAccessPdf": {"url": "https://example.com/paper.pdf"},
            "externalIds": {"DOI": "10.1234/test", "ArXiv": "2401.00001"},
            "authors": [
                {"authorId": "a1", "name": "John Doe", "affiliations": ["MIT"]},
                {"authorId": "a2", "name": "Jane Smith", "affiliations": []},
            ],
            "fieldsOfStudy": ["Computer Science", "Education"],
            "publicationTypes": ["JournalArticle"],
            "tldr": {"text": "Summary of the paper"},
            "embedding": {"vector": [0.1, 0.2, 0.3]},
        }

        paper = SemanticScholarPaper.from_api_response(data)

        assert paper.paper_id == "abc123"
        assert paper.title == "Test Paper"
        assert paper.abstract == "This is a test abstract."
        assert paper.year == 2024
        assert paper.citation_count == 10
        assert paper.is_open_access is True
        assert paper.doi == "10.1234/test"
        assert paper.arxiv_id == "2401.00001"
        assert len(paper.authors) == 2
        assert paper.embedding == [0.1, 0.2, 0.3]
        assert paper.tldr == "Summary of the paper"


class TestSemanticScholarClient:
    """Test SemanticScholarClient."""

    @pytest.mark.asyncio
    async def test_search_papers_mocked(self):
        """Test paper search with mocked response."""
        mock_response = {
            "data": [
                {
                    "paperId": "paper1",
                    "title": "Machine Learning in Education",
                    "year": 2024,
                    "citationCount": 50,
                }
            ]
        }

        with patch.object(SemanticScholarClient, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with SemanticScholarClient() as client:
                papers = await client.search_papers("machine learning education", limit=10)

            assert len(papers) == 1
            assert papers[0].title == "Machine Learning in Education"

    @pytest.mark.asyncio
    async def test_get_paper_mocked(self):
        """Test getting a single paper with mocked response."""
        mock_response = {
            "paperId": "abc123",
            "title": "Test Paper",
            "year": 2024,
        }

        with patch.object(SemanticScholarClient, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with SemanticScholarClient() as client:
                paper = await client.get_paper("abc123")

            assert paper is not None
            assert paper.paper_id == "abc123"
            assert paper.title == "Test Paper"

    @pytest.mark.asyncio
    async def test_get_references_mocked(self):
        """Test getting paper references with mocked response."""
        mock_response = {
            "data": [
                {"citedPaper": {"paperId": "ref1", "title": "Reference 1"}},
                {"citedPaper": {"paperId": "ref2", "title": "Reference 2"}},
            ]
        }

        with patch.object(SemanticScholarClient, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with SemanticScholarClient() as client:
                refs = await client.get_references("paper1")

            assert len(refs) == 2
            assert refs[0].paper_id == "ref1"

    @pytest.mark.asyncio
    async def test_get_citations_mocked(self):
        """Test getting paper citations with mocked response."""
        mock_response = {
            "data": [
                {"citingPaper": {"paperId": "cite1", "title": "Citation 1"}},
            ]
        }

        with patch.object(SemanticScholarClient, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with SemanticScholarClient() as client:
                cites = await client.get_citations("paper1")

            assert len(cites) == 1
            assert cites[0].paper_id == "cite1"


# ==================== OpenAlex Tests ====================

class TestOpenAlexWork:
    """Test OpenAlexWork model."""

    def test_from_api_response(self):
        """Test parsing API response."""
        data = {
            "id": "W123456",
            "title": "Test Work",
            "display_name": "Test Work Display",
            "publication_year": 2024,
            "publication_date": "2024-01-15",
            "type": "journal-article",
            "cited_by_count": 25,
            "referenced_works_count": 30,
            "open_access": {
                "is_oa": True,
                "oa_status": "gold",
                "oa_url": "https://example.com/paper.pdf",
            },
            "ids": {
                "doi": "https://doi.org/10.1234/test",
                "pmid": "12345678",
            },
            "authorships": [
                {
                    "author": {
                        "id": "A123",
                        "display_name": "John Doe",
                        "orcid": "0000-0001-2345-6789",
                    },
                    "institutions": [
                        {"id": "I123", "display_name": "MIT", "country_code": "US"}
                    ],
                    "author_position": "first",
                }
            ],
            "concepts": [
                {"id": "C1", "display_name": "Machine Learning", "level": 1, "score": 0.95}
            ],
            "topics": [
                {"id": "T1", "display_name": "AI in Education", "score": 0.88}
            ],
        }

        work = OpenAlexWork.from_api_response(data)

        assert work.id == "W123456"
        assert work.title == "Test Work"
        assert work.publication_year == 2024
        assert work.is_open_access is True
        assert work.open_access_status == "gold"
        assert work.citation_count == 25
        assert len(work.authors) == 1
        assert work.authors[0]["display_name"] == "John Doe"
        assert len(work.concepts) == 1

    def test_reconstruct_abstract(self):
        """Test abstract reconstruction from inverted index."""
        inverted_index = {
            "This": [0],
            "is": [1],
            "a": [2],
            "test": [3],
            "abstract": [4],
        }

        abstract = OpenAlexWork._reconstruct_abstract(inverted_index)
        assert abstract == "This is a test abstract"


class TestOpenAlexClient:
    """Test OpenAlexClient."""

    @pytest.mark.asyncio
    async def test_search_works_mocked(self):
        """Test works search with mocked response."""
        mock_response = {
            "results": [
                {
                    "id": "W123",
                    "title": "AI in Education",
                    "publication_year": 2024,
                }
            ]
        }

        with patch.object(OpenAlexClient, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with OpenAlexClient(email="test@example.com") as client:
                works = await client.search_works("AI education")

            assert len(works) == 1
            assert works[0].id == "W123"

    @pytest.mark.asyncio
    async def test_get_work_mocked(self):
        """Test getting a single work with mocked response."""
        mock_response = {
            "id": "W123",
            "title": "Test Work",
            "publication_year": 2024,
        }

        with patch.object(OpenAlexClient, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with OpenAlexClient() as client:
                work = await client.get_work("W123")

            assert work is not None
            assert work.id == "W123"


# ==================== Zotero Tests ====================

class TestZoteroItem:
    """Test ZoteroItem model."""

    def test_from_api_response(self):
        """Test parsing API response."""
        data = {
            "key": "ABC123",
            "version": 1,
            "data": {
                "itemType": "journalArticle",
                "title": "Test Article",
                "abstractNote": "This is a test abstract.",
                "date": "2024-01-15",
                "DOI": "10.1234/test",
                "url": "https://example.com",
                "creators": [
                    {"creatorType": "author", "firstName": "John", "lastName": "Doe"},
                ],
                "publicationTitle": "Test Journal",
                "volume": "10",
                "issue": "2",
                "pages": "100-110",
                "tags": [{"tag": "machine learning"}],
                "collections": ["COL123"],
            },
        }

        item = ZoteroItem.from_api_response(data)

        assert item.key == "ABC123"
        assert item.version == 1
        assert item.item_type == "journalArticle"
        assert item.title == "Test Article"
        assert item.year == 2024
        assert item.doi == "10.1234/test"
        assert len(item.creators) == 1

    def test_to_api_format(self):
        """Test converting to API format."""
        item = ZoteroItem(
            key="",
            version=0,
            item_type="journalArticle",
            title="New Article",
            abstract="Test abstract",
            doi="10.1234/new",
            creators=[{"creatorType": "author", "firstName": "Jane", "lastName": "Doe"}],
            tags=[{"tag": "test"}],
        )

        data = item.to_api_format()

        assert data["itemType"] == "journalArticle"
        assert data["title"] == "New Article"
        assert data["abstractNote"] == "Test abstract"
        assert data["DOI"] == "10.1234/new"
        assert len(data["creators"]) == 1


class TestZoteroClient:
    """Test ZoteroClient."""

    @pytest.mark.asyncio
    async def test_get_collections_mocked(self):
        """Test getting collections with mocked response."""
        mock_response = [
            {
                "key": "COL1",
                "version": 1,
                "data": {"name": "My Collection"},
                "meta": {"numItems": 10},
            }
        ]

        with patch.object(ZoteroClient, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = (mock_response, {})

            async with ZoteroClient("api_key", user_id="12345") as client:
                collections = await client.get_collections()

            assert len(collections) == 1
            assert collections[0].name == "My Collection"

    @pytest.mark.asyncio
    async def test_get_items_mocked(self):
        """Test getting items with mocked response."""
        mock_response = [
            {
                "key": "ITEM1",
                "version": 1,
                "data": {
                    "itemType": "journalArticle",
                    "title": "Test Paper",
                },
            }
        ]

        with patch.object(ZoteroClient, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = (mock_response, {})

            async with ZoteroClient("api_key", user_id="12345") as client:
                items = await client.get_items()

            assert len(items) == 1
            assert items[0].title == "Test Paper"

    @pytest.mark.asyncio
    async def test_import_collection_to_project(self):
        """Test importing collection to ScholaRAG format."""
        mock_items = [
            ZoteroItem(
                key="ITEM1",
                version=1,
                item_type="journalArticle",
                title="Test Paper",
                abstract="Abstract text",
                year=2024,
                doi="10.1234/test",
                creators=[
                    {"creatorType": "author", "firstName": "John", "lastName": "Doe"},
                ],
                publication_title="Test Journal",
                tags=[{"tag": "AI"}],
            )
        ]

        with patch.object(ZoteroClient, "get_items_all", new_callable=AsyncMock) as mock_get_items:
            mock_get_items.return_value = mock_items

            async with ZoteroClient("api_key", user_id="12345") as client:
                papers = await client.import_collection_to_project("COL123")

            assert len(papers) == 1
            assert papers[0]["title"] == "Test Paper"
            assert papers[0]["authors"] == ["John Doe"]
            assert papers[0]["doi"] == "10.1234/test"


# ==================== Integration Tests (require API access) ====================

@pytest.mark.skip(reason="Requires actual API access")
class TestSemanticScholarLive:
    """Live integration tests for Semantic Scholar API."""

    @pytest.mark.asyncio
    async def test_search_papers_live(self):
        """Test live paper search."""
        async with SemanticScholarClient() as client:
            papers = await client.search_papers("machine learning", limit=5)
            assert len(papers) > 0
            assert all(p.title for p in papers)

    @pytest.mark.asyncio
    async def test_get_paper_by_doi_live(self):
        """Test getting paper by DOI."""
        async with SemanticScholarClient() as client:
            # Famous paper DOI
            paper = await client.get_paper("DOI:10.1038/nature14539")
            assert paper is not None
            assert "deep learning" in paper.title.lower()


@pytest.mark.skip(reason="Requires actual API access")
class TestOpenAlexLive:
    """Live integration tests for OpenAlex API."""

    @pytest.mark.asyncio
    async def test_search_works_live(self):
        """Test live works search."""
        async with OpenAlexClient(email="test@example.com") as client:
            works = await client.search_works("machine learning", per_page=5)
            assert len(works) > 0

    @pytest.mark.asyncio
    async def test_get_work_by_doi_live(self):
        """Test getting work by DOI."""
        async with OpenAlexClient() as client:
            work = await client.get_work("https://doi.org/10.1038/nature14539")
            assert work is not None


# ==================== v0.14.0: get_effective_api_key Tests ====================

# Import the function we're testing
from routers.integrations import get_effective_api_key


@pytest.mark.asyncio
async def test_get_effective_api_key_user_key_priority():
    """User API key should take priority over server fallback."""
    mock_user = MagicMock()
    mock_user.id = "user-123"

    with patch("routers.integrations.db") as mock_db:
        mock_db.fetch_one = AsyncMock(return_value={
            "preferences": {"api_keys": {"semantic_scholar": "user-key-abc"}}
        })

        result = await get_effective_api_key(mock_user, "semantic_scholar", "server-key-xyz")
        assert result == "user-key-abc"


@pytest.mark.asyncio
async def test_get_effective_api_key_fallback_when_no_user():
    """Should return fallback when no user is authenticated."""
    result = await get_effective_api_key(None, "semantic_scholar", "server-key-xyz")
    assert result == "server-key-xyz"


@pytest.mark.asyncio
async def test_get_effective_api_key_fallback_when_no_user_key():
    """Should return fallback when user has no key for this provider."""
    mock_user = MagicMock()
    mock_user.id = "user-123"

    with patch("routers.integrations.db") as mock_db:
        mock_db.fetch_one = AsyncMock(return_value={
            "preferences": {"api_keys": {}}
        })

        result = await get_effective_api_key(mock_user, "semantic_scholar", "server-key-xyz")
        assert result == "server-key-xyz"


@pytest.mark.asyncio
async def test_get_effective_api_key_fallback_when_empty_user_key():
    """Should return fallback when user key is empty string."""
    mock_user = MagicMock()
    mock_user.id = "user-123"

    with patch("routers.integrations.db") as mock_db:
        mock_db.fetch_one = AsyncMock(return_value={
            "preferences": {"api_keys": {"semantic_scholar": ""}}
        })

        result = await get_effective_api_key(mock_user, "semantic_scholar", "server-key-xyz")
        assert result == "server-key-xyz"


@pytest.mark.asyncio
async def test_get_effective_api_key_fallback_when_no_preferences():
    """Should return fallback when user profile has no preferences."""
    mock_user = MagicMock()
    mock_user.id = "user-123"

    with patch("routers.integrations.db") as mock_db:
        mock_db.fetch_one = AsyncMock(return_value={"preferences": None})

        result = await get_effective_api_key(mock_user, "semantic_scholar", "server-key-xyz")
        assert result == "server-key-xyz"


@pytest.mark.asyncio
async def test_get_effective_api_key_fallback_when_db_error():
    """Should return fallback gracefully when DB query fails."""
    mock_user = MagicMock()
    mock_user.id = "user-123"

    with patch("routers.integrations.db") as mock_db:
        mock_db.fetch_one = AsyncMock(side_effect=Exception("DB connection error"))

        result = await get_effective_api_key(mock_user, "semantic_scholar", "server-key-xyz")
        assert result == "server-key-xyz"


@pytest.mark.asyncio
async def test_get_effective_api_key_none_fallback():
    """Should return None when no user and no fallback."""
    result = await get_effective_api_key(None, "semantic_scholar", None)
    assert result is None
