"""
Zotero RDF Export Importer - Import Zotero exported folders with RDF + PDF files

This importer processes Zotero's "Export with Files" output, which contains:
- A .rdf file with metadata in RDF/XML format
- A files/ subdirectory with PDFs organized by item key

Advantages over API integration:
- No API key required
- Drag & drop friendly for researchers
- Works offline
- Complete PDF access without permission issues

Process:
1. Parse RDF/XML file for bibliographic metadata
2. Map PDFs from files/{item_key}/filename.pdf structure
3. Extract text from PDFs using PyMuPDF
4. Use LLM to extract concepts, methods, findings
5. Build concept-centric knowledge graph
"""

import logging
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

import fitz  # PyMuPDF

from database import Database
from graph.graph_store import GraphStore
from graph.entity_extractor import EntityExtractor, ExtractedEntity, EntityType
from graph.relationship_builder import ConceptCentricRelationshipBuilder

logger = logging.getLogger(__name__)

# RDF Namespaces used by Zotero
NAMESPACES = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'z': 'http://www.zotero.org/namespaces/export#',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
    'bib': 'http://purl.org/net/biblio#',
    'foaf': 'http://xmlns.com/foaf/0.1/',
    'link': 'http://purl.org/rss/1.0/modules/link/',
    'prism': 'http://prismstandard.org/namespaces/1.2/basic/',
}


