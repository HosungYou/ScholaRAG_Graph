"""
Centrality Analyzer

NetworkX-based centrality analysis for knowledge graphs.
Provides methods for computing various centrality metrics and graph slicing.
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import networkx as nx
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)


@dataclass
class CentralityMetrics:
    """Container for all centrality metrics."""
    betweenness: Dict[str, float]
    degree: Dict[str, float]
    eigenvector: Dict[str, float]
    pagerank: Dict[str, float]


@dataclass
class ClusterResult:
    """Container for clustering results."""
    cluster_id: int
    node_ids: List[str]
    node_names: List[str]
    centroid: Optional[List[float]]
    size: int
    label: Optional[str] = None


class CentralityAnalyzer:
    """
    Analyzer for computing centrality metrics and performing graph operations.

    Supports:
    - Betweenness centrality (bridge nodes)
    - Degree centrality (hub nodes)
    - Eigenvector centrality (influential nodes)
    - PageRank (importance)
    - Node slicing (removing top-N nodes)
    - K-means clustering
    """

    def __init__(self):
        self._cache: Dict[str, CentralityMetrics] = {}

    def build_graph(
        self,
        nodes: List[dict],
        edges: List[dict]
    ) -> nx.Graph:
        """
        Build a NetworkX graph from nodes and edges.

        Args:
            nodes: List of node dictionaries with 'id' and optional 'properties'
            edges: List of edge dictionaries with 'source', 'target', and optional 'weight'

        Returns:
            NetworkX Graph
        """
        G = nx.Graph()

        for node in nodes:
            node_id = node.get('id')
            properties = node.get('properties', {})
            name = node.get('name', node_id)
            entity_type = node.get('entity_type', 'Unknown')
            G.add_node(
                node_id,
                name=name,
                entity_type=entity_type,
                **properties
            )

        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')
            weight = edge.get('weight', 1.0)
            if source and target and G.has_node(source) and G.has_node(target):
                G.add_edge(source, target, weight=float(weight))

        return G

    def compute_all_centrality(
        self,
        nodes: List[dict],
        edges: List[dict],
        cache_key: Optional[str] = None
    ) -> CentralityMetrics:
        """
        Compute all centrality metrics for the graph.

        Args:
            nodes: List of node dictionaries
            edges: List of edge dictionaries
            cache_key: Optional key for caching results

        Returns:
            CentralityMetrics with all computed metrics
        """
        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]

        G = self.build_graph(nodes, edges)

        if G.number_of_nodes() == 0:
            empty_result = CentralityMetrics(
                betweenness={},
                degree={},
                eigenvector={},
                pagerank={}
            )
            return empty_result

        # Compute betweenness centrality
        try:
            betweenness = nx.betweenness_centrality(G, weight='weight')
        except Exception as e:
            logger.warning(f"Failed to compute betweenness centrality: {e}")
            betweenness = {n: 0.0 for n in G.nodes()}

        # Compute degree centrality
        try:
            degree = dict(G.degree())
            max_degree = max(degree.values()) if degree else 1
            degree = {k: v / max_degree for k, v in degree.items()}
        except Exception as e:
            logger.warning(f"Failed to compute degree centrality: {e}")
            degree = {n: 0.0 for n in G.nodes()}

        # Compute eigenvector centrality
        try:
            eigenvector = nx.eigenvector_centrality(
                G,
                max_iter=100,
                weight='weight'
            )
        except Exception as e:
            logger.warning(f"Failed to compute eigenvector centrality: {e}")
            eigenvector = {n: 0.0 for n in G.nodes()}

        # Compute PageRank
        try:
            pagerank = nx.pagerank(G, weight='weight')
        except Exception as e:
            logger.warning(f"Failed to compute PageRank: {e}")
            pagerank = {n: 0.0 for n in G.nodes()}

        metrics = CentralityMetrics(
            betweenness=betweenness,
            degree=degree,
            eigenvector=eigenvector,
            pagerank=pagerank
        )

        if cache_key:
            self._cache[cache_key] = metrics

        return metrics

    def get_top_bridges(
        self,
        centrality: Dict[str, float],
        top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Get the top N nodes by centrality score.

        Args:
            centrality: Dictionary mapping node IDs to scores
            top_n: Number of top nodes to return

        Returns:
            List of (node_id, score) tuples sorted by score descending
        """
        sorted_nodes = sorted(
            centrality.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_nodes[:top_n]

    def slice_graph(
        self,
        nodes: List[dict],
        edges: List[dict],
        remove_top_n: int,
        metric: str = 'betweenness'
    ) -> Tuple[List[dict], List[dict], List[str], List[Tuple[str, float]]]:
        """
        Remove the top N nodes by centrality metric.

        This reveals hidden cluster structures by removing bridge nodes.

        Args:
            nodes: Original list of node dictionaries
            edges: Original list of edge dictionaries
            remove_top_n: Number of top nodes to remove
            metric: Centrality metric to use ('betweenness', 'degree', 'eigenvector')

        Returns:
            Tuple of (filtered_nodes, filtered_edges, removed_ids, top_bridges)
        """
        metrics = self.compute_all_centrality(nodes, edges)

        if metric == 'betweenness':
            centrality = metrics.betweenness
        elif metric == 'degree':
            centrality = metrics.degree
        elif metric == 'eigenvector':
            centrality = metrics.eigenvector
        else:
            centrality = metrics.betweenness

        top_bridges = self.get_top_bridges(centrality, remove_top_n)
        top_ids = {node_id for node_id, _ in top_bridges}

        # Filter out top nodes
        filtered_nodes = [n for n in nodes if n.get('id') not in top_ids]

        # Filter edges that connect to removed nodes
        filtered_edges = [
            e for e in edges
            if e.get('source') not in top_ids and e.get('target') not in top_ids
        ]

        return filtered_nodes, filtered_edges, list(top_ids), top_bridges

    def compute_optimal_k(
        self,
        embeddings: np.ndarray,
        min_k: int = 2,
        max_k: int = 10
    ) -> int:
        """
        Find the optimal number of clusters using silhouette score.

        Args:
            embeddings: Node embeddings as numpy array
            min_k: Minimum number of clusters to try
            max_k: Maximum number of clusters to try

        Returns:
            Optimal number of clusters
        """
        if len(embeddings) < min_k:
            return min_k

        max_k = min(max_k, len(embeddings) - 1)

        best_k = min_k
        best_score = -1

        for k in range(min_k, max_k + 1):
            try:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = kmeans.fit_predict(embeddings)
                score = silhouette_score(embeddings, labels)

                if score > best_score:
                    best_score = score
                    best_k = k
            except Exception as e:
                logger.warning(f"Failed to compute silhouette for k={k}: {e}")
                continue

        return best_k

    def cluster_nodes(
        self,
        nodes: List[dict],
        embeddings: Optional[np.ndarray] = None,
        n_clusters: int = 5
    ) -> List[ClusterResult]:
        """
        Cluster nodes using K-means.

        Args:
            nodes: List of node dictionaries
            embeddings: Optional pre-computed embeddings
            n_clusters: Number of clusters

        Returns:
            List of ClusterResult objects
        """
        if embeddings is None:
            # If no embeddings, use graph-based features
            G = nx.Graph()
            for node in nodes:
                G.add_node(node.get('id'))

            # Use spectral embedding as fallback
            if G.number_of_nodes() < n_clusters:
                return []

            try:
                embeddings = nx.spectral_layout(G)
                embeddings = np.array([embeddings[n] for n in G.nodes()])
            except Exception:
                return []

        if len(embeddings) < n_clusters:
            n_clusters = max(2, len(embeddings) // 2)

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)

        # Group nodes by cluster
        clusters_dict: Dict[int, List[dict]] = {}
        for node, label in zip(nodes, labels):
            if label not in clusters_dict:
                clusters_dict[label] = []
            clusters_dict[label].append(node)

        results = []
        for cluster_id, cluster_nodes in clusters_dict.items():
            results.append(ClusterResult(
                cluster_id=int(cluster_id),
                node_ids=[n.get('id') for n in cluster_nodes],
                node_names=[n.get('name', n.get('id')) for n in cluster_nodes],
                centroid=kmeans.cluster_centers_[cluster_id].tolist() if hasattr(kmeans, 'cluster_centers_') else None,
                size=len(cluster_nodes),
                label=None  # Can be set later using LLM
            ))

        return results

    def get_node_name(
        self,
        node_id: str,
        nodes: List[dict]
    ) -> str:
        """Get node name by ID."""
        for node in nodes:
            if node.get('id') == node_id:
                return node.get('name', node_id)
        return node_id

    def clear_cache(self, cache_key: Optional[str] = None):
        """Clear the centrality cache."""
        if cache_key:
            self._cache.pop(cache_key, None)
        else:
            self._cache.clear()


# Singleton instance
centrality_analyzer = CentralityAnalyzer()
