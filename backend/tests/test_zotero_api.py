"""
API endpoint tests for Zotero import
"""

import pytest
from httpx import AsyncClient, ASGITransport
import tempfile
import os
from pathlib import Path

# Sample Zotero RDF export content
SAMPLE_RDF = """<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:bib="http://purl.org/net/biblio#"
    xmlns:foaf="http://xmlns.com/foaf/0.1/">

    <bib:Article rdf:about="#item_TEST001">
        <dc:title>Test Article for API Testing</dc:title>
        <dcterms:abstract>This is a test abstract for API testing.</dcterms:abstract>
        <dc:date>2024</dc:date>
        <bib:authors>
            <rdf:Seq>
                <rdf:li>
                    <foaf:Person>
                        <foaf:surname>Test</foaf:surname>
                        <foaf:givenName>Author</foaf:givenName>
                    </foaf:Person>
                </rdf:li>
            </rdf:Seq>
        </bib:authors>
    </bib:Article>
</rdf:RDF>
"""


@pytest.fixture
def sample_rdf_file():
    """Create a temporary RDF file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.rdf', delete=False) as f:
        f.write(SAMPLE_RDF)
        f.flush()
        yield f.name
    os.unlink(f.name)


class TestZoteroValidateAPI:
    """Test the Zotero validation API endpoint."""

    @pytest.mark.asyncio
    async def test_validate_with_rdf_file(self, sample_rdf_file):
        """Test validation endpoint with a valid RDF file."""
        from main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Read the RDF file
            with open(sample_rdf_file, 'rb') as f:
                rdf_content = f.read()

            # Send validation request
            response = await client.post(
                "/api/import/zotero/validate",
                files=[("files", ("test.rdf", rdf_content, "application/rdf+xml"))],
            )

            assert response.status_code == 200
            data = response.json()

            assert data["valid"] is True
            assert data["items_count"] == 1
            assert len(data["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_without_rdf(self):
        """Test validation fails without RDF file."""
        from main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Send validation request without files
            response = await client.post(
                "/api/import/zotero/validate",
                files=[("files", ("test.pdf", b"%PDF-1.4 dummy", "application/pdf"))],
            )

            assert response.status_code == 200
            data = response.json()

            assert data["valid"] is False
            assert len(data["errors"]) > 0


class TestZoteroImportAPI:
    """Test the Zotero import API endpoint."""

    @pytest.mark.asyncio
    async def test_import_creates_job(self, sample_rdf_file):
        """Test that import endpoint creates a job."""
        from main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Read the RDF file
            with open(sample_rdf_file, 'rb') as f:
                rdf_content = f.read()

            # Send import request
            response = await client.post(
                "/api/import/zotero",
                files=[("files", ("test.rdf", rdf_content, "application/rdf+xml"))],
                params={
                    "project_name": "Test Zotero Import",
                    "extract_concepts": "false",
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert "job_id" in data
            assert data["status"] == "pending"
            assert data["items_count"] >= 0

    @pytest.mark.asyncio
    async def test_import_rejects_no_rdf(self):
        """Test import rejects request without RDF file."""
        from main import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Send import request without RDF
            response = await client.post(
                "/api/import/zotero",
                files=[("files", ("test.pdf", b"%PDF-1.4 dummy", "application/pdf"))],
            )

            assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
