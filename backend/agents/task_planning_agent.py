"""
Task Planning Agent

Decomposes complex queries into sub-tasks.
Example: "Compare A and B" → [Search A, Search B, Find common concepts, Analyze differences]
"""

from typing import Optional
from pydantic import BaseModel
from .intent_agent import IntentType


class SubTask(BaseModel):
    task_type: str  # search, retrieve, analyze, compare, summarize
    description: str
    parameters: dict = {}
    depends_on: list[int] = []  # Indices of tasks this depends on


class TaskPlan(BaseModel):
    original_query: str
    intent: IntentType
    tasks: list[SubTask]
    estimated_complexity: str  # low, medium, high


class TaskPlanningAgent:
    """
    Decomposes queries into executable sub-tasks.
    """

    def __init__(self, llm_provider=None):
        self.llm = llm_provider

    def _build_reliability_params(self, intent: IntentType, query: str) -> dict:
        """
        Build trust-filter parameters to enforce evidence reliability at execution time.

        Defaults:
        - Strict filtering for high-stakes intents (explain, compare, gap analysis)
        - Optional filtering for search-like intents only when user explicitly asks reliability
        """
        normalized_query = (query or "").lower()
        explicit_reliability_request = any(
            token in normalized_query
            for token in (
                "reliable",
                "reliability",
                "trust",
                "confidence",
                "evidence",
                "provenance",
                "신뢰",
                "근거",
                "검증",
            )
        )

        strict_intents = {
            IntentType.EXPLAIN,
            IntentType.COMPARE,
            IntentType.IDENTIFY_GAPS,
        }
        if intent in strict_intents:
            return {"exclude_low_trust": True, "min_confidence": 0.6}

        if explicit_reliability_request:
            return {"exclude_low_trust": True, "min_confidence": 0.65}

        return {}

    async def plan(
        self, query: str, intent: IntentType, extracted_entities: list
    ) -> TaskPlan:
        """
        Create a task plan based on intent and extracted entities.
        """
        tasks = []
        reliability_params = self._build_reliability_params(intent, query)

        if intent == IntentType.SEARCH:
            tasks.append(
                SubTask(
                    task_type="search",
                    description="Search for relevant entities",
                    parameters={"query": query, "limit": 20, **reliability_params},
                )
            )
            tasks.append(
                SubTask(
                    task_type="analyze",
                    description="Analyze search results",
                    depends_on=[0],
                )
            )

        elif intent == IntentType.COMPARE:
            # Extract entities to compare
            tasks.append(
                SubTask(
                    task_type="search",
                    description="Find first entity",
                    parameters={"entity_index": 0, **reliability_params},
                )
            )
            tasks.append(
                SubTask(
                    task_type="search",
                    description="Find second entity",
                    parameters={"entity_index": 1, **reliability_params},
                )
            )
            tasks.append(
                SubTask(
                    task_type="compare",
                    description="Compare the two entities",
                    depends_on=[0, 1],
                )
            )

        elif intent == IntentType.EXPLAIN:
            tasks.append(
                SubTask(
                    task_type="retrieve",
                    description="Retrieve entity details",
                    parameters={"query": query, **reliability_params},
                )
            )
            tasks.append(
                SubTask(
                    task_type="explain",
                    description="Generate explanation",
                    depends_on=[0],
                )
            )

        elif intent == IntentType.IDENTIFY_GAPS:
            tasks.append(
                SubTask(
                    task_type="analyze_gaps",
                    description="Find research gaps in the graph",
                    parameters={"min_papers": 3, **reliability_params},
                )
            )

        else:
            # Default: simple search and summarize
            tasks.append(
                SubTask(
                    task_type="search",
                    description="Search for relevant information",
                    parameters={"query": query, **reliability_params},
                )
            )

        return TaskPlan(
            original_query=query,
            intent=intent,
            tasks=tasks,
            estimated_complexity="medium" if len(tasks) > 2 else "low",
        )
