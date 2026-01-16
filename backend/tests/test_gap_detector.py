"""
Tests for Gap Detector module.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch


class TestGapDetector:
    """Test gap detection functionality."""

    @pytest.fixture
    def sample_concepts(self):
        """Sample concept data for testing."""
        return [
            {"id": "1", "name": "machine learning", "embedding": [0.1, 0.2, 0.3]},
            {"id": "2", "name": "deep learning", "embedding": [0.15, 0.25, 0.35]},
            {"id": "3", "name": "education", "embedding": [0.8, 0.7, 0.6]},
            {"id": "4", "name": "pedagogy", "embedding": [0.85, 0.75, 0.65]},
            {"id": "5", "name": "assessment", "embedding": [0.82, 0.72, 0.62]},
        ]

    @pytest.fixture
    def sample_relationships(self):
        """Sample relationship data for testing."""
        return [
            {"source_id": "1", "target_id": "2"},
            {"source_id": "3", "target_id": "4"},
            {"source_id": "4", "target_id": "5"},
        ]

    @pytest.fixture
    def gap_detector(self):
        """Create gap detector instance."""
        from graph.gap_detector import GapDetector
        return GapDetector()

    def test_detector_initialization(self, gap_detector):
        """Test gap detector initializes correctly."""
        assert gap_detector is not None

    def test_cluster_concepts(self, gap_detector, sample_concepts):
        """Test concept clustering."""
        clusters = gap_detector.cluster_concepts(sample_concepts, n_clusters=2)

        # Returns list of ConceptCluster objects, not dicts
        assert isinstance(clusters, list)
        assert len(clusters) == 2

        # Each cluster should have required attributes (using object attributes, not dict keys)
        for cluster in clusters:
            assert hasattr(cluster, 'id')
            assert hasattr(cluster, 'concept_ids')
            assert hasattr(cluster, 'color')

    def test_cluster_with_few_concepts(self, gap_detector):
        """Test clustering with fewer concepts than clusters."""
        concepts = [
            {"id": "1", "name": "test", "embedding": [0.1, 0.2, 0.3]},
        ]

        clusters = gap_detector.cluster_concepts(concepts, n_clusters=2)

        # Should handle gracefully - returns empty list for too few concepts
        assert isinstance(clusters, list)
        assert len(clusters) == 0  # Too few concepts

    def test_detect_gaps(self, gap_detector, sample_concepts, sample_relationships):
        """Test gap detection between clusters."""
        # First cluster concepts
        clusters = gap_detector.cluster_concepts(sample_concepts, n_clusters=2)

        # detect_gaps takes 3 arguments: clusters, relationships, concepts
        gaps = gap_detector.detect_gaps(clusters, sample_relationships, sample_concepts)

        assert isinstance(gaps, list)

        # Each gap should be a StructuralGap object with required attributes
        for gap in gaps:
            assert hasattr(gap, 'cluster_a_id')
            assert hasattr(gap, 'cluster_b_id')
            assert hasattr(gap, 'gap_strength')
            assert 0 <= gap.gap_strength <= 1

    def test_calculate_centrality(self, gap_detector, sample_concepts, sample_relationships):
        """Test centrality calculation."""
        # Returns list of CentralityMetrics objects, not dict
        centrality = gap_detector.calculate_centrality(sample_concepts, sample_relationships)

        assert isinstance(centrality, list)

        # Each item should be a CentralityMetrics object
        for metrics in centrality:
            assert hasattr(metrics, 'entity_id')
            assert hasattr(metrics, 'degree')
            assert hasattr(metrics, 'betweenness')
            assert metrics.degree >= 0

    def test_find_bridge_candidates(self, gap_detector, sample_concepts, sample_relationships):
        """Test finding bridge concept candidates."""
        from graph.gap_detector import StructuralGap

        # First cluster and calculate centrality
        clusters = gap_detector.cluster_concepts(sample_concepts, n_clusters=2)
        centrality = gap_detector.calculate_centrality(sample_concepts, sample_relationships)

        # Detect gaps
        gaps = gap_detector.detect_gaps(clusters, sample_relationships, sample_concepts)

        # find_bridge_candidates takes (gap, concepts, centrality_metrics)
        if gaps:
            bridges = gap_detector.find_bridge_candidates(gaps[0], sample_concepts, centrality)

            assert isinstance(bridges, list)
            # Each bridge is a concept ID string
            for bridge in bridges:
                assert isinstance(bridge, str)

    def test_optimal_cluster_determination(self, gap_detector, sample_concepts):
        """Test automatic cluster number determination."""
        embeddings = np.array([c["embedding"] for c in sample_concepts])

        optimal_k = gap_detector._determine_optimal_clusters(embeddings)

        assert isinstance(optimal_k, int)
        assert 2 <= optimal_k <= len(sample_concepts)


class TestStructuralGap:
    """Test StructuralGap dataclass."""

    def test_structural_gap_creation(self):
        """Test creating a StructuralGap."""
        from graph.gap_detector import StructuralGap

        gap = StructuralGap(
            cluster_a_id=0,
            cluster_b_id=1,
            gap_strength=0.8,
            concept_a_ids=["1", "2"],
            concept_b_ids=["3", "4"],
            bridge_concepts=["5"],
            suggested_research_questions=["How can A connect to B?"],
            status="detected"
        )

        assert gap.cluster_a_id == 0
        assert gap.gap_strength == 0.8
        assert gap.status == "detected"
        # id is auto-generated
        assert gap.id is not None


class TestConceptCluster:
    """Test ConceptCluster dataclass."""

    def test_concept_cluster_creation(self):
        """Test creating a ConceptCluster."""
        from graph.gap_detector import ConceptCluster

        cluster = ConceptCluster(
            id=0,
            name="AI Cluster",
            color="#FF5733",
            concept_ids=["1", "2", "3"],
            centroid=np.array([0.1, 0.2, 0.3]),
            keywords=["machine learning", "AI"],
            avg_centrality=0.5
        )

        assert cluster.id == 0
        assert cluster.name == "AI Cluster"
        assert len(cluster.concept_ids) == 3


class TestCentralityMetrics:
    """Test CentralityMetrics dataclass."""

    def test_centrality_metrics_creation(self):
        """Test creating CentralityMetrics."""
        from graph.gap_detector import CentralityMetrics

        metrics = CentralityMetrics(
            entity_id="concept-1",
            degree=0.8,
            betweenness=0.5,
            pagerank=0.6,
            cluster_id=0
        )

        assert metrics.entity_id == "concept-1"
        assert metrics.degree == 0.8
        assert metrics.betweenness == 0.5


class TestResearchQuestionGeneration:
    """Test research question generation."""

    @pytest.fixture
    def gap_detector_with_llm(self):
        """Create gap detector with mocked LLM."""
        from graph.gap_detector import GapDetector

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="How can machine learning improve education?\nWhat is the role of AI in pedagogy?")

        detector = GapDetector(llm_provider=mock_llm)
        return detector

    @pytest.mark.asyncio
    async def test_generate_research_questions(self, gap_detector_with_llm):
        """Test generating research questions for a gap."""
        from graph.gap_detector import StructuralGap

        # Create a StructuralGap object
        gap = StructuralGap(
            cluster_a_id=0,
            cluster_b_id=1,
            gap_strength=0.1,
            concept_a_ids=["1", "2"],
            concept_b_ids=["3", "4"],
        )

        # generate_research_questions takes (gap, cluster_a_concepts, cluster_b_concepts)
        questions = await gap_detector_with_llm.generate_research_questions(
            gap,
            ["machine learning", "neural networks"],  # Concept names from cluster A
            ["pedagogy", "assessment"],  # Concept names from cluster B
        )

        assert isinstance(questions, list)

    @pytest.mark.asyncio
    async def test_generate_research_questions_without_llm(self):
        """Test generating research questions without LLM (fallback)."""
        from graph.gap_detector import GapDetector, StructuralGap

        # Create gap detector without LLM
        detector = GapDetector(llm_provider=None)

        gap = StructuralGap(
            cluster_a_id=0,
            cluster_b_id=1,
            gap_strength=0.1,
        )

        questions = await detector.generate_research_questions(
            gap,
            ["machine learning"],
            ["education"],
        )

        # Should return template questions
        assert isinstance(questions, list)
        assert len(questions) > 0


class TestClusterColors:
    """Test cluster color assignment."""

    def test_cluster_colors_distinct(self):
        """Test that cluster colors are visually distinct."""
        from graph.gap_detector import CLUSTER_COLORS

        assert len(CLUSTER_COLORS) >= 8  # Should have enough colors

        # All colors should be unique
        assert len(set(CLUSTER_COLORS)) == len(CLUSTER_COLORS)

    def test_color_assignment(self):
        """Test color assignment to clusters."""
        from graph.gap_detector import GapDetector

        detector = GapDetector()

        # Create clusters and check color assignment
        concepts = [
            {"id": str(i), "name": f"concept{i}", "embedding": [i * 0.1, i * 0.2, i * 0.3]}
            for i in range(10)
        ]

        clusters = detector.cluster_concepts(concepts, n_clusters=3)

        # Access color through object attribute, not dict key
        colors = [c.color for c in clusters]
        assert len(set(colors)) == 3  # Each cluster has unique color


class TestFullGraphAnalysis:
    """Test full graph analysis workflow."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for full analysis."""
        concepts = [
            {"id": str(i), "name": f"concept{i}", "embedding": [np.sin(i), np.cos(i), i * 0.1]}
            for i in range(15)
        ]

        relationships = [
            {"source_id": str(i), "target_id": str(i + 1)}
            for i in range(10)
        ]

        return concepts, relationships

    @pytest.mark.asyncio
    async def test_analyze_graph(self, sample_data):
        """Test full graph analysis."""
        from graph.gap_detector import GapDetector

        concepts, relationships = sample_data
        detector = GapDetector()

        result = await detector.analyze_graph(concepts, relationships)

        assert "clusters" in result
        assert "gaps" in result
        assert "centrality" in result
        assert "summary" in result

        assert isinstance(result["clusters"], list)
        assert isinstance(result["gaps"], list)
        assert isinstance(result["summary"], str)
