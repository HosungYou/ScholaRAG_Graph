"""
Intent Agent

Classifies user intent using Few-Shot Learning with LLM.
Categories: search, explore, explain, compare, create, summarize, identify_gaps
"""

import json
import logging
from enum import Enum
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    SEARCH = "search"
    EXPLORE = "explore"
    EXPLAIN = "explain"
    COMPARE = "compare"
    CREATE = "create"
    SUMMARIZE = "summarize"
    IDENTIFY_GAPS = "identify_gaps"
    # TTO-specific intents
    PATENT_SEARCH = "patent_search"
    INVENTOR_LOOKUP = "inventor_lookup"
    TECHNOLOGY_TREND = "technology_trend"
    LICENSE_STATUS = "license_status"


class IntentResult(BaseModel):
    intent: IntentType
    confidence: float
    entities_mentioned: list[str] = []
    keywords: list[str] = []
    reasoning: str = ""


class IntentAgent:
    """Intent Agent using Few-Shot Learning to classify user queries."""

    FEW_SHOT_EXAMPLES = [
        {"query": "What papers discuss machine learning?", "intent": "search"},
        {"query": "Show me papers connected to this author", "intent": "explore"},
        {"query": "Explain what this methodology means", "intent": "explain"},
        {"query": "Compare paper A with paper B", "intent": "compare"},
        {"query": "What are the research gaps?", "intent": "identify_gaps"},
        {"query": "Summarize the findings", "intent": "summarize"},
        # TTO-specific examples
        {"query": "Find patents related to machine learning", "intent": "patent_search"},
        {"query": "Who invented the quantum sensing device?", "intent": "inventor_lookup"},
        {"query": "What technologies are most frequently patented?", "intent": "technology_trend"},
        {"query": "Which inventions are currently licensed?", "intent": "license_status"},
    ]

    SYSTEM_PROMPT = """Classify queries into: search, explore, explain, compare, summarize, identify_gaps, patent_search, inventor_lookup, technology_trend, license_status.
Respond with JSON: {"intent": "<type>", "confidence": 0.0-1.0, "keywords": [], "reasoning": "brief"}"""

    def __init__(self, llm_provider=None):
        self.llm = llm_provider

    async def classify(self, query: str) -> IntentResult:
        """Classify user query intent. Uses LLM if available."""
        if self.llm:
            try:
                return await self._classify_with_llm(query)
            except Exception as e:
                logger.warning(f"LLM classification failed: {e}")
        return self._classify_with_keywords(query)

    async def _classify_with_llm(self, query: str) -> IntentResult:
        """Use LLM with few-shot examples."""
        examples = "\n".join([f"Q: \"{ex['query']}\" -> {ex['intent']}" for ex in self.FEW_SHOT_EXAMPLES])
        prompt = f"Examples:\n{examples}\n\nClassify: \"{query}\""

        response = await self.llm.generate(
            prompt=prompt, system_prompt=self.SYSTEM_PROMPT, max_tokens=200, temperature=0.1
        )

        try:
            json_str = response.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(json_str)
            return IntentResult(
                intent=IntentType(data.get("intent", "search")),
                confidence=float(data.get("confidence", 0.8)),
                keywords=data.get("keywords", []),
                reasoning=data.get("reasoning", ""),
            )
        except Exception:
            return self._classify_with_keywords(query)

    def _classify_with_keywords(self, query: str) -> IntentResult:
        """Fallback keyword-based classification."""
        q = query.lower()
        mappings = [
            # TTO-specific intents (check first for specificity)
            (IntentType.PATENT_SEARCH, ["patent", "patents", "filing", "prior art", "claims"]),
            (IntentType.INVENTOR_LOOKUP, ["inventor", "invented", "who created", "who developed"]),
            (IntentType.TECHNOLOGY_TREND, ["technology trend", "tech area", "most patented", "technology distribution"]),
            (IntentType.LICENSE_STATUS, ["license", "licensed", "licensing", "commercialize"]),
            # General intents
            (IntentType.COMPARE, ["compare", "versus", "vs", "difference"]),
            (IntentType.EXPLAIN, ["explain", "what is", "define", "meaning"]),
            (IntentType.IDENTIFY_GAPS, ["gap", "missing", "underresearched"]),
            (IntentType.SUMMARIZE, ["summarize", "summary", "overview"]),
            (IntentType.EXPLORE, ["show", "connected", "related", "relationship"]),
        ]
        for intent, words in mappings:
            if any(w in q for w in words):
                return IntentResult(intent=intent, confidence=0.75, keywords=q.split()[:5])
        return IntentResult(intent=IntentType.SEARCH, confidence=0.6, keywords=q.split()[:5])
