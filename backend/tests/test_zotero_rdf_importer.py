"""
Tests for Zotero RDF Importer
"""

import pytest
import tempfile
import os
from pathlib import Path

# Sample Zotero RDF export content
SAMPLE_RDF = """<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:z="http://www.zotero.org/namespaces/export#"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:bib="http://purl.org/net/biblio#"
    xmlns:foaf="http://xmlns.com/foaf/0.1/"
    xmlns:prism="http://prismstandard.org/namespaces/1.2/basic/">

    <bib:Article rdf:about="#item_ABC123">
        <dc:title>Deep Learning for Natural Language Processing: A Survey</dc:title>
        <dcterms:abstract>This paper presents a comprehensive survey of deep learning techniques applied to natural language processing tasks.</dcterms:abstract>
        <dc:date>2023</dc:date>
        <dc:identifier>DOI: 10.1234/example.2023.001</dc:identifier>
        <bib:authors>
            <rdf:Seq>
                <rdf:li>
                    <foaf:Person>
                        <foaf:surname>Kim</foaf:surname>
                        <foaf:givenName>Yoon</foaf:givenName>
                    </foaf:Person>
                </rdf:li>
                <rdf:li>
                    <foaf:Person>
                        <foaf:surname>Lee</foaf:surname>
                        <foaf:givenName>Jinho</foaf:givenName>
                    </foaf:Person>
                </rdf:li>
            </rdf:Seq>
        </bib:authors>
        <dc:subject>deep learning</dc:subject>
        <dc:subject>NLP</dc:subject>
        <dc:subject>transformers</dc:subject>
    </bib:Article>

    <bib:Article rdf:about="#item_DEF456">
        <dc:title>Attention Is All You Need</dc:title>
        <dcterms:abstract>We propose a new simple network architecture, the Transformer, based solely on attention mechanisms.</dcterms:abstract>
        <dc:date>2017-06-12</dc:date>
        <dc:identifier>DOI: 10.48550/arXiv.1706.03762</dc:identifier>
        <bib:authors>
            <rdf:Seq>
                <rdf:li>
                    <foaf:Person>
                        <foaf:surname>Vaswani</foaf:surname>
                        <foaf:givenName>Ashish</foaf:givenName>
                    </foaf:Person>
                </rdf:li>
            </rdf:Seq>
        </bib:authors>
        <dc:subject>attention mechanism</dc:subject>
        <dc:subject>transformer</dc:subject>
    </bib:Article>

    <bib:Book rdf:about="#item_GHI789">
        <dc:title>Speech and Language Processing</dc:title>
        <dc:date>2024</dc:date>
        <bib:authors>
            <rdf:Seq>
                <rdf:li>
                    <foaf:Person>
                        <foaf:surname>Jurafsky</foaf:surname>
                        <foaf:givenName>Daniel</foaf:givenName>
                    </foaf:Person>
                </rdf:li>
                <rdf:li>
                    <foaf:Person>
                        <foaf:surname>Martin</foaf:surname>
                        <foaf:givenName>James H.</foaf:givenName>
                    </foaf:Person>
                </rdf:li>
            </rdf:Seq>
        </bib:authors>
    </bib:Book>
</rdf:RDF>
"""