@dataclass
class ImportProgress:
    """Track import progress for UI updates."""
    status: str = "pending"
    progress: float = 0.0
    message: str = ""
    papers_processed: int = 0
    papers_total: int = 0
    pdfs_found: int = 0
    pdfs_processed: int = 0
    concepts_extracted: int = 0
    relationships_created: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class ZoteroItem:
    """Parsed Zotero item from RDF."""
    item_key: str
    item_type: str
    title: str
    abstract: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    pdf_paths: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class ZoteroRDFImporter:
    """
    Import Zotero exported folders (RDF + Files) into ScholaRAG_Graph.

    Designed for researchers who want to:
    1. Export their Zotero collection with "Export Files" checked
    2. Upload the folder to ScholaRAG_Graph
    3. Automatically build a concept-centric knowledge graph
    """

    def __init__(
        self,
        llm_provider=None,
        llm_model: str = "claude-3-5-haiku-20241022",
        db_connection: Optional[Database] = None,
        graph_store: Optional[GraphStore] = None,
        progress_callback: Optional[Callable[[ImportProgress], None]] = None,
    ):
        self.llm = llm_provider
        self.llm_model = llm_model
        self.db = db_connection
        self.graph_store = graph_store
        self.progress_callback = progress_callback
        self.progress = ImportProgress()

        # Initialize processors
        self.entity_extractor = EntityExtractor(llm_provider=llm_provider)
        self.relationship_builder = ConceptCentricRelationshipBuilder(llm_provider=llm_provider)

        # Cache for deduplication
        self._concept_cache: Dict[str, dict] = {}

    def _update_progress(
        self,
        status: str = None,
        progress: float = None,
        message: str = None,
    ):
        """Update and broadcast progress."""
        if status:
            self.progress.status = status
        if progress is not None:
            self.progress.progress = progress
        if message:
            self.progress.message = message

        if self.progress_callback:
            self.progress_callback(self.progress)

        logger.info(f"[{self.progress.status}] {self.progress.progress:.0%} - {self.progress.message}")

    def _parse_rdf_file(self, rdf_path: Path) -> List[ZoteroItem]:
        """Parse Zotero RDF/XML export file."""
        items = []

        try:
            tree = ET.parse(rdf_path)
            root = tree.getroot()

            # Find all bibliographic items
            # Zotero exports items as various types: bib:Article, bib:Book, etc.
            for item_type in ['Article', 'Book', 'BookSection', 'ConferencePaper',
                             'JournalArticle', 'Report', 'Thesis', 'Document']:
                for elem in root.findall(f'.//bib:{item_type}', NAMESPACES):
                    item = self._parse_item_element(elem, item_type)
                    if item and item.title:
                        items.append(item)

            # Also check for z:* item types (Zotero-specific)
            for elem in root.findall('.//z:Attachment', NAMESPACES):
                # Skip standalone attachments
                continue

            logger.info(f"Parsed {len(items)} items from RDF file")

        except ET.ParseError as e:
            logger.error(f"RDF parse error: {e}")
            self.progress.errors.append(f"RDF 파싱 오류: {e}")
        except Exception as e:
            logger.error(f"Error parsing RDF: {e}")
            self.progress.errors.append(f"RDF 처리 오류: {e}")

        return items

    def _parse_item_element(self, elem: ET.Element, item_type: str) -> Optional[ZoteroItem]:
        """Parse a single item element from RDF."""
        try:
            # Get item key from rdf:about attribute
            about = elem.get(f'{{{NAMESPACES["rdf"]}}}about', '')
            item_key = about.split('#')[-1] if '#' in about else str(uuid4())[:8]

            # Parse title
            title_elem = elem.find('dc:title', NAMESPACES)
            title = title_elem.text if title_elem is not None else None

            if not title:
                return None

            item = ZoteroItem(
                item_key=item_key,
                item_type=item_type,
                title=title.strip(),
            )

            # Abstract
            abstract_elem = elem.find('dcterms:abstract', NAMESPACES)
            if abstract_elem is not None and abstract_elem.text:
                item.abstract = abstract_elem.text.strip()

            # Authors
            for creator in elem.findall('.//foaf:Person', NAMESPACES):
                surname = creator.find('foaf:surname', NAMESPACES)
                given = creator.find('foaf:givenName', NAMESPACES)
                if surname is not None:
                    name = surname.text or ""
                    if given is not None and given.text:
                        name = f"{name}, {given.text}"
                    item.authors.append(name)

            # Also check bib:authors structure
            for author_elem in elem.findall('.//bib:authors//rdf:Seq/rdf:li', NAMESPACES):
                person = author_elem.find('.//foaf:Person', NAMESPACES)
                if person is not None:
                    surname = person.find('foaf:surname', NAMESPACES)
                    given = person.find('foaf:givenName', NAMESPACES)
                    if surname is not None:
                        name = surname.text or ""
                        if given is not None and given.text:
                            name = f"{name}, {given.text}"
                        if name and name not in item.authors:
                            item.authors.append(name)

            # Year/Date
            date_elem = elem.find('dc:date', NAMESPACES)
            if date_elem is not None and date_elem.text:
                year_match = re.search(r'(\d{4})', date_elem.text)
                if year_match:
                    item.year = int(year_match.group(1))

            # DOI
            doi_elem = elem.find('dc:identifier', NAMESPACES)
            if doi_elem is not None and doi_elem.text:
                if 'doi' in doi_elem.text.lower():
                    # Extract DOI from various formats
                    doi_match = re.search(r'10\.\d{4,}/[^\s]+', doi_elem.text)
                    if doi_match:
                        item.doi = doi_match.group(0)

            # Also check dcterms:DOI
            for identifier in elem.findall('.//dcterms:identifier', NAMESPACES):
                if identifier.text and '10.' in identifier.text:
                    doi_match = re.search(r'10\.\d{4,}/[^\s]+', identifier.text)
                    if doi_match:
                        item.doi = doi_match.group(0)
                        break

            # URL
            url_elem = elem.find('dc:identifier', NAMESPACES)
            if url_elem is not None and url_elem.text:
                if url_elem.text.startswith('http'):
                    item.url = url_elem.text

            # Journal info (for articles)
            journal_elem = elem.find('.//dcterms:isPartOf', NAMESPACES)
            if journal_elem is not None:
                journal_title = journal_elem.find('.//dc:title', NAMESPACES)
                if journal_title is not None:
                    item.journal = journal_title.text

            # Volume, Issue, Pages
            volume_elem = elem.find('prism:volume', NAMESPACES)
            if volume_elem is not None:
                item.volume = volume_elem.text

            issue_elem = elem.find('prism:number', NAMESPACES)
            if issue_elem is not None:
                item.issue = issue_elem.text

            pages_elem = elem.find('bib:pages', NAMESPACES)
            if pages_elem is not None:
                item.pages = pages_elem.text

            # Tags/Keywords
            for subject in elem.findall('dc:subject', NAMESPACES):
                if subject.text:
                    item.tags.append(subject.text.strip())

            # Linked PDFs (resource references)
            for link in elem.findall('.//link:link', NAMESPACES):
                href = link.get(f'{{{NAMESPACES["rdf"]}}}resource', '')
                if href and '.pdf' in href.lower():
                    item.pdf_paths.append(href)

            return item

        except Exception as e:
            logger.warning(f"Error parsing item element: {e}")
            return None

    def _find_pdf_files(self, export_folder: Path, items: List[ZoteroItem]) -> Dict[str, str]:
        """
        Map item keys to PDF file paths.

        Zotero export structure:
        - export_folder/
          - *.rdf (metadata)
          - files/
            - {item_key}/
              - filename.pdf
        """
        pdf_map: Dict[str, str] = {}
        files_dir = export_folder / "files"

        if not files_dir.exists():
            logger.warning(f"Files directory not found: {files_dir}")
            return pdf_map

        # Build a map of item keys to look for
        item_keys = {item.item_key: item for item in items}

        # Scan files directory
        for subdir in files_dir.iterdir():
            if subdir.is_dir():
                # The subdirectory name is often the item key or a numeric ID
                subdir_name = subdir.name

                # Look for PDFs in this subdirectory
                for pdf_file in subdir.glob("*.pdf"):
                    # Try to match to an item
                    # First, try direct key match
                    if subdir_name in item_keys:
                        pdf_map[subdir_name] = str(pdf_file)
                        self.progress.pdfs_found += 1
                        continue

                    # Try to match by filename to title
                    pdf_basename = pdf_file.stem.lower().replace("_", " ").replace("-", " ")
                    for item_key, item in item_keys.items():
                        if item_key not in pdf_map:
                            # Fuzzy match on title
                            title_lower = item.title.lower()
                            if self._fuzzy_match(pdf_basename, title_lower):
                                pdf_map[item_key] = str(pdf_file)
                                self.progress.pdfs_found += 1
                                break

                    # If still no match, use directory name as key
                    if subdir_name not in pdf_map:
                        pdf_map[subdir_name] = str(pdf_file)
                        self.progress.pdfs_found += 1

        logger.info(f"Found {len(pdf_map)} PDFs for {len(items)} items")
        return pdf_map

    def _fuzzy_match(self, s1: str, s2: str, threshold: float = 0.6) -> bool:
        """Simple fuzzy string matching based on word overlap."""
        words1 = set(s1.split())
        words2 = set(s2.split())

        if not words1 or not words2:
            return False

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) >= threshold

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using PyMuPDF."""
        try:
            doc = fitz.open(pdf_path)
            text_parts = []

            for page in doc:
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)

            doc.close()
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            return ""

    async def validate_folder(self, folder_path: str) -> Dict[str, Any]:
        """
        Validate a Zotero export folder.

        Returns validation results including:
        - Whether RDF file exists
        - Number of items found
        - PDF availability status
        """
        folder = Path(folder_path)

        validation = {
            "valid": False,
            "folder_path": str(folder),
            "rdf_file": None,
            "items_count": 0,
            "pdfs_available": 0,
            "has_files_dir": False,
            "errors": [],
            "warnings": [],
        }

        if not folder.exists():
            validation["errors"].append(f"폴더가 존재하지 않습니다: {folder}")
            return validation

        # Find RDF file (search recursively in case of nested folder structure)
        rdf_files = list(folder.glob("**/*.rdf"))
        if not rdf_files:
            validation["errors"].append("RDF 파일을 찾을 수 없습니다. Zotero에서 RDF 형식으로 내보내기 해주세요.")
            return validation

        validation["rdf_file"] = str(rdf_files[0])
        rdf_parent = rdf_files[0].parent  # Get the folder containing the RDF file

        # Parse RDF to count items
        items = self._parse_rdf_file(rdf_files[0])
        validation["items_count"] = len(items)

        if len(items) == 0:
            validation["errors"].append("RDF 파일에서 항목을 찾을 수 없습니다.")
            return validation

        # Check for files directory (relative to RDF file location)
        files_dir = rdf_parent / "files"
        validation["has_files_dir"] = files_dir.exists()

        if not files_dir.exists():
            validation["warnings"].append(
                "'files' 폴더가 없습니다. Zotero 내보내기 시 'Export Files' 옵션을 체크해주세요."
            )
        else:
            # Count available PDFs - use rdf_parent (not folder) since files/ is relative to RDF
            pdf_map = self._find_pdf_files(rdf_parent, items)
            validation["pdfs_available"] = len(pdf_map)

            if len(pdf_map) < len(items):
                validation["warnings"].append(
                    f"{len(items)}개 항목 중 {len(pdf_map)}개의 PDF만 발견되었습니다."
                )

        validation["valid"] = True
        return validation

    async def import_folder(
        self,
        folder_path: str,
        project_name: Optional[str] = None,
        research_question: Optional[str] = None,
        extract_concepts: bool = True,
    ) -> Dict[str, Any]:
        """
        Import a Zotero export folder and build knowledge graph.

        Args:
            folder_path: Path to Zotero export folder
            project_name: Name for the project (optional)
            research_question: Research question for context (optional)
            extract_concepts: Whether to use LLM for concept extraction

        Returns:
            Import result with project_id, statistics, errors
        """
        self._update_progress("validating", 0.0, "폴더 검증 중...")

        # Validate folder
        folder = Path(folder_path)
        validation = await self.validate_folder(folder_path)

        if not validation["valid"]:
            return {
                "success": False,
                "errors": validation["errors"],
            }

        self._update_progress("parsing", 0.1, "RDF 메타데이터 파싱 중...")

        # Parse RDF
        rdf_path = Path(validation["rdf_file"])
        rdf_parent = rdf_path.parent  # Folder containing the RDF file
        items = self._parse_rdf_file(rdf_path)
        self.progress.papers_total = len(items)

        # Find PDFs - use rdf_parent since files/ is relative to RDF location
        self._update_progress("scanning", 0.15, "PDF 파일 스캔 중...")
        pdf_map = self._find_pdf_files(rdf_parent, items)

        # Create project
        self._update_progress("creating_project", 0.2, "프로젝트 생성 중...")

        if not project_name:
            project_name = f"Zotero Import {datetime.now().strftime('%Y-%m-%d')}"

        if not research_question:
            research_question = f"Zotero library analysis: {len(items)} papers"

        project_id = None
        if self.graph_store:
            project_id = await self.graph_store.create_project(
                name=project_name,
                description=research_question,
                config={
                    "source": "zotero_rdf",
                    "items_count": len(items),
                    "pdfs_count": len(pdf_map),
                    "import_date": datetime.now().isoformat(),
                },
            )
        else:
            project_id = str(uuid4())

        # Process items
        self._update_progress("importing", 0.25, "논문 데이터 처리 중...")

        results = {
            "success": True,
            "project_id": project_id,
            "project_name": project_name,
            "papers_imported": 0,
            "pdfs_processed": 0,
            "concepts_extracted": 0,
            "relationships_created": 0,
            "errors": [],
            "warnings": validation.get("warnings", []),
        }

        # Import each item
        for i, item in enumerate(items):
            try:
                progress_pct = 0.25 + (0.65 * (i / len(items)))
                self._update_progress(
                    "importing",
                    progress_pct,
                    f"논문 처리 중: {i+1}/{len(items)} - {item.title[:50]}..."
                )

                # Get PDF text if available
                pdf_text = ""
                if item.item_key in pdf_map:
                    pdf_path = pdf_map[item.item_key]
                    pdf_text = self.extract_text_from_pdf(pdf_path)
                    if pdf_text:
                        self.progress.pdfs_processed += 1
                        results["pdfs_processed"] += 1

                # Store paper metadata
                paper_id = None
                if self.graph_store:
                    paper_id = await self.graph_store.store_paper_metadata(
                        project_id=project_id,
                        title=item.title,
                        abstract=item.abstract or "",
                        authors=item.authors,
                        year=item.year,
                        doi=item.doi,
                        source="zotero",
                        properties={
                            "zotero_key": item.item_key,
                            "item_type": item.item_type,
                            "journal": item.journal,
                            "volume": item.volume,
                            "issue": item.issue,
                            "pages": item.pages,
                            "url": item.url,
                            "tags": item.tags,
                            "has_pdf": item.item_key in pdf_map,
                        },
                    )
                else:
                    paper_id = str(uuid4())

                self.progress.papers_processed += 1
                results["papers_imported"] += 1

                # Extract concepts if enabled
                if extract_concepts and self.llm and (item.abstract or pdf_text):
                    text_for_extraction = item.abstract or pdf_text[:4000]

                    try:
                        entities = await self.entity_extractor.extract_entities(
                            text=text_for_extraction,
                            title=item.title,
                            context=research_question,
                        )

                        # Store entities
                        for entity in entities:
                            if self.graph_store:
                                entity_id = await self.graph_store.store_entity(
                                    project_id=project_id,
                                    name=entity.name,
                                    entity_type=entity.entity_type.value,
                                    description=entity.description or "",
                                    source_paper_id=paper_id,
                                    confidence=entity.confidence,
                                    properties=entity.properties or {},
                                )

                                self.progress.concepts_extracted += 1
                                results["concepts_extracted"] += 1

                    except Exception as e:
                        logger.warning(f"Entity extraction failed for {item.title}: {e}")

            except Exception as e:
                error_msg = f"항목 처리 실패 ({item.title}): {e}"
                logger.error(error_msg)
                self.progress.errors.append(error_msg)
                results["errors"].append(error_msg)

        # Build relationships
        if extract_concepts and self.graph_store and self.progress.concepts_extracted > 0:
            self._update_progress("building_relationships", 0.92, "관계 구축 중...")

            try:
                relationship_count = await self.graph_store.build_concept_relationships(
                    project_id=project_id
                )
                self.progress.relationships_created = relationship_count
                results["relationships_created"] = relationship_count
            except Exception as e:
                logger.warning(f"Relationship building failed: {e}")

        # Create embeddings
        if self.graph_store:
            self._update_progress("embeddings", 0.96, "임베딩 생성 중...")
            try:
                await self.graph_store.create_embeddings(project_id=project_id)
            except Exception as e:
                logger.warning(f"Embedding creation failed: {e}")

        self._update_progress("complete", 1.0, "Import 완료!")

        return results

    async def import_from_upload(
        self,
        files: List[tuple],  # List of (filename, content) tuples
        project_name: Optional[str] = None,
        research_question: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import from uploaded files (for web interface).

        Args:
            files: List of (filename, bytes) tuples from upload
            project_name: Optional project name
            research_question: Optional research question

        Returns:
            Import result
        """
        import tempfile
        import shutil

        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix="zotero_import_")

        try:
            rdf_file = None

            # Save uploaded files, preserving full relative paths
            # This maintains Zotero's folder structure: files/<item_key>/paper.pdf
            for filename, content in files:
                # Security: Validate path (no absolute paths or path traversal)
                if not filename or filename.startswith("/") or ".." in filename:
                    logger.warning(f"Rejected unsafe path: {filename}")
                    continue

                # Preserve full relative path for ALL files (RDF and PDF)
                target_path = Path(temp_dir) / filename
                target_path.parent.mkdir(parents=True, exist_ok=True)

                with open(target_path, 'wb') as f:
                    f.write(content)

                if filename.lower().endswith('.rdf'):
                    rdf_file = target_path
                elif filename.lower().endswith('.pdf'):
                    logger.info(f"Saved PDF with preserved path: {target_path}")

            if not rdf_file:
                return {
                    "success": False,
                    "errors": ["RDF 파일이 업로드되지 않았습니다."],
                }

            # Import from temp directory
            result = await self.import_folder(
                folder_path=temp_dir,
                project_name=project_name,
                research_question=research_question,
            )

            return result

        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
