"""
Multi-Agent Orchestrator

Coordinates the 6-agent system for processing user queries:
1. Intent Agent - Classifies user intent
2. Concept Extraction Agent - Extracts entities from query
3. Task Planning Agent - Creates execution plan
4. Query Execution Agent - Executes queries against graph
5. Reasoning Agent - Synthesizes results
6. Response Agent - Generates final response
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from .intent_agent import IntentAgent, IntentResult, IntentType
from .concept_extraction_agent import ConceptExtractionAgent, ExtractionResult
from .task_planning_agent import TaskPlanningAgent, TaskPlan
from .query_execution_agent import QueryExecutionAgent, ExecutionResult
from .reasoning_agent import ReasoningAgent, ReasoningResult
from .response_agent import ResponseAgent, ResponseResult

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Maintains conversation state across turns."""
    conversation_id: str
    project_id: str
    messages: list = field(default_factory=list)
    highlighted_nodes: list = field(default_factory=list)
    highlighted_edges: list = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ResearchGapSummary:
    """Summary of a research gap suggestion."""
    description: str
    questions: list[str] = field(default_factory=list)
    bridge_concepts: list[str] = field(default_factory=list)


@dataclass
class OrchestratorResult:
    """Complete result from the orchestration pipeline."""
    content: str
    citations: list[str] = field(default_factory=list)
    highlighted_nodes: list[str] = field(default_factory=list)
    highlighted_edges: list[str] = field(default_factory=list)
    suggested_follow_ups: list[str] = field(default_factory=list)
    intent: Optional[str] = None
    confidence: float = 0.0
    processing_steps: list[Dict[str, Any]] = field(default_factory=list)
    # New: Gap-based suggestions
    research_gaps: list[ResearchGapSummary] = field(default_factory=list)
    hidden_connections: list[str] = field(default_factory=list)