class TestZoteroRDFParser:
    """Test the RDF parsing functionality."""

    def test_parse_rdf_file(self):
        """Test parsing a valid RDF file."""
        from importers.zotero_rdf_importer import ZoteroRDFImporter

        # Create temp directory with RDF file
        with tempfile.TemporaryDirectory() as tmpdir:
            rdf_path = Path(tmpdir) / "test_export.rdf"
            rdf_path.write_text(SAMPLE_RDF, encoding="utf-8")

            importer = ZoteroRDFImporter()
            items = importer._parse_rdf_file(rdf_path)

            # Should find 3 items (2 Articles + 1 Book)
            assert len(items) == 3

            # Check first article
            article1 = next((i for i in items if "Deep Learning" in i.title), None)
            assert article1 is not None
            assert article1.item_type == "Article"
            assert len(article1.authors) == 2
            assert "Kim" in article1.authors[0]
            assert article1.year == 2023
            assert "deep learning" in article1.tags
            assert article1.abstract is not None

            # Check second article (Attention paper)
            article2 = next((i for i in items if "Attention" in i.title), None)
            assert article2 is not None
            assert article2.year == 2017
            assert "10.48550/arXiv.1706.03762" in (article2.doi or "")

            # Check book
            book = next((i for i in items if "Speech and Language" in i.title), None)
            assert book is not None
            assert book.item_type == "Book"
            assert book.year == 2024

    def test_parse_empty_rdf(self):
        """Test parsing an empty RDF file."""
        from importers.zotero_rdf_importer import ZoteroRDFImporter

        empty_rdf = """<?xml version="1.0" encoding="UTF-8"?>
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
        </rdf:RDF>
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            rdf_path = Path(tmpdir) / "empty.rdf"
            rdf_path.write_text(empty_rdf, encoding="utf-8")

            importer = ZoteroRDFImporter()
            items = importer._parse_rdf_file(rdf_path)

            assert len(items) == 0

    def test_fuzzy_match(self):
        """Test fuzzy string matching for PDF mapping."""
        from importers.zotero_rdf_importer import ZoteroRDFImporter

        importer = ZoteroRDFImporter()

        # Should match
        assert importer._fuzzy_match("deep learning nlp", "deep learning for nlp")
        assert importer._fuzzy_match("attention is all you need", "attention all you need")

        # Should not match
        assert not importer._fuzzy_match("completely different", "nothing similar")
        assert not importer._fuzzy_match("", "some text")


class TestZoteroValidation:
    """Test the folder validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_valid_folder(self):
        """Test validation of a valid Zotero export folder."""
        from importers.zotero_rdf_importer import ZoteroRDFImporter

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create RDF file
            rdf_path = Path(tmpdir) / "export.rdf"
            rdf_path.write_text(SAMPLE_RDF, encoding="utf-8")

            # Create files directory with dummy PDFs
            files_dir = Path(tmpdir) / "files"
            files_dir.mkdir()

            pdf_dir = files_dir / "ABC123"
            pdf_dir.mkdir()
            (pdf_dir / "paper.pdf").write_bytes(b"%PDF-1.4 dummy content")

            importer = ZoteroRDFImporter()
            result = await importer.validate_folder(tmpdir)

            assert result["valid"] is True
            assert result["items_count"] == 3
            assert result["pdfs_available"] >= 1
            assert result["has_files_dir"] is True
            assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_missing_rdf(self):
        """Test validation fails when RDF file is missing."""
        from importers.zotero_rdf_importer import ZoteroRDFImporter

        with tempfile.TemporaryDirectory() as tmpdir:
            importer = ZoteroRDFImporter()
            result = await importer.validate_folder(tmpdir)

            assert result["valid"] is False
            assert len(result["errors"]) > 0
            assert "RDF" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_validate_no_files_dir(self):
        """Test validation warns when files directory is missing."""
        from importers.zotero_rdf_importer import ZoteroRDFImporter

        with tempfile.TemporaryDirectory() as tmpdir:
            rdf_path = Path(tmpdir) / "export.rdf"
            rdf_path.write_text(SAMPLE_RDF, encoding="utf-8")

            importer = ZoteroRDFImporter()
            result = await importer.validate_folder(tmpdir)

            assert result["valid"] is True  # Still valid, just missing PDFs
            assert result["has_files_dir"] is False
            assert len(result["warnings"]) > 0


class TestZoteroImport:
    """Test the import functionality."""

    @pytest.mark.asyncio
    async def test_import_without_llm(self):
        """Test import without LLM (metadata only)."""
        from importers.zotero_rdf_importer import ZoteroRDFImporter

        with tempfile.TemporaryDirectory() as tmpdir:
            rdf_path = Path(tmpdir) / "export.rdf"
            rdf_path.write_text(SAMPLE_RDF, encoding="utf-8")

            # Import without LLM and without database
            importer = ZoteroRDFImporter(
                llm_provider=None,
                db_connection=None,
                graph_store=None,
            )

            result = await importer.import_folder(
                folder_path=tmpdir,
                project_name="Test Project",
                extract_concepts=False,
            )

            assert result["success"] is True
            assert result["papers_imported"] == 3
            assert result["project_name"] == "Test Project"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
