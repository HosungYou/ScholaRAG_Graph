"""
Chat API Router

Handles multi-agent chat interactions with graph-grounded responses.
"""

import os
import logging
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

from agents.orchestrator import AgentOrchestrator
from llm.claude_provider import ClaudeProvider

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic Models
class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime
    citations: Optional[List[str]] = None
    highlighted_nodes: Optional[List[str]] = None
    highlighted_edges: Optional[List[str]] = None
    suggested_follow_ups: Optional[List[str]] = None


class ChatRequest(BaseModel):
    project_id: UUID
    message: str
    conversation_id: Optional[str] = None
    include_trace: bool = False


class SimpleCitation(BaseModel):
    """Citation reference for chat responses."""
    id: str
    label: str
    entity_type: Optional[str] = None


class ResearchGapSummary(BaseModel):
    """Summary of a research gap for chat responses."""
    description: str
    questions: List[str] = []
    bridge_concepts: List[str] = []


class ChatResponse(BaseModel):
    """Flat response structure aligned with frontend expectations."""
    conversation_id: str
    answer: str
    citations: List[SimpleCitation] = []
    highlighted_nodes: List[str] = []
    highlighted_edges: List[str] = []
    suggested_follow_ups: List[str] = []
    agent_trace: Optional[dict] = None
    # New: Gap-based suggestions
    research_gaps: List[ResearchGapSummary] = []
    hidden_connections: List[str] = []


class ConversationHistory(BaseModel):
    conversation_id: str
    project_id: UUID
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime


# In-memory storage
_conversations_db: dict = {}

# Global orchestrator instance (lazy loaded)
_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        llm_provider = None
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            try:
                llm_provider = ClaudeProvider(api_key=api_key)
                logger.info("Initialized Claude LLM provider")
            except Exception as e:
                logger.warning(f"Failed to initialize Claude provider: {e}")

        _orchestrator = AgentOrchestrator(llm_provider=llm_provider)
    return _orchestrator


