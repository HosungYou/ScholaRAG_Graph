"""
ScholaRAG Folder Importer - Concept-Centric Knowledge Graph

Imports existing ScholaRAG project folders and builds CONCEPT-CENTRIC knowledge graphs.

Key Design Principles:
1. Concepts are PRIMARY nodes (visualized, connected, analyzed)
2. Papers/Authors are METADATA (stored but not visualized as nodes)
3. Gap Detection identifies research opportunities between concept clusters

Process:
1. Parse config.yaml and .scholarag metadata
2. Read papers from CSV files
3. Use LLM to extract Concepts, Methods, Findings, Problems from abstracts
4. Store Papers/Authors as metadata (not graph nodes)
5. Build semantic relationships between concepts
6. Run clustering and gap detection
7. Calculate centrality metrics
"""

import asyncio
import csv
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import uuid4

import yaml

from graph.entity_extractor import (
    EntityExtractor,
    ExtractedEntity,
    EntityType,
)
from graph.relationship_builder import (
    ConceptCentricRelationshipBuilder,
    RelationshipCandidate,
)
from graph.gap_detector import GapDetector, ConceptCluster, StructuralGap
from graph.entity_resolution import EntityResolutionService

logger = logging.getLogger(__name__)


@dataclass
class ImportProgress:
    """Track import progress for WebSocket updates."""

    status: str = "pending"
    progress: float = 0.0
    message: str = ""
    papers_processed: int = 0
    papers_total: int = 0
    concepts_extracted: int = 0
    relationships_created: int = 0
    gaps_detected: int = 0
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


