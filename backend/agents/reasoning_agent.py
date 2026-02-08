"""
Reasoning Agent

Applies Chain-of-Thought reasoning to synthesize query results
and draw evidence-based conclusions.

Enhanced with Gap Detection integration for suggesting new research directions.
"""

import json
import logging
from typing import Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ReasoningStep(BaseModel):
    step_number: int
    description: str
    evidence: list[str] = []
    conclusion: str


class ResearchGapSuggestion(BaseModel):
    """Suggested research gap or opportunity."""
    gap_description: str
    connecting_clusters: list[str] = []
    suggested_questions: list[str] = []
    bridge_concepts: list[str] = []
    relevance_score: float = 0.0


class ReasoningResult(BaseModel):
    steps: list[ReasoningStep]
    final_conclusion: str
    confidence: float
    supporting_nodes: list[str] = []
    supporting_edges: list[str] = []
    # New: Gap-based suggestions
    research_gaps: list[ResearchGapSuggestion] = []
    hidden_connections: list[str] = []


class ReasoningAgent:
    """Applies Chain-of-Thought reasoning to execution results.

    Enhanced with:
    - Gap Detection integration for research opportunities
    - Hidden connection discovery
    - Concept-centric analysis
    """

    SYSTEM_PROMPT = """You are a research analyst specializing in systematic literature review.
You analyze a concept-centric knowledge graph where:
- Concepts, Methods, Findings, Problems, Datasets, Metrics, Innovations, and Limitations are primary nodes
- Papers and Authors are metadata attached to concepts (not visible as separate nodes)
- Relationships show how concepts relate across the literature

CRITICAL RULES:
- If research gap data is provided in the context below, you MUST analyze and present it. NEVER claim the graph is unavailable or not initialized when data is present.
- Base your response ONLY on the provided data. Do not fabricate error messages.
- If data shows gaps between clusters, describe them clearly with the cluster names.
- If evidence is sparse, add a short 'Reliability note' warning in the final conclusion.

Apply step-by-step reasoning to answer the user's question.
When relevant, identify research gaps - areas where concept clusters have weak connections.

For each step:
1. Examine the evidence from the knowledge graph
2. Identify patterns and connections between concepts
3. Note any gaps or opportunities in the research landscape
4. Draw logical conclusions

Respond with JSON:
{
    "steps": [{"step_number": 1, "description": "...", "evidence": [...], "conclusion": "..."}],
    "final_conclusion": "comprehensive answer",
    "confidence": 0.0-1.0,
    "research_gaps": [{"gap_description": "...", "suggested_questions": [...]}],
    "hidden_connections": ["Connection between X and Y suggests..."]
}"""

    GAP_ANALYSIS_PROMPT = """You are analyzing research gaps in an academic knowledge graph.

Given the following structural gaps between concept clusters:
{gap_context}

And the user's query: {query}

Identify which gaps are most relevant to the user's research interest.
Suggest concrete research questions that could bridge these gaps.

Respond with JSON:
{
    "relevant_gaps": [
        {
            "gap_description": "Gap between X and Y clusters",
            "relevance_score": 0.0-1.0,
            "suggested_questions": ["Research question 1", "Research question 2"],
            "bridge_concepts": ["Concept that could connect these areas"]
        }
    ],
    "hidden_connections": ["Unexpected connection that emerged from analysis"]
}"""

    def __init__(self, llm_provider=None, db_connection=None):
        self.llm = llm_provider
        self.db = db_connection

    def _build_provenance_warning(self, execution_result) -> Optional[str]:
        """
        Build a reliability warning when provenance/evidence signals are weak.
        """
        results = execution_result.results or []
        successful_with_data = sum(1 for r in results if r.success and r.data)
        signal_count = len(execution_result.nodes_accessed) + len(execution_result.edges_traversed)

        if successful_with_data == 0:
            return (
                "Reliability note: No directly supporting graph evidence was retrieved for this answer. "
                "Treat this as exploratory guidance."
            )

        if signal_count < 3:
            return (
                "Reliability note: Evidence coverage is limited (few supporting nodes/edges). "
                "Please verify with additional sources."
            )

        return None

    async def reason(
        self,
        query: str,
        intent,
        execution_result,
        project_id: Optional[str] = None,
        include_gaps: bool = True
    ) -> ReasoningResult:
        """Apply Chain-of-Thought reasoning. Uses LLM if available.

        Args:
            query: User's query
            intent: Classified intent
            execution_result: Results from query execution
            project_id: Project ID for gap analysis
            include_gaps: Whether to include gap analysis
        """
        # Get gap context if available
        gap_context = None
        if include_gaps and project_id and self.db:
            gap_context = await self._get_relevant_gaps(project_id, query)

        if self.llm:
            try:
                return await self._reason_with_llm(
                    query, intent, execution_result, gap_context
                )
            except Exception as e:
                logger.warning(f"LLM reasoning failed: {e}")
        return self._reason_with_fallback(query, execution_result, gap_context)

    async def _get_relevant_gaps(self, project_id: str, query: str) -> Optional[dict]:
        """Fetch relevant structural gaps for the project."""
        try:
            # Get gaps from database
            gap_rows = await self.db.fetch(
                """
                SELECT id, cluster_a_names, cluster_b_names, gap_strength,
                       bridge_candidates, research_questions
                FROM structural_gaps
                WHERE project_id = $1
                ORDER BY gap_strength DESC
                LIMIT 5
                """,
                project_id,
            )

            if not gap_rows:
                return None

            gaps = []
            for row in gap_rows:
                gaps.append({
                    "id": str(row["id"]),
                    "cluster_a": row["cluster_a_names"][:3],
                    "cluster_b": row["cluster_b_names"][:3],
                    "strength": row["gap_strength"],
                    "bridges": row["bridge_candidates"][:3] if row["bridge_candidates"] else [],
                    "questions": row["research_questions"][:2] if row["research_questions"] else [],
                })

            return {"gaps": gaps, "total": len(gap_rows)}

        except Exception as e:
            logger.warning(f"Failed to get gaps: {e}")
            return None

    async def _reason_with_llm(
        self,
        query: str,
        intent,
        execution_result,
        gap_context: Optional[dict] = None
    ) -> ReasoningResult:
        """Use LLM for Chain-of-Thought reasoning with gap awareness."""
        # Build context from execution results
        results_summary = []
        for i, result in enumerate(execution_result.results):
            if result.success and result.data:
                results_summary.append(f"Task {i+1}: {result.data}")

        context = f"""Query: {query}
Intent: {intent.value if hasattr(intent, 'value') else str(intent)}
Results found: {len(execution_result.results)}
Nodes accessed: {len(execution_result.nodes_accessed)}
Data: {results_summary[:3]}"""

        # Add gap context if available
        if gap_context and gap_context.get("gaps"):
            gap_text = "\n".join([
                f"- Gap between clusters [{', '.join(g['cluster_a'])}] and [{', '.join(g['cluster_b'])}] (strength: {g['strength']:.2f})"
                + (f"\n  Suggested questions: {'; '.join(g.get('questions', []))}" if g.get('questions') else "")
                + (f"\n  Bridge concepts: {', '.join(g.get('bridges', []))}" if g.get('bridges') else "")
                for g in gap_context["gaps"][:5]
            ])
            context += f"\n\nResearch Gaps Detected ({gap_context.get('total', 0)} total):\n{gap_text}"

        prompt = f"Analyze this research query and results:\n{context}"
        response = await self.llm.generate(
            prompt=prompt, system_prompt=self.SYSTEM_PROMPT, max_tokens=1500, temperature=0.1
        )

        try:
            json_str = response.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(json_str)

            steps = [
                ReasoningStep(
                    step_number=s.get("step_number", i+1),
                    description=s.get("description", ""),
                    evidence=s.get("evidence", []),
                    conclusion=s.get("conclusion", ""),
                )
                for i, s in enumerate(data.get("steps", []))
            ]

            # Parse gap suggestions from LLM response
            research_gaps = []
            for gap_data in data.get("research_gaps", []):
                research_gaps.append(
                    ResearchGapSuggestion(
                        gap_description=gap_data.get("gap_description", ""),
                        suggested_questions=gap_data.get("suggested_questions", []),
                        bridge_concepts=gap_data.get("bridge_concepts", []),
                        relevance_score=gap_data.get("relevance_score", 0.5),
                    )
                )

            return ReasoningResult(
                steps=steps,
                final_conclusion=(
                    data.get("final_conclusion", "Analysis complete.")
                    + (
                        "\n\n" + warning
                        if (warning := self._build_provenance_warning(execution_result))
                        else ""
                    )
                ),
                confidence=float(data.get("confidence", 0.7)),
                supporting_nodes=execution_result.nodes_accessed,
                supporting_edges=execution_result.edges_traversed,
                research_gaps=research_gaps,
                hidden_connections=data.get("hidden_connections", []),
            )
        except Exception as e:
            logger.warning(f"JSON parsing failed: {e}")
            return self._reason_with_fallback(query, execution_result, gap_context)

    def _reason_with_fallback(
        self,
        query: str,
        execution_result,
        gap_context: Optional[dict] = None
    ) -> ReasoningResult:
        """
        Fallback structured reasoning with gap awareness.

        v0.6.0 Fix: Uses actual execution_result data instead of generic templates.
        """
        num_results = len(execution_result.results)
        successful = sum(1 for r in execution_result.results if r.success)

        # v0.6.0: Extract actual findings from execution results
        actual_findings = []
        entity_names = []
        relationship_count = 0

        for result in execution_result.results:
            if result.success and result.data:
                if isinstance(result.data, dict):
                    # Extract entities if available
                    if 'entities' in result.data:
                        entities = result.data['entities'][:5]
                        entity_names.extend([e.get('name', 'unknown') for e in entities if isinstance(e, dict)])
                    # Count relationships
                    if 'relationships' in result.data:
                        rel_count = len(result.data['relationships'])
                        relationship_count += rel_count
                    # Extract any summary or description
                    if 'summary' in result.data:
                        actual_findings.append(result.data['summary'][:200])
                    if 'description' in result.data:
                        actual_findings.append(result.data['description'][:200])
                elif isinstance(result.data, list):
                    for item in result.data[:3]:
                        if isinstance(item, dict) and 'name' in item:
                            entity_names.append(item['name'])

        # Remove duplicates and limit
        entity_names = list(dict.fromkeys(entity_names))[:10]

        steps = [
            ReasoningStep(
                step_number=1,
                description="Analyzing query and retrieved data",
                evidence=[f"Executed {num_results} tasks", f"{successful} successful"],
                conclusion="Data retrieval complete",
            ),
            ReasoningStep(
                step_number=2,
                description="Synthesizing findings from concept network",
                evidence=[
                    f"Accessed {len(execution_result.nodes_accessed)} concept nodes",
                    f"Found {len(entity_names)} related concepts" if entity_names else "No direct matches"
                ],
                conclusion="Patterns analyzed",
            ),
            ReasoningStep(
                step_number=3,
                description="Formulating response",
                evidence=actual_findings[:2] if actual_findings else [],
                conclusion="Ready to present findings",
            ),
        ]

        # Add gap-related step if gaps are available
        research_gaps = []
        if gap_context and gap_context.get("gaps"):
            steps.append(
                ReasoningStep(
                    step_number=4,
                    description="Identifying research opportunities",
                    evidence=[f"Found {len(gap_context['gaps'])} structural gaps"],
                    conclusion="Research gaps detected in concept network",
                )
            )

            # Create gap suggestions from context
            for gap in gap_context["gaps"][:3]:
                research_gaps.append(
                    ResearchGapSuggestion(
                        gap_description=f"Gap between {', '.join(gap['cluster_a'][:2])} and {', '.join(gap['cluster_b'][:2])}",
                        suggested_questions=gap.get("questions", []),
                        bridge_concepts=gap.get("bridges", []),
                        relevance_score=gap.get("strength", 0.5),
                    )
                )

        # v0.6.0: Build data-based conclusion instead of generic template
        if entity_names:
            concepts_str = ', '.join(entity_names[:5])
            conclusion = f"Analysis of '{query}' in the knowledge graph:\n"
            conclusion += f"• Related concepts: {concepts_str}\n"
            if relationship_count > 0:
                conclusion += f"• Found {relationship_count} relationship(s) between concepts\n"
            if len(entity_names) > 5:
                conclusion += f"• {len(entity_names) - 5} additional related concepts available"
            confidence = 0.6 + min(0.3, len(entity_names) * 0.03)
        else:
            conclusion = (
                f"No direct matches found for '{query}' in the knowledge graph. "
                "Try using different keywords or broader concepts. "
                f"The graph contains {len(execution_result.nodes_accessed)} accessible nodes."
            )
            confidence = 0.3

        return ReasoningResult(
            steps=steps,
            final_conclusion=(
                conclusion
                + (
                    "\n\n" + warning
                    if (warning := self._build_provenance_warning(execution_result))
                    else ""
                )
            ),
            confidence=confidence,
            supporting_nodes=execution_result.nodes_accessed,
            supporting_edges=execution_result.edges_traversed,
            research_gaps=research_gaps,
            hidden_connections=[],
        )

    async def analyze_gaps_for_query(
        self,
        query: str,
        project_id: str
    ) -> list[ResearchGapSuggestion]:
        """Analyze which gaps are relevant to the user's query."""
        if not self.llm or not self.db:
            return []

        try:
            gap_context = await self._get_relevant_gaps(project_id, query)
            if not gap_context:
                return []

            # Format gap context for LLM
            gap_text = json.dumps(gap_context["gaps"], indent=2)

            prompt = self.GAP_ANALYSIS_PROMPT.format(
                gap_context=gap_text,
                query=query
            )

            response = await self.llm.generate(
                prompt=prompt,
                system_prompt="You are a research gap analyst.",
                max_tokens=1000,
                temperature=0.3
            )

            json_str = response.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(json_str)

            suggestions = []
            for gap_data in data.get("relevant_gaps", []):
                suggestions.append(
                    ResearchGapSuggestion(
                        gap_description=gap_data.get("gap_description", ""),
                        suggested_questions=gap_data.get("suggested_questions", []),
                        bridge_concepts=gap_data.get("bridge_concepts", []),
                        relevance_score=float(gap_data.get("relevance_score", 0.5)),
                    )
                )

            return suggestions

        except Exception as e:
            logger.error(f"Failed to analyze gaps: {e}")
            return []
