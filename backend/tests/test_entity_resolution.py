"""
Tests for entity resolution behavior in academic domain ingestion.
"""

import json
import re

import pytest

from graph.entity_extractor import ExtractedEntity, EntityType
from graph.entity_resolution import EntityResolutionService


def test_resolve_entities_merges_acronym_with_long_form():
    service = EntityResolutionService()
    entities = [
        ExtractedEntity(
            entity_type=EntityType.CONCEPT,
            name="Graph Convolutional Network (GCN)",
            confidence=0.9,
            source_paper_id="p1",
        ),
        ExtractedEntity(
            entity_type=EntityType.CONCEPT,
            name="GCN",
            confidence=0.8,
            source_paper_id="p2",
        ),
    ]

    resolved, stats = service.resolve_entities(entities)
    assert len(resolved) == 1
    assert stats.merged_entities == 1
    assert resolved[0].name == "graph convolutional network"
    assert set(resolved[0].properties["source_paper_ids"]) == {"p1", "p2"}
    assert resolved[0].properties["alias_count"] == 2


def test_resolve_entities_merges_hyphen_and_compound_variants():
    service = EntityResolutionService()
    entities = [
        ExtractedEntity(entity_type=EntityType.METHOD, name="Fine-Tuning", confidence=0.9),
        ExtractedEntity(entity_type=EntityType.METHOD, name="finetuning", confidence=0.85),
    ]

    resolved, stats = service.resolve_entities(entities)
    assert len(resolved) == 1
    assert stats.merged_entities == 1
    assert resolved[0].name == "fine tuning"
    assert resolved[0].properties["alias_count"] == 2


def test_resolve_entities_does_not_merge_different_entity_types():
    service = EntityResolutionService()
    entities = [
        ExtractedEntity(entity_type=EntityType.CONCEPT, name="Transformer", confidence=0.8),
        ExtractedEntity(entity_type=EntityType.METHOD, name="Transformer", confidence=0.9),
    ]

    resolved, stats = service.resolve_entities(entities)
    assert len(resolved) == 2
    assert stats.merged_entities == 0


def test_resolve_entities_splits_homonym_by_context():
    service = EntityResolutionService()
    entities = [
        ExtractedEntity(
            entity_type=EntityType.CONCEPT,
            name="SAT",
            definition="Boolean satisfiability formulation solved by a CNF solver.",
            confidence=0.88,
            source_paper_id="logic-paper",
        ),
        ExtractedEntity(
            entity_type=EntityType.CONCEPT,
            name="SAT",
            definition="Scholastic Aptitude Test score prediction for college applicants.",
            confidence=0.84,
            source_paper_id="education-paper",
        ),
    ]

    resolved, stats = service.resolve_entities(entities)
    assert len(resolved) == 2
    assert stats.merged_entities == 0
    buckets = {entity.properties.get("resolution_context_bucket") for entity in resolved}
    assert "logic" in buckets
    assert "education" in buckets


def test_resolve_entities_merges_homonym_when_context_matches():
    service = EntityResolutionService()
    entities = [
        ExtractedEntity(
            entity_type=EntityType.CONCEPT,
            name="SAT",
            description="Boolean satisfiability problem encoded in CNF clauses.",
            confidence=0.86,
            source_paper_id="p1",
        ),
        ExtractedEntity(
            entity_type=EntityType.CONCEPT,
            name="S.A.T.",
            description="SAT solver optimization for propositional logic constraints.",
            confidence=0.9,
            source_paper_id="p2",
        ),
    ]

    resolved, stats = service.resolve_entities(entities)
    assert len(resolved) == 1
    assert stats.merged_entities == 1
    assert resolved[0].name == "sat"
    assert resolved[0].properties.get("resolution_context_bucket") == "logic"


class _AcceptAllPairsLLM:
    async def generate(self, prompt: str, **kwargs) -> str:
        pair_ids = re.findall(r"id=(p\d+)", prompt)
        return json.dumps(
            {"decisions": [{"id": pair_id, "same": True} for pair_id in pair_ids]}
        )


@pytest.mark.asyncio
async def test_resolve_entities_async_uses_llm_confirmation_for_uncertain_pairs():
    service = EntityResolutionService(
        llm_provider=_AcceptAllPairsLLM(),
        auto_merge_threshold=0.99,  # Prevent deterministic merge
        llm_review_threshold=0.7,   # Allow uncertain pair review
        max_llm_pair_checks=10,
        llm_batch_size=5,
    )
    entities = [
        ExtractedEntity(
            entity_type=EntityType.CONCEPT,
            name="Graph Attention Network",
            confidence=0.82,
            source_paper_id="p1",
        ),
        ExtractedEntity(
            entity_type=EntityType.CONCEPT,
            name="Graph Attention Networks",
            confidence=0.8,
            source_paper_id="p2",
        ),
    ]

    sync_resolved, _ = service.resolve_entities(entities)
    async_resolved, async_stats = await service.resolve_entities_async(
        entities,
        use_llm_confirmation=True,
    )

    assert len(sync_resolved) == 2
    assert len(async_resolved) == 1
    assert async_stats.merged_entities == 1
    assert async_stats.llm_pairs_reviewed == 1
    assert async_stats.llm_pairs_confirmed == 1
    assert async_stats.potential_false_merge_count == 1
    assert len(async_stats.potential_false_merge_samples) == 1
