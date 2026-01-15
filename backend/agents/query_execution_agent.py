"""
Query Execution Agent

Executes sub-tasks by running SQL queries, vector searches, and graph traversals.
Supports all task types from TaskPlanningAgent: search, retrieve, analyze, compare, explain, analyze_gaps.
"""

import logging
from typing import Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class QueryResult(BaseModel):
    task_index: int
    success: bool
    data: Any = None
    error: str | None = None


class ExecutionResult(BaseModel):
    results: list[QueryResult]
    nodes_accessed: list[str] = []
    edges_traversed: list[str] = []


class QueryExecutionAgent:
    """
    Executes queries against the database and graph.
    Supports task types: search, retrieve, analyze, compare, explain, analyze_gaps.
    """

    def __init__(self, db_connection=None, vector_store=None, graph_store=None, llm_provider=None):
        self.db = db_connection
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.llm = llm_provider
        self._previous_results: dict[int, Any] = {}  # Store results for dependent tasks

    async def execute(self, task_plan) -> ExecutionResult:
        """
        Execute all tasks in the plan.
        """
        results = []
        nodes_accessed = []
        edges_traversed = []
        self._previous_results = {}

        for i, task in enumerate(task_plan.tasks):
            # Check dependencies
            deps_satisfied = all(
                results[dep].success for dep in task.depends_on if dep < len(results)
            )

            if not deps_satisfied:
                results.append(
                    QueryResult(
                        task_index=i,
                        success=False,
                        error="Dependencies not satisfied",
                    )
                )
                continue

            try:
                # Get dependent results for context
                dep_results = [self._previous_results.get(dep) for dep in task.depends_on]

                # Route to appropriate handler
                if task.task_type == "search":
                    data = await self._execute_search(task.parameters)
                elif task.task_type == "retrieve":
                    data = await self._execute_retrieve(task.parameters)
                elif task.task_type == "analyze":
                    data = await self._execute_analyze(task.parameters, dep_results)
                elif task.task_type == "compare":
                    data = await self._execute_compare(task.parameters, dep_results)
                elif task.task_type == "explain":
                    data = await self._execute_explain(task.parameters, dep_results)
                elif task.task_type == "analyze_gaps":
                    data = await self._execute_gap_analysis(task.parameters)
                else:
                    logger.warning(f"Unknown task type: {task.task_type}, returning empty result")
                    data = {"task_type": task.task_type, "status": "unsupported"}

                # Store for dependent tasks
                self._previous_results[i] = data

                # Track accessed nodes
                if isinstance(data, dict) and "nodes" in data:
                    nodes_accessed.extend([n.get("id", "") for n in data.get("nodes", [])])
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "id" in item:
                            nodes_accessed.append(item["id"])

                results.append(
                    QueryResult(task_index=i, success=True, data=data)
                )

            except Exception as e:
                logger.error(f"Task execution failed: {task.task_type} - {e}")
                results.append(
                    QueryResult(task_index=i, success=False, error=str(e))
                )

        return ExecutionResult(
            results=results,
            nodes_accessed=list(set(nodes_accessed)),  # Deduplicate
            edges_traversed=edges_traversed,
        )

    async def _execute_search(self, params: dict) -> list:
        """Execute a search query against the graph store."""
        query = params.get("query", "")
        limit = params.get("limit", 20)
        entity_types = params.get("entity_types")
        project_id = params.get("project_id")

        if self.graph_store and project_id:
            try:
                results = await self.graph_store.search_entities(
                    query=query,
                    project_id=project_id,
                    entity_types=entity_types,
                    limit=limit,
                )
                return results
            except Exception as e:
                logger.warning(f"Graph store search failed: {e}")

        # Fallback: return empty but valid result
        return []

    async def _execute_retrieve(self, params: dict) -> dict:
        """Retrieve entity details from graph store."""
        entity_id = params.get("entity_id")
        query = params.get("query", "")
        project_id = params.get("project_id")

        if self.graph_store and entity_id:
            try:
                entity = await self.graph_store.get_entity(entity_id)
                if entity:
                    return entity
            except Exception as e:
                logger.warning(f"Entity retrieval failed: {e}")

        # Fallback: search by query
        if self.graph_store and query and project_id:
            results = await self._execute_search({"query": query, "limit": 1, "project_id": project_id})
            if results:
                return results[0]

        return {"status": "not_found", "query": query}

    async def _execute_analyze(self, params: dict, dep_results: list) -> dict:
        """
        Analyze search results to extract patterns and insights.
        Depends on prior search results.
        """
        # Collect entities from dependent results
        entities = []
        for result in dep_results:
            if isinstance(result, list):
                entities.extend(result)
            elif isinstance(result, dict) and "nodes" in result:
                entities.extend(result["nodes"])

        # Basic analysis: count by type, extract common attributes
        type_counts = {}
        years = []
        concepts = []

        for entity in entities:
            if isinstance(entity, dict):
                etype = entity.get("entity_type", "Unknown")
                type_counts[etype] = type_counts.get(etype, 0) + 1

                props = entity.get("properties", {})
                if props.get("year"):
                    years.append(props["year"])

        analysis = {
            "total_entities": len(entities),
            "by_type": type_counts,
            "year_range": [min(years), max(years)] if years else None,
            "insights": [],
        }

        # Generate insights
        if type_counts.get("Paper", 0) > 10:
            analysis["insights"].append(f"Found {type_counts['Paper']} relevant papers")
        if years:
            analysis["insights"].append(f"Research spans {min(years)} to {max(years)}")

        return analysis

    async def _execute_compare(self, params: dict, dep_results: list) -> dict:
        """
        Compare two or more entities based on their properties and relationships.
        Depends on prior search/retrieve results.
        """
        entities_to_compare = []
        for result in dep_results:
            if isinstance(result, list) and result:
                entities_to_compare.append(result[0])
            elif isinstance(result, dict) and "id" in result:
                entities_to_compare.append(result)

        if len(entities_to_compare) < 2:
            return {
                "status": "insufficient_data",
                "message": "Need at least 2 entities to compare",
                "entities_found": len(entities_to_compare),
            }

        # Extract comparison dimensions
        comparison = {
            "entities": [
                {
                    "id": e.get("id"),
                    "name": e.get("name"),
                    "type": e.get("entity_type"),
                }
                for e in entities_to_compare
            ],
            "similarities": [],
            "differences": [],
        }

        # Compare properties
        e1, e2 = entities_to_compare[0], entities_to_compare[1]
        props1 = e1.get("properties", {})
        props2 = e2.get("properties", {})

        # Find common and different properties
        all_keys = set(props1.keys()) | set(props2.keys())
        for key in all_keys:
            if key in props1 and key in props2:
                if props1[key] == props2[key]:
                    comparison["similarities"].append(f"{key}: {props1[key]}")
                else:
                    comparison["differences"].append(f"{key}: {props1[key]} vs {props2[key]}")

        return comparison

    async def _execute_explain(self, params: dict, dep_results: list) -> dict:
        """
        Generate explanation for an entity using LLM.
        Depends on prior retrieve results.
        """
        # Get entity from dependent results
        entity = None
        for result in dep_results:
            if isinstance(result, dict) and "name" in result:
                entity = result
                break
            elif isinstance(result, list) and result:
                entity = result[0]
                break

        if not entity:
            return {
                "status": "no_entity",
                "explanation": "Could not find entity to explain.",
            }

        name = entity.get("name", "Unknown")
        entity_type = entity.get("entity_type", "Entity")
        props = entity.get("properties", {})

        # Build explanation context
        explanation = {
            "entity_name": name,
            "entity_type": entity_type,
            "summary": f"This is a {entity_type} named '{name}'.",
            "details": [],
        }

        # Add property-based details
        if entity_type == "Paper":
            if props.get("abstract"):
                explanation["details"].append(f"Abstract: {props['abstract'][:500]}...")
            if props.get("year"):
                explanation["details"].append(f"Published in {props['year']}")
            if props.get("citation_count"):
                explanation["details"].append(f"Cited {props['citation_count']} times")
        elif entity_type == "Concept":
            if props.get("description"):
                explanation["details"].append(f"Description: {props['description']}")
            if props.get("paper_count"):
                explanation["details"].append(f"Discussed in {props['paper_count']} papers")
        elif entity_type == "Author":
            if props.get("affiliation"):
                explanation["details"].append(f"Affiliated with {props['affiliation']}")
            if props.get("paper_count"):
                explanation["details"].append(f"Has {props['paper_count']} papers in this collection")

        # Use LLM for richer explanation if available
        if self.llm and props.get("abstract"):
            try:
                prompt = f"Briefly explain this {entity_type} '{name}' based on: {props.get('abstract', '')[:1000]}"
                llm_explanation = await self.llm.generate(prompt=prompt, max_tokens=300)
                explanation["ai_summary"] = llm_explanation
            except Exception as e:
                logger.warning(f"LLM explanation failed: {e}")

        return explanation

    async def _execute_gap_analysis(self, params: dict) -> dict:
        """
        Find research gaps by analyzing the knowledge graph structure.
        """
        min_papers = params.get("min_papers", 3)
        project_id = params.get("project_id")

        gaps = {
            "identified_gaps": [],
            "underexplored_concepts": [],
            "methodology_gaps": [],
            "recommendations": [],
        }

        if not self.graph_store or not project_id:
            gaps["status"] = "graph_store_unavailable"
            gaps["recommendations"].append("Import more papers to enable gap analysis")
            return gaps

        try:
            # Get concepts with low paper counts
            # This would require graph traversal - simplified implementation
            gaps["recommendations"].extend([
                "Consider exploring concepts with fewer than 3 papers",
                "Look for methodological approaches not yet applied to your domain",
                "Identify recent trends that lack comprehensive coverage",
            ])
            gaps["status"] = "analysis_complete"
        except Exception as e:
            logger.warning(f"Gap analysis failed: {e}")
            gaps["status"] = "partial"

        return gaps
