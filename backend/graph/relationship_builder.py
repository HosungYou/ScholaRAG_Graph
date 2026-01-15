"""
Relationship Builder - Concept-Centric Knowledge Graph

Builds relationships between entities with focus on concept connectivity:
- Semantic similarity (embedding-based RELATED_TO)
- Co-occurrence within papers (CO_OCCURS_WITH)
- Learning prerequisites (PREREQUISITE_OF)
- Method applications (APPLIES_TO)
- Evidence relationships (SUPPORTS, CONTRADICTS)

Enhanced for InfraNodus-style gap detection and concept-centric design.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


@dataclass
class RelationshipCandidate:
    """Candidate relationship to be created."""

    source_id: str
    target_id: str
    relationship_type: str
    confidence: float
    properties: dict = field(default_factory=dict)
    source_type: str = ""  # Entity type of source
    target_type: str = ""  # Entity type of target

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


class ConceptCentricRelationshipBuilder:
    """
    Builds relationships for concept-centric knowledge graphs.

    Primary Relationship Types (Concept-focused):
    - RELATED_TO: Concept → Concept (semantic similarity via embeddings)
    - CO_OCCURS_WITH: Concept → Concept (appear in same paper)
    - PREREQUISITE_OF: Concept → Concept (learning order)
    - BRIDGES_GAP: Concept → Concept (AI-suggested bridge)

    Secondary Relationship Types:
    - APPLIES_TO: Method → Concept
    - SUPPORTS: Finding → Concept
    - CONTRADICTS: Finding → Concept
    - ADDRESSES: Problem → Concept
    - EVALUATES_WITH: Method → Metric

    Metadata Relationships (not for visualization):
    - AUTHORED_BY: Paper → Author
    - DISCUSSES_CONCEPT: Paper → Concept
    - USES_METHOD: Paper → Method
    """

    def __init__(
        self,
        llm_provider=None,
        similarity_threshold: float = 0.7,
        cooccurrence_threshold: int = 2,
    ):
        self.llm = llm_provider
        self.similarity_threshold = similarity_threshold
        self.cooccurrence_threshold = cooccurrence_threshold

    def build_semantic_relationships(
        self,
        concepts: list[dict],
        similarity_threshold: Optional[float] = None,
    ) -> list[RelationshipCandidate]:
        """
        Build RELATED_TO relationships based on embedding similarity.

        Args:
            concepts: List of concept dicts with 'id', 'name', 'embedding'
            similarity_threshold: Minimum cosine similarity (default: 0.7)

        Returns:
            List of RELATED_TO relationship candidates
        """
        if similarity_threshold is None:
            similarity_threshold = self.similarity_threshold

        relationships = []

        # Filter concepts with embeddings
        concepts_with_embeddings = [
            c for c in concepts
            if c.get("embedding") is not None and len(c.get("embedding", [])) > 0
        ]

        if len(concepts_with_embeddings) < 2:
            logger.warning("Too few concepts with embeddings for semantic relationships")
            return []

        logger.info(f"Computing semantic similarity for {len(concepts_with_embeddings)} concepts")

        # Stack embeddings into matrix
        embeddings = np.array([c["embedding"] for c in concepts_with_embeddings])

        # Compute pairwise cosine similarity
        similarity_matrix = cosine_similarity(embeddings)

        # Extract relationships above threshold
        for i in range(len(concepts_with_embeddings)):
            for j in range(i + 1, len(concepts_with_embeddings)):
                similarity = similarity_matrix[i, j]

                if similarity >= similarity_threshold:
                    relationships.append(
                        RelationshipCandidate(
                            source_id=concepts_with_embeddings[i]["id"],
                            target_id=concepts_with_embeddings[j]["id"],
                            relationship_type="RELATED_TO",
                            confidence=float(similarity),
                            properties={
                                "similarity_score": float(similarity),
                                "inference_method": "embedding_similarity",
                            },
                            source_type="Concept",
                            target_type="Concept",
                        )
                    )

        logger.info(f"Found {len(relationships)} semantic relationships (threshold: {similarity_threshold})")
        return relationships

    def build_cooccurrence_relationships(
        self,
        concepts: list[dict],
        paper_concepts: dict[str, list[str]],
        min_cooccurrence: Optional[int] = None,
    ) -> list[RelationshipCandidate]:
        """
        Build CO_OCCURS_WITH relationships based on paper co-occurrence.

        Args:
            concepts: List of concept dicts
            paper_concepts: Mapping of paper_id -> list of concept_ids
            min_cooccurrence: Minimum co-occurrence count (default: 2)

        Returns:
            List of CO_OCCURS_WITH relationship candidates
        """
        if min_cooccurrence is None:
            min_cooccurrence = self.cooccurrence_threshold

        relationships = []

        # Count co-occurrences
        cooccurrence_count = defaultdict(int)
        cooccurrence_papers = defaultdict(list)

        for paper_id, concept_ids in paper_concepts.items():
            for i, c1 in enumerate(concept_ids):
                for c2 in concept_ids[i + 1:]:
                    pair = tuple(sorted([c1, c2]))
                    cooccurrence_count[pair] += 1
                    cooccurrence_papers[pair].append(paper_id)

        # Create relationships for significant co-occurrences
        for pair, count in cooccurrence_count.items():
            if count >= min_cooccurrence:
                relationships.append(
                    RelationshipCandidate(
                        source_id=pair[0],
                        target_id=pair[1],
                        relationship_type="CO_OCCURS_WITH",
                        confidence=min(1.0, count / 10),  # Cap at 10 co-occurrences
                        properties={
                            "co_occurrence_count": count,
                            "paper_ids": cooccurrence_papers[pair][:10],  # Keep top 10
                        },
                        source_type="Concept",
                        target_type="Concept",
                    )
                )

        logger.info(f"Found {len(relationships)} co-occurrence relationships (min: {min_cooccurrence})")
        return relationships

    def build_method_concept_relationships(
        self,
        methods: list[dict],
        concepts: list[dict],
        paper_methods: dict[str, list[str]],
        paper_concepts: dict[str, list[str]],
    ) -> list[RelationshipCandidate]:
        """
        Build APPLIES_TO relationships between methods and concepts.

        A method APPLIES_TO a concept if they frequently appear in the same papers.

        Args:
            methods: List of method dicts
            concepts: List of concept dicts
            paper_methods: Mapping of paper_id -> list of method_ids
            paper_concepts: Mapping of paper_id -> list of concept_ids

        Returns:
            List of APPLIES_TO relationship candidates
        """
        relationships = []

        # Count method-concept co-occurrences
        method_concept_count = defaultdict(int)

        for paper_id in set(paper_methods.keys()) & set(paper_concepts.keys()):
            methods_in_paper = paper_methods[paper_id]
            concepts_in_paper = paper_concepts[paper_id]

            for method_id in methods_in_paper:
                for concept_id in concepts_in_paper:
                    method_concept_count[(method_id, concept_id)] += 1

        # Create relationships for significant co-occurrences
        for (method_id, concept_id), count in method_concept_count.items():
            if count >= 2:  # At least 2 papers
                relationships.append(
                    RelationshipCandidate(
                        source_id=method_id,
                        target_id=concept_id,
                        relationship_type="APPLIES_TO",
                        confidence=min(1.0, count / 5),
                        properties={"paper_count": count},
                        source_type="Method",
                        target_type="Concept",
                    )
                )

        logger.info(f"Found {len(relationships)} method-concept relationships")
        return relationships

    def build_finding_concept_relationships(
        self,
        findings: list[dict],
        concepts: list[dict],
    ) -> list[RelationshipCandidate]:
        """
        Build SUPPORTS and CONTRADICTS relationships from findings to concepts.

        Uses the supports_concepts and contradicts_concepts fields in findings.

        Args:
            findings: List of finding dicts with supports_concepts, contradicts_concepts
            concepts: List of concept dicts

        Returns:
            List of SUPPORTS/CONTRADICTS relationship candidates
        """
        relationships = []
        concept_ids = {c["id"] for c in concepts}

        for finding in findings:
            finding_id = finding["id"]

            # SUPPORTS relationships
            for concept_id in finding.get("supports_concepts", []):
                if concept_id in concept_ids:
                    relationships.append(
                        RelationshipCandidate(
                            source_id=finding_id,
                            target_id=concept_id,
                            relationship_type="SUPPORTS",
                            confidence=finding.get("confidence", 0.8),
                            properties={
                                "effect_size": finding.get("effect_size"),
                                "significance": finding.get("significance"),
                            },
                            source_type="Finding",
                            target_type="Concept",
                        )
                    )

            # CONTRADICTS relationships
            for concept_id in finding.get("contradicts_concepts", []):
                if concept_id in concept_ids:
                    relationships.append(
                        RelationshipCandidate(
                            source_id=finding_id,
                            target_id=concept_id,
                            relationship_type="CONTRADICTS",
                            confidence=finding.get("confidence", 0.8),
                            properties={
                                "effect_size": finding.get("effect_size"),
                                "significance": finding.get("significance"),
                            },
                            source_type="Finding",
                            target_type="Concept",
                        )
                    )

        logger.info(f"Found {len(relationships)} finding-concept relationships")
        return relationships

    def build_problem_concept_relationships(
        self,
        problems: list[dict],
        concepts: list[dict],
        paper_problems: dict[str, list[str]],
        paper_concepts: dict[str, list[str]],
    ) -> list[RelationshipCandidate]:
        """
        Build ADDRESSES relationships between problems and concepts.

        Args:
            problems: List of problem dicts
            concepts: List of concept dicts
            paper_problems: Mapping of paper_id -> list of problem_ids
            paper_concepts: Mapping of paper_id -> list of concept_ids

        Returns:
            List of ADDRESSES relationship candidates
        """
        relationships = []

        # Count problem-concept co-occurrences
        problem_concept_count = defaultdict(int)

        for paper_id in set(paper_problems.keys()) & set(paper_concepts.keys()):
            problems_in_paper = paper_problems[paper_id]
            concepts_in_paper = paper_concepts[paper_id]

            for problem_id in problems_in_paper:
                for concept_id in concepts_in_paper:
                    problem_concept_count[(problem_id, concept_id)] += 1

        # Create relationships
        for (problem_id, concept_id), count in problem_concept_count.items():
            if count >= 1:  # Any co-occurrence
                relationships.append(
                    RelationshipCandidate(
                        source_id=problem_id,
                        target_id=concept_id,
                        relationship_type="ADDRESSES",
                        confidence=min(1.0, count / 3),
                        properties={"paper_count": count},
                        source_type="Problem",
                        target_type="Concept",
                    )
                )

        logger.info(f"Found {len(relationships)} problem-concept relationships")
        return relationships

    async def infer_prerequisite_relationships(
        self,
        concepts: list[dict],
        existing_relationships: list[RelationshipCandidate],
    ) -> list[RelationshipCandidate]:
        """
        Infer PREREQUISITE_OF relationships using LLM.

        Identifies concepts that are foundational to understanding others.

        Args:
            concepts: List of concept dicts with 'name' and 'definition'
            existing_relationships: Already established relationships

        Returns:
            List of PREREQUISITE_OF relationship candidates
        """
        if not self.llm or len(concepts) < 2:
            return []

        relationships = []

        # Find highly connected concept pairs that might have prerequisite order
        related_pairs = [
            (r.source_id, r.target_id)
            for r in existing_relationships
            if r.relationship_type in ["RELATED_TO", "CO_OCCURS_WITH"]
            and r.confidence > 0.5
        ]

        if not related_pairs:
            return []

        # Build concept name lookup
        concept_by_id = {c["id"]: c for c in concepts}

        # Process in batches
        batch_size = 10
        for i in range(0, min(len(related_pairs), 50), batch_size):  # Max 50 pairs
            batch = related_pairs[i:i + batch_size]

            pair_descriptions = []
            for src_id, tgt_id in batch:
                src = concept_by_id.get(src_id, {})
                tgt = concept_by_id.get(tgt_id, {})

                if src and tgt:
                    pair_descriptions.append(
                        f"A: {src.get('name', 'Unknown')} - {src.get('definition', 'No definition')[:100]}\n"
                        f"B: {tgt.get('name', 'Unknown')} - {tgt.get('definition', 'No definition')[:100]}"
                    )

            if not pair_descriptions:
                continue

            prompt = f"""Analyze these concept pairs from academic literature.
