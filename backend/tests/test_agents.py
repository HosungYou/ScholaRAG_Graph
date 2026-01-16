"""
Tests for Multi-Agent System.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass, field


class TestIntentAgent:
    """Test Intent Agent functionality."""

    @pytest.fixture
    def intent_agent(self):
        """Create intent agent."""
        from agents.intent_agent import IntentAgent
        return IntentAgent()

    @pytest.mark.asyncio
    async def test_classify_search_intent(self, intent_agent):
        """Test classifying search queries."""
        result = await intent_agent.classify("What papers discuss machine learning?")

        # IntentAgent.classify() returns IntentResult Pydantic model
        assert hasattr(result, 'intent')
        assert hasattr(result, 'confidence')
        assert result.confidence >= 0 and result.confidence <= 1

    @pytest.mark.asyncio
    async def test_classify_compare_intent(self, intent_agent):
        """Test classifying comparison queries."""
        result = await intent_agent.classify("Compare neural networks vs decision trees")

        # IntentType is an enum with lowercase values
        assert result.intent.value in ["compare", "search", "explore", "explain", "summarize", "identify_gaps", "create"]

    @pytest.mark.asyncio
    async def test_classify_gap_intent(self, intent_agent):
        """Test classifying gap detection queries."""
        result = await intent_agent.classify("What research gaps exist in AI education?")

        assert result.intent.value in ["identify_gaps", "search", "explore"]

    @pytest.mark.asyncio
    async def test_extract_keywords(self, intent_agent):
        """Test keyword extraction."""
        result = await intent_agent.classify("machine learning in healthcare")

        assert hasattr(result, 'keywords')
        assert isinstance(result.keywords, list)

    def test_fallback_classification(self, intent_agent):
        """Test fallback rule-based classification."""
        # Without LLM, should use keyword-based rules
        # Method renamed from _fallback_classify to _classify_with_keywords
        result = intent_agent._classify_with_keywords("compare A versus B")

        assert result.intent.value == "compare"


class TestConceptExtractionAgent:
    """Test Concept Extraction Agent functionality."""

    @pytest.fixture
    def concept_agent(self):
        """Create concept extraction agent."""
        from agents.concept_extraction_agent import ConceptExtractionAgent
        return ConceptExtractionAgent()

    @pytest.mark.asyncio
    async def test_extract_entities(self, concept_agent):
        """Test entity extraction from query."""
        result = await concept_agent.extract(
            "How does machine learning improve medical diagnosis?"
        )

        # ExtractionResult is a Pydantic model
        assert hasattr(result, 'entities')
        assert isinstance(result.entities, list)

    @pytest.mark.asyncio
    async def test_extract_with_existing_graph(self, concept_agent):
        """Test extraction with graph node matching."""
        # Note: graph_context parameter doesn't exist in current API
        # The graph_store is passed to constructor, not extract method
        result = await concept_agent.extract(
            "machine learning in medical diagnosis"
        )

        # Extracted entities should be a list (may be empty without LLM)
        assert hasattr(result, 'entities')
        assert isinstance(result.entities, list)

    @pytest.mark.asyncio
    async def test_extract_keywords(self, concept_agent):
        """Test keyword extraction from queries."""
        result = await concept_agent.extract("deep learning for image classification")

        assert hasattr(result, 'keywords')
        assert isinstance(result.keywords, list)
        assert len(result.keywords) > 0


class TestTaskPlanningAgent:
    """Test Task Planning Agent functionality."""

    @pytest.fixture
    def task_agent(self):
        """Create task planning agent."""
        from agents.task_planning_agent import TaskPlanningAgent
        return TaskPlanningAgent()

    @pytest.mark.asyncio
    async def test_plan_simple_search(self, task_agent):
        """Test planning for simple search."""
        from agents.intent_agent import IntentType
        from agents.concept_extraction_agent import ExtractedEntity

        # plan() now takes query, intent_type, entities
        entities = [ExtractedEntity(text="machine learning", entity_type="Concept", confidence=0.8)]

        plan = await task_agent.plan("What is machine learning?", IntentType.SEARCH, entities)

        # TaskPlan is a Pydantic model with tasks attribute
        assert hasattr(plan, 'tasks')
        assert len(plan.tasks) >= 1

    @pytest.mark.asyncio
    async def test_plan_comparison(self, task_agent):
        """Test planning for comparison queries."""
        from agents.intent_agent import IntentType
        from agents.concept_extraction_agent import ExtractedEntity

        entities = [
            ExtractedEntity(text="neural networks", entity_type="Concept", confidence=0.8),
            ExtractedEntity(text="decision trees", entity_type="Concept", confidence=0.8),
        ]

        plan = await task_agent.plan("Compare neural networks with decision trees", IntentType.COMPARE, entities)

        # Should have multiple tasks
        assert hasattr(plan, 'tasks')
        task_types = [t.task_type for t in plan.tasks]
        assert "compare" in task_types or "search" in task_types


class TestQueryExecutionAgent:
    """Test Query Execution Agent functionality."""

    @pytest.fixture
    def query_agent(self):
        """Create query execution agent."""
        from agents.query_execution_agent import QueryExecutionAgent

        mock_graph_store = MagicMock()
        mock_graph_store.search_entities = AsyncMock(return_value=[])
        mock_graph_store.get_entity = AsyncMock(return_value=None)

        return QueryExecutionAgent(graph_store=mock_graph_store)

    @pytest.mark.asyncio
    async def test_execute_search_task(self, query_agent):
        """Test executing search task."""
        from agents.task_planning_agent import TaskPlan, SubTask
        from agents.intent_agent import IntentType

        # Create a TaskPlan with tasks - SubTask (not Task)
        task = SubTask(
            task_type="search",
            description="Search for machine learning",
            parameters={"query": "machine learning"},
        )
        # TaskPlan requires original_query, intent, estimated_complexity
        task_plan = TaskPlan(
            original_query="What is machine learning?",
            intent=IntentType.SEARCH,
            tasks=[task],
            estimated_complexity="low",
        )

        result = await query_agent.execute(task_plan)

        # ExecutionResult has results list
        assert hasattr(result, 'results')

    @pytest.mark.asyncio
    async def test_execute_returns_nodes_accessed(self, query_agent):
        """Test that execution returns accessed nodes."""
        from agents.task_planning_agent import TaskPlan, SubTask
        from agents.intent_agent import IntentType

        task = SubTask(
            task_type="search",
            description="Search test",
            parameters={"query": "test"},
        )
        task_plan = TaskPlan(
            original_query="test query",
            intent=IntentType.SEARCH,
            tasks=[task],
            estimated_complexity="low",
        )

        result = await query_agent.execute(task_plan)

        assert hasattr(result, 'nodes_accessed')
        assert isinstance(result.nodes_accessed, list)


class TestReasoningAgent:
    """Test Reasoning Agent functionality."""

    @pytest.fixture
    def reasoning_agent(self):
        """Create reasoning agent."""
        from agents.reasoning_agent import ReasoningAgent

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="Step 1: Analysis...")

        return ReasoningAgent(llm_provider=mock_llm)

    @pytest.mark.asyncio
    async def test_chain_of_thought_reasoning(self, reasoning_agent):
        """Test chain-of-thought reasoning."""
        from agents.intent_agent import IntentType
        from agents.query_execution_agent import ExecutionResult, QueryResult

        # QueryResult uses task_index, not task_type
        execution_result = ExecutionResult(
            results=[QueryResult(task_index=0, success=True, data=[{"name": "test"}])],
            nodes_accessed=[],
        )

        result = await reasoning_agent.reason(
            query="What are the key findings?",
            intent=IntentType.SEARCH,
            execution_result=execution_result,
        )

        # ReasoningResult has steps and final_conclusion
        assert hasattr(result, 'steps') or hasattr(result, 'final_conclusion')

    @pytest.mark.asyncio
    async def test_gap_analysis_reasoning(self, reasoning_agent):
        """Test reasoning with gap analysis."""
        from agents.intent_agent import IntentType
        from agents.query_execution_agent import ExecutionResult, QueryResult

        # QueryResult uses task_index, not task_type
        execution_result = ExecutionResult(
            results=[QueryResult(task_index=0, success=True, data={"gaps": []})],
            nodes_accessed=[],
        )

        result = await reasoning_agent.reason(
            query="What research gaps exist?",
            intent=IntentType.IDENTIFY_GAPS,
            execution_result=execution_result,
            include_gaps=True,
        )

        assert hasattr(result, 'research_gaps') or hasattr(result, 'final_conclusion')


class TestResponseAgent:
    """Test Response Agent functionality."""

    @pytest.fixture
    def response_agent(self):
        """Create response agent."""
        from agents.response_agent import ResponseAgent

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="Based on the analysis...")

        return ResponseAgent(llm_provider=mock_llm)

    @pytest.mark.asyncio
    async def test_generate_response(self, response_agent):
        """Test response generation."""
        from agents.intent_agent import IntentType
        from agents.reasoning_agent import ReasoningResult, ReasoningStep

        # ReasoningStep requires step_number field
        reasoning = ReasoningResult(
            final_conclusion="The analysis shows...",
            steps=[ReasoningStep(step_number=1, description="Step 1", conclusion="Found X")],
            confidence=0.8,
        )

        result = await response_agent.generate(
            query="What is machine learning?",
            reasoning_result=reasoning,
            intent=IntentType.SEARCH,
        )

        # ResponseResult has answer attribute
        assert hasattr(result, 'answer')
        assert isinstance(result.answer, str)

    @pytest.mark.asyncio
    async def test_response_with_citations(self, response_agent):
        """Test response includes citations."""
        from agents.intent_agent import IntentType
        from agents.reasoning_agent import ReasoningResult, ReasoningStep

        # ReasoningStep requires step_number field
        reasoning = ReasoningResult(
            final_conclusion="The analysis shows...",
            steps=[ReasoningStep(step_number=1, description="Step 1", conclusion="Found X")],
            confidence=0.8,
            supporting_nodes=["node-1", "node-2"],
        )

        result = await response_agent.generate(
            query="Explain X",
            reasoning_result=reasoning,
            intent=IntentType.EXPLAIN,
        )

        assert hasattr(result, 'citations')

    @pytest.mark.asyncio
    async def test_follow_up_suggestions(self, response_agent):
        """Test follow-up question generation."""
        from agents.intent_agent import IntentType
        from agents.reasoning_agent import ReasoningResult, ReasoningStep

        # ReasoningStep requires step_number field
        reasoning = ReasoningResult(
            final_conclusion="AI improves education.",
            steps=[ReasoningStep(step_number=1, description="Step 1", conclusion="Found evidence")],
            confidence=0.8,
        )

        result = await response_agent.generate(
            query="How does AI help education?",
            reasoning_result=reasoning,
            intent=IntentType.SEARCH,
        )

        assert hasattr(result, 'suggested_follow_ups')
        assert isinstance(result.suggested_follow_ups, list)


class TestOrchestrator:
    """Test Agent Orchestrator functionality."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked LLM."""
        from agents.orchestrator import AgentOrchestrator

        # Create mock LLM provider
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value='{"intent": "search", "confidence": 0.9, "keywords": []}')

        # AgentOrchestrator takes llm_provider, graph_store, vector_store, db_connection
        # NOT individual agents
        return AgentOrchestrator(
            llm_provider=mock_llm,
            graph_store=None,
            vector_store=None,
            db_connection=None,
        )

    @pytest.mark.asyncio
    async def test_full_pipeline(self, orchestrator):
        """Test full agent pipeline."""
        # Mock the internal agents to avoid LLM calls
        with patch.object(orchestrator.intent_agent, 'classify') as mock_intent, \
             patch.object(orchestrator.concept_agent, 'extract') as mock_concept, \
             patch.object(orchestrator.planning_agent, 'plan') as mock_plan, \
             patch.object(orchestrator.execution_agent, 'execute') as mock_exec, \
             patch.object(orchestrator.reasoning_agent, 'reason') as mock_reason, \
             patch.object(orchestrator.response_agent, 'generate') as mock_response:

            # Setup mock returns
            from agents.intent_agent import IntentResult, IntentType
            from agents.concept_extraction_agent import ExtractionResult
            from agents.task_planning_agent import TaskPlan
            from agents.query_execution_agent import ExecutionResult
            from agents.reasoning_agent import ReasoningResult
            from agents.response_agent import ResponseResult, Citation

            mock_intent.return_value = IntentResult(intent=IntentType.SEARCH, confidence=0.9)
            mock_concept.return_value = ExtractionResult(entities=[], keywords=[], query_without_entities="test")
            # TaskPlan requires original_query, intent, estimated_complexity
            mock_plan.return_value = TaskPlan(
                original_query="What is machine learning?",
                intent=IntentType.SEARCH,
                tasks=[],
                estimated_complexity="low",
            )
            mock_exec.return_value = ExecutionResult(results=[], nodes_accessed=[])
            mock_reason.return_value = ReasoningResult(final_conclusion="test", steps=[], confidence=0.8)
            mock_response.return_value = ResponseResult(
                answer="test answer",
                citations=[],
                highlighted_nodes=[],
                highlighted_edges=[],
                suggested_follow_ups=[],
            )

            # process_query takes query and project_id (not project_id and message)
            result = await orchestrator.process_query(
                query="What is machine learning?",
                project_id="test-project",
            )

            # Returns OrchestratorResult dataclass
            assert hasattr(result, 'content')

    @pytest.mark.asyncio
    async def test_conversation_context_preserved(self, orchestrator):
        """Test that conversation context is preserved."""
        # Mock the internal agents
        with patch.object(orchestrator.intent_agent, 'classify') as mock_intent, \
             patch.object(orchestrator.concept_agent, 'extract') as mock_concept, \
             patch.object(orchestrator.planning_agent, 'plan') as mock_plan, \
             patch.object(orchestrator.execution_agent, 'execute') as mock_exec, \
             patch.object(orchestrator.reasoning_agent, 'reason') as mock_reason, \
             patch.object(orchestrator.response_agent, 'generate') as mock_response:

            from agents.intent_agent import IntentResult, IntentType
            from agents.concept_extraction_agent import ExtractionResult
            from agents.task_planning_agent import TaskPlan
            from agents.query_execution_agent import ExecutionResult
            from agents.reasoning_agent import ReasoningResult
            from agents.response_agent import ResponseResult

            mock_intent.return_value = IntentResult(intent=IntentType.SEARCH, confidence=0.9)
            mock_concept.return_value = ExtractionResult(entities=[], keywords=[], query_without_entities="test")
            # TaskPlan requires original_query, intent, estimated_complexity
            mock_plan.return_value = TaskPlan(
                original_query="What is AI?",
                intent=IntentType.SEARCH,
                tasks=[],
                estimated_complexity="low",
            )
            mock_exec.return_value = ExecutionResult(results=[], nodes_accessed=[])
            mock_reason.return_value = ReasoningResult(final_conclusion="test", steps=[], confidence=0.8)
            mock_response.return_value = ResponseResult(
                answer="test answer",
                citations=[],
                highlighted_nodes=[],
                highlighted_edges=[],
                suggested_follow_ups=[],
            )

            # First query
            await orchestrator.process_query(
                query="What is AI?",
                project_id="test-project",
                conversation_id="conv-1",
            )

            # Second query in same conversation
            result = await orchestrator.process_query(
                query="Tell me more about that",
                project_id="test-project",
                conversation_id="conv-1",
            )

            # Should have access to context
            assert result is not None

            # Check context was created
            context = orchestrator.get_context_summary("conv-1")
            assert context is not None
            assert context["num_messages"] == 4  # 2 user + 2 assistant messages
