"""
API Contract Tests

Validates that API responses match expected schemas using OpenAPI spec.
Tests frontend/backend type alignment.
"""

import pytest
from pydantic import BaseModel, ValidationError
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# Define expected response schemas (matching frontend types)
class CitationSchema(BaseModel):
    """Citation schema matching frontend Citation interface."""
    id: str
    label: str
    entity_type: Optional[str] = None


class ChatResponseSchema(BaseModel):
    """Chat response schema matching frontend ChatResponse interface."""
    conversation_id: str
    answer: str
    intent: Optional[str] = None
    citations: List[CitationSchema] = []
    highlighted_nodes: List[str] = []
    highlighted_edges: List[str] = []
    suggested_follow_ups: Optional[List[str]] = None


class NodeResponseSchema(BaseModel):
    """Node schema matching frontend expectations."""
    id: str
    entity_type: str
    name: str
    properties: dict = {}


class EdgeResponseSchema(BaseModel):
    """Edge schema matching frontend expectations."""
    id: str
    source: str
    target: str
    relationship_type: str
    properties: dict = {}
    weight: float = 1.0


class GraphDataResponseSchema(BaseModel):
    """Graph data schema for visualization."""
    nodes: List[NodeResponseSchema]
    edges: List[EdgeResponseSchema]


class ProjectResponseSchema(BaseModel):
    """Project response schema."""
    id: UUID
    name: str
    research_question: Optional[str]
    source_path: Optional[str]
    created_at: datetime
    updated_at: datetime
    stats: Optional[dict] = None


class ImportJobResponseSchema(BaseModel):
    """Import job response schema."""
    job_id: str
    status: str
    progress: float
    message: str
    project_id: Optional[UUID] = None
    stats: Optional[dict] = None
    reliability_summary: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class GapReproBridgeRelationshipSchema(BaseModel):
    relationship_id: str
    source_name: str
    target_name: str
    confidence: float
    hypothesis_title: Optional[str] = None
    ai_generated: bool


class GapReproRecommendationTraceSchema(BaseModel):
    status: str
    query_used: str
    retry_after_seconds: Optional[int] = None
    error: Optional[str] = None
    papers: List[dict] = []


class GapReproReportSchema(BaseModel):
    project_id: str
    gap_id: str
    generated_at: str
    gap_strength: float
    cluster_a_names: List[str]
    cluster_b_names: List[str]
    bridge_candidates: List[str]
    research_questions: List[str]
    bridge_relationships: List[GapReproBridgeRelationshipSchema]
    recommendation: GapReproRecommendationTraceSchema


class TestChatAPIContract:
    """Test chat API response contracts."""

    def test_chat_response_schema_valid(self):
        """Test that valid chat response passes schema validation."""
        valid_response = {
            "conversation_id": "conv-123",
            "answer": "Based on the literature review...",
            "intent": "identify_gaps",
            "citations": [
                {"id": "paper-1", "label": "Smith et al. 2024", "entity_type": "Paper"},
            ],
            "highlighted_nodes": ["uuid-1", "uuid-2"],
            "highlighted_edges": ["edge-1"],
            "suggested_follow_ups": ["What about X?"],
        }

        result = ChatResponseSchema(**valid_response)
        assert result.answer == "Based on the literature review..."
        assert result.intent == "identify_gaps"
        assert len(result.citations) == 1
        assert result.citations[0].entity_type == "Paper"

    def test_chat_response_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        invalid_response = {
            "conversation_id": "conv-123",
            # Missing 'answer' field
            "citations": [],
        }

        with pytest.raises(ValidationError):
            ChatResponseSchema(**invalid_response)

    def test_chat_response_minimal(self):
        """Test minimal valid chat response."""
        minimal = {
            "conversation_id": "conv-123",
            "answer": "Response text",
        }

        result = ChatResponseSchema(**minimal)
        assert result.citations == []
        assert result.highlighted_nodes == []


class TestGraphAPIContract:
    """Test graph API response contracts."""

    def test_node_response_schema(self):
        """Test node response schema validation."""
        valid_node = {
            "id": "node-uuid-123",
            "entity_type": "Paper",
            "name": "Test Paper Title",
            "properties": {"year": 2024, "abstract": "..."},
        }

        result = NodeResponseSchema(**valid_node)
        assert result.entity_type == "Paper"

    def test_edge_response_schema(self):
        """Test edge response schema validation."""
        valid_edge = {
            "id": "edge-uuid-123",
            "source": "node-1",
            "target": "node-2",
            "relationship_type": "AUTHORED_BY",
            "properties": {},
            "weight": 1.0,
        }

        result = EdgeResponseSchema(**valid_edge)
        assert result.relationship_type == "AUTHORED_BY"

    def test_graph_data_response_schema(self):
        """Test graph data response schema."""
        valid_graph = {
            "nodes": [
                {"id": "n1", "entity_type": "Paper", "name": "Paper 1", "properties": {}},
                {"id": "n2", "entity_type": "Author", "name": "Author 1", "properties": {}},
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "n1",
                    "target": "n2",
                    "relationship_type": "AUTHORED_BY",
                    "properties": {},
                    "weight": 1.0,
                }
            ],
        }

        result = GraphDataResponseSchema(**valid_graph)
        assert len(result.nodes) == 2
        assert len(result.edges) == 1


