"""
Diversity Analyzer - Knowledge Graph Diversity & Bias Detection

Analyzes the diversity and potential bias in a knowledge graph by:
1. Measuring cluster size distribution (Shannon Entropy)
2. Calculating modularity (cluster separation quality)
3. Detecting bias indicators (cluster dominance)

Reference: InfraNodus diversity metrics
"""

import logging
import math
from dataclasses import dataclass
from typing import Optional

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DiversityMetrics:
    """Diversity metrics for a knowledge graph."""

    shannon_entropy: float
    normalized_entropy: float  # 0-1 scale
    modularity: float
    bias_score: float  # 0-1, higher = more biased (one cluster dominates)
    diversity_rating: str  # "high", "medium", "low"
    cluster_sizes: list[int]
    dominant_cluster_ratio: float
    gini_coefficient: float  # Inequality measure


class DiversityAnalyzer:
    """
    Analyzes diversity in knowledge graphs.

    Metrics:
    1. Shannon Entropy: Measures evenness of cluster size distribution
       - Higher entropy = more evenly distributed = more diverse
       - H = -sum(p * log(p)) where p = cluster_size / total

    2. Modularity: Measures how well-defined clusters are
       - Range: -0.5 to 1.0, higher = better separated clusters
       - Using NetworkX's modularity function

    3. Bias Score: Indicates if one cluster dominates
       - bias = max_cluster_size / total_nodes
       - > 0.5 indicates significant bias

    4. Gini Coefficient: Measures inequality in cluster sizes
       - 0 = perfect equality, 1 = complete inequality
    """

    def compute_metrics(
        self,
        graph: nx.Graph,
        clusters: list[list[str]],
    ) -> DiversityMetrics:
        """
        Compute diversity metrics for a graph with clusters.

        Args:
            graph: NetworkX graph
            clusters: List of clusters, each containing node IDs

        Returns:
            DiversityMetrics with all computed values
        """
        if not clusters or len(clusters) == 0:
            return DiversityMetrics(
                shannon_entropy=0.0,
                normalized_entropy=0.0,
                modularity=0.0,
                bias_score=1.0,
                diversity_rating="low",
                cluster_sizes=[],
                dominant_cluster_ratio=1.0,
                gini_coefficient=1.0,
            )

        # Get cluster sizes
        cluster_sizes = [len(c) for c in clusters]
        total_nodes = sum(cluster_sizes)

        if total_nodes == 0:
            return DiversityMetrics(
                shannon_entropy=0.0,
                normalized_entropy=0.0,
                modularity=0.0,
                bias_score=1.0,
                diversity_rating="low",
                cluster_sizes=cluster_sizes,
                dominant_cluster_ratio=1.0,
                gini_coefficient=1.0,
            )

        # Calculate Shannon Entropy
        probabilities = [s / total_nodes for s in cluster_sizes if s > 0]
        shannon_entropy = -sum(p * math.log(p) for p in probabilities if p > 0)

        # Normalize entropy (0-1 scale)
        max_entropy = math.log(len(clusters)) if len(clusters) > 1 else 1.0
        normalized_entropy = shannon_entropy / max_entropy if max_entropy > 0 else 0.0

        # Calculate modularity
        modularity = self._compute_modularity(graph, clusters)

        # Calculate bias score (dominant cluster ratio)
        max_size = max(cluster_sizes)
        bias_score = max_size / total_nodes
        dominant_cluster_ratio = bias_score

        # Calculate Gini coefficient
        gini_coefficient = self._compute_gini(cluster_sizes)

        # Determine diversity rating
        diversity_rating = self._compute_rating(
            normalized_entropy,
            bias_score,
            gini_coefficient,
        )

        return DiversityMetrics(
            shannon_entropy=round(shannon_entropy, 4),
            normalized_entropy=round(normalized_entropy, 4),
            modularity=round(modularity, 4),
            bias_score=round(bias_score, 4),
            diversity_rating=diversity_rating,
            cluster_sizes=cluster_sizes,
            dominant_cluster_ratio=round(dominant_cluster_ratio, 4),
            gini_coefficient=round(gini_coefficient, 4),
        )

    def _compute_modularity(
        self,
        graph: nx.Graph,
        clusters: list[list[str]],
    ) -> float:
        """
        Compute modularity score for the clustering.

        Uses NetworkX's modularity function.
        """
        if not graph or graph.number_of_nodes() == 0:
            return 0.0

        try:
            # Convert clusters to set format for NetworkX
            # Filter to only include nodes that exist in the graph
            graph_nodes = set(graph.nodes())
            communities = [
                set(c) & graph_nodes for c in clusters
            ]
            # Remove empty communities
            communities = [c for c in communities if len(c) > 0]

            if len(communities) < 2:
                return 0.0

            return nx.algorithms.community.modularity(graph, communities)

        except Exception as e:
            logger.warning(f"Could not compute modularity: {e}")
            return 0.0

    def _compute_gini(self, values: list[int]) -> float:
        """
        Compute Gini coefficient for a list of values.

        0 = perfect equality (all clusters same size)
        1 = complete inequality (one cluster has everything)
        """
        if not values or len(values) < 2:
            return 0.0

        values = sorted(values)
        n = len(values)
        total = sum(values)

        if total == 0:
            return 0.0

        cumulative = 0.0
        gini_sum = 0.0

        for i, v in enumerate(values):
            cumulative += v
            gini_sum += (2 * (i + 1) - n - 1) * v

        return gini_sum / (n * total)

    def _compute_rating(
        self,
        normalized_entropy: float,
        bias_score: float,
        gini_coefficient: float,
    ) -> str:
        """
        Compute overall diversity rating.

        Considers:
        - Normalized entropy (higher = better)
        - Bias score (lower = better)
        - Gini coefficient (lower = better)
        """
        # Composite score (higher = more diverse)
        diversity_score = (
            normalized_entropy * 0.4 +
            (1 - bias_score) * 0.3 +
            (1 - gini_coefficient) * 0.3
        )

        if diversity_score >= 0.7:
            return "high"
        elif diversity_score >= 0.4:
            return "medium"
        else:
            return "low"

    def analyze_from_data(
        self,
        nodes: list[dict],
        edges: list[dict],
        clusters: list[dict],
    ) -> DiversityMetrics:
        """
        Analyze diversity from node/edge/cluster data.

        Args:
            nodes: List of node dicts with 'id'
            edges: List of edge dicts with 'source', 'target'
            clusters: List of cluster dicts with 'node_ids' or 'concepts'

        Returns:
            DiversityMetrics
        """
        # Build NetworkX graph
        G = nx.Graph()

        for node in nodes:
            G.add_node(node["id"])

        for edge in edges:
            G.add_edge(edge["source"], edge["target"])

        # Extract cluster node lists
        cluster_lists = []
        for cluster in clusters:
            node_ids = cluster.get("node_ids") or cluster.get("concepts") or []
            cluster_lists.append(node_ids)

        return self.compute_metrics(G, cluster_lists)


# Singleton instance
diversity_analyzer = DiversityAnalyzer()
