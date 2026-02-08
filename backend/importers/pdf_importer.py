"""
Direct PDF Importer - Import PDFs without ScholaRAG project structure

This importer allows users to upload PDF files directly and build a knowledge graph
without needing a config.yaml or ScholaRAG folder structure.

Process:
1. Accept uploaded PDF file(s)
2. Extract text using PyMuPDF
3. Extract metadata (title, authors, year) from PDF properties and first page
4. Use LLM to extract concepts, methods, findings from full text
5. Create project and paper records using GraphStore
6. Build knowledge graph
"""

import logging
import re
import tempfile
import os
from pathlib import Path
from typing import Optional, List, Callable, Dict, Any
from uuid import uuid4
from datetime import datetime

import fitz  # PyMuPDF

from database import Database
from graph.graph_store import GraphStore
from graph.entity_extractor import EntityExtractor
from graph.entity_resolution import EntityResolutionService
from graph.relationship_builder import ConceptCentricRelationshipBuilder
from importers.semantic_chunker import SemanticChunker

logger = logging.getLogger(__name__)


class PDFImporter:
    """Import PDF files directly without ScholaRAG project structure."""

    def __init__(
        self,
        llm_provider: str = "anthropic",
        llm_model: str = "claude-3-5-haiku-20241022",
        db_connection: Optional[Database] = None,
        graph_store: Optional[GraphStore] = None,
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
    ):
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.db = db_connection
        self.graph_store = graph_store
        self.progress_callback = progress_callback

        # Initialize entity extractor and semantic chunker
        self.entity_extractor = EntityExtractor(llm_provider=llm_provider)
        self.entity_resolution = EntityResolutionService(llm_provider=self.entity_extractor.llm)
        self.semantic_chunker = SemanticChunker()

    def _update_progress(self, stage: str, progress: float, message: str):
        """Update import progress."""
        if self.progress_callback:
            self.progress_callback(stage, progress, message)
        logger.info(f"[{stage}] {progress:.0%} - {message}")

    def _accumulate_resolution_stats(self, stats: Dict[str, Any], resolution) -> None:
        """Accumulate shared entity-resolution metrics into importer stats."""
        stats["raw_entities_extracted"] = stats.get("raw_entities_extracted", 0) + int(resolution.raw_entities)
        stats["entities_after_resolution"] = stats.get("entities_after_resolution", 0) + int(resolution.resolved_entities)
        stats["merges_applied"] = stats.get("merges_applied", 0) + int(resolution.merged_entities)
        stats["llm_pairs_reviewed"] = stats.get("llm_pairs_reviewed", 0) + int(
            getattr(resolution, "llm_pairs_reviewed", 0)
        )
        stats["llm_pairs_confirmed"] = stats.get("llm_pairs_confirmed", 0) + int(
            getattr(resolution, "llm_pairs_confirmed", 0)
        )
        stats["potential_false_merge_count"] = stats.get("potential_false_merge_count", 0) + int(
            getattr(resolution, "potential_false_merge_count", 0)
        )
        stats.setdefault("potential_false_merge_samples", [])
        samples = getattr(resolution, "potential_false_merge_samples", []) or []
        if samples:
            stats["potential_false_merge_samples"].extend(samples)
            stats["potential_false_merge_samples"] = stats["potential_false_merge_samples"][:15]

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract all text from a PDF file."""
        try:
            doc = fitz.open(pdf_path)
            text_parts = []

            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)

            doc.close()
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""

    def extract_metadata_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF file."""
        metadata = {
            "title": None,
            "authors": [],
            "year": None,
            "abstract": None,
        }

        try:
            doc = fitz.open(pdf_path)

            # Try to get metadata from PDF properties
            pdf_metadata = doc.metadata
            if pdf_metadata:
                if pdf_metadata.get("title"):
                    metadata["title"] = pdf_metadata["title"]
                if pdf_metadata.get("author"):
                    # Authors might be comma or semicolon separated
                    author_str = pdf_metadata["author"]
                    authors = re.split(r'[;,]', author_str)
                    metadata["authors"] = [a.strip() for a in authors if a.strip()]
                if pdf_metadata.get("creationDate"):
                    # Try to extract year from creation date
                    date_str = pdf_metadata["creationDate"]
                    year_match = re.search(r'(\d{4})', date_str)
                    if year_match:
                        metadata["year"] = int(year_match.group(1))

            # If title not found, try to extract from first page
            if not metadata["title"] and doc.page_count > 0:
                first_page_text = doc[0].get_text()
                lines = [l.strip() for l in first_page_text.split('\n') if l.strip()]

                # First substantial line is often the title
                for line in lines[:5]:  # Check first 5 lines
                    if len(line) > 10 and len(line) < 200:  # Reasonable title length
                        metadata["title"] = line
                        break

            # Try to extract abstract
            full_text = self.extract_text_from_pdf(pdf_path)
            abstract_match = re.search(
                r'abstract[:\s]*(.{100,2000}?)(?=\n\n|\nintroduction|\n1\.)',
                full_text,
                re.IGNORECASE | re.DOTALL
            )
            if abstract_match:
                metadata["abstract"] = abstract_match.group(1).strip()

            doc.close()

        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")

        # Use filename as fallback title
        if not metadata["title"]:
            metadata["title"] = Path(pdf_path).stem.replace("_", " ").replace("-", " ")

        return metadata

    async def import_single_pdf(
        self,
        pdf_content: bytes,
        filename: str,
        project_name: Optional[str] = None,
        research_question: Optional[str] = None,
        extract_concepts: bool = True,
    ) -> Dict[str, Any]:
        """
        Import a single PDF file and create a knowledge graph.

        Args:
            pdf_content: Raw PDF file bytes
            filename: Original filename
            project_name: Optional project name (defaults to filename)
            research_question: Optional research question (will be generated if not provided)
            extract_concepts: Whether to use LLM for concept extraction

        Returns:
            Import result with project_id and statistics
        """
        self._update_progress("starting", 0.0, "Starting PDF import...")

        # Save PDF to temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(pdf_content)
            tmp_path = tmp_file.name

        try:
            # Extract text and metadata
            self._update_progress("extracting", 0.1, "Extracting text from PDF...")
            full_text = self.extract_text_from_pdf(tmp_path)

            if not full_text or len(full_text) < 100:
                return {
                    "success": False,
                    "error": "Could not extract text from PDF. The file may be scanned or image-based."
                }

            self._update_progress("extracting", 0.2, "Extracting metadata...")
            metadata = self.extract_metadata_from_pdf(tmp_path)

            # Generate project info
            project_id = str(uuid4())
            project_name_final = project_name or metadata["title"] or Path(filename).stem

            # Generate research question if not provided
            if not research_question:
                research_question = f"Analysis of: {metadata['title'] or filename}"

            self._update_progress("creating", 0.3, "Creating project...")

            # Create project in database
            if self.db:
                await self.db.execute(
                    """
                    INSERT INTO projects (id, name, research_question, created_at)
                    VALUES ($1, $2, $3, $4)
                    """,
                    project_id, project_name_final, research_question, datetime.utcnow()
                )

            self._update_progress("storing", 0.4, "Storing paper metadata...")

            # Create Paper entity using GraphStore
            paper_id = None
            if self.graph_store:
                paper_id = await self.graph_store.add_entity(
                    project_id=project_id,
                    entity_type="Paper",
                    name=metadata["title"] or filename,
                    properties={
                        "title": metadata["title"],
                        "abstract": metadata.get("abstract") or full_text[:2000],
                        "year": metadata.get("year"),
                        "source": "direct_upload",
                        "filename": filename,
                        "full_text_preview": full_text[:5000],
                    },
                )

                # Create Author entities and relationships
                author_ids = []
                for author_name in metadata.get("authors", []):
                    author_id = await self.graph_store.add_entity(
                        project_id=project_id,
                        entity_type="Author",
                        name=author_name,
                        properties={
                            "name": author_name,
                        },
                    )
                    author_ids.append(author_id)

                    # Create AUTHORED_BY relationship
                    await self.graph_store.add_relationship(
                        project_id=project_id,
                        source_id=paper_id,
                        target_id=author_id,
                        relationship_type="AUTHORED_BY",
                        properties={},
                    )

            # Extract concepts if enabled
            stats = {
                "papers_imported": 1,
                "authors_extracted": len(metadata.get("authors", [])),
                "concepts_extracted": 0,
                "methods_extracted": 0,
                "findings_extracted": 0,
                "raw_entities_extracted": 0,
                "entities_after_resolution": 0,
                "merges_applied": 0,
                "llm_pairs_reviewed": 0,
                "llm_pairs_confirmed": 0,
                "potential_false_merge_count": 0,
                "potential_false_merge_samples": [],
            }

            if extract_concepts and self.graph_store:
                self._update_progress("analyzing", 0.5, "Extracting concepts with LLM...")

                try:
                    # Use abstract or first part of text for extraction
                    text_for_extraction = metadata.get("abstract") or full_text[:4000]

                    extraction_result = await self.entity_extractor.extract_from_paper(
                        title=metadata["title"] or filename,
                        abstract=text_for_extraction,
                        paper_id=paper_id,
                    )

                    self._update_progress("storing", 0.7, "Storing extracted entities...")

                    # Store entities from all categories
                    all_entities = (
                        extraction_result.get("concepts", []) +
                        extraction_result.get("methods", []) +
                        extraction_result.get("findings", [])
                    )
                    resolved_entities, resolution = await self.entity_resolution.resolve_entities_async(
                        all_entities,
                        use_llm_confirmation=True,
                    )
                    self._accumulate_resolution_stats(stats, resolution)

                    for entity in resolved_entities:
                        # Get entity type as string
                        entity_type_str = str(entity.entity_type.value) if hasattr(entity.entity_type, 'value') else str(entity.entity_type)

                        entity_id = await self.graph_store.add_entity(
                            project_id=project_id,
                            entity_type=entity_type_str,
                            name=self.entity_resolution.canonicalize_name(entity.name),
                            properties={
                                "definition": getattr(entity, 'definition', ''),
                                "description": getattr(entity, 'description', ''),
                                "source_paper_ids": [paper_id] if paper_id else [],
                                "confidence": getattr(entity, 'confidence', 0.7),
                            },
                        )

                        # Create relationship from Paper to this entity
                        if paper_id and entity_id:
                            rel_type = {
                                "Concept": "DISCUSSES_CONCEPT",
                                "Method": "USES_METHOD",
                                "Finding": "REPORTS_FINDING",
                            }.get(entity_type_str, "RELATED_TO")

                            await self.graph_store.add_relationship(
                                project_id=project_id,
                                source_id=paper_id,
                                target_id=entity_id,
                                relationship_type=rel_type,
                                properties={"confidence": getattr(entity, 'confidence', 0.7)},
                            )

                        # Update stats
                        if entity_type_str == "Concept":
                            stats["concepts_extracted"] += 1
                        elif entity_type_str == "Method":
                            stats["methods_extracted"] += 1
                        elif entity_type_str == "Finding":
                            stats["findings_extracted"] += 1

                    self._update_progress("building", 0.85, "Building relationships...")

                    # Build additional relationships between entities
                    builder = ConceptCentricRelationshipBuilder(
                        llm_provider=self.entity_extractor.llm,
                    )
                    # Backward-compatible guard: some builder versions do not expose build_relationships().
                    if hasattr(builder, "build_relationships"):
                        await builder.build_relationships(project_id=project_id)

                except Exception as e:
                    logger.warning(f"Entity extraction failed: {e}")
                    # Continue without entities - still create the project

            if stats["raw_entities_extracted"] > 0:
                stats["canonicalization_rate"] = (
                    stats["merges_applied"] / stats["raw_entities_extracted"]
                )
            else:
                stats["canonicalization_rate"] = 0.0

            self._update_progress("complete", 1.0, "Import complete!")

            return {
                "success": True,
                "project_id": project_id,
                "paper_id": paper_id,
                "stats": stats,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"PDF import failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass

    async def import_multiple_pdfs(
        self,
        pdf_files: List[tuple],  # List of (filename, content) tuples
        project_name: str,
        research_question: Optional[str] = None,
        extract_concepts: bool = True,
    ) -> Dict[str, Any]:
        """
        Import multiple PDF files into a single project.

        Args:
            pdf_files: List of (filename, content) tuples
            project_name: Name for the project
            research_question: Optional research question
            extract_concepts: Whether to use LLM for concept extraction

        Returns:
            Import result with project_id and statistics
        """
        self._update_progress("starting", 0.0, f"Starting import of {len(pdf_files)} PDFs...")

        # Create project
        project_id = str(uuid4())
        research_question = research_question or f"Literature review: {project_name}"

        if self.db:
            await self.db.execute(
                """
                INSERT INTO projects (id, name, research_question, created_at)
                VALUES ($1, $2, $3, $4)
                """,
                project_id, project_name, research_question, datetime.utcnow()
            )

        total_stats = {
            "papers_imported": 0,
            "papers_failed": 0,
            "authors_extracted": 0,
            "concepts_extracted": 0,
            "methods_extracted": 0,
            "findings_extracted": 0,
            "raw_entities_extracted": 0,
            "entities_after_resolution": 0,
            "merges_applied": 0,
            "llm_pairs_reviewed": 0,
            "llm_pairs_confirmed": 0,
            "potential_false_merge_count": 0,
            "potential_false_merge_samples": [],
        }

        for i, (filename, content) in enumerate(pdf_files):
            progress = 0.1 + (0.8 * (i / len(pdf_files)))
            self._update_progress(
                "importing",
                progress,
                f"Processing {i+1}/{len(pdf_files)}: {filename}"
            )

            # Import single PDF (but use existing project)
            result = await self._import_pdf_to_project(
                pdf_content=content,
                filename=filename,
                project_id=project_id,
                extract_concepts=extract_concepts,
            )

            if result["success"]:
                total_stats["papers_imported"] += 1
                for key in [
                    "authors_extracted",
                    "concepts_extracted",
                    "methods_extracted",
                    "findings_extracted",
                    "raw_entities_extracted",
                    "entities_after_resolution",
                    "merges_applied",
                    "llm_pairs_reviewed",
                    "llm_pairs_confirmed",
                    "potential_false_merge_count",
                ]:
                    total_stats[key] += result.get("stats", {}).get(key, 0)
                samples = result.get("stats", {}).get("potential_false_merge_samples", []) or []
                if samples:
                    total_stats["potential_false_merge_samples"].extend(samples)
                    total_stats["potential_false_merge_samples"] = total_stats[
                        "potential_false_merge_samples"
                    ][:15]
            else:
                total_stats["papers_failed"] += 1

        # Build relationships across all papers
        if extract_concepts and self.graph_store:
            self._update_progress("building", 0.9, "Building cross-paper relationships...")
            builder = ConceptCentricRelationshipBuilder(
                llm_provider=self.entity_extractor.llm,
            )
            if hasattr(builder, "build_relationships"):
                await builder.build_relationships(project_id=project_id)

        if total_stats["raw_entities_extracted"] > 0:
            total_stats["canonicalization_rate"] = (
                total_stats["merges_applied"] / total_stats["raw_entities_extracted"]
            )
        else:
            total_stats["canonicalization_rate"] = 0.0

        self._update_progress("complete", 1.0, "Import complete!")

        return {
            "success": True,
            "project_id": project_id,
            "stats": total_stats,
        }

    async def _import_pdf_to_project(
        self,
        pdf_content: bytes,
        filename: str,
        project_id: str,
        extract_concepts: bool = True,
    ) -> Dict[str, Any]:
        """Import a single PDF into an existing project."""
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(pdf_content)
            tmp_path = tmp_file.name

        try:
            full_text = self.extract_text_from_pdf(tmp_path)
            if not full_text or len(full_text) < 100:
                return {"success": False, "error": "Could not extract text"}

            metadata = self.extract_metadata_from_pdf(tmp_path)

            stats = {
                "authors_extracted": 0,
                "concepts_extracted": 0,
                "methods_extracted": 0,
                "findings_extracted": 0,
                "chunks_created": 0,
                "raw_entities_extracted": 0,
                "entities_after_resolution": 0,
                "merges_applied": 0,
                "llm_pairs_reviewed": 0,
                "llm_pairs_confirmed": 0,
                "potential_false_merge_count": 0,
                "potential_false_merge_samples": [],
            }
            stored_entity_keys = set()

            # Create Paper entity using GraphStore
            paper_id = None
            if self.graph_store:
                paper_id = await self.graph_store.add_entity(
                    project_id=project_id,
                    entity_type="Paper",
                    name=metadata["title"] or filename,
                    properties={
                        "title": metadata["title"],
                        "abstract": metadata.get("abstract") or full_text[:2000],
                        "year": metadata.get("year"),
                        "source": "direct_upload",
                        "filename": filename,
                    },
                )

                # Create Author entities and relationships
                for author_name in metadata.get("authors", []):
                    author_id = await self.graph_store.add_entity(
                        project_id=project_id,
                        entity_type="Author",
                        name=author_name,
                        properties={"name": author_name},
                    )
                    stats["authors_extracted"] += 1

                    # Create AUTHORED_BY relationship
                    await self.graph_store.add_relationship(
                        project_id=project_id,
                        source_id=paper_id,
                        target_id=author_id,
                        relationship_type="AUTHORED_BY",
                        properties={},
                    )

            # Semantic Chunking: Create hierarchical chunks from full text
            chunks_created = 0
            if paper_id and self.graph_store and len(full_text) > 500:
                try:
                    # Chunk the full text with section detection
                    chunked_result = self.semantic_chunker.chunk_academic_text(
                        text=full_text,
                        paper_id=paper_id,
                        detect_sections=True,
                        max_chunk_tokens=400,
                    )
                    
                    if chunked_result.get("chunks"):
                        # Store chunks using graph_store
                        await self.graph_store.store_chunks(
                            project_id=project_id,
                            paper_id=paper_id,
                            chunks=chunked_result["chunks"],
                        )
                        chunks_created = len(chunked_result["chunks"])
                        logger.info(f"Created {chunks_created} semantic chunks for {filename}")
                        
                        # Use section-aware extraction if sections detected
                        if chunked_result.get("sections") and extract_concepts:
                            try:
                                section_entities = await self.entity_extractor.extract_from_sections(
                                    sections=chunked_result["sections"],
                                    paper_id=paper_id,
                                )
                                resolved_section_entities, section_resolution = await self.entity_resolution.resolve_entities_async(
                                    section_entities,
                                    use_llm_confirmation=True,
                                )
                                self._accumulate_resolution_stats(stats, section_resolution)
                                # Merge section entities into main extraction
                                if resolved_section_entities:
                                    for entity in resolved_section_entities:
                                        entity_type_str = str(entity.entity_type.value) if hasattr(entity.entity_type, 'value') else str(entity.entity_type)
                                        canonical_name = self.entity_resolution.canonicalize_name(entity.name)
                                        entity_key = f"{entity_type_str}:{canonical_name}"
                                        if entity_key in stored_entity_keys:
                                            stats["merges_applied"] += 1
                                            continue

                                        entity_id = await self.graph_store.add_entity(
                                            project_id=project_id,
                                            entity_type=entity_type_str,
                                            name=canonical_name,
                                            properties={
                                                "definition": getattr(entity, 'definition', ''),
                                                "description": getattr(entity, 'description', ''),
                                                "source_paper_ids": [paper_id],
                                                "confidence": getattr(entity, 'confidence', 0.7),
                                                "source_section": getattr(entity, 'source_section', ''),
                                            },
                                        )
                                        if paper_id and entity_id:
                                            rel_type = {
                                                "Concept": "DISCUSSES_CONCEPT",
                                                "Method": "USES_METHOD",
                                                "Finding": "REPORTS_FINDING",
                                                "Problem": "ADDRESSES_PROBLEM",
                                                "Innovation": "PROPOSES_INNOVATION",
                                                "Dataset": "USES_DATASET",
                                            }.get(entity_type_str, "RELATED_TO")
                                            await self.graph_store.add_relationship(
                                                project_id=project_id,
                                                source_id=paper_id,
                                                target_id=entity_id,
                                                relationship_type=rel_type,
                                                properties={"confidence": getattr(entity, 'confidence', 0.7)},
                                            )
                                        if entity_type_str == "Concept":
                                            stats["concepts_extracted"] += 1
                                        elif entity_type_str == "Method":
                                            stats["methods_extracted"] += 1
                                        elif entity_type_str == "Finding":
                                            stats["findings_extracted"] += 1
                                        stored_entity_keys.add(entity_key)
                            except Exception as e:
                                logger.warning(f"Section-aware extraction failed: {e}")
                except Exception as e:
                    logger.warning(f"Semantic chunking failed for {filename}: {e}")
            
            stats["chunks_created"] = chunks_created

            if extract_concepts and self.graph_store:
                try:
                    text_for_extraction = metadata.get("abstract") or full_text[:4000]
                    extraction_result = await self.entity_extractor.extract_from_paper(
                        title=metadata["title"] or filename,
                        abstract=text_for_extraction,
                        paper_id=paper_id,
                    )

                    # Store entities from all categories
                    all_entities = (
                        extraction_result.get("concepts", []) +
                        extraction_result.get("methods", []) +
                        extraction_result.get("findings", [])
                    )
                    resolved_entities, resolution = await self.entity_resolution.resolve_entities_async(
                        all_entities,
                        use_llm_confirmation=True,
                    )
                    self._accumulate_resolution_stats(stats, resolution)

                    for entity in resolved_entities:
                        # Get entity type as string
                        entity_type_str = str(entity.entity_type.value) if hasattr(entity.entity_type, 'value') else str(entity.entity_type)
                        canonical_name = self.entity_resolution.canonicalize_name(entity.name)
                        entity_key = f"{entity_type_str}:{canonical_name}"
                        if entity_key in stored_entity_keys:
                            stats["merges_applied"] += 1
                            continue

                        entity_id = await self.graph_store.add_entity(
                            project_id=project_id,
                            entity_type=entity_type_str,
                            name=canonical_name,
                            properties={
                                "definition": getattr(entity, 'definition', ''),
                                "description": getattr(entity, 'description', ''),
                                "source_paper_ids": [paper_id] if paper_id else [],
                                "confidence": getattr(entity, 'confidence', 0.7),
                            },
                        )

                        # Create relationship from Paper to this entity
                        if paper_id and entity_id:
                            rel_type = {
                                "Concept": "DISCUSSES_CONCEPT",
                                "Method": "USES_METHOD",
                                "Finding": "REPORTS_FINDING",
                            }.get(entity_type_str, "RELATED_TO")

                            await self.graph_store.add_relationship(
                                project_id=project_id,
                                source_id=paper_id,
                                target_id=entity_id,
                                relationship_type=rel_type,
                                properties={"confidence": getattr(entity, 'confidence', 0.7)},
                            )

                        if entity_type_str == "Concept":
                            stats["concepts_extracted"] += 1
                        elif entity_type_str == "Method":
                            stats["methods_extracted"] += 1
                        elif entity_type_str == "Finding":
                            stats["findings_extracted"] += 1
                        stored_entity_keys.add(entity_key)

                except Exception as e:
                    logger.warning(f"Entity extraction failed for {filename}: {e}")

            if stats["raw_entities_extracted"] > 0:
                stats["canonicalization_rate"] = (
                    stats["merges_applied"] / stats["raw_entities_extracted"]
                )
            else:
                stats["canonicalization_rate"] = 0.0

            return {"success": True, "paper_id": paper_id, "stats": stats}

        except Exception as e:
            logger.error(f"Failed to import {filename}: {e}")
            return {"success": False, "error": str(e)}
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
