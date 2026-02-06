"""
Concept Extraction Agent

Extracts entities (papers, authors, concepts, methods) from user queries
using NER and matches them to existing entities in the graph.
"""

import json
import logging
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ExtractedEntity(BaseModel):
    text: str
    entity_type: str  # Paper, Author, Concept, Method, Finding
    matched_id: Optional[str] = None
    confidence: float = 0.0


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity]
    keywords: list[str]
    query_without_entities: str


class ConceptExtractionAgent:
    """Extracts and matches entities from user queries."""

    SYSTEM_PROMPT = """Extract entities from user queries about a research/technology transfer knowledge graph.
Entity types: Paper, Author, Concept, Method, Finding, Invention, Patent, Inventor, Technology, License, Grant, Department.

For technology transfer queries, use these entity types:
- Invention: a novel creation or discovery
- Patent: a patent filing or granted patent (includes patent numbers like "US 11,xxx,xxx")
- Inventor: a person who created an invention
- Technology: a technology area or domain (e.g., "Machine Learning", "Quantum Computing")
- License: a licensing agreement
- Grant: a research funding grant
- Department: an academic department

Respond with JSON:
{
    "entities": [{"text": "entity name", "entity_type": "type", "confidence": 0.0-1.0}],
    "keywords": ["key", "terms"],
    "query_without_entities": "query with entities removed"
}"""

    def __init__(self, llm_provider=None, graph_store=None):
        self.llm = llm_provider
        self.graph_store = graph_store

    async def extract(self, query: str) -> ExtractionResult:
        """Extract entities from query. Uses LLM if available."""
        if self.llm:
            try:
                return await self._extract_with_llm(query)
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}")
        return self._extract_with_keywords(query)

    async def _extract_with_llm(self, query: str) -> ExtractionResult:
        """Use LLM for named entity recognition."""
        prompt = f'Extract entities from: "{query}"'
        response = await self.llm.generate(
            prompt=prompt, system_prompt=self.SYSTEM_PROMPT, max_tokens=500, temperature=0.1
        )

        try:
            json_str = response.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(json_str)

            entities = [
                ExtractedEntity(
                    text=e.get("text", ""),
                    entity_type=e.get("entity_type", "Concept"),
                    confidence=float(e.get("confidence", 0.7)),
                )
                for e in data.get("entities", [])
            ]

            # Try to match entities to graph
            if self.graph_store:
                for entity in entities:
                    matched_id = await self.match_to_graph(entity.text, entity.entity_type)
                    if matched_id:
                        entity.matched_id = matched_id

            return ExtractionResult(
                entities=entities,
                keywords=data.get("keywords", query.lower().split()[:10]),
                query_without_entities=data.get("query_without_entities", query),
            )
        except Exception:
            return self._extract_with_keywords(query)

    def _extract_with_keywords(self, query: str) -> ExtractionResult:
        """Fallback keyword extraction."""
        stop_words = {"the", "a", "an", "is", "are", "what", "how", "who", "which", "in", "on", "at", "to", "for"}
        words = [w.strip("?.,!") for w in query.lower().split() if w.strip("?.,!") not in stop_words and len(w) > 2]
        return ExtractionResult(entities=[], keywords=words[:10], query_without_entities=query)

    async def match_to_graph(self, entity_text: str, entity_type: str) -> Optional[str]:
        """Try to match entity to graph using fuzzy search."""
        if not self.graph_store:
            return None
        try:
            results = await self.graph_store.search_entities(
                query=entity_text, entity_types=[entity_type], limit=1
            )
            if results:
                return results[0].get("id")
        except Exception as e:
            logger.warning(f"Graph matching failed: {e}")
        return None
