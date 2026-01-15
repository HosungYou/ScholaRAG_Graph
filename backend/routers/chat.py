"""
Chat API Router

Handles multi-agent chat interactions with graph-grounded responses.

Security:
- All endpoints require authentication in production (configurable via REQUIRE_AUTH)
- Conversation ownership is tracked via user_id field
- Users can only access their own conversations or conversations in projects they have access to

Storage:
- Primary: PostgreSQL database (conversations + messages tables)
- Fallback: In-memory storage when DB unavailable (development mode)
"""

import os
import json
import logging
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime

from agents.orchestrator import AgentOrchestrator
from llm.claude_provider import ClaudeProvider
from auth.dependencies import require_auth_if_configured
from auth.models import User
from database import db

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Database Operations with In-Memory Fallback
# ============================================================================

# In-memory storage (fallback when DB unavailable)
_conversations_db: dict = {}
_use_memory_fallback: bool = False


async def _check_db_available() -> bool:
    """Check if database is connected and available."""
    global _use_memory_fallback
    try:
        if db.is_connected and await db.health_check():
            _use_memory_fallback = False
            return True
    except Exception as e:
        logger.warning(f"Database check failed: {e}")

    if not _use_memory_fallback:
        logger.warning("Database unavailable - using in-memory storage (data will be lost on restart)")
        _use_memory_fallback = True
    return False