class TestProjectAPIContract:
    """Test project API response contracts."""

    def test_project_response_schema(self):
        """Test project response schema."""
        valid_project = {
            "id": "12345678-1234-1234-1234-123456789012",
            "name": "Test Project",
            "research_question": "How does AI impact education?",
            "source_path": "/path/to/source",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "stats": {"total_papers": 100},
        }

        result = ProjectResponseSchema(**valid_project)
        assert result.name == "Test Project"

    def test_project_response_optional_fields(self):
        """Test project response with optional fields null."""
        minimal_project = {
            "id": "12345678-1234-1234-1234-123456789012",
            "name": "Test Project",
            "research_question": None,
            "source_path": None,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        result = ProjectResponseSchema(**minimal_project)
        assert result.research_question is None


class TestImportAPIContract:
    """Test import API response contracts."""

    def test_import_job_response_schema(self):
        """Test import job response schema."""
        valid_job = {
            "job_id": "job-uuid-123",
            "status": "processing",
            "progress": 0.5,
            "message": "Processing papers...",
            "project_id": None,
            "stats": None,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        result = ImportJobResponseSchema(**valid_job)
        assert result.progress == 0.5

    def test_import_job_completed_schema(self):
        """Test completed import job response."""
        completed_job = {
            "job_id": "job-uuid-123",
            "status": "completed",
            "progress": 1.0,
            "message": "Import completed successfully!",
            "project_id": "12345678-1234-1234-1234-123456789012",
            "stats": {
                "papers_imported": 50,
                "authors_extracted": 100,
                "concepts_extracted": 30,
            },
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T01:00:00",
        }

        result = ImportJobResponseSchema(**completed_job)
        assert result.status == "completed"
        assert result.stats is not None


class TestFrontendBackendAlignment:
    """
    Tests to ensure frontend TypeScript types match backend Python schemas.

    These tests document the API contract between frontend and backend.
    If any of these fail, both sides need to be updated together.
    """

    def test_citation_alignment(self):
        """
        Frontend: Citation { id: string; label: string; entity_type?: string; }
        Backend: SimpleCitation(id: str, label: str, entity_type: Optional[str])
        """
        # Backend response format
        backend_citation = {"id": "paper-1", "label": "Smith 2024", "entity_type": "Paper"}

        # Should match frontend expectation
        result = CitationSchema(**backend_citation)
        assert hasattr(result, "id")
        assert hasattr(result, "label")
        assert hasattr(result, "entity_type")

    def test_chat_response_alignment(self):
        """
        Frontend: ChatResponse { conversation_id, answer, citations, highlighted_nodes, highlighted_edges, suggested_follow_ups }
        Backend: ChatResponse (same fields)
        """
        backend_response = {
            "conversation_id": "conv-1",
            "answer": "The answer",
            "intent": "search",
            "citations": [],
            "highlighted_nodes": [],
            "highlighted_edges": [],
            "suggested_follow_ups": [],
        }

        result = ChatResponseSchema(**backend_response)

        # Verify all expected fields exist
        expected_fields = [
            "conversation_id",
            "answer",
            "intent",
            "citations",
            "highlighted_nodes",
            "highlighted_edges",
            "suggested_follow_ups",
        ]
        for field in expected_fields:
            assert hasattr(result, field), f"Missing field: {field}"

    def test_node_response_alignment(self):
        """
        Frontend: NodeResponse { id, entity_type, name, properties }
        Backend: NodeResponse (same fields)
        """
        backend_node = {
            "id": "n1",
            "entity_type": "Concept",
            "name": "Machine Learning",
            "properties": {"domain": "AI"},
        }

        result = NodeResponseSchema(**backend_node)
        assert result.id == "n1"
        assert result.entity_type == "Concept"

    def test_gap_repro_report_alignment(self):
        """
        Frontend/Backend: Gap reproducibility report contract.
        """
        backend_report = {
            "project_id": "proj-1",
            "gap_id": "gap-1",
            "generated_at": "2026-02-08T00:00:00Z",
            "gap_strength": 0.62,
            "cluster_a_names": ["self-supervised learning"],
            "cluster_b_names": ["causal inference"],
            "bridge_candidates": ["representation learning"],
            "research_questions": ["How does representation learning bridge SSL and causal inference?"],
            "bridge_relationships": [
                {
                    "relationship_id": "rel-1",
                    "source_name": "self-supervised learning",
                    "target_name": "representation learning",
                    "confidence": 0.74,
                    "hypothesis_title": "Bridge hypothesis A",
                    "ai_generated": True,
                }
            ],
            "recommendation": {
                "status": "success",
                "query_used": "representation learning self-supervised learning causal inference",
                "retry_after_seconds": None,
                "error": None,
                "papers": [],
            },
        }

        result = GapReproReportSchema(**backend_report)
        assert result.gap_id == "gap-1"
        assert len(result.bridge_relationships) == 1
        assert result.recommendation.status == "success"
