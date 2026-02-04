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
    CONVERSATIONAL = "conversational"  # Greetings, thanks, casual chat


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
        {"query": "Hello, how are you?", "intent": "conversational"},
        {"query": "안녕하세요", "intent": "conversational"},
    ]

    SYSTEM_PROMPT = """Classify queries into: search, explore, explain, compare, summarize, identify_gaps, conversational.
Use 'conversational' for greetings, thanks, or casual chat (e.g., "hello", "안녕", "thanks").
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
        q = query.lower().strip()

        # Detect conversational/greeting patterns FIRST (before other classifications)
        conversational_patterns = [
            "안녕", "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
            "thanks", "thank you", "bye", "goodbye", "how are you", "what's up",
            "nice to meet", "help me", "can you help",
        ]
        # Short queries (< 5 chars) or greetings should be conversational
        if len(q) < 5 or any(p in q for p in conversational_patterns):
            return IntentResult(
                intent=IntentType.CONVERSATIONAL,
                confidence=0.95,
                keywords=[],
                reasoning="Detected greeting or conversational query"
            )

        mappings = [
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