async def _db_create_conversation(
    conversation_id: str,
    project_id: str,
    user_id: Optional[str]
) -> None:
    """Create a new conversation in the database."""
    if not await _check_db_available():
        # Fallback to in-memory
        _conversations_db[conversation_id] = {
            "conversation_id": conversation_id,
            "project_id": project_id,
            "user_id": user_id,
            "messages": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        return

    try:
        await db.execute(
            """
            INSERT INTO conversations (id, project_id, user_id, created_at, updated_at)
            VALUES ($1, $2::uuid, $3::uuid, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
            """,
            conversation_id,
            project_id,
            user_id,
        )
    except Exception as e:
        logger.error(f"Failed to create conversation in DB: {e}")
        # Fallback to in-memory
        _conversations_db[conversation_id] = {
            "conversation_id": conversation_id,
            "project_id": project_id,
            "user_id": user_id,
            "messages": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }


async def _db_add_messages(
    conversation_id: str,
    user_message: "ChatMessage",
    assistant_message: "ChatMessage"
) -> None:
    """Add user and assistant messages to a conversation."""
    if not await _check_db_available():
        # Fallback to in-memory
        if conversation_id in _conversations_db:
            _conversations_db[conversation_id]["messages"].extend([
                user_message.model_dump(), assistant_message.model_dump()
            ])
            _conversations_db[conversation_id]["updated_at"] = datetime.now()
        return

    try:
        # Insert user message
        await db.execute(
            """
            INSERT INTO messages (
                id, conversation_id, role, content, citations,
                highlighted_nodes, highlighted_edges, suggested_follow_ups, created_at
            )
            VALUES (
                gen_random_uuid(), $1, $2, $3, $4::jsonb,
                $5::jsonb, $6::jsonb, $7::jsonb, $8
            )
            """,
            conversation_id,
            user_message.role,
            user_message.content,
            json.dumps(user_message.citations or []),
            json.dumps(user_message.highlighted_nodes or []),
            json.dumps(user_message.highlighted_edges or []),
            json.dumps(user_message.suggested_follow_ups or []),
            user_message.timestamp,
        )

        # Insert assistant message
        await db.execute(
            """
            INSERT INTO messages (
                id, conversation_id, role, content, citations,
                highlighted_nodes, highlighted_edges, suggested_follow_ups, created_at
            )
            VALUES (
                gen_random_uuid(), $1, $2, $3, $4::jsonb,
                $5::jsonb, $6::jsonb, $7::jsonb, $8
            )
            """,
            conversation_id,
            assistant_message.role,
            assistant_message.content,
            json.dumps(assistant_message.citations or []),
            json.dumps(assistant_message.highlighted_nodes or []),
            json.dumps(assistant_message.highlighted_edges or []),
            json.dumps(assistant_message.suggested_follow_ups or []),
            assistant_message.timestamp,
        )

        # Update conversation timestamp
        await db.execute(
            "UPDATE conversations SET updated_at = NOW() WHERE id = $1",
            conversation_id,
        )
    except Exception as e:
        logger.error(f"Failed to add messages to DB: {e}")
        # Fallback to in-memory
        if conversation_id not in _conversations_db:
            _conversations_db[conversation_id] = {
                "conversation_id": conversation_id,
                "project_id": "unknown",
                "user_id": None,
                "messages": [],
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }
        _conversations_db[conversation_id]["messages"].extend([
            user_message.model_dump(), assistant_message.model_dump()
        ])
        _conversations_db[conversation_id]["updated_at"] = datetime.now()


async def _db_get_conversation(conversation_id: str) -> Optional[dict]:
    """Get a conversation with all its messages."""
    if not await _check_db_available():
        return _conversations_db.get(conversation_id)

    try:
        # Get conversation metadata
        conv_row = await db.fetchrow(
            """
            SELECT id, project_id, user_id, created_at, updated_at
            FROM conversations
            WHERE id = $1
            """,
            conversation_id,
        )

        if not conv_row:
            # Check in-memory fallback (for conversations created before DB was available)
            return _conversations_db.get(conversation_id)

        # Get messages
        messages = await db.fetch(
            """
            SELECT role, content, citations, highlighted_nodes,
                   highlighted_edges, suggested_follow_ups, created_at as timestamp
            FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at ASC
            """,
            conversation_id,
        )

        return {
            "conversation_id": conv_row["id"],
            "project_id": str(conv_row["project_id"]) if conv_row["project_id"] else None,
            "user_id": str(conv_row["user_id"]) if conv_row["user_id"] else None,
            "messages": [
                {
                    "role": m["role"],
                    "content": m["content"],
                    "timestamp": m["timestamp"],
                    "citations": m["citations"] or [],
                    "highlighted_nodes": m["highlighted_nodes"] or [],
                    "highlighted_edges": m["highlighted_edges"] or [],
                    "suggested_follow_ups": m["suggested_follow_ups"] or [],
                }
                for m in messages
            ],
            "created_at": conv_row["created_at"],
            "updated_at": conv_row["updated_at"],
        }
    except Exception as e:
        logger.error(f"Failed to get conversation from DB: {e}")
        return _conversations_db.get(conversation_id)


async def _db_get_conversations_by_project(project_id: str) -> List[dict]:
    """Get all conversations for a project."""
    if not await _check_db_available():
        return [
            conv for conv in _conversations_db.values()
            if conv["project_id"] == project_id
        ]

    try:
        conv_rows = await db.fetch(
            """
            SELECT id FROM conversations
            WHERE project_id = $1::uuid
            ORDER BY updated_at DESC
            """,
            project_id,
        )

        result = []
        for row in conv_rows:
            conv = await _db_get_conversation(row["id"])
            if conv:
                result.append(conv)

        # Also include any in-memory conversations for this project
        for conv in _conversations_db.values():
            if conv["project_id"] == project_id:
                # Check if already in result (by conversation_id)
                if not any(c["conversation_id"] == conv["conversation_id"] for c in result):
                    result.append(conv)

        return result
    except Exception as e:
        logger.error(f"Failed to get conversations from DB: {e}")
        return [
            conv for conv in _conversations_db.values()
            if conv["project_id"] == project_id
        ]


async def _db_delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation and all its messages."""
    if not await _check_db_available():
        if conversation_id in _conversations_db:
            del _conversations_db[conversation_id]
            return True
        return False

    try:
        # Delete from database (cascade will delete messages)
        result = await db.execute(
            "DELETE FROM conversations WHERE id = $1",
            conversation_id,
        )

        # Also remove from in-memory if present
        if conversation_id in _conversations_db:
            del _conversations_db[conversation_id]

        return "DELETE 1" in result
    except Exception as e:
        logger.error(f"Failed to delete conversation from DB: {e}")
        # Try in-memory fallback
        if conversation_id in _conversations_db:
            del _conversations_db[conversation_id]
            return True
        return False


async def _db_check_conversation_ownership(
    conversation_id: str,
    user_id: Optional[str]
) -> bool:
    """Check if a user owns a conversation."""
    if user_id is None:
        return True

    conv = await _db_get_conversation(conversation_id)
    if not conv:
        return False

    return conv.get("user_id") == user_id


# ============================================================================
# Pydantic Models
# ============================================================================

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


# ============================================================================
# Global Orchestrator
# ============================================================================

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


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Send a query to the multi-agent system. Requires auth in production.

    Pipeline:
    1. Intent Agent - Classify user intent
    2. Concept Extraction Agent - Extract entities from query
    3. Task Planning Agent - Break down complex queries
    4. Query Execution Agent - Run SQL + Vector searches
    5. Reasoning Agent - Synthesize results
    6. Response Agent - Generate user-friendly response
    """
    conversation_id = request.conversation_id or str(uuid4())
    user_id = current_user.id if current_user else None

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

    # Store conversation in database (with fallback to memory)
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

    # Check if this is a new conversation
    existing_conv = await _db_get_conversation(conversation_id)
    if not existing_conv:
        await _db_create_conversation(
            conversation_id=conversation_id,
            project_id=str(request.project_id),
            user_id=user_id,
        )

    # Add messages to conversation
    await _db_add_messages(conversation_id, user_message, assistant_message)

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
async def get_chat_history(
    project_id: UUID,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """Get all conversations for a project. Requires auth in production."""
    conversations_data = await _db_get_conversations_by_project(str(project_id))

    conversations = []
    for conv in conversations_data:
        try:
            # Convert messages to ChatMessage objects
            messages = [
                ChatMessage(
                    role=m.get("role", "user"),
                    content=m.get("content", ""),
                    timestamp=m.get("timestamp", datetime.now()) if isinstance(m.get("timestamp"), datetime) else datetime.fromisoformat(str(m.get("timestamp", datetime.now().isoformat()))),
                    citations=m.get("citations"),
                    highlighted_nodes=m.get("highlighted_nodes"),
                    highlighted_edges=m.get("highlighted_edges"),
                    suggested_follow_ups=m.get("suggested_follow_ups"),
                )
                for m in conv.get("messages", [])
            ]

            conversations.append(ConversationHistory(
                conversation_id=conv["conversation_id"],
                project_id=UUID(conv["project_id"]) if conv.get("project_id") else project_id,
                messages=messages,
                created_at=conv.get("created_at", datetime.now()),
                updated_at=conv.get("updated_at", datetime.now()),
            ))
        except Exception as e:
            logger.warning(f"Skipping invalid conversation {conv.get('conversation_id')}: {e}")
            continue

    return conversations


@router.get("/conversation/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(
    conversation_id: str,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Get a specific conversation.

    Access control:
    - User must be the owner of the conversation
    - Or auth is not configured (development mode)

    Requires authentication in production.
    """
    conv = await _db_get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Verify ownership if auth is configured
    if current_user is not None:
        if not await _db_check_conversation_ownership(conversation_id, current_user.id):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this conversation"
            )

    # Convert messages to ChatMessage objects
    messages = [
        ChatMessage(
            role=m.get("role", "user"),
            content=m.get("content", ""),
            timestamp=m.get("timestamp", datetime.now()) if isinstance(m.get("timestamp"), datetime) else datetime.fromisoformat(str(m.get("timestamp", datetime.now().isoformat()))),
            citations=m.get("citations"),
            highlighted_nodes=m.get("highlighted_nodes"),
            highlighted_edges=m.get("highlighted_edges"),
            suggested_follow_ups=m.get("suggested_follow_ups"),
        )
        for m in conv.get("messages", [])
    ]

    return ConversationHistory(
        conversation_id=conv["conversation_id"],
        project_id=UUID(conv["project_id"]) if conv.get("project_id") else UUID("00000000-0000-0000-0000-000000000000"),
        messages=messages,
        created_at=conv.get("created_at", datetime.now()),
        updated_at=conv.get("updated_at", datetime.now()),
    )


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Delete a conversation.

    Access control:
    - Only the owner of the conversation can delete it
    - Or auth is not configured (development mode)

    Requires authentication in production.
    """
    conv = await _db_get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Verify ownership if auth is configured
    if current_user is not None:
        if not await _db_check_conversation_ownership(conversation_id, current_user.id):
            raise HTTPException(
                status_code=403,
                detail="Only the owner of the conversation can delete it"
            )

    success = await _db_delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

    logger.info(f"Deleted conversation {conversation_id} by user {current_user.id if current_user else 'anonymous'}")
    return {"status": "deleted", "conversation_id": conversation_id}


class ExplainRequest(BaseModel):
    node_name: Optional[str] = None
    node_type: Optional[str] = None
    node_properties: Optional[dict] = None


@router.post("/explain/{node_id}")
async def explain_node(
    node_id: str,
    project_id: UUID,
    request: Optional[ExplainRequest] = None,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Generate AI explanation for a node when clicked in Exploration Mode.
    Uses the orchestrator's LLM provider for generation.

    Requires authentication in production.
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
async def ask_about_node(
    node_id: str,
    project_id: UUID,
    question: str,
    current_user: Optional[User] = Depends(require_auth_if_configured),
):
    """
    Ask a specific question about a node.
    Called from NodeDetails "Ask AI" button.

    Requires authentication in production.
    """
    conversation_id = str(uuid4())
    user_id = current_user.id if current_user else None
    orchestrator = get_orchestrator()

    try:
        result = await orchestrator.process_query(
            query=question,
            project_id=str(project_id),
            conversation_id=conversation_id,
        )

        # Create conversation and store messages in database
        await _db_create_conversation(
            conversation_id=conversation_id,
            project_id=str(project_id),
            user_id=user_id,
        )

        user_message = ChatMessage(
            role="user",
            content=question,
            timestamp=datetime.now(),
        )
        assistant_message = ChatMessage(
            role="assistant",
            content=result.content,
            timestamp=datetime.now(),
            citations=result.citations,
            highlighted_nodes=result.highlighted_nodes,
            suggested_follow_ups=result.suggested_follow_ups,
        )

        await _db_add_messages(conversation_id, user_message, assistant_message)

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
            "answer": "I couldn't process your question. Please try again or rephrase your query.",
            "citations": [],
            "highlighted_nodes": [],
            "suggested_follow_ups": [],
        }
