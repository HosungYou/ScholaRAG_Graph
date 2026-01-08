"""
ScholaRAG Folder Importer

Imports existing ScholaRAG project folders and builds knowledge graphs.

Process:
1. Parse config.yaml and .scholarag metadata
2. Read papers from CSV files (relevant_papers.csv or all_screened_papers.csv)
3. Extract Authors from paper metadata
4. Use LLM to extract Concepts, Methods, Findings from abstracts
5. Build relationships (AUTHORED_BY, DISCUSSES_CONCEPT, etc.)
6. Store entities and relationships in PostgreSQL
"""

import asyncio
import csv
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import uuid4

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ImportProgress:
    """Track import progress for WebSocket updates."""

    status: str = "pending"
    progress: float = 0.0
    message: str = ""
    papers_processed: int = 0
    papers_total: int = 0
    entities_created: int = 0
    relationships_created: int = 0
    errors: list = field(default_factory=list)


@dataclass
class ProjectConfig:
    """Parsed ScholaRAG project configuration."""

    name: str
    research_question: str
    project_type: str
    created_date: str
    databases: list[str]
    year_range: tuple[int, int]
    inclusion_criteria: list[str]
    exclusion_criteria: list[str]


@dataclass
class PaperData:
    """Parsed paper data from CSV."""

    paper_id: str
    title: str
    abstract: str
    authors: list[str]
    year: Optional[int]
    doi: Optional[str]
    source: str
    citation_count: int
    pdf_url: Optional[str]
    properties: dict = field(default_factory=dict)


@dataclass
class ExtractedEntity:
    """Entity extracted from paper."""

    entity_type: str  # Paper, Author, Concept, Method, Finding
    name: str
    properties: dict = field(default_factory=dict)
    source_paper_id: Optional[str] = None


@dataclass
class ExtractedRelationship:
    """Relationship between entities."""

    relationship_type: str
    source_id: str
    target_id: str
    properties: dict = field(default_factory=dict)


