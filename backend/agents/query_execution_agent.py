"""
Query Execution Agent

Executes sub-tasks by running SQL queries, vector searches, and graph traversals.
Supports all task types from TaskPlanningAgent: search, retrieve, analyze, compare, explain, analyze_gaps.
"""

import logging
from typing import Any, Optional
from pydantic import BaseModel

from graph.hierarchical_retriever import HierarchicalRetriever, RetrievalMode

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
        
        # Initialize hierarchical retriever for chunk-based search
        self.hierarchical_retriever = HierarchicalRetriever(graph_store=graph_store) if graph_store else None

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
                elif task.task_type == "document_search":
                    # Chunk-based document search with hierarchical retrieval
                    params = {**task.parameters, "use_chunks": True}
                    data = await self._execute_search(params)
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
        """Execute a search query against the graph store.
        
        Supports both entity search and chunk-based document search.
        Set use_chunks=True to search through semantic chunks with parent context expansion.
        """
        query = params.get("query", "")
        limit = params.get("limit", 20)
        entity_types = params.get("entity_types")
        project_id = params.get("project_id")
        use_chunks = params.get("use_chunks", False)
        section_filter = params.get("section_filter")  # e.g., ["methodology", "results"]

        # Chunk-based hierarchical search
        if use_chunks and self.hierarchical_retriever and project_id:
            try:
                retrieval_result = await self.hierarchical_retriever.search(
                    query=query,
                    project_id=project_id,
                    mode=RetrievalMode.PARENT_EXPAND,  # Expand to parent for context
                    section_filter=section_filter,
                    limit=limit,
                )
                # Convert to serializable format
                return [
                    {
                        "chunk_id": r.chunk_id,
                        "text": r.text,
                        "summary": r.summary,
                        "section_type": r.section_type,
                        "score": r.score,
                        "paper_id": r.paper_id,
                        "parent_context": r.parent_context.text if r.parent_context else None,
                    }
                    for r in retrieval_result.results
                ]
            except Exception as e:
                logger.warning(f"Hierarchical retrieval failed: {e}")
                # Fall through to entity search

        # Entity-based search (default)
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
        Queries structural_gaps and entities tables for real gap data.
        """
        project_id = params.get("project_id")

        gaps = {
            "identified_gaps": [],
            "underexplored_concepts": [],
            "methodology_gaps": [],
            "recommendations": [],
        }

        if not self.graph_store or not project_id:
            gaps["status"] = "graph_store_unavailable"
            gaps["message"] = "Knowledge graph is not initialized. Please import papers first."
            return gaps

        try:
            db = self.graph_store.db

            # 1. Query structural_gaps table for detected gaps
            gap_rows = await db.fetch(
                """
                SELECT cluster_a_names, cluster_b_names, gap_strength,
                       bridge_candidates, research_questions
                FROM structural_gaps
                WHERE project_id = $1
                ORDER BY gap_strength ASC
                LIMIT 10
                """,
                str(project_id),
            )

            for row in gap_rows:
                a_names = row.get("cluster_a_names") or []
                b_names = row.get("cluster_b_names") or []
                strength = row.get("gap_strength", 0)
                questions = row.get("research_questions") or []

                gaps["identified_gaps"].append({
                    "cluster_a": a_names[:3],
                    "cluster_b": b_names[:3],
                    "gap_strength": round(strength, 3),
                    "research_questions": questions[:3],
                })

            # 2. Query underexplored concepts (low degree entities)
            underexplored_rows = await db.fetch(
                """
                SELECT e.name, e.entity_type::text as entity_type,
                       COUNT(r.id) as rel_count
                FROM entities e
                LEFT JOIN relationships r ON (r.source_id = e.id OR r.target_id = e.id)
                WHERE e.project_id = $1
                  AND e.entity_type::text IN ('Concept', 'Method', 'Finding')
                GROUP BY e.id, e.name, e.entity_type
                HAVING COUNT(r.id) <= 2
                ORDER BY COUNT(r.id) ASC
                LIMIT 10
                """,
                str(project_id),
            )

            for row in underexplored_rows:
                gaps["underexplored_concepts"].append({
                    "name": row["name"],
                    "type": row["entity_type"],
                    "connection_count": row["rel_count"],
                })

            # 3. Check for methodology gaps
            method_rows = await db.fetch(
                """
                SELECT e.name, COUNT(r.id) as usage_count
                FROM entities e
                LEFT JOIN relationships r ON (r.source_id = e.id OR r.target_id = e.id)
                WHERE e.project_id = $1
                  AND e.entity_type::text = 'Method'
                GROUP BY e.id, e.name
                ORDER BY COUNT(r.id) ASC
                LIMIT 5
                """,
                str(project_id),
            )

            for row in method_rows:
                gaps["methodology_gaps"].append({
                    "method": row["name"],
                    "usage_count": row["usage_count"],
                })

            # 4. Generate contextual recommendations
            if gaps["identified_gaps"]:
                for g in gaps["identified_gaps"][:3]:
                    a = ", ".join(g["cluster_a"][:2])
                    b = ", ".join(g["cluster_b"][:2])
                    gaps["recommendations"].append(
                        f"Explore the connection between {a} and {b} (gap strength: {g['gap_strength']:.1%})"
                    )

            if gaps["underexplored_concepts"]:
                names = [c["name"] for c in gaps["underexplored_concepts"][:3]]
                gaps["recommendations"].append(
                    f"These concepts need more research coverage: {', '.join(names)}"
                )

            if gaps["methodology_gaps"]:
                methods = [m["method"] for m in gaps["methodology_gaps"][:2]]
                gaps["recommendations"].append(
                    f"Consider applying underutilized methods: {', '.join(methods)}"
                )

            if not gaps["identified_gaps"] and not gaps["underexplored_concepts"]:
                gaps["recommendations"].append(
                    "No structural gaps detected. Consider refreshing gap analysis from the graph panel."
                )

            gaps["status"] = "analysis_complete"
            gaps["total_gaps"] = len(gaps["identified_gaps"])
            gaps["total_underexplored"] = len(gaps["underexplored_concepts"])

        except Exception as e:
            logger.error(f"Gap analysis query failed: {e}")
            gaps["status"] = "error"
            gaps["message"] = f"Gap analysis encountered an error: {str(e)}"

        return gaps