class ConceptCentricScholarAGImporter:
    """
    Imports ScholaRAG project folders with CONCEPT-CENTRIC knowledge graph design.

    Key differences from traditional import:
    - Papers and Authors become metadata, NOT graph nodes
    - Concepts, Methods, Findings are PRIMARY nodes
    - LLM extracts rich semantic entities using NLP-AKG methodology
    - Gap detection identifies research opportunities
    - Centrality metrics calculated for node importance
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

        # Initialize specialized processors
        self.entity_extractor = EntityExtractor(llm_provider=llm_provider)
        self.relationship_builder = ConceptCentricRelationshipBuilder(llm_provider=llm_provider)
        self.gap_detector = GapDetector(llm_provider=llm_provider)
        self.entity_resolution = EntityResolutionService(llm_provider=llm_provider)

        # Caches for deduplication
        self._concept_cache: dict[str, dict] = {}  # normalized_name -> entity_data
        self._paper_metadata: dict[str, dict] = {}  # paper_id -> metadata

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
        """Validate a ScholaRAG project folder."""
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
                try:
                    with open(csv_path, "r", encoding="utf-8") as f:
                        validation["papers_count"] = sum(1 for _ in f) - 1
                except Exception as e:
                    validation["warnings"].append(f"Could not count papers: {e}")
                break

        if not validation["papers_csv_found"]:
            validation["errors"].append("No papers CSV found")
            validation["valid"] = False

        # Check PDFs
        pdfs_dir = folder / "data" / "03_pdfs"
        if pdfs_dir.exists():
            validation["pdfs_count"] = len(list(pdfs_dir.rglob("*.pdf")))

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
        extract_concepts: bool = True,
        run_gap_detection: bool = True,
    ) -> dict:
        """
        Import a ScholaRAG project folder with concept-centric design.

        Args:
            folder_path: Path to ScholaRAG project folder
            project_name: Optional name override
            extract_concepts: Whether to use LLM for concept extraction
            run_gap_detection: Whether to run gap detection after import

        Returns:
            Import result with project_id and statistics
        """
        folder = Path(folder_path)
        self._update_progress("validating", 0.05, "Validating folder structure...")

        # Validate
        validation = await self.validate_folder(folder_path)
        if not validation["valid"]:
            self._update_progress("failed", 0.0, "Validation failed")
            return {"success": False, "error": "Validation failed", "validation": validation}

        try:
            # Parse config
            self._update_progress("extracting", 0.1, "Parsing configuration...")
            config = await self._parse_config(folder)

            # Create project
            project_id = str(uuid4())
            project_name_final = project_name or config.name
            logger.info(f"Creating project: {project_name_final} (ID: {project_id})")

            if self.db:
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

            # Parse papers
            self._update_progress("extracting", 0.15, "Reading papers from CSV...")
            papers = await self._parse_papers_csv(Path(validation["papers_csv_path"]))
            self.progress.papers_total = len(papers)

            # Phase 1: Store paper metadata (for reference)
            self._update_progress("processing", 0.2, "Storing paper metadata...")
            await self._store_paper_metadata(project_id, papers)

            # Phase 1.5: Store Paper and Author as GRAPH NODES (Hybrid Mode)
            self._update_progress("processing", 0.22, "Creating Paper/Author graph nodes (Hybrid Mode)...")
            paper_entity_ids, author_entity_ids = await self._store_paper_and_author_entities(project_id, papers)

            # Phase 2: Extract concepts from all papers
            self._update_progress("processing", 0.25, "Extracting concepts with LLM...")
            all_entities = []
            paper_entities_map = {}  # paper_id -> {type: [entity_ids]}
            resolution_stats = {
                "raw_entities_extracted": 0,
                "entities_after_resolution": 0,
                "merges_applied": 0,
                "llm_pairs_reviewed": 0,
                "llm_pairs_confirmed": 0,
                "potential_false_merge_count": 0,
                "potential_false_merge_samples": [],
            }

            for i, paper in enumerate(papers):
                if extract_concepts and paper.abstract:
                    entities = await self.entity_extractor.extract_entities(
                        title=paper.title,
                        abstract=paper.abstract,
                        paper_id=paper.paper_id,
                    )
                    resolved_entities, resolved_metrics = await self.entity_resolution.resolve_entities_async(
                        entities,
                        use_llm_confirmation=True,
                    )
                    resolution_stats["raw_entities_extracted"] += resolved_metrics.raw_entities
                    resolution_stats["entities_after_resolution"] += resolved_metrics.resolved_entities
                    resolution_stats["merges_applied"] += resolved_metrics.merged_entities
                    resolution_stats["llm_pairs_reviewed"] += resolved_metrics.llm_pairs_reviewed
                    resolution_stats["llm_pairs_confirmed"] += resolved_metrics.llm_pairs_confirmed
                    resolution_stats["potential_false_merge_count"] += resolved_metrics.potential_false_merge_count
                    if resolved_metrics.potential_false_merge_samples:
                        resolution_stats["potential_false_merge_samples"].extend(
                            resolved_metrics.potential_false_merge_samples
                        )
                        resolution_stats["potential_false_merge_samples"] = resolution_stats[
                            "potential_false_merge_samples"
                        ][:15]

                    # Track entities by paper for relationship building
                    paper_entities_map[paper.paper_id] = self._group_entities_by_type(resolved_entities)

                    for entity in resolved_entities:
                        # Deduplicate by name
                        normalized = self.entity_resolution.canonicalize_name(entity.name)
                        if normalized not in self._concept_cache:
                            entity_id = str(uuid4())
                            entity_data = {
                                "id": entity_id,
                                "name": normalized,
                                "definition": entity.definition,
                                "entity_type": entity.entity_type.value,
                                "confidence": entity.confidence,
                                "source_paper_ids": [paper.paper_id],
                                "embedding": None,  # Will be generated
                            }
                            self._concept_cache[normalized] = entity_data
                            all_entities.append(entity_data)
                        else:
                            # Update source papers for existing entity
                            self._concept_cache[normalized]["source_paper_ids"].append(paper.paper_id)

                self.progress.papers_processed = i + 1
                progress = 0.25 + (0.35 * (i + 1) / len(papers))
                self._update_progress("processing", progress, f"Extracting concepts from paper {i + 1}/{len(papers)}...")

                # Yield control periodically
                if (i + 1) % 10 == 0:
                    await asyncio.sleep(0)

            self.progress.concepts_extracted = len(all_entities)

            # Phase 3: Generate embeddings for concepts
            self._update_progress("processing", 0.6, "Generating concept embeddings...")
            all_entities = await self._generate_embeddings(all_entities)

            # Phase 4: Store concept entities (these ARE graph nodes)
            self._update_progress("processing", 0.65, "Storing concept entities...")
            id_mapping = await self._store_concept_entities(project_id, all_entities)

            # Phase 4.5: Create DISCUSSES_CONCEPT relationships (Paper → Concept)
            self._update_progress("processing", 0.68, "Creating Paper-Concept relationships...")
            paper_concept_rels_count = await self._store_paper_concept_relationships(
                project_id, paper_entity_ids, all_entities, self._concept_cache
            )
            logger.info(f"Created {paper_concept_rels_count} Paper→Concept relationships")

            # Phase 5: Build relationships
            self._update_progress("building_graph", 0.7, "Building concept relationships...")

            # Prepare data for relationship builder
            entities_by_type = self._organize_entities_by_type(all_entities)
            paper_entities_typed = self._convert_paper_entities_map(paper_entities_map)

            relationships = await self.relationship_builder.build_all_relationships(
                entities_by_type=entities_by_type,
                paper_entities=paper_entities_typed,
                include_prerequisites=False,  # Skip for now - can be slow
            )

            # Store relationships
            self._update_progress("building_graph", 0.8, "Storing relationships...")
            await self._store_relationships(project_id, relationships, id_mapping)
            self.progress.relationships_created = len(relationships)

            # Phase 6: Run gap detection
            if run_gap_detection and len(all_entities) >= 10:
                self._update_progress("analyzing", 0.85, "Detecting research gaps...")

                # Prepare data for gap detector
                concepts_for_gap = [
                    {
                        "id": e["id"],
                        "name": e["name"],
                        "embedding": e.get("embedding"),
                    }
                    for e in all_entities
                    if e["entity_type"] == "Concept"
                ]

                relationships_for_gap = [
                    {"source_id": r.source_id, "target_id": r.target_id}
                    for r in relationships
                ]

                gap_analysis = await self.gap_detector.analyze_graph(
                    concepts=concepts_for_gap,
                    relationships=relationships_for_gap,
                )

                # Store clusters and gaps
                await self._store_clusters(project_id, gap_analysis["clusters"])
                await self._store_gaps(project_id, gap_analysis["gaps"])

                # Update centrality metrics
                await self._update_centrality(project_id, gap_analysis["centrality"], gap_analysis["clusters"])

                self.progress.gaps_detected = len(gap_analysis["gaps"])

            # Complete
            self._update_progress("completed", 1.0, "Import completed successfully!")

            return {
                "success": True,
                "project_id": project_id,
                "stats": {
                    "papers_imported": len(papers),
                    "concepts_extracted": len(all_entities),
                    "relationships_created": len(relationships),
                    "gaps_detected": self.progress.gaps_detected,
                    "raw_entities_extracted": resolution_stats["raw_entities_extracted"],
                    "entities_after_resolution": resolution_stats["entities_after_resolution"],
                    "merges_applied": resolution_stats["merges_applied"],
                    "llm_pairs_reviewed": resolution_stats["llm_pairs_reviewed"],
                    "llm_pairs_confirmed": resolution_stats["llm_pairs_confirmed"],
                    "potential_false_merge_count": resolution_stats["potential_false_merge_count"],
                    "potential_false_merge_samples": resolution_stats["potential_false_merge_samples"],
                    "canonicalization_rate": (
                        resolution_stats["merges_applied"] / resolution_stats["raw_entities_extracted"]
                        if resolution_stats["raw_entities_extracted"] > 0
                        else 0.0
                    ),
                },
            }

        except Exception as e:
            logger.exception(f"Import failed: {e}")
            self._update_progress("failed", 0.0, f"Import failed: {str(e)}")
            self.progress.errors.append(str(e))
            return {"success": False, "error": str(e)}

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

        project_info = config_data.get("project", {})
        search_info = config_data.get("search", {})

        return ProjectConfig(
            name=project_info.get("name") or metadata.get("project_name") or folder.name,
            research_question=project_info.get("research_question") or metadata.get("research_question", ""),
            project_type=project_info.get("project_type") or metadata.get("project_type", "systematic_review"),
            created_date=project_info.get("created") or metadata.get("created", datetime.now().strftime("%Y-%m-%d")),
            databases=self._extract_databases(config_data),
            year_range=(
                search_info.get("year_range", {}).get("start", 2020),
                search_info.get("year_range", {}).get("end", 2025),
            ),
            inclusion_criteria=config_data.get("prisma_criteria", {}).get("inclusion", []),
            exclusion_criteria=config_data.get("prisma_criteria", {}).get("exclusion", []),
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

            for row in reader:
                # Skip rejected papers
                decision = row.get("decision", "").lower()
                rejected_decisions = ["no", "exclude", "excluded", "reject", "rejected", "auto-exclude"]
                if decision in rejected_decisions:
                    continue

                # Parse authors
                authors_str = row.get("authors", "")
                if authors_str:
                    if ";" in authors_str:
                        authors = [a.strip() for a in authors_str.split(";")]
                    elif "," in authors_str and not any(c.isdigit() for c in authors_str):
                        authors = [a.strip() for a in authors_str.split(",")]
                    else:
                        authors = [authors_str.strip()]
                else:
                    authors = []

                # Parse year
                try:
                    year = int(row.get("year", "")) if row.get("year") else None
                except ValueError:
                    year = None

                # Parse citation count
                try:
                    citation_count = int(row.get("citation_count", 0) or row.get("citations", 0) or 0)
                except ValueError:
                    citation_count = 0

                papers.append(
                    PaperData(
                        paper_id=row.get("paperId") or row.get("openalex_id") or row.get("doi") or str(uuid4())[:8],
                        title=row.get("title", "Untitled"),
                        abstract=row.get("abstract", ""),
                        authors=authors,
                        year=year,
                        doi=row.get("doi"),
                        source=row.get("source", "unknown"),
                        citation_count=citation_count,
                        pdf_url=row.get("pdf_url") or row.get("open_access_pdf"),
                        properties={k: v for k, v in row.items() if k not in ["title", "abstract", "authors", "year", "doi", "source", "citation_count", "pdf_url"]},
                    )
                )

        return papers

    async def _store_paper_metadata(self, project_id: str, papers: list[PaperData]):
        """
        Store papers as METADATA (not graph nodes).

        Papers are stored in paper_metadata table, NOT entities table.
        """
        if not self.db:
            return

        logger.info(f"Storing {len(papers)} papers as metadata")

        for paper in papers:
            paper_uuid = str(uuid4())
            self._paper_metadata[paper.paper_id] = {
                "uuid": paper_uuid,
                "title": paper.title,
                "authors": paper.authors,
            }

            try:
                await self.db.execute(
                    """
                    INSERT INTO paper_metadata (
                        id, project_id, paper_id, doi, title, authors,
                        abstract, year, source, citation_count, pdf_url,
                        screening_status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    paper_uuid,
                    project_id,
                    paper.paper_id,
                    paper.doi,
                    paper.title[:500] if paper.title else "Untitled",
                    json.dumps([{"name": a} for a in paper.authors]),
                    paper.abstract[:5000] if paper.abstract else "",
                    paper.year,
                    paper.source,
                    paper.citation_count,
                    paper.pdf_url,
                    "included",
                )
            except Exception as e:
                logger.warning(f"Failed to store paper metadata: {e}")

    async def _store_paper_and_author_entities(
        self, project_id: str, papers: list[PaperData]
    ) -> tuple[dict[str, str], dict[str, str]]:
        """
        Store Paper and Author as GRAPH NODES (Hybrid Mode).

        This enables Papers and Authors to be visualized alongside Concepts.
        Papers connect to Concepts via DISCUSSES_CONCEPT relationships.

        Returns:
            Tuple of (paper_entity_ids, author_entity_ids) mappings
        """
        if not self.db:
            return {}, {}

        paper_entity_ids = {}  # paper_id -> entity_uuid
        author_entity_ids = {}  # author_name_normalized -> entity_uuid

        logger.info(f"Creating {len(papers)} Paper entities for Hybrid Mode visualization")

        for paper in papers:
            # Create Paper entity
            paper_entity_uuid = str(uuid4())
            paper_entity_ids[paper.paper_id] = paper_entity_uuid

            try:
                await self.db.execute(
                    """
                    INSERT INTO entities (
                        id, project_id, entity_type, name, properties,
                        is_visualized, definition
                    ) VALUES ($1, $2, $3::entity_type, $4, $5, $6, $7)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    paper_entity_uuid,
                    project_id,
                    "Paper",  # Entity type
                    paper.title[:500] if paper.title else "Untitled",
                    json.dumps({
                        "doi": paper.doi,
                        "year": paper.year,
                        "authors": paper.authors,
                        "citation_count": paper.citation_count,
                        "source": paper.source,
                        "pdf_url": paper.pdf_url,
                    }),
                    True,  # is_visualized = True for Hybrid Mode
                    paper.abstract[:500] if paper.abstract else "",  # Use abstract as definition
                )
            except Exception as e:
                logger.warning(f"Failed to store Paper entity: {e}")

            # Create Author entities (deduplicated by name)
            for author_name in paper.authors:
                normalized_name = author_name.strip().lower()
                if normalized_name and normalized_name not in author_entity_ids:
                    author_entity_uuid = str(uuid4())
                    author_entity_ids[normalized_name] = author_entity_uuid

                    try:
                        await self.db.execute(
                            """
                            INSERT INTO entities (
                                id, project_id, entity_type, name, properties,
                                is_visualized
                            ) VALUES ($1, $2, $3::entity_type, $4, $5, $6)
                            ON CONFLICT (id) DO NOTHING
                            """,
                            author_entity_uuid,
                            project_id,
                            "Author",  # Entity type
                            author_name.strip()[:500],
                            json.dumps({"paper_count": 1}),
                            True,  # is_visualized = True for Hybrid Mode
                        )
                    except Exception as e:
                        logger.warning(f"Failed to store Author entity: {e}")
                elif normalized_name in author_entity_ids:
                    # Increment paper_count for existing author (optional)
                    pass

            # Create HAS_AUTHOR relationships (Paper → Author)
            for author_name in paper.authors:
                normalized_name = author_name.strip().lower()
                if normalized_name in author_entity_ids:
                    try:
                        await self.db.execute(
                            """
                            INSERT INTO relationships (
                                id, project_id, source_id, target_id,
                                relationship_type, properties, weight
                            ) VALUES ($1, $2, $3, $4, $5::relationship_type, $6, $7)
                            ON CONFLICT (source_id, target_id, relationship_type) DO NOTHING
                            """,
                            str(uuid4()),
                            project_id,
                            paper_entity_uuid,  # Paper
                            author_entity_ids[normalized_name],  # Author
                            "AUTHORED_BY",  # Use AUTHORED_BY which exists in relationship_type enum
                            json.dumps({}),
                            1.0,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to store HAS_AUTHOR relationship: {e}")

        logger.info(f"Created {len(paper_entity_ids)} Paper entities and {len(author_entity_ids)} Author entities")
        return paper_entity_ids, author_entity_ids

    async def _store_paper_concept_relationships(
        self,
        project_id: str,
        paper_entity_ids: dict[str, str],
        all_entities: list[dict],
        concept_cache: dict[str, dict],
    ) -> int:
        """
        Create DISCUSSES_CONCEPT relationships between Papers and extracted Concepts.

        For each concept, link it to all papers that mentioned it via source_paper_ids.
        """
        if not self.db:
            return 0

        relationships_created = 0

        for entity in all_entities:
            entity_id = entity["id"]
            source_paper_ids = entity.get("source_paper_ids", [])

            for paper_id in source_paper_ids:
                paper_entity_uuid = paper_entity_ids.get(paper_id)
                if not paper_entity_uuid:
                    continue

                try:
                    await self.db.execute(
                        """
                        INSERT INTO relationships (
                            id, project_id, source_id, target_id,
                            relationship_type, properties, weight
                        ) VALUES ($1, $2, $3, $4, $5::relationship_type, $6, $7)
                        ON CONFLICT (source_id, target_id, relationship_type) DO NOTHING
                        """,
                        str(uuid4()),
                        project_id,
                        paper_entity_uuid,  # Paper (source)
                        entity_id,  # Concept (target)
                        "DISCUSSES_CONCEPT",
                        json.dumps({"confidence": entity.get("confidence", 0.8)}),
                        entity.get("confidence", 0.8),
                    )
                    relationships_created += 1
                except Exception as e:
                    logger.warning(f"Failed to store DISCUSSES_CONCEPT relationship: {e}")

        return relationships_created

    def _group_entities_by_type(self, entities: list[ExtractedEntity]) -> dict[str, list[str]]:
        """Group entities by type for relationship building."""
        grouped = {}
        for entity in entities:
            type_name = entity.entity_type.value
            if type_name not in grouped:
                grouped[type_name] = []

            # Use normalized name as temporary ID
            normalized = entity.name.strip().lower()
            if normalized in self._concept_cache:
                grouped[type_name].append(self._concept_cache[normalized]["id"])

        return grouped

    async def _generate_embeddings(self, entities: list[dict]) -> list[dict]:
        """Generate embeddings for entities using LLM provider."""
        if not self.llm or not hasattr(self.llm, "get_embeddings"):
            logger.warning("No embedding function available - skipping embedding generation")
            return entities

        logger.info(f"Generating embeddings for {len(entities)} entities")

        # Batch embedding generation
        texts = [f"{e['name']}: {e.get('definition', '')}" for e in entities]

        try:
            embeddings = await self.llm.get_embeddings(texts)
            for i, entity in enumerate(entities):
                if i < len(embeddings):
                    entity["embedding"] = embeddings[i]
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")

        return entities

    async def _store_concept_entities(self, project_id: str, entities: list[dict]) -> dict[str, str]:
        """
        Store concept entities (these ARE graph nodes).

        Returns mapping from entity_id to database UUID.
        """
        if not self.db:
            return {}

        id_mapping = {}
        logger.info(f"Storing {len(entities)} concept entities")

        for entity in entities:
            entity_id = entity["id"]
            id_mapping[entity_id] = entity_id

            try:
                # Get paper UUIDs for source_paper_ids
                source_paper_uuids = [
                    self._paper_metadata[pid]["uuid"]
                    for pid in entity.get("source_paper_ids", [])
                    if pid in self._paper_metadata
                ]

                await self.db.execute(
                    """
                    INSERT INTO entities (
                        id, project_id, entity_type, name, properties,
                        is_visualized, source_paper_ids, definition
                    ) VALUES ($1, $2, $3::entity_type, $4, $5, $6, $7, $8)
                    ON CONFLICT (id) DO UPDATE SET
                        source_paper_ids = EXCLUDED.source_paper_ids,
                        definition = EXCLUDED.definition
                    """,
                    entity_id,
                    project_id,
                    entity["entity_type"],
                    entity["name"][:500],
                    json.dumps({"confidence": entity.get("confidence", 0.8)}),
                    True,  # is_visualized = True for concepts
                    source_paper_uuids,
                    entity.get("definition", ""),
                )

                # Store embedding if available
                if entity.get("embedding"):
                    await self.db.execute(
                        """
                        UPDATE entities SET embedding = $1 WHERE id = $2
                        """,
                        entity["embedding"],
                        entity_id,
                    )

            except Exception as e:
                logger.warning(f"Failed to store entity {entity['name'][:30]}: {e}")

        return id_mapping

    def _organize_entities_by_type(self, entities: list[dict]) -> dict[str, list[dict]]:
        """Organize entities by type for relationship builder."""
        by_type = {}
        for entity in entities:
            entity_type = entity["entity_type"]
            if entity_type not in by_type:
                by_type[entity_type] = []
            by_type[entity_type].append(entity)
        return by_type

    def _convert_paper_entities_map(self, paper_entities_map: dict) -> dict[str, dict[str, list[str]]]:
        """Convert paper entities map to relationship builder format."""
        result = {}
        for paper_id, entities_by_type in paper_entities_map.items():
            result[paper_id] = entities_by_type
        return result

    async def _store_relationships(
        self,
        project_id: str,
        relationships: list[RelationshipCandidate],
        id_mapping: dict[str, str],
    ):
        """Store relationships in database."""
        if not self.db:
            return

        logger.info(f"Storing {len(relationships)} relationships")

        for rel in relationships:
            source_uuid = id_mapping.get(rel.source_id)
            target_uuid = id_mapping.get(rel.target_id)

            if not source_uuid or not target_uuid:
                continue

            try:
                await self.db.execute(
                    """
                    INSERT INTO relationships (
                        id, project_id, source_id, target_id,
                        relationship_type, properties, weight
                    ) VALUES ($1, $2, $3, $4, $5::relationship_type, $6, $7)
                    ON CONFLICT (source_id, target_id, relationship_type) DO NOTHING
                    """,
                    str(uuid4()),
                    project_id,
                    source_uuid,
                    target_uuid,
                    rel.relationship_type,
                    json.dumps(rel.properties),
                    rel.confidence,
                )
            except Exception as e:
                logger.warning(f"Failed to store relationship: {e}")

    async def _store_clusters(self, project_id: str, clusters: list[ConceptCluster]):
        """Store concept clusters in database."""
        if not self.db or not clusters:
            return

        logger.info(f"Storing {len(clusters)} concept clusters")

        def _get_cluster_label(c):
            """Get meaningful cluster label, avoiding UUIDs."""
            if c.name and len(c.name) < 100 and not (len(c.name) == 36 and c.name.count('-') == 4):
                return c.name
            if c.keywords:
                return " / ".join(c.keywords[:3])
            return f"Cluster {c.id + 1}"

        for cluster in clusters:
            try:
                await self.db.execute(
                    """
                    INSERT INTO concept_clusters (
                        id, project_id, name, color, concept_count, keywords
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    cluster.id,
                    project_id,
                    _get_cluster_label(cluster)[:255],
                    cluster.color,
                    len(cluster.concept_ids),
                    cluster.keywords[:10],
                )

                # Update entities with cluster_id
                for concept_id in cluster.concept_ids:
                    await self.db.execute(
                        """
                        UPDATE entities SET cluster_id = $1 WHERE id = $2
                        """,
                        cluster.id,
                        concept_id,
                    )

            except Exception as e:
                logger.warning(f"Failed to store cluster: {e}")

    async def _store_gaps(self, project_id: str, gaps: list[StructuralGap]):
        """Store structural gaps in database."""
        if not self.db or not gaps:
            return

        logger.info(f"Storing {len(gaps)} structural gaps")

        for gap in gaps:
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
                    project_id,
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

    async def _update_centrality(
        self,
        project_id: str,
        centrality_metrics: list,
        clusters: list[ConceptCluster],
    ):
        """Update centrality metrics for entities."""
        if not self.db or not centrality_metrics:
            return

        logger.info(f"Updating centrality for {len(centrality_metrics)} entities")

        for metric in centrality_metrics:
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


# Backward compatibility alias
ScholarAGImporter = ConceptCentricScholarAGImporter
