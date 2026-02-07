"""Tests for v0.14.0 gap_detector — empty keyword filtering in cluster labels."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from graph.gap_detector import GapDetector


@pytest.fixture
def detector():
    """Create GapDetector without LLM for testing fallback behavior."""
    return GapDetector(llm_provider=None)


@pytest.mark.asyncio
async def test_label_filters_empty_keywords(detector):
    """Should filter out empty strings from keywords."""
    result = await detector._generate_cluster_label(["AI", "", "learning"])
    assert result == "AI / learning"


@pytest.mark.asyncio
async def test_label_filters_whitespace_keywords(detector):
    """Should filter out whitespace-only strings (within first 3)."""
    # Takes first 3: ["AI", "  ", "\t"], filters to ["AI"]
    result = await detector._generate_cluster_label(["AI", "  ", "\t", "NLP"])
    assert result == "AI"


@pytest.mark.asyncio
async def test_label_all_empty_keywords(detector):
    """Should return fallback when all keywords are empty."""
    result = await detector._generate_cluster_label(["", "", ""])
    assert "Cluster" in result or "concepts" in result


@pytest.mark.asyncio
async def test_label_normal_keywords(detector):
    """Should join normal keywords with separator."""
    result = await detector._generate_cluster_label(["machine learning", "NLP", "deep learning"])
    assert result == "machine learning / NLP / deep learning"


@pytest.mark.asyncio
async def test_label_empty_list(detector):
    """Should handle empty keyword list."""
    result = await detector._generate_cluster_label([])
    # No LLM and no keywords → empty filtered list → fallback
    assert "Cluster" in result or "concepts" in result or result == ""


@pytest.mark.asyncio
async def test_label_single_keyword(detector):
    """Should handle single keyword."""
    result = await detector._generate_cluster_label(["AI"])
    assert result == "AI"


@pytest.mark.asyncio
async def test_label_limits_to_three(detector):
    """Should only use first 3 keywords."""
    result = await detector._generate_cluster_label(["a", "b", "c", "d", "e"])
    assert result == "a / b / c"


@pytest.mark.asyncio
async def test_label_filters_empty_then_limits(detector):
    """Should limit to 3 first, then filter empty strings."""
    # Takes first 3: ["a", "", "b"], filters to ["a", "b"]
    result = await detector._generate_cluster_label(["a", "", "b", "", "c", "d", "e"])
    assert result == "a / b"


@pytest.mark.asyncio
async def test_label_mixed_whitespace_and_valid(detector):
    """Should handle mix of whitespace and valid keywords (within first 3)."""
    # Takes first 3: [" ", "AI", "\n\t"], filters to ["AI"]
    result = await detector._generate_cluster_label([" ", "AI", "\n\t", "ML", ""])
    assert result == "AI"
