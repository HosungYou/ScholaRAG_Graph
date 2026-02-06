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

import gc
import logging
import os
import re
import time
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
from importers.semantic_chunker import SemanticChunker

logger = logging.getLogger(__name__)


# Track entities per paper for co-occurrence relationship building
@dataclass
class PaperEntities:
    """Track extracted entities for a paper (used for co-occurrence relationships)."""
    paper_id: str
    entity_ids: List[str] = field(default_factory=list)

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
    # BUG-028 Extension: Track current paper for checkpoint support
    current_paper_id: Optional[str] = None
    current_paper_index: int = 0


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
        self.semantic_chunker = SemanticChunker()

        # Cache for deduplication
        self._concept_cache: Dict[str, dict] = {}

        # Track entities per paper for co-occurrence relationship building
        self._paper_entities: Dict[str, PaperEntities] = {}

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

            # Notes (z:Note elements linked to item)
            # Zotero stores notes as separate bib:Memo elements linked via dcterms:isReferencedBy
            for note_ref in elem.findall('.//z:Note', NAMESPACES):
                note_resource = note_ref.get(f'{{{NAMESPACES["rdf"]}}}resource', '')
                if note_resource:
                    item.notes.append(note_resource)  # Store reference for later resolution
            
            # Also check inline notes (rdf:value within bib:Memo)
            for memo in elem.findall('.//bib:Memo', NAMESPACES):
                value_elem = memo.find('rdf:value', NAMESPACES)
                if value_elem is not None and value_elem.text:
                    # Strip HTML tags if present
                    note_text = re.sub(r'<[^>]+>', '', value_elem.text)
                    if note_text.strip():
                        item.notes.append(note_text.strip())

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

    def _chunk_text_for_extraction(
        self,
        text: str,
        chunk_size: int = 4000,
        overlap: int = 200,
    ) -> List[str]:
        """
        Chunk text into overlapping segments for entity extraction.

        This ensures all PDF content is processed, not just the first 4000 chars.

        Args:
            text: Full text to chunk
            chunk_size: Maximum characters per chunk
            overlap: Characters to overlap between chunks

        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            # Try to break at sentence boundary for cleaner chunks
            if end < len(text):
                # Look for sentence-ending punctuation in the last 200 chars
                search_start = max(end - 200, start)
                last_period = text.rfind('. ', search_start, end)
                last_question = text.rfind('? ', search_start, end)
                last_exclaim = text.rfind('! ', search_start, end)

                best_break = max(last_period, last_question, last_exclaim)
                if best_break > search_start:
                    end = best_break + 2  # Include the punctuation and space

            chunks.append(text[start:end])
            start = end - overlap

            # Prevent infinite loop on very small overlaps
            if start >= len(text) - overlap:
                break

        logger.debug(f"Split {len(text)} chars into {len(chunks)} chunks for extraction")
        return chunks

    async def _extract_entities_from_full_text(
        self,
        pdf_text: str,
        item: ZoteroItem,
        research_question: Optional[str] = None,
    ) -> List[ExtractedEntity]:
        """
        PERF-011: Extract entities using single API call (Abstract + Introduction).

        Optimized from multi-chunk strategy to single-call for:
        - API calls: 8-24 → 1 (87-96% reduction)
        - Time per paper: 4-5min → 30-45sec

        Strategy:
        1. Primary: Abstract (best quality summary)
        2. Secondary: PDF introduction (first 4000 chars, skip header noise)
        3. Combined text capped at 6000 chars for single API call

        Args:
            pdf_text: Full PDF text
            item: ZoteroItem with metadata (tags, notes, etc.)
            research_question: Research context for extraction

        Returns:
            List of ExtractedEntity objects
        """
        text_sources = []

        # 1. Abstract (highest priority - best summary of paper)
        if item.abstract and len(item.abstract) > 100:
            text_sources.append(("ABSTRACT", item.abstract))

        # 2. PDF Introduction (skip first 500 chars for header/title noise)
        if pdf_text and len(pdf_text) > 500:
            intro_text = pdf_text[500:4500]  # chars 500-4500 = introduction
            text_sources.append(("INTRODUCTION", intro_text))

        # Combine sources into single text (6000 char limit for single API call)
        combined_text = "\n\n".join([
            f"[{source_type}]:\n{text}" for source_type, text in text_sources
        ])[:6000]

        # Fallback: if no text available, return empty
        if not combined_text or len(combined_text) < 50:
            logger.warning(f"Insufficient text for entity extraction: '{item.title[:40]}...'")
            return []

        # Single API call for entity extraction
        try:
            entities = await self.entity_extractor.extract_entities(
                text=combined_text,
                title=item.title,
                context=research_question,
                seed_concepts=item.tags if item.tags else None,
                user_notes=item.notes if item.notes else None,
            )

            # Add metadata to entities
            for entity in entities:
                entity.properties = entity.properties or {}
                entity.properties["extraction_method"] = "abstract_intro_single_call"
                entity.properties["text_length"] = len(combined_text)

            logger.info(
                f"PERF-011: Extracted {len(entities)} entities (1 API call, "
                f"{len(combined_text)} chars) for '{item.title[:40]}...'"
            )

            return entities

        except Exception as e:
            logger.warning(f"Entity extraction failed for '{item.title[:40]}...': {e}")
            return []

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

    async def _build_cooccurrence_relationships(
        self,
        project_id: str,
    ) -> int:
        """
        Build CO_OCCURS_WITH relationships between entities that appear in the same paper.

        This method creates relationships based on co-occurrence - entities extracted
        from the same paper are considered related. This works WITHOUT embeddings,
        providing a fallback when Cohere API or other embedding services are unavailable.

        The weight of the relationship is set to 1.0 for same-paper co-occurrence.

        Args:
            project_id: Project UUID

        Returns:
            Number of relationships created
        """
        if not self.graph_store or not self._paper_entities:
            logger.info("No paper entities tracked for co-occurrence relationships")
            return 0

        relationships_created = 0
        seen_pairs = set()  # Track (entity1_id, entity2_id) pairs to avoid duplicates

        for paper_id, paper_entity_tracker in self._paper_entities.items():
            entity_ids = paper_entity_tracker.entity_ids

            # Skip papers with 0 or 1 entities (no co-occurrence possible)
            if len(entity_ids) < 2:
                continue

            # Create relationships between all pairs of entities in this paper
            for i, entity1_id in enumerate(entity_ids):
                for entity2_id in entity_ids[i + 1:]:
                    # Ensure consistent ordering for deduplication
                    pair_key = tuple(sorted([entity1_id, entity2_id]))

                    if pair_key in seen_pairs:
                        continue

                    seen_pairs.add(pair_key)

                    try:
                        await self.graph_store.add_relationship(
                            project_id=project_id,
                            source_id=entity1_id,
                            target_id=entity2_id,
                            relationship_type="CO_OCCURS_WITH",
                            properties={
                                "source_paper_id": paper_id,
                                "auto_generated": True,
                                "generation_method": "cooccurrence",
                            },
                            weight=1.0,
                        )
                        relationships_created += 1
                    except Exception as e:
                        # Log but continue - may fail due to unique constraint if relationship exists
                        logger.debug(f"Could not create co-occurrence relationship: {e}")

        logger.info(
            f"Created {relationships_created} co-occurrence relationships "
            f"from {len(self._paper_entities)} papers"
        )

        # MEM-001: Clear the tracker and force GC after building relationships
        papers_count = len(self._paper_entities)
        self._paper_entities.clear()
        gc.collect()
        logger.debug(f"MEM-001: Cleared {papers_count} paper entity trackers, GC triggered")

        return relationships_created

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
        skip_paper_ids: Optional[set] = None,
        existing_project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import a Zotero export folder and build knowledge graph.

        Args:
            folder_path: Path to Zotero export folder
            project_name: Name for the project (optional)
            research_question: Research question for context (optional)
            extract_concepts: Whether to use LLM for concept extraction
            skip_paper_ids: BUG-028 Extension - Set of paper IDs to skip (for resume)
            existing_project_id: BUG-028 Extension - Use existing project instead of creating new

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

        # Create or use existing project
        # BUG-028 Extension: Support resume with existing project
        if existing_project_id:
            self._update_progress("creating_project", 0.2, "기존 프로젝트에 재개 중...")
            project_id = existing_project_id
            logger.info(f"Resuming import to existing project: {project_id}")
        else:
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
            "chunks_created": 0,
            "errors": [],
            "warnings": validation.get("warnings", []),
        }

        # BUG-028 Extension: Initialize skip set
        skip_ids = skip_paper_ids or set()
        skipped_count = 0

        # Import each item
        for i, item in enumerate(items):
            # BUG-028 Extension: Skip already processed papers (for resume)
            if item.item_key in skip_ids:
                skipped_count += 1
                logger.debug(f"Skipping already processed paper: {item.item_key}")
                continue

            # PERF-011: Track timing for each paper to identify slow processing
            paper_start_time = time.time()

            try:
                # BUG-028 Extension: Update progress with current paper info for checkpoint
                self.progress.current_paper_id = item.item_key
                self.progress.current_paper_index = i

                progress_pct = 0.25 + (0.65 * (i / len(items)))
                self._update_progress(
                    "importing",
                    progress_pct,
                    f"논문 처리 중: {i+1}/{len(items)} - {item.title[:50]}..."
                )

                # PERF-011: Log paper processing start
                logger.info(f"PERF-011: Starting paper {i+1}/{len(items)}: '{item.title[:50]}...'")

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

                # Semantic Chunking: Create hierarchical chunks from PDF text
                if pdf_text and paper_id and self.graph_store and len(pdf_text) > 500:
                    try:
                        chunked_result = self.semantic_chunker.chunk_academic_text(
                            text=pdf_text,
                            paper_id=paper_id,
                            detect_sections=True,
                            max_chunk_tokens=400,
                        )
                        
                        if chunked_result.get("chunks"):
                            await self.graph_store.store_chunks(
                                project_id=project_id,
                                paper_id=paper_id,
                                chunks=chunked_result["chunks"],
                            )
                            if "chunks_created" not in results:
                                results["chunks_created"] = 0
                            results["chunks_created"] += len(chunked_result["chunks"])
                            logger.info(f"Created {len(chunked_result['chunks'])} chunks for {item.title[:30]}...")
                    except Exception as e:
                        logger.warning(f"Semantic chunking failed for {item.title}: {e}")

                # Extract concepts if enabled - use full PDF text with chunking
                if extract_concepts and self.llm and (item.abstract or pdf_text):
                    try:
                        # Use chunking strategy to process full PDF content
                        # instead of truncating to 4000 chars (which loses 95%+ of content)
                        entities = await self._extract_entities_from_full_text(
                            pdf_text=pdf_text,
                            item=item,
                            research_question=research_question,
                        )

                        # Track entities per paper for co-occurrence relationships
                        paper_entity_tracker = PaperEntities(paper_id=paper_id)

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

                                # Track entity ID for co-occurrence relationships
                                paper_entity_tracker.entity_ids.append(entity_id)

                                self.progress.concepts_extracted += 1
                                results["concepts_extracted"] += 1

                        # Store paper entities for later co-occurrence building
                        if paper_entity_tracker.entity_ids:
                            self._paper_entities[paper_id] = paper_entity_tracker

                    except Exception as e:
                        logger.warning(f"Entity extraction failed for {item.title}: {e}")

                # PERF-011: Log paper processing completion with timing
                paper_elapsed = time.time() - paper_start_time
                if paper_elapsed > 30.0:  # Warn if paper takes more than 30 seconds
                    logger.warning(
                        f"PERF-011: Slow paper processing: {paper_elapsed:.1f}s for "
                        f"'{item.title[:40]}...' (paper {i+1}/{len(items)})"
                    )
                else:
                    logger.info(
                        f"PERF-011: Completed paper {i+1}/{len(items)} in {paper_elapsed:.1f}s: "
                        f"'{item.title[:40]}...'"
                    )

            except Exception as e:
                error_msg = f"항목 처리 실패 ({item.title}): {e}"
                logger.error(error_msg)
                self.progress.errors.append(error_msg)
                results["errors"].append(error_msg)

            # MEM-001: Periodic memory cleanup every 5 papers
            if (i + 1) % 5 == 0:
                # Clear entity extractor cache
                self.entity_extractor.clear_cache()

                # Clear EntityDAO in-memory cache if using DB
                if self.graph_store and hasattr(self.graph_store, '_entity_dao'):
                    self.graph_store._entity_dao.clear_memory_cache()

                # Force garbage collection
                gc.collect()
                logger.info(f"MEM-001: Memory cleanup after paper {i+1}/{len(items)}")

        # Create embeddings (optional - may fail if Cohere API unavailable)
        embeddings_created = 0
        if self.graph_store and self.progress.concepts_extracted > 0:
            self._update_progress("embeddings", 0.85, "임베딩 생성 중...")
            try:
                embeddings_created = await self.graph_store.create_embeddings(project_id=project_id)
                logger.info(f"Created {embeddings_created} embeddings")
            except Exception as e:
                logger.error(f"Embedding creation failed: {e}. Gap detection will use TF-IDF fallback.")
                self._update_progress("embeddings", 0.87, "임베딩 실패 - TF-IDF 폴백 사용 예정")

        # Build relationships - ALWAYS build co-occurrence, optionally build semantic
        if extract_concepts and self.graph_store:
            total_relationships = 0

            # Step 1: Build co-occurrence relationships (NO embeddings needed)
            # Entities that appear in the same paper are related
            self._update_progress("building_relationships", 0.90, "공출현 관계 구축 중...")
            try:
                cooccurrence_count = await self._build_cooccurrence_relationships(
                    project_id=project_id
                )
                total_relationships += cooccurrence_count
                logger.info(f"Created {cooccurrence_count} co-occurrence relationships")
            except Exception as e:
                logger.warning(f"Co-occurrence relationship building failed: {e}")

            # Step 2: Build semantic relationships (ONLY if embeddings exist)
            if embeddings_created > 0:
                self._update_progress("building_relationships", 0.95, "의미적 관계 구축 중...")
                try:
                    semantic_count = await self.graph_store.build_concept_relationships(
                        project_id=project_id
                    )
                    total_relationships += semantic_count
                    logger.info(f"Created {semantic_count} semantic relationships")
                except Exception as e:
                    logger.warning(f"Semantic relationship building failed: {e}")
            else:
                logger.info("Skipping semantic relationships (no embeddings available)")

            self.progress.relationships_created = total_relationships
            results["relationships_created"] = total_relationships

        # Phase: Clustering + Gap Detection + Centrality (v0.11.0)
        if self.graph_store and results.get("concepts_extracted", 0) >= 10:
            self._update_progress("analyzing", 0.97, "클러스터링 및 갭 분석 중...")
            try:
                from graph.gap_detector import GapDetector

                gap_detector = GapDetector()

                pid = project_id if isinstance(project_id, __import__('uuid').UUID) \
                    else __import__('uuid').UUID(project_id)

                # Fetch Concept entities with embeddings from DB
                concept_rows = await self.db.fetch(
                    """
                    SELECT id::text, name, embedding
                    FROM entities
                    WHERE project_id = $1 AND entity_type::text = 'Concept'
                    AND embedding IS NOT NULL
                    """,
                    pid
                )

                concepts_for_gap = []
                for r in concept_rows:
                    emb = r["embedding"]
                    if emb is not None:
                        # Handle pgvector embedding format
                        if isinstance(emb, str):
                            emb_list = [float(x) for x in emb.strip("[]").split(",")]
                        elif isinstance(emb, (list, tuple)):
                            emb_list = [float(x) for x in emb]
                        else:
                            continue
                        concepts_for_gap.append({
                            "id": r["id"],
                            "name": r["name"],
                            "embedding": emb_list,
                        })

                # TF-IDF fallback: if no embeddings available, generate pseudo-embeddings
                if len(concepts_for_gap) < 10:
                    logger.warning(
                        f"Only {len(concepts_for_gap)} concepts with embeddings "
                        f"(need 10+). Using TF-IDF fallback for clustering."
                    )
                    # Fetch ALL concepts (including those without embeddings)
                    all_concept_rows = await self.db.fetch(
                        """
                        SELECT id::text, name
                        FROM entities
                        WHERE project_id = $1 AND entity_type::text = 'Concept'
                        """,
                        pid
                    )

                    if len(all_concept_rows) >= 10:
                        try:
                            from sklearn.feature_extraction.text import TfidfVectorizer

                            concept_names = [r["name"] for r in all_concept_rows]
                            vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
                            tfidf_matrix = vectorizer.fit_transform(concept_names)

                            concepts_for_gap = []
                            for i, r in enumerate(all_concept_rows):
                                tfidf_vec = tfidf_matrix[i].toarray()[0].tolist()
                                concepts_for_gap.append({
                                    "id": r["id"],
                                    "name": r["name"],
                                    "embedding": tfidf_vec,
                                })
                            logger.info(f"TF-IDF fallback: generated {len(concepts_for_gap)} pseudo-embeddings")
                        except Exception as tfidf_err:
                            logger.error(f"TF-IDF fallback failed: {tfidf_err}")

                # Fetch relationships
                rel_rows = await self.db.fetch(
                    """
                    SELECT source_id::text, target_id::text FROM relationships
                    WHERE project_id = $1
                    """,
                    project_id if isinstance(project_id, __import__('uuid').UUID)
                    else __import__('uuid').UUID(project_id)
                )
                relationships_for_gap = [
                    {"source_id": r["source_id"], "target_id": r["target_id"]}
                    for r in rel_rows
                ]

                if len(concepts_for_gap) >= 10:
                    gap_analysis = await gap_detector.analyze_graph(
                        concepts=concepts_for_gap,
                        relationships=relationships_for_gap,
                    )

                    def _get_cluster_label(c):
                        """Get meaningful cluster label, avoiding UUIDs."""
                        if c.name and len(c.name) < 100 and not (len(c.name) == 36 and c.name.count('-') == 4):
                            return c.name
                        if c.keywords:
                            return " / ".join(c.keywords[:3])
                        return f"Cluster {c.id + 1}"

                    # Store clusters
                    for cluster in gap_analysis.get("clusters", []):
                        try:
                            await self.db.execute(
                                """
                                INSERT INTO concept_clusters (
                                    id, project_id, name, color, concept_count, keywords
                                ) VALUES ($1, $2, $3, $4, $5, $6)
                                ON CONFLICT (id) DO NOTHING
                                """,
                                cluster.id,
                                project_id if isinstance(project_id, __import__('uuid').UUID)
                                else __import__('uuid').UUID(str(project_id)),
                                _get_cluster_label(cluster)[:255],
                                cluster.color,
                                len(cluster.concept_ids),
                                cluster.keywords[:10],
                            )
                            # Update entities with cluster_id
                            for concept_id in cluster.concept_ids:
                                await self.db.execute(
                                    "UPDATE entities SET cluster_id = $1 WHERE id = $2",
                                    cluster.id,
                                    concept_id if isinstance(concept_id, __import__('uuid').UUID)
                                    else __import__('uuid').UUID(concept_id),
                                )
                        except Exception as e:
                            logger.warning(f"Failed to store cluster: {e}")

                    # Store gaps
                    for gap in gap_analysis.get("gaps", []):
                        try:
                            await self.db.execute(
                                """
                                INSERT INTO structural_gaps (
                                    id, project_id, cluster_a_id, cluster_b_id,
                                    gap_strength, concept_a_ids, concept_b_ids,
                                    suggested_bridge_concepts, suggested_research_questions, status
                                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                                ON CONFLICT (id) DO NOTHING
                                """,
                                gap.id,
                                project_id if isinstance(project_id, __import__('uuid').UUID)
                                else __import__('uuid').UUID(str(project_id)),
                                gap.cluster_a_id,
                                gap.cluster_b_id,
                                gap.gap_strength,
                                gap.concept_a_ids,
                                gap.concept_b_ids,
                                gap.bridge_concepts,
                                gap.suggested_research_questions,
                                gap.status,
                            )
                        except Exception as e:
                            logger.warning(f"Failed to store gap: {e}")

                    # Update centrality metrics
                    for metric in gap_analysis.get("centrality", []):
                        try:
                            await self.db.execute(
                                """
                                UPDATE entities SET
                                    centrality_degree = $1,
                                    centrality_betweenness = $2,
                                    centrality_pagerank = $3
                                WHERE id = $4
                                """,
                                metric.degree,
                                metric.betweenness,
                                metric.pagerank,
                                metric.entity_id,
                            )
                        except Exception as e:
                            logger.warning(f"Failed to update centrality: {e}")

                    results["gaps_detected"] = len(gap_analysis.get("gaps", []))
                    results["clusters_created"] = len(gap_analysis.get("clusters", []))
                    logger.info(f"Gap analysis complete: {results.get('gaps_detected', 0)} gaps, {results.get('clusters_created', 0)} clusters")

            except Exception as e:
                logger.warning(f"Gap analysis failed (non-critical): {e}")

        self._update_progress("complete", 1.0, "Import 완료!")

        return results


    async def sync_folder(
        self,
        folder_path: str,
        project_id: str,
        extract_concepts: bool = True,
    ) -> Dict[str, Any]:
        """
        Incrementally sync a Zotero export folder with existing project.
        
        Only processes items that are new or have been modified since last sync.
        Uses zotero_key to track items and modification timestamps for diff.
        
        Args:
            folder_path: Path to Zotero export folder
            project_id: Existing project UUID to sync with
            extract_concepts: Whether to extract concepts from new/changed items
            
        Returns:
            Sync result with statistics
        """
        self._update_progress("validating", 0.0, "동기화 준비 중...")
        
        # Validate folder
        validation = await self.validate_folder(folder_path)
        if not validation["valid"]:
            return {
                "success": False,
                "errors": validation["errors"],
            }
        
        # Parse RDF
        rdf_path = Path(validation["rdf_file"])
        items = self._parse_rdf_file(rdf_path)
        
        # Get existing items from database
        self._update_progress("comparing", 0.1, "기존 항목과 비교 중...")
        
        existing_keys = set()
        if self.db:
            try:
                rows = await self.db.fetch(
                    """
                    SELECT properties->>'zotero_key' as zotero_key
                    FROM paper_metadata
                    WHERE project_id = $1
                      AND properties->>'zotero_key' IS NOT NULL
                    """,
                    project_id if isinstance(project_id, __import__('uuid').UUID) 
                    else __import__('uuid').UUID(project_id)
                )
                existing_keys = {row["zotero_key"] for row in rows}
            except Exception as e:
                logger.warning(f"Failed to fetch existing items: {e}")
        
        # Find new items
        new_items = [item for item in items if item.item_key not in existing_keys]
        
        if not new_items:
            self._update_progress("complete", 1.0, "동기화 완료 - 새 항목 없음")
            return {
                "success": True,
                "project_id": project_id,
                "items_checked": len(items),
                "items_added": 0,
                "items_skipped": len(items),
                "message": "모든 항목이 이미 동기화되어 있습니다.",
            }
        
        logger.info(f"Found {len(new_items)} new items to sync (of {len(items)} total)")
        
        # Find PDFs
        rdf_parent = rdf_path.parent
        pdf_map = self._find_pdf_files(rdf_parent, new_items)
        
        # Process new items
        self._update_progress("syncing", 0.2, f"새 항목 {len(new_items)}개 동기화 중...")
        
        results = {
            "success": True,
            "project_id": project_id,
            "items_checked": len(items),
            "items_added": 0,
            "items_skipped": len(existing_keys),
            "pdfs_processed": 0,
            "concepts_extracted": 0,
            "relationships_created": 0,
            "errors": [],
        }
        
        for i, item in enumerate(new_items):
            try:
                progress_pct = 0.2 + (0.7 * (i / len(new_items)))
                self._update_progress(
                    "syncing",
                    progress_pct,
                    f"동기화 중: {i+1}/{len(new_items)} - {item.title[:40]}..."
                )
                
                # Get PDF text if available
                pdf_text = ""
                if item.item_key in pdf_map:
                    pdf_path = pdf_map[item.item_key]
                    pdf_text = self.extract_text_from_pdf(pdf_path)
                    if pdf_text:
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
                        source="zotero_sync",
                        properties={
                            "zotero_key": item.item_key,
                            "item_type": item.item_type,
                            "journal": item.journal,
                            "tags": item.tags,
                            "synced_at": __import__('datetime').datetime.now().isoformat(),
                        },
                    )
                
                results["items_added"] += 1
                
                # Extract concepts if enabled - use full PDF text with chunking
                if extract_concepts and self.llm and (item.abstract or pdf_text):
                    try:
                        # Use chunking strategy to process full PDF content
                        # instead of truncating to 4000 chars (which loses 95%+ of content)
                        entities = await self._extract_entities_from_full_text(
                            pdf_text=pdf_text,
                            item=item,
                            research_question=None,  # sync_folder doesn't have research_question
                        )

                        # Track entities per paper for co-occurrence relationships
                        paper_entity_tracker = PaperEntities(paper_id=paper_id)

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
                                paper_entity_tracker.entity_ids.append(entity_id)
                                results["concepts_extracted"] += 1

                        # Store paper entities for later co-occurrence building
                        if paper_entity_tracker.entity_ids:
                            self._paper_entities[paper_id] = paper_entity_tracker

                    except Exception as e:
                        logger.warning(f"Entity extraction failed for {item.title}: {e}")

            except Exception as e:
                error_msg = f"동기화 실패 ({item.title}): {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        # Create embeddings for new entities (optional - may fail)
        embeddings_created = 0
        if self.graph_store and results["concepts_extracted"] > 0:
            self._update_progress("embeddings", 0.90, "새 항목 임베딩 생성 중...")
            try:
                embeddings_created = await self.graph_store.create_embeddings(project_id=project_id)
            except Exception as e:
                logger.warning(f"Embedding creation failed (continuing with co-occurrence): {e}")

        # Build co-occurrence relationships (works without embeddings)
        if self.graph_store and results["concepts_extracted"] > 0:
            self._update_progress("building_relationships", 0.95, "관계 구축 중...")
            try:
                cooccurrence_count = await self._build_cooccurrence_relationships(
                    project_id=project_id
                )
                results["relationships_created"] = cooccurrence_count
                logger.info(f"Created {cooccurrence_count} co-occurrence relationships during sync")
            except Exception as e:
                logger.warning(f"Co-occurrence relationship building failed: {e}")

        self._update_progress("complete", 1.0, "동기화 완료!")
        
        return results

    async def get_sync_status(
        self,
        folder_path: str,
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Check sync status without making changes.
        
        Returns counts of new, existing, and modified items.
        
        Args:
            folder_path: Path to Zotero export folder
            project_id: Project UUID
            
        Returns:
            Dict with sync status information
        """
        # Validate folder
        validation = await self.validate_folder(folder_path)
        if not validation["valid"]:
            return {"success": False, "errors": validation["errors"]}
        
        # Parse RDF
        rdf_path = Path(validation["rdf_file"])
        items = self._parse_rdf_file(rdf_path)
        
        # Get existing items
        existing_keys = set()
        if self.db:
            try:
                rows = await self.db.fetch(
                    """
                    SELECT properties->>'zotero_key' as zotero_key
                    FROM paper_metadata
                    WHERE project_id = $1
                      AND properties->>'zotero_key' IS NOT NULL
                    """,
                    project_id if isinstance(project_id, __import__('uuid').UUID)
                    else __import__('uuid').UUID(project_id)
                )
                existing_keys = {row["zotero_key"] for row in rows}
            except Exception as e:
                logger.warning(f"Failed to fetch existing items: {e}")
        
        new_items = [item for item in items if item.item_key not in existing_keys]
        existing_items = [item for item in items if item.item_key in existing_keys]
        
        return {
            "success": True,
            "total_in_folder": len(items),
            "already_synced": len(existing_items),
            "new_items": len(new_items),
            "new_item_titles": [item.title for item in new_items[:10]],  # Preview
            "needs_sync": len(new_items) > 0,
        }

    async def import_from_upload(
        self,
        files: List[tuple],  # List of (filename, content) tuples
        project_name: Optional[str] = None,
        research_question: Optional[str] = None,
        skip_paper_ids: Optional[set] = None,
        existing_project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import from uploaded files (for web interface).

        Args:
            files: List of (filename, bytes) tuples from upload
            project_name: Optional project name
            research_question: Optional research question
            skip_paper_ids: BUG-028 Extension - Set of paper IDs to skip (for resume)
            existing_project_id: BUG-028 Extension - Use existing project instead of creating new

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
            # BUG-028 Extension: Pass resume parameters
            result = await self.import_folder(
                folder_path=temp_dir,
                project_name=project_name,
                research_question=research_question,
                skip_paper_ids=skip_paper_ids,
                existing_project_id=existing_project_id,
            )

            return result

        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