class ScholarAGImporter:
    """
    Imports ScholaRAG project folders into ScholaRAG_Graph.
    """

    def __init__(
        self,
        llm_provider=None,
        db_connection=None,
        graph_store=None,
        progress_callback: Optional[Callable[[ImportProgress], None]] = None,
    ):
        self.llm = llm_provider
        self.db = db_connection
        self.graph_store = graph_store
        self.progress_callback = progress_callback
        self.progress = ImportProgress()

        # Entity deduplication cache: maps name -> entity_id (UUID)
        self._author_cache: dict[str, str] = {}
        self._concept_cache: dict[str, str] = {}
        self._paper_id_map: dict[str, str] = {}  # paper_id (from CSV) -> entity_id (UUID)

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

    async def validate_folder(self, folder_path: str) -> dict:
        """
        Validate a ScholaRAG project folder.

        Returns validation results with details about what was found.
        """
        folder = Path(folder_path)
        validation = {
            "valid": True,
            "folder_path": folder_path,
            "config_found": False,
            "scholarag_metadata_found": False,
            "papers_csv_found": False,
            "papers_csv_path": None,
            "papers_count": 0,
            "pdfs_count": 0,
            "chroma_db_found": False,
            "errors": [],
            "warnings": [],
        }

        # Check folder exists
        if not folder.exists():
            validation["valid"] = False
            validation["errors"].append(f"Folder not found: {folder_path}")
            return validation

        # Check config.yaml
        config_path = folder / "config.yaml"
        validation["config_found"] = config_path.exists()
        if not validation["config_found"]:
            validation["errors"].append("config.yaml not found")
            validation["valid"] = False

        # Check .scholarag metadata
        metadata_path = folder / ".scholarag"
        validation["scholarag_metadata_found"] = metadata_path.exists()
        if not validation["scholarag_metadata_found"]:
            validation["warnings"].append(".scholarag metadata not found (optional)")

        # Find papers CSV
        papers_csv_paths = [
            folder / "data" / "02_screening" / "relevant_papers.csv",
            folder / "data" / "02_screening" / "all_screened_papers.csv",
            folder / "data" / "02_screening" / "screening_progress.csv",
            folder / "data" / "01_identification" / "deduplicated.csv",
        ]

        for csv_path in papers_csv_paths:
            if csv_path.exists():
                validation["papers_csv_found"] = True
                validation["papers_csv_path"] = str(csv_path)
                # Count rows
                try:
                    with open(csv_path, "r", encoding="utf-8") as f:
                        validation["papers_count"] = sum(1 for _ in f) - 1
                except Exception as e:
                    validation["warnings"].append(f"Could not count papers: {e}")
                break

        if not validation["papers_csv_found"]:
            validation["errors"].append("No papers CSV found in data/02_screening/")
            validation["valid"] = False

        # Check PDFs
        pdfs_dir = folder / "data" / "03_pdfs"
        if pdfs_dir.exists():
            validation["pdfs_count"] = len(list(pdfs_dir.rglob("*.pdf")))
        else:
            validation["warnings"].append("No PDFs directory found")

        # Check ChromaDB
        chroma_paths = [
            folder / "data" / "04_rag" / "chroma_db",
            folder / "rag" / "chroma_db",
        ]
        for chroma_path in chroma_paths:
            if chroma_path.exists() and any(chroma_path.iterdir()):
                validation["chroma_db_found"] = True
                break

        return validation

    async def import_folder(
        self,
        folder_path: str,
        project_name: Optional[str] = None,
        extract_entities: bool = True,
    ) -> dict:
        """
        Import a ScholaRAG project folder.

        Args:
            folder_path: Path to ScholaRAG project folder
            project_name: Optional name override
            extract_entities: Whether to use LLM to extract Concept, Method, Finding

        Returns:
            Import result with project_id and statistics
        """
        folder = Path(folder_path)
        self._update_progress("validating", 0.05, "Validating folder structure...")

        # Validate
        validation = await self.validate_folder(folder_path)
        if not validation["valid"]:
            self._update_progress("failed", 0.0, "Validation failed")
            return {
                "success": False,
                "error": "Validation failed",
                "validation": validation,
            }

        try:
            # Parse config
            self._update_progress("extracting", 0.1, "Parsing configuration...")
            config = await self._parse_config(folder)

            # Create project in database
            project_id = str(uuid4())
            project_name_final = project_name or config.name
            logger.info(f"Creating project: {project_name_final} (ID: {project_id})")

            if self.db:
                try:
                    await self.db.execute(
                        """
                        INSERT INTO projects (id, name, research_question, source_path)
                        VALUES ($1, $2, $3, $4)
                        """,
                        project_id,
                        project_name_final,
                        config.research_question,
                        folder_path,
                    )
                    logger.info(f"Project created in database: {project_id}")
                except Exception as e:
                    logger.error(f"Failed to create project in database: {e}")
                    raise

            project = {
                "id": project_id,
                "name": project_name_final,
                "research_question": config.research_question,
                "source_path": folder_path,
                "created_at": datetime.now().isoformat(),
            }

            # Parse papers
            self._update_progress("extracting", 0.15, "Reading papers from CSV...")
            papers = await self._parse_papers_csv(
                Path(validation["papers_csv_path"])
            )
            self.progress.papers_total = len(papers)

            # Create entities
            self._update_progress("processing", 0.2, "Creating Paper entities...")
            all_entities: list[ExtractedEntity] = []
            all_relationships: list[ExtractedRelationship] = []

            # Process papers in batches
            batch_size = 50
            for i, paper in enumerate(papers):
                # Create Paper entity
                paper_entity = ExtractedEntity(
                    entity_type="Paper",
                    name=paper.title,
                    properties={
                        "paper_id": paper.paper_id,
                        "abstract": paper.abstract[:2000] if paper.abstract else "",
                        "year": paper.year,
                        "doi": paper.doi,
                        "source": paper.source,
                        "citation_count": paper.citation_count,
                        "pdf_url": paper.pdf_url,
                        **paper.properties,
                    },
                )
                paper_entity_id = f"paper_{paper.paper_id}"
                all_entities.append(paper_entity)

                # Extract and link Authors
                for author_name in paper.authors:
                    if not author_name.strip():
                        continue

                    author_id = self._get_or_create_author(author_name, all_entities)
                    all_relationships.append(
                        ExtractedRelationship(
                            relationship_type="AUTHORED_BY",
                            source_id=paper_entity_id,
                            target_id=author_id,
                        )
                    )

                # Extract Concepts, Methods, Findings using LLM
                if extract_entities and paper.abstract and self.llm:
                    extracted = await self._extract_entities_from_paper(paper)
                    for entity in extracted:
                        entity.source_paper_id = paper_entity_id
                        all_entities.append(entity)

                        # Create relationship
                        rel_type = self._get_relationship_type(entity.entity_type)
                        if rel_type:
                            all_relationships.append(
                                ExtractedRelationship(
                                    relationship_type=rel_type,
                                    source_id=paper_entity_id,
                                    target_id=f"{entity.entity_type.lower()}_{entity.name[:50]}",
                                )
                            )

                self.progress.papers_processed = i + 1
                progress = 0.2 + (0.6 * (i + 1) / len(papers))
                self._update_progress(
                    "processing",
                    progress,
                    f"Processing paper {i + 1}/{len(papers)}...",
                )

                # Yield control every batch
                if (i + 1) % batch_size == 0:
                    await asyncio.sleep(0)

            # Build concept co-occurrence relationships
            self._update_progress("building_graph", 0.85, "Building concept relationships...")
            concept_relationships = self._build_concept_relationships(all_entities)
            all_relationships.extend(concept_relationships)

            # Store in database
            self._update_progress("building_graph", 0.9, "Storing entities in database...")
            id_mapping = await self._store_entities(project_id, all_entities)

            self._update_progress("building_graph", 0.95, "Storing relationships in database...")
            await self._store_relationships(project_id, all_relationships, id_mapping)

            self.progress.entities_created = len(all_entities)
            self.progress.relationships_created = len(all_relationships)

            logger.info(f"Import complete: {len(all_entities)} entities, {len(all_relationships)} relationships")

            # Complete
            self._update_progress("completed", 1.0, "Import completed successfully!")

            return {
                "success": True,
                "project_id": project_id,
                "project": project,
                "stats": {
                    "papers_imported": len(papers),
                    "authors_extracted": len(self._author_cache),
                    "concepts_extracted": len(self._concept_cache),
                    "total_entities": len(all_entities),
                    "total_relationships": len(all_relationships),
                },
            }

        except Exception as e:
            logger.exception(f"Import failed: {e}")
            self._update_progress("failed", 0.0, f"Import failed: {str(e)}")
            self.progress.errors.append(str(e))
            return {
                "success": False,
                "error": str(e),
                "progress": self.progress,
            }

    async def _parse_config(self, folder: Path) -> ProjectConfig:
        """Parse config.yaml and .scholarag files."""
        config_path = folder / "config.yaml"
        metadata_path = folder / ".scholarag"

        config_data = {}
        metadata = {}

        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}

        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = yaml.safe_load(f) or {}

        # Extract project info
        project_info = config_data.get("project", {})
        search_info = config_data.get("search", {})

        return ProjectConfig(
            name=project_info.get("name") or metadata.get("project_name") or folder.name,
            research_question=project_info.get("research_question")
            or metadata.get("research_question", ""),
            project_type=project_info.get("project_type")
            or metadata.get("project_type", "systematic_review"),
            created_date=project_info.get("created")
            or metadata.get("created", datetime.now().strftime("%Y-%m-%d")),
            databases=self._extract_databases(config_data),
            year_range=(
                search_info.get("year_range", {}).get("start", 2020),
                search_info.get("year_range", {}).get("end", 2025),
            ),
            inclusion_criteria=config_data.get("prisma_criteria", {}).get(
                "inclusion", []
            ),
            exclusion_criteria=config_data.get("prisma_criteria", {}).get(
                "exclusion", []
            ),
        )

    def _extract_databases(self, config_data: dict) -> list[str]:
        """Extract enabled databases from config."""
        databases = []
        db_config = config_data.get("databases", {})

        for category in ["open_access", "institutional"]:
            category_dbs = db_config.get(category, {})
            for db_name, settings in category_dbs.items():
                if isinstance(settings, dict) and settings.get("enabled"):
                    databases.append(db_name)

        return databases

    async def _parse_papers_csv(self, csv_path: Path) -> list[PaperData]:
        """Parse papers from CSV file."""
        papers = []

        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)

            for i, row in enumerate(reader):
                # Skip explicitly excluded papers if decision column exists
                decision = row.get("decision", "").lower()
                # Reject: no, exclude, excluded, reject, rejected
                # Accept everything else (including human-review, auto-include, yes, include, empty, etc.)
                rejected_decisions = ["no", "exclude", "excluded", "reject", "rejected", "auto-exclude"]
                if decision in rejected_decisions:
                    continue

                # Parse authors
                authors_str = row.get("authors", "")
                if authors_str:
                    # Handle various author formats
                    if ";" in authors_str:
                        authors = [a.strip() for a in authors_str.split(";")]
                    elif "," in authors_str and not any(
                        c.isdigit() for c in authors_str
                    ):
                        authors = [a.strip() for a in authors_str.split(",")]
                    else:
                        authors = [authors_str.strip()]
                else:
                    authors = []

                # Parse year
                year_str = row.get("year", "")
                try:
                    year = int(year_str) if year_str else None
                except ValueError:
                    year = None

                # Parse citation count
                try:
                    citation_count = int(row.get("citation_count", 0) or row.get("citations", 0) or 0)
                except ValueError:
                    citation_count = 0

                papers.append(
                    PaperData(
                        paper_id=row.get("paperId")
                        or row.get("openalex_id")
                        or row.get("doi")
                        or str(uuid4())[:8],
                        title=row.get("title", "Untitled"),
                        abstract=row.get("abstract", ""),
                        authors=authors,
                        year=year,
                        doi=row.get("doi"),
                        source=row.get("source", "unknown"),
                        citation_count=citation_count,
                        pdf_url=row.get("pdf_url") or row.get("open_access_pdf"),
                        properties={
                            k: v
                            for k, v in row.items()
                            if k
                            not in [
                                "title",
                                "abstract",
                                "authors",
                                "year",
                                "doi",
                                "source",
                                "citation_count",
                                "pdf_url",
                            ]
                        },
                    )
                )

        return papers

    def _get_or_create_author(
        self, author_name: str, entities: list[ExtractedEntity]
    ) -> str:
        """Get existing author ID or create new author entity."""
        # Normalize name
        normalized = author_name.strip().lower()

        if normalized in self._author_cache:
            return self._author_cache[normalized]

        # Create new author
        author_id = f"author_{len(self._author_cache)}"
        entities.append(
            ExtractedEntity(
                entity_type="Author",
                name=author_name.strip(),
                properties={},
            )
        )
        self._author_cache[normalized] = author_id
        return author_id

    async def _extract_entities_from_paper(
        self, paper: PaperData
    ) -> list[ExtractedEntity]:
        """
        Use LLM to extract Concepts, Methods, and Findings from paper abstract.
        """
        if not self.llm or not paper.abstract:
            return []

        # TODO: Implement LLM-based extraction
        # For now, use simple keyword extraction

        entities = []

        # Extract concepts from title and abstract
        text = f"{paper.title} {paper.abstract}".lower()
        keywords = self._extract_keywords(text)

        for keyword in keywords[:5]:  # Limit to 5 concepts per paper
            if keyword not in self._concept_cache:
                concept_id = f"concept_{len(self._concept_cache)}"
                entities.append(
                    ExtractedEntity(
                        entity_type="Concept",
                        name=keyword,
                        properties={"extracted_from": "keyword_extraction"},
                    )
                )
                self._concept_cache[keyword] = concept_id

        return entities

    def _extract_keywords(self, text: str) -> list[str]:
        """Simple keyword extraction using common academic terms."""
        # Common academic keywords to look for
        keywords = []

        # Common concept patterns
        concept_patterns = [
            r"\b(machine learning|deep learning|neural network|nlp|natural language processing)\b",
            r"\b(chatbot|conversational agent|dialogue system)\b",
            r"\b(education|learning|teaching|pedagogy)\b",
            r"\b(effectiveness|efficacy|impact|outcome)\b",
            r"\b(student|learner|participant)\b",
            r"\b(experimental|quasi-experimental|rct|randomized)\b",
            r"\b(meta-analysis|systematic review|literature review)\b",
        ]

        for pattern in concept_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.extend([m.lower() if isinstance(m, str) else m[0].lower() for m in matches])

        return list(set(keywords))

    def _get_relationship_type(self, entity_type: str) -> Optional[str]:
        """Map entity type to relationship type."""
        mapping = {
            "Concept": "DISCUSSES_CONCEPT",
            "Method": "USES_METHOD",
            "Finding": "SUPPORTS",
            "Dataset": "USES_DATASET",
        }
        return mapping.get(entity_type)

    def _build_concept_relationships(
        self, entities: list[ExtractedEntity]
    ) -> list[ExtractedRelationship]:
        """Build RELATED_TO relationships between concepts that co-occur."""
        relationships = []

        # Group concepts by source paper
        paper_concepts: dict[str, list[str]] = {}
        for entity in entities:
            if entity.entity_type == "Concept" and entity.source_paper_id:
                if entity.source_paper_id not in paper_concepts:
                    paper_concepts[entity.source_paper_id] = []
                paper_concepts[entity.source_paper_id].append(entity.name)

        # Create RELATED_TO for concepts that co-occur in multiple papers
        concept_pairs: dict[tuple, int] = {}
        for concepts in paper_concepts.values():
            for i, c1 in enumerate(concepts):
                for c2 in concepts[i + 1 :]:
                    pair = tuple(sorted([c1, c2]))
                    concept_pairs[pair] = concept_pairs.get(pair, 0) + 1

        # Create relationships for frequently co-occurring concepts
        for (c1, c2), count in concept_pairs.items():
            if count >= 2:  # At least 2 co-occurrences
                relationships.append(
                    ExtractedRelationship(
                        relationship_type="RELATED_TO",
                        source_id=f"concept_{c1}",
                        target_id=f"concept_{c2}",
                        properties={"co_occurrence_count": count},
                    )
                )

        return relationships

    async def _store_entities(
        self, project_id: str, entities: list[ExtractedEntity]
    ) -> dict[str, str]:
        """
        Store entities in database.

        Returns a mapping from local entity IDs (e.g., "paper_xxx") to database UUIDs.
        """
        logger.info(f"Storing {len(entities)} entities for project {project_id}")

        id_mapping: dict[str, str] = {}  # local_id -> database_uuid
        author_name_to_uuid: dict[str, str] = {}  # author_name.lower() -> uuid
        concept_name_to_uuid: dict[str, str] = {}  # concept_name.lower() -> uuid

        if not self.db:
            logger.warning("No database connection - skipping entity storage")
            return id_mapping

        # Count by type for logging
        type_counts = {}

        # Batch insert entities
        for i, entity in enumerate(entities):
            try:
                entity_uuid = str(uuid4())

                # Track type counts
                type_counts[entity.entity_type] = type_counts.get(entity.entity_type, 0) + 1

                # Determine the local ID for this entity
                if entity.entity_type == "Paper":
                    paper_id = entity.properties.get("paper_id", str(i))
                    local_id = f"paper_{paper_id}"
                    # Also store in paper_id_map
                    self._paper_id_map[paper_id] = entity_uuid

                elif entity.entity_type == "Author":
                    normalized_name = entity.name.strip().lower()
                    # Check if we already stored this author
                    if normalized_name in author_name_to_uuid:
                        continue  # Skip duplicate author
                    local_id = self._author_cache.get(normalized_name, f"author_{normalized_name}")
                    author_name_to_uuid[normalized_name] = entity_uuid

                elif entity.entity_type == "Concept":
                    normalized_name = entity.name.strip().lower()
                    # Check if we already stored this concept
                    if normalized_name in concept_name_to_uuid:
                        continue  # Skip duplicate concept
                    local_id = self._concept_cache.get(normalized_name, f"concept_{entity.name[:50]}")
                    concept_name_to_uuid[normalized_name] = entity_uuid

                else:
                    local_id = f"{entity.entity_type.lower()}_{i}"

                # Store mapping
                id_mapping[local_id] = entity_uuid

                # Insert into database
                await self.db.execute(
                    """
                    INSERT INTO entities (id, project_id, entity_type, name, properties)
                    VALUES ($1, $2, $3::entity_type, $4, $5)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    entity_uuid,
                    project_id,
                    entity.entity_type,
                    entity.name[:500],  # Truncate name to fit VARCHAR(500)
                    json.dumps(entity.properties),
                )

                if (i + 1) % 100 == 0:
                    logger.info(f"  Stored {i + 1}/{len(entities)} entities...")

            except Exception as e:
                logger.error(f"Failed to store entity {entity.name}: {e}")
                continue

        # Update caches with UUID mappings for relationship resolution
        for name, local_id in self._author_cache.items():
            if name in author_name_to_uuid:
                id_mapping[local_id] = author_name_to_uuid[name]

        for name, local_id in self._concept_cache.items():
            if name in concept_name_to_uuid:
                id_mapping[local_id] = concept_name_to_uuid[name]

        logger.info(f"Stored entities successfully: {type_counts}")
        return id_mapping

    async def _store_relationships(
        self, project_id: str, relationships: list[ExtractedRelationship], id_mapping: dict[str, str]
    ):
        """
        Store relationships in database.

        Args:
            project_id: Project UUID
            relationships: List of extracted relationships
            id_mapping: Mapping from local IDs to database UUIDs
        """
        logger.info(f"Storing {len(relationships)} relationships for project {project_id}")

        if not self.db:
            logger.warning("No database connection - skipping relationship storage")
            return

        stored_count = 0
        for i, rel in enumerate(relationships):
            try:
                # Resolve source and target IDs
                source_uuid = id_mapping.get(rel.source_id)
                target_uuid = id_mapping.get(rel.target_id)

                if not source_uuid or not target_uuid:
                    # Try to find by paper_id directly
                    if rel.source_id.startswith("paper_"):
                        paper_id = rel.source_id[6:]  # Remove "paper_" prefix
                        source_uuid = self._paper_id_map.get(paper_id)

                    # Skip if we still can't resolve
                    if not source_uuid or not target_uuid:
                        continue

                rel_uuid = str(uuid4())

                await self.db.execute(
                    """
                    INSERT INTO relationships (id, project_id, source_id, target_id, relationship_type, properties, weight)
                    VALUES ($1, $2, $3, $4, $5::relationship_type, $6, $7)
                    ON CONFLICT (source_id, target_id, relationship_type) DO NOTHING
                    """,
                    rel_uuid,
                    project_id,
                    source_uuid,
                    target_uuid,
                    rel.relationship_type,
                    json.dumps(rel.properties),
                    rel.properties.get("weight", 1.0),
                )
                stored_count += 1

                if (i + 1) % 100 == 0:
                    logger.info(f"  Stored {i + 1}/{len(relationships)} relationships...")

            except Exception as e:
                logger.error(f"Failed to store relationship {rel.relationship_type}: {e}")
                continue

        logger.info(f"Stored {stored_count} relationships successfully")