@router.post("/query", response_model=ChatResponse)
async def chat_query(request: ChatRequest):
    """
    Send a query to the multi-agent system.

    Pipeline:
    1. Intent Agent - Classify user intent
    2. Concept Extraction Agent - Extract entities from query
    3. Task Planning Agent - Break down complex queries
    4. Query Execution Agent - Run SQL + Vector searches
    5. Reasoning Agent - Synthesize results
    6. Response Agent - Generate user-friendly response
    """
    conversation_id = request.conversation_id or str(uuid4())

    # Get orchestrator and process query
    orchestrator = get_orchestrator()

    answer = ""
    citations: List[SimpleCitation] = []
    highlighted_nodes: List[str] = []
    highlighted_edges: List[str] = []
    suggested_follow_ups: List[str] = []
    research_gaps: List[ResearchGapSummary] = []
    hidden_connections: List[str] = []
    agent_trace = None

    try:
        result = await orchestrator.process_query(
            query=request.message,
            project_id=str(request.project_id),
            conversation_id=conversation_id,
            include_processing_steps=request.include_trace,
        )

        answer = result.content
        # Convert string citations to SimpleCitation objects
        citations = [
            SimpleCitation(id=str(i), label=cite, entity_type="Concept")  # Concept-centric
            for i, cite in enumerate(result.citations or [])
        ]
        highlighted_nodes = result.highlighted_nodes or []
        highlighted_edges = result.highlighted_edges or []
        suggested_follow_ups = result.suggested_follow_ups or []

        # Convert research gaps to response format
        research_gaps = [
            ResearchGapSummary(
                description=gap.description,
                questions=gap.questions,
                bridge_concepts=gap.bridge_concepts,
            )
            for gap in (result.research_gaps or [])
        ]
        hidden_connections = result.hidden_connections or []

        if request.include_trace:
            agent_trace = {
                "intent": result.intent,
                "confidence": result.confidence,
                "processing_steps": result.processing_steps,
            }

    except Exception as e:
        logger.error(f"Chat query failed: {e}")
        answer = "I encountered an error processing your request. Please try again."
        agent_trace = {"error": "Processing error occurred"} if request.include_trace else None

    # Store conversation in memory
    assistant_message = ChatMessage(
        role="assistant",
        content=answer,
        timestamp=datetime.now(),
        citations=[c.label for c in citations],
        highlighted_nodes=highlighted_nodes,
        highlighted_edges=highlighted_edges,
        suggested_follow_ups=suggested_follow_ups,
    )
    user_message = ChatMessage(role="user", content=request.message, timestamp=datetime.now())

    if conversation_id not in _conversations_db:
        _conversations_db[conversation_id] = {
            "conversation_id": conversation_id,
            "project_id": str(request.project_id),
            "messages": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

    _conversations_db[conversation_id]["messages"].extend([
        user_message.model_dump(), assistant_message.model_dump()
    ])
    _conversations_db[conversation_id]["updated_at"] = datetime.now()

    return ChatResponse(
        conversation_id=conversation_id,
        answer=answer,
        citations=citations,
        highlighted_nodes=highlighted_nodes,
        highlighted_edges=highlighted_edges,
        suggested_follow_ups=suggested_follow_ups,
        agent_trace=agent_trace,
        research_gaps=research_gaps,
        hidden_connections=hidden_connections,
    )


@router.get("/history/{project_id}", response_model=List[ConversationHistory])
async def get_chat_history(project_id: UUID):
    """Get all conversations for a project."""
    conversations = [
        ConversationHistory(**conv)
        for conv in _conversations_db.values()
        if conv["project_id"] == str(project_id)
    ]
    return conversations


@router.get("/conversation/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(conversation_id: str):
    """Get a specific conversation."""
    conv = _conversations_db.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationHistory(**conv)


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    if conversation_id not in _conversations_db:
        raise HTTPException(status_code=404, detail="Conversation not found")
    del _conversations_db[conversation_id]
    return {"status": "deleted", "conversation_id": conversation_id}


class ExplainRequest(BaseModel):
    node_name: Optional[str] = None
    node_type: Optional[str] = None
    node_properties: Optional[dict] = None


@router.post("/explain/{node_id}")
async def explain_node(node_id: str, project_id: UUID, request: Optional[ExplainRequest] = None):
    """
    Generate AI explanation for a node when clicked in Exploration Mode.
    Uses the orchestrator's LLM provider for generation.
    """
    orchestrator = get_orchestrator()

    # Build context for explanation
    node_name = request.node_name if request else node_id
    node_type = request.node_type if request else "Entity"
    properties = request.node_properties if request else {}

    # Generate explanation using orchestrator
    query = f"Explain this {node_type}: {node_name}"

    try:
        result = await orchestrator.process_query(
            query=query,
            project_id=str(project_id),
        )

        return {
            "node_id": node_id,
            "explanation": result.content,
            "related_nodes": result.highlighted_nodes,
            "suggested_questions": result.suggested_follow_ups or [
                f"What papers discuss {node_name}?",
                f"How does {node_name} relate to other concepts?",
                f"What are the key findings about {node_name}?",
            ],
        }
    except Exception as e:
        logger.error(f"Node explanation failed: {e}")
        return {
            "node_id": node_id,
            "explanation": f"Unable to generate explanation for {node_name}.",
            "related_nodes": [],
            "suggested_questions": [
                "What papers discuss this topic?",
                "Show related concepts",
                "What are the key findings?",
            ],
        }


@router.post("/ask-about/{node_id}")
async def ask_about_node(node_id: str, project_id: UUID, question: str):
    """
    Ask a specific question about a node.
    Called from NodeDetails "Ask AI" button.
    """
    conversation_id = str(uuid4())
    orchestrator = get_orchestrator()

    try:
        result = await orchestrator.process_query(
            query=question,
            project_id=str(project_id),
            conversation_id=conversation_id,
        )

        return {
            "conversation_id": conversation_id,
            "node_id": node_id,
            "question": question,
            "answer": result.content,
            "citations": result.citations,
            "highlighted_nodes": result.highlighted_nodes,
            "suggested_follow_ups": result.suggested_follow_ups,
        }
    except Exception as e:
        logger.error(f"Ask about node failed: {e}")
        return {
            "conversation_id": conversation_id,
            "node_id": node_id,
            "question": question,
            "answer": f"I couldn't process your question. Error: {str(e)}",
            "citations": [],
            "highlighted_nodes": [],
            "suggested_follow_ups": [],
        }