class AgentOrchestrator:
    """
    Orchestrates the multi-agent system following AGENTiGraph architecture.

    Pipeline flow:
    Query → Intent → Concept Extraction → Task Planning →
    Query Execution → Reasoning → Response
    """

    def __init__(
        self,
        llm_provider=None,
        graph_store=None,
        vector_store=None,
        db_connection=None,
    ):
        self.llm = llm_provider
        self.graph_store = graph_store
        self.vector_store = vector_store
        self.db = db_connection

        # Initialize agents
        self.intent_agent = IntentAgent(llm_provider)
        self.concept_agent = ConceptExtractionAgent(llm_provider, graph_store)
        self.planning_agent = TaskPlanningAgent(llm_provider)
        self.execution_agent = QueryExecutionAgent(db_connection, vector_store, graph_store)
        self.reasoning_agent = ReasoningAgent(llm_provider, db_connection)  # Pass db for gap analysis
        self.response_agent = ResponseAgent(llm_provider)

        # Conversation contexts
        self._contexts: Dict[str, ConversationContext] = {}

    def get_or_create_context(
        self, conversation_id: str, project_id: str
    ) -> ConversationContext:
        """Get existing context or create new one."""
        if conversation_id not in self._contexts:
            self._contexts[conversation_id] = ConversationContext(
                conversation_id=conversation_id,
                project_id=project_id,
            )
        return self._contexts[conversation_id]

    async def process_query(
        self,
        query: str,
        project_id: str,
        conversation_id: Optional[str] = None,
        include_processing_steps: bool = False,
    ) -> OrchestratorResult:
        """
        Process a user query through the full agent pipeline.

        Args:
            query: User's question
            project_id: ID of the project/knowledge graph
            conversation_id: Optional conversation ID for context
            include_processing_steps: Whether to include detailed processing info

        Returns:
            OrchestratorResult with answer and metadata
        """
        processing_steps = []

        try:
            # Step 1: Intent Classification
            logger.info(f"[1/6] Classifying intent for: {query[:50]}...")
            intent_result = await self.intent_agent.classify(query)
            processing_steps.append({
                "step": "intent_classification",
                "result": {
                    "intent": intent_result.intent.value,
                    "confidence": intent_result.confidence,
                }
            })

            # Early return for conversational queries (greetings, thanks, etc.)
            if intent_result.intent == IntentType.CONVERSATIONAL:
                logger.info("[CONVERSATIONAL] Returning friendly greeting response")
                return OrchestratorResult(
                    content="안녕하세요! ScholaRAG 연구 어시스턴트입니다. 문헌 검색, 연구 갭 분석, 개념 탐색에 대해 질문해 주세요.\n\nHello! I'm ScholaRAG's research assistant. I can help you with:\n• **Literature search** - Find papers on specific topics\n• **Research gap analysis** - Discover unexplored research areas\n• **Concept exploration** - Understand relationships between concepts\n\nHow can I assist with your research today?",
                    intent="conversational",
                    confidence=intent_result.confidence,
                    suggested_follow_ups=[
                        "What are the main research topics?",
                        "Show me research gaps in this field",
                        "Explain the key concepts",
                    ],
                    processing_steps=processing_steps if include_processing_steps else [],
                )

            # Step 2: Concept/Entity Extraction
            logger.info(f"[2/6] Extracting concepts...")
            extraction_result = await self.concept_agent.extract(query)
            processing_steps.append({
                "step": "concept_extraction",
                "result": {
                    "entities_found": len(extraction_result.entities),
                    "keywords": extraction_result.keywords[:5],
                }
            })

            # Step 3: Task Planning
            logger.info(f"[3/6] Planning tasks...")
            task_plan = await self.planning_agent.plan(
                query, intent_result.intent, extraction_result.entities
            )
            processing_steps.append({
                "step": "task_planning",
                "result": {
                    "num_tasks": len(task_plan.tasks),
                    "complexity": task_plan.estimated_complexity,
                }
            })

            # Step 4: Query Execution
            logger.info(f"[4/6] Executing {len(task_plan.tasks)} tasks...")
            execution_result = await self.execution_agent.execute(task_plan)
            processing_steps.append({
                "step": "query_execution",
                "result": {
                    "successful_tasks": sum(1 for r in execution_result.results if r.success),
                    "total_tasks": len(execution_result.results),
                    "nodes_accessed": len(execution_result.nodes_accessed),
                }
            })

            # Step 5: Reasoning (with gap analysis)
            logger.info(f"[5/6] Applying reasoning with gap analysis...")
            reasoning_result = await self.reasoning_agent.reason(
                query,
                intent_result.intent,
                execution_result,
                project_id=project_id,  # Pass project_id for gap analysis
                include_gaps=True,
            )
            processing_steps.append({
                "step": "reasoning",
                "result": {
                    "num_steps": len(reasoning_result.steps),
                    "confidence": reasoning_result.confidence,
                    "research_gaps": len(reasoning_result.research_gaps),
                    "hidden_connections": len(reasoning_result.hidden_connections),
                }
            })

            # Step 6: Response Generation
            logger.info(f"[6/6] Generating response...")
            response_result = await self.response_agent.generate(
                query, reasoning_result, intent_result.intent
            )
            processing_steps.append({
                "step": "response_generation",
                "result": {
                    "answer_length": len(response_result.answer),
                    "num_citations": len(response_result.citations),
                }
            })

            # Update conversation context if provided
            if conversation_id:
                context = self.get_or_create_context(conversation_id, project_id)
                context.messages.append({
                    "role": "user",
                    "content": query,
                    "timestamp": datetime.now().isoformat(),
                })
                context.messages.append({
                    "role": "assistant",
                    "content": response_result.answer,
                    "timestamp": datetime.now().isoformat(),
                })
                context.highlighted_nodes = response_result.highlighted_nodes
                context.highlighted_edges = response_result.highlighted_edges
                context.last_updated = datetime.now()

            # Convert research gaps to summaries
            research_gap_summaries = [
                ResearchGapSummary(
                    description=gap.gap_description,
                    questions=gap.suggested_questions,
                    bridge_concepts=gap.bridge_concepts,
                )
                for gap in reasoning_result.research_gaps
            ]

            return OrchestratorResult(
                content=response_result.answer,
                citations=[c.label for c in response_result.citations],
                highlighted_nodes=response_result.highlighted_nodes,
                highlighted_edges=response_result.highlighted_edges,
                suggested_follow_ups=response_result.suggested_follow_ups,
                intent=intent_result.intent.value,
                confidence=reasoning_result.confidence,
                processing_steps=processing_steps if include_processing_steps else [],
                research_gaps=research_gap_summaries,
                hidden_connections=reasoning_result.hidden_connections,
            )

        except Exception as e:
            logger.error(f"Orchestration error: {e}")
            processing_steps.append({
                "step": "error",
                "error": str(e),
            })

            return OrchestratorResult(
                content=f"I encountered an error while processing your query. Please try rephrasing or ask a different question.\n\nError: {str(e)}",
                processing_steps=processing_steps if include_processing_steps else [],
            )

    async def process_with_llm_enhancement(
        self,
        query: str,
        project_id: str,
        conversation_id: Optional[str] = None,
    ) -> OrchestratorResult:
        """
        Enhanced processing that uses LLM for better responses.
        Falls back to basic processing if LLM is unavailable.
        """
        # Get conversation context for better responses
        context = None
        if conversation_id:
            context = self.get_or_create_context(conversation_id, project_id)

        # If LLM is available, use it for enhanced processing
        if self.llm:
            try:
                # Build context from conversation history
                history_context = ""
                if context and context.messages:
                    recent_messages = context.messages[-6:]  # Last 3 turns
                    history_context = "\n".join([
                        f"{m['role'].title()}: {m['content']}"
                        for m in recent_messages
                    ])

                # Get graph context
                graph_context = await self._get_graph_context(query, project_id)

                # Generate enhanced response
                system_prompt = self._build_system_prompt(graph_context)

                enhanced_response = await self.llm.generate(
                    prompt=f"Previous conversation:\n{history_context}\n\nUser query: {query}",
                    system_prompt=system_prompt,
                    max_tokens=2000,
                    temperature=0.7,
                )

                return OrchestratorResult(
                    content=enhanced_response,
                    highlighted_nodes=[],
                    highlighted_edges=[],
                    suggested_follow_ups=[
                        "What methods are most commonly used?",
                        "Show me related concepts",
                        "What are the key findings?",
                    ],
                )

            except Exception as e:
                logger.warning(f"LLM enhancement failed, falling back: {e}")

        # Fall back to basic processing
        return await self.process_query(query, project_id, conversation_id)

    async def _get_graph_context(self, query: str, project_id: str) -> str:
        """Get relevant graph context for the query."""
        if not self.graph_store:
            return "No graph context available."

        try:
            # Search for relevant entities
            entities = await self.graph_store.search_entities(
                query=query,
                project_id=project_id,
                limit=10,
            )

            if not entities:
                return "No relevant entities found in the knowledge graph."

            context_parts = ["Relevant entities from knowledge graph:"]
            for entity in entities[:5]:
                context_parts.append(
                    f"- {entity.get('name', 'Unknown')} ({entity.get('entity_type', 'Unknown')})"
                )

            return "\n".join(context_parts)

        except Exception as e:
            logger.warning(f"Failed to get graph context: {e}")
            return "Graph context unavailable."

    def _build_system_prompt(self, graph_context: str) -> str:
        """Build system prompt for LLM - concept-centric design."""
        return f"""You are a research assistant analyzing a concept-centric knowledge graph.
This is NOT a paper-centric graph. Instead:
- Concepts, Methods, Findings, Problems, Datasets, Metrics, Innovations, and Limitations are PRIMARY nodes
- Papers and Authors are METADATA attached to concepts (not visible as separate nodes)
- The focus is on understanding the research landscape through concept relationships

{graph_context}

Guidelines:
1. Focus on concepts and their relationships, not individual papers
2. Identify patterns and themes across the literature
3. Highlight research gaps - areas where concept clusters have weak connections
4. Suggest bridge concepts that could connect different research areas
5. Generate actionable research questions based on detected gaps

When analyzing the graph:
- Concepts connect via: RELATED_TO, CO_OCCURS_WITH, PREREQUISITE_OF
- Methods connect to concepts via: APPLIES_TO
- Findings connect to concepts via: SUPPORTS, CONTRADICTS
- BRIDGES_GAP indicates AI-suggested connections across research gaps

Your goal is to help researchers discover hidden connections and unexplored research opportunities."""

    def clear_context(self, conversation_id: str) -> bool:
        """Clear conversation context."""
        if conversation_id in self._contexts:
            del self._contexts[conversation_id]
            return True
        return False

    def get_context_summary(self, conversation_id: str) -> Optional[Dict]:
        """Get summary of conversation context."""
        if conversation_id not in self._contexts:
            return None

        ctx = self._contexts[conversation_id]
        return {
            "conversation_id": ctx.conversation_id,
            "project_id": ctx.project_id,
            "num_messages": len(ctx.messages),
            "highlighted_nodes": len(ctx.highlighted_nodes),
            "created_at": ctx.created_at.isoformat(),
            "last_updated": ctx.last_updated.isoformat(),
        }