For each pair, determine if one concept is a PREREQUISITE for understanding the other.

{chr(10).join(f'{i+1}. {desc}' for i, desc in enumerate(pair_descriptions))}

For each pair, respond with one of:
- "A->B" if A is a prerequisite for B
- "B->A" if B is a prerequisite for A
- "NONE" if neither is a prerequisite

Return ONLY the answers, one per line, in format: "1. A->B" or "1. NONE"
"""

            try:
                response = await self.llm.generate(prompt)

                # Parse response
                for line in response.strip().split("\n"):
                    try:
                        parts = line.split(".")
                        if len(parts) < 2:
                            continue

                        idx = int(parts[0].strip()) - 1
                        answer = parts[1].strip().upper()

                        if idx < 0 or idx >= len(batch):
                            continue

                        src_id, tgt_id = batch[idx]

                        if answer == "A->B":
                            relationships.append(
                                RelationshipCandidate(
                                    source_id=src_id,
                                    target_id=tgt_id,
                                    relationship_type="PREREQUISITE_OF",
                                    confidence=0.7,
                                    properties={"inference_method": "llm"},
                                    source_type="Concept",
                                    target_type="Concept",
                                )
                            )
                        elif answer == "B->A":
                            relationships.append(
                                RelationshipCandidate(
                                    source_id=tgt_id,
                                    target_id=src_id,
                                    relationship_type="PREREQUISITE_OF",
                                    confidence=0.7,
                                    properties={"inference_method": "llm"},
                                    source_type="Concept",
                                    target_type="Concept",
                                )
                            )
                    except (ValueError, IndexError):
                        continue

            except Exception as e:
                logger.error(f"Failed to infer prerequisites: {e}")
                continue

        logger.info(f"Inferred {len(relationships)} prerequisite relationships")
        return relationships

    def build_bridge_relationships(
        self,
        bridge_concept_id: str,
        cluster_a_concept_ids: list[str],
        cluster_b_concept_ids: list[str],
    ) -> list[RelationshipCandidate]:
        """
        Build BRIDGES_GAP relationships for gap-bridging concepts.

        Args:
            bridge_concept_id: The concept that bridges the gap
            cluster_a_concept_ids: Concepts in cluster A
            cluster_b_concept_ids: Concepts in cluster B

        Returns:
            List of BRIDGES_GAP relationship candidates
        """
        relationships = []

        # Connect bridge to top concepts in each cluster
        for concept_id in cluster_a_concept_ids[:3]:
            relationships.append(
                RelationshipCandidate(
                    source_id=bridge_concept_id,
                    target_id=concept_id,
                    relationship_type="BRIDGES_GAP",
                    confidence=0.6,
                    properties={"cluster": "A", "is_bridge": True},
                    source_type="Concept",
                    target_type="Concept",
                )
            )

        for concept_id in cluster_b_concept_ids[:3]:
            relationships.append(
                RelationshipCandidate(
                    source_id=bridge_concept_id,
                    target_id=concept_id,
                    relationship_type="BRIDGES_GAP",
                    confidence=0.6,
                    properties={"cluster": "B", "is_bridge": True},
                    source_type="Concept",
                    target_type="Concept",
                )
            )

        return relationships

    async def build_all_relationships(
        self,
        entities_by_type: dict[str, list[dict]],
        paper_entities: dict[str, dict[str, list[str]]],
        include_prerequisites: bool = False,
    ) -> list[RelationshipCandidate]:
        """
        Build all relationships for the knowledge graph.

        Args:
            entities_by_type: Dict mapping entity type to list of entities
                {"Concept": [...], "Method": [...], "Finding": [...], etc.}
            paper_entities: Dict mapping paper_id to entity type to entity_ids
                {"paper1": {"Concept": ["c1", "c2"], "Method": ["m1"]}, ...}
            include_prerequisites: Whether to infer prerequisite relationships (slow)

        Returns:
            List of all relationship candidates
        """
        all_relationships = []

        concepts = entities_by_type.get("Concept", [])
        methods = entities_by_type.get("Method", [])
        findings = entities_by_type.get("Finding", [])
        problems = entities_by_type.get("Problem", [])

        # Build paper_* mappings
        paper_concepts = {
            pid: entities.get("Concept", [])
            for pid, entities in paper_entities.items()
        }
        paper_methods = {
            pid: entities.get("Method", [])
            for pid, entities in paper_entities.items()
        }
        paper_problems = {
            pid: entities.get("Problem", [])
            for pid, entities in paper_entities.items()
        }

        # 1. Semantic relationships (Concept-Concept)
        semantic_rels = self.build_semantic_relationships(concepts)
        all_relationships.extend(semantic_rels)

        # 2. Co-occurrence relationships (Concept-Concept)
        cooccurrence_rels = self.build_cooccurrence_relationships(concepts, paper_concepts)
        all_relationships.extend(cooccurrence_rels)

        # 3. Method-Concept relationships
        method_rels = self.build_method_concept_relationships(
            methods, concepts, paper_methods, paper_concepts
        )
        all_relationships.extend(method_rels)

        # 4. Finding-Concept relationships
        finding_rels = self.build_finding_concept_relationships(findings, concepts)
        all_relationships.extend(finding_rels)

        # 5. Problem-Concept relationships
        problem_rels = self.build_problem_concept_relationships(
            problems, concepts, paper_problems, paper_concepts
        )
        all_relationships.extend(problem_rels)

        # 6. Prerequisite relationships (optional, uses LLM)
        if include_prerequisites and self.llm:
            prerequisite_rels = await self.infer_prerequisite_relationships(
                concepts, all_relationships
            )
            all_relationships.extend(prerequisite_rels)

        # Deduplicate
        all_relationships = self.deduplicate_relationships(all_relationships)

        logger.info(f"Built {len(all_relationships)} total relationships")
        return all_relationships

    def deduplicate_relationships(
        self,
        relationships: list[RelationshipCandidate],
    ) -> list[RelationshipCandidate]:
        """
        Remove duplicate relationships, keeping highest confidence.

        For bidirectional relationships (RELATED_TO, CO_OCCURS_WITH),
        normalizes direction to ensure only one exists.
        """
        unique = {}
        bidirectional_types = {"RELATED_TO", "CO_OCCURS_WITH"}

        for rel in relationships:
            # Normalize bidirectional relationships
            if rel.relationship_type in bidirectional_types:
                key = (
                    tuple(sorted([rel.source_id, rel.target_id])),
                    rel.relationship_type,
                )
            else:
                key = (rel.source_id, rel.target_id, rel.relationship_type)

            if key not in unique or rel.confidence > unique[key].confidence:
                unique[key] = rel

        return list(unique.values())


# Backward compatibility alias
RelationshipBuilder = ConceptCentricRelationshipBuilder
