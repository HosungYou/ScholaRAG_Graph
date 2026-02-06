"""
Gap Detector - InfraNodus-style Structural Gap Detection

Detects structural gaps (research opportunities) in the knowledge graph by:
1. Clustering concepts based on embeddings
2. Analyzing inter-cluster connectivity
3. Identifying bridge concepts with high betweenness centrality
4. Generating AI-suggested research questions to bridge gaps

Reference: InfraNodus content gap analysis methodology
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


@dataclass
class ConceptCluster:
    """Represents a cluster of related concepts."""

    id: int
    name: str = ""
    color: str = "#808080"
    concept_ids: list[str] = field(default_factory=list)
    centroid: Optional[np.ndarray] = None
    keywords: list[str] = field(default_factory=list)
    avg_centrality: float = 0.0


@dataclass
class PotentialEdge:
    """Represents a potential (ghost) edge between two concepts across clusters."""

    source_id: str
    target_id: str
    similarity: float
    gap_id: str
    source_name: str = ""
    target_name: str = ""


@dataclass
class StructuralGap:
    """Represents a structural gap between two concept clusters."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cluster_a_id: int = 0
    cluster_b_id: int = 0
    gap_strength: float = 0.0  # 0 = strong gap (no connections), 1 = well connected
    concept_a_ids: list[str] = field(default_factory=list)
    concept_b_ids: list[str] = field(default_factory=list)
    bridge_concepts: list[str] = field(default_factory=list)  # Concepts that could bridge
    suggested_research_questions: list[str] = field(default_factory=list)
    potential_edges: list[PotentialEdge] = field(default_factory=list)  # Ghost edges for visualization
    status: str = "detected"  # detected, explored, bridged, dismissed


@dataclass
class CentralityMetrics:
    """Centrality metrics for a concept."""

    entity_id: str
    degree: float = 0.0
    betweenness: float = 0.0
    pagerank: float = 0.0
    cluster_id: Optional[int] = None


# Cluster color palette (visually distinct)
CLUSTER_COLORS = [
    "#FF6B6B",  # Red
    "#4ECDC4",  # Teal
    "#45B7D1",  # Sky Blue
    "#96CEB4",  # Sage Green
    "#FFEAA7",  # Yellow
    "#DDA0DD",  # Plum
    "#98D8C8",  # Mint
    "#F7DC6F",  # Gold
    "#BB8FCE",  # Lavender
    "#85C1E9",  # Light Blue
    "#F8B500",  # Orange
    "#82E0AA",  # Light Green
]


class GapDetector:
    """
    Detects structural gaps in the knowledge graph.

    Based on InfraNodus methodology:
    1. Cluster concepts by semantic similarity (embeddings)
    2. Build co-occurrence graph within and across clusters
    3. Calculate inter-cluster connectivity
    4. Gaps = cluster pairs with low connectivity but high semantic potential
    5. Generate bridge suggestions using LLM
    """

    def __init__(self, llm_provider=None, min_clusters: int = 3, max_clusters: int = 10):
        self.llm = llm_provider
        self.min_clusters = min_clusters
        self.max_clusters = max_clusters

    def cluster_concepts(
        self,
        concepts: list[dict],
        n_clusters: Optional[int] = None,
    ) -> list[ConceptCluster]:
        """
        Cluster concepts based on their embeddings using K-means.

        Args:
            concepts: List of concept dicts with 'id', 'name', 'embedding'
            n_clusters: Number of clusters (auto-determined if None)

        Returns:
            List of ConceptCluster objects
        """
        if len(concepts) < 3:
            logger.warning("Too few concepts for clustering")
            return []

        # Filter concepts with embeddings
        concepts_with_embeddings = [
            c for c in concepts
            if c.get("embedding") is not None and len(c.get("embedding", [])) > 0
        ]

        if len(concepts_with_embeddings) < 3:
            logger.warning("Too few concepts with embeddings for clustering")
            return []

        # Validate all embeddings have the same dimension
        expected_dim = len(concepts_with_embeddings[0]["embedding"])
        valid_concepts = [
            c for c in concepts_with_embeddings
            if len(c["embedding"]) == expected_dim
        ]

        if len(valid_concepts) < 3:
            logger.warning(f"Too few concepts with valid {expected_dim}-dim embeddings for clustering")
            return []

        if len(valid_concepts) != len(concepts_with_embeddings):
            logger.warning(
                f"Filtered out {len(concepts_with_embeddings) - len(valid_concepts)} concepts "
                f"with mismatched embedding dimensions"
            )
            concepts_with_embeddings = valid_concepts

        # Stack embeddings into matrix
        embeddings = np.array([c["embedding"] for c in concepts_with_embeddings], dtype=np.float32)

        # Determine optimal number of clusters
        if n_clusters is None:
            n_clusters = self._determine_optimal_clusters(embeddings)

        n_clusters = min(n_clusters, len(concepts_with_embeddings))

        # Run K-means clustering
        logger.info(f"Clustering {len(concepts_with_embeddings)} concepts into {n_clusters} clusters")

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)

        # Build cluster objects
        clusters = {}
        for i, concept in enumerate(concepts_with_embeddings):
            cluster_id = int(cluster_labels[i])

            if cluster_id not in clusters:
                clusters[cluster_id] = ConceptCluster(
                    id=cluster_id,
                    color=CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)],
                    concept_ids=[],
                    keywords=[],
                )

            clusters[cluster_id].concept_ids.append(concept["id"])
            clusters[cluster_id].keywords.append(concept["name"])

        # Set centroids and finalize
        result = []
        for cluster_id, cluster in clusters.items():
            cluster.centroid = kmeans.cluster_centers_[cluster_id]

            # Use top 5 most central concepts as keywords
            cluster.keywords = cluster.keywords[:5]

            # Generate cluster name from top keywords
            if cluster.keywords:
                cluster.name = " / ".join(cluster.keywords[:3])
            else:
                cluster.name = f"Cluster {cluster_id + 1}"

            result.append(cluster)

        logger.info(f"Created {len(result)} concept clusters")
        return result

    def _determine_optimal_clusters(self, embeddings: np.ndarray) -> int:
        """
        Determine optimal number of clusters using elbow method.
        """
        max_k = min(self.max_clusters, len(embeddings) - 1)
        min_k = min(self.min_clusters, max_k)

        if max_k <= min_k:
            return min_k

        inertias = []
        k_range = range(min_k, max_k + 1)

        for k in k_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=5)
            kmeans.fit(embeddings)
            inertias.append(kmeans.inertia_)

        # Find elbow using second derivative
        if len(inertias) < 3:
            return min_k

        diffs = np.diff(inertias)
        diffs2 = np.diff(diffs)

        # Elbow is where second derivative is maximum (most negative curvature)
        if len(diffs2) > 0:
            elbow_idx = np.argmax(diffs2) + min_k + 1
            return int(min(elbow_idx, max_k))

        return (min_k + max_k) // 2

    def detect_gaps(
        self,
        clusters: list[ConceptCluster],
        relationships: list[dict],
        concepts: list[dict],
        min_gaps: int = 3,
        max_gaps: int = 10,
    ) -> list[StructuralGap]:
        """
        Detect structural gaps between concept clusters.

        A gap exists when two clusters have:
        - Low inter-cluster connectivity (few relationships)
        - But potential for connection (semantic similarity)

        v0.6.0 Fix: Uses adaptive threshold to ensure gaps are detected even in dense graphs.

        Args:
            clusters: List of ConceptCluster objects
            relationships: List of relationship dicts with source_id, target_id
            concepts: List of concept dicts for semantic analysis
            min_gaps: Minimum number of gaps to return (default: 3)
            max_gaps: Maximum number of gaps to return (default: 10)

        Returns:
            List of StructuralGap objects, sorted by gap strength (strongest gaps first)
        """
        if len(clusters) < 2:
            return []

        # Build concept -> cluster mapping
        concept_to_cluster = {}
        for cluster in clusters:
            for concept_id in cluster.concept_ids:
                concept_to_cluster[concept_id] = cluster.id

        # Count inter-cluster relationships
        cluster_connections = defaultdict(int)
        total_relationships = 0

        for rel in relationships:
            # Support both naming conventions for backward compatibility
            source_id = rel.get("source_id") or rel.get("source")
            target_id = rel.get("target_id") or rel.get("target")
            source_cluster = concept_to_cluster.get(source_id)
            target_cluster = concept_to_cluster.get(target_id)

            if source_cluster is not None and target_cluster is not None:
                if source_cluster != target_cluster:
                    # Inter-cluster connection
                    pair = tuple(sorted([source_cluster, target_cluster]))
                    cluster_connections[pair] += 1
                    total_relationships += 1

        # Calculate gap strength for each cluster pair
        # v0.6.0: First calculate ALL gap strengths, then apply adaptive threshold
        all_gap_candidates = []
        cluster_ids = [c.id for c in clusters]

        for i, c1 in enumerate(cluster_ids):
            for c2 in cluster_ids[i + 1:]:
                pair = tuple(sorted([c1, c2]))
                connection_count = cluster_connections.get(pair, 0)

                # Gap strength: 0 = no connections (strong gap), 1 = well connected
                # Normalize by the maximum possible connections
                c1_size = len([c for c in clusters if c.id == c1][0].concept_ids)
                c2_size = len([c for c in clusters if c.id == c2][0].concept_ids)
                max_connections = c1_size * c2_size

                if max_connections > 0:
                    gap_strength = connection_count / max_connections
                else:
                    gap_strength = 0.0

                cluster_a = [c for c in clusters if c.id == c1][0]
                cluster_b = [c for c in clusters if c.id == c2][0]

                gap = StructuralGap(
                    cluster_a_id=c1,
                    cluster_b_id=c2,
                    gap_strength=gap_strength,
                    concept_a_ids=cluster_a.concept_ids[:5],  # Top 5 concepts
                    concept_b_ids=cluster_b.concept_ids[:5],
                )
                all_gap_candidates.append(gap)

        # Sort by gap strength (strongest gaps = lowest strength first)
        all_gap_candidates.sort(key=lambda g: g.gap_strength)

        # v0.6.0: Apply adaptive threshold
        if all_gap_candidates:
            strengths = [g.gap_strength for g in all_gap_candidates]

            # Calculate 25th percentile
            import numpy as np
            percentile_25 = np.percentile(strengths, 25)

            # Adaptive threshold: min of 0.3 (absolute) or 25th percentile + 0.1
            adaptive_threshold = min(0.3, percentile_25 + 0.1)

            # Filter gaps using adaptive threshold
            filtered_gaps = [g for g in all_gap_candidates if g.gap_strength < adaptive_threshold]

            # v0.9.0: Ensure minimum number of gaps is returned (stronger enforcement)
            # If adaptive threshold is too strict, always return at least min_gaps from candidates
            if len(filtered_gaps) < min_gaps and len(all_gap_candidates) >= min_gaps:
                # Threshold was too strict - return top min_gaps regardless
                filtered_gaps = all_gap_candidates[:min_gaps]
                logger.info(
                    f"Adaptive threshold too strict ({adaptive_threshold:.2f}), "
                    f"returning top {min_gaps} gaps instead"
                )
            elif len(filtered_gaps) < min_gaps and len(all_gap_candidates) > 0:
                # Have some candidates but less than min_gaps
                filtered_gaps = all_gap_candidates
                logger.info(f"Only {len(all_gap_candidates)} gap candidates available")

            gaps = filtered_gaps[:max_gaps]

            # Log for monitoring
            logger.info(
                f"Gap detection: {len(gaps)}/{len(all_gap_candidates)} gaps "
                f"(adaptive threshold: {adaptive_threshold:.2f}, 25th percentile: {percentile_25:.2f})"
            )
        else:
            gaps = []
            logger.info("Gap detection: No cluster pairs to analyze")

        return gaps

    def calculate_centrality(
        self,
        concepts: list[dict],
        relationships: list[dict],
    ) -> list[CentralityMetrics]:
        """
        Calculate centrality metrics for all concepts.

        Metrics:
        - Degree centrality: Number of connections
        - Betweenness centrality: Bridge importance (approximation)
        - PageRank: Influence-based centrality

        Args:
            concepts: List of concept dicts
            relationships: List of relationship dicts

        Returns:
            List of CentralityMetrics objects
        """
        if not concepts or not relationships:
            return []

        # Build adjacency data
        concept_ids = {c["id"] for c in concepts}
        degree = defaultdict(int)
        neighbors = defaultdict(set)

        for rel in relationships:
            src = rel.get("source_id")
            tgt = rel.get("target_id")

            if src in concept_ids and tgt in concept_ids:
                degree[src] += 1
                degree[tgt] += 1
                neighbors[src].add(tgt)
                neighbors[tgt].add(src)

        # Normalize degree
        max_degree = max(degree.values()) if degree else 1

        # Calculate PageRank (simplified)
        n = len(concepts)
        damping = 0.85
        pagerank = {c["id"]: 1.0 / n for c in concepts}

        for _ in range(20):  # 20 iterations usually enough
            new_pr = {}
            for concept in concepts:
                cid = concept["id"]
                incoming_pr = 0.0

                for neighbor in neighbors.get(cid, []):
                    out_degree = len(neighbors.get(neighbor, set()))
                    if out_degree > 0:
                        incoming_pr += pagerank.get(neighbor, 0) / out_degree

                new_pr[cid] = (1 - damping) / n + damping * incoming_pr

            pagerank = new_pr

        # Normalize PageRank
        max_pr = max(pagerank.values()) if pagerank else 1

        # Calculate betweenness (approximation using neighbor connectivity)
        betweenness = {}
        for concept in concepts:
            cid = concept["id"]
            cneighbors = neighbors.get(cid, set())

            if len(cneighbors) < 2:
                betweenness[cid] = 0.0
                continue

            # Count how many neighbor pairs are NOT directly connected
            # Higher = more "bridge-like"
            unconnected_pairs = 0
            total_pairs = 0

            neighbor_list = list(cneighbors)
            for i, n1 in enumerate(neighbor_list):
                for n2 in neighbor_list[i + 1:]:
                    total_pairs += 1
                    if n2 not in neighbors.get(n1, set()):
                        unconnected_pairs += 1

            betweenness[cid] = unconnected_pairs / total_pairs if total_pairs > 0 else 0.0

        # Build results
        results = []
        for concept in concepts:
            cid = concept["id"]
            results.append(CentralityMetrics(
                entity_id=cid,
                degree=degree.get(cid, 0) / max_degree if max_degree > 0 else 0,
                betweenness=betweenness.get(cid, 0),
                pagerank=pagerank.get(cid, 0) / max_pr if max_pr > 0 else 0,
            ))

        return results

    def find_bridge_candidates(
        self,
        gap: StructuralGap,
        concepts: list[dict],
        centrality_metrics: list[CentralityMetrics],
    ) -> list[str]:
        """
        Find concepts that could bridge a structural gap.

        Bridge candidates are concepts with:
        - High betweenness centrality (already connecting different areas)
        - Semantic similarity to both clusters

        Args:
            gap: The structural gap to bridge
            concepts: All concepts with embeddings
            centrality_metrics: Pre-calculated centrality metrics

        Returns:
            List of concept IDs that could bridge the gap
        """
        # Get concepts from both clusters
        cluster_a_concepts = [c for c in concepts if c["id"] in gap.concept_a_ids]
        cluster_b_concepts = [c for c in concepts if c["id"] in gap.concept_b_ids]

        if not cluster_a_concepts or not cluster_b_concepts:
            return []

        # Get centrality lookup
        centrality_by_id = {m.entity_id: m for m in centrality_metrics}

        # Score all concepts as potential bridges
        bridge_scores = []

        for concept in concepts:
            cid = concept["id"]

            # Skip concepts already in either cluster
            if cid in gap.concept_a_ids or cid in gap.concept_b_ids:
                continue

            embedding = concept.get("embedding")
            if embedding is None:
                continue

            # Calculate average similarity to both clusters
            emb_array = np.array(embedding).reshape(1, -1)

            sim_to_a = 0.0
            for c in cluster_a_concepts:
                if c.get("embedding"):
                    c_emb = np.array(c["embedding"]).reshape(1, -1)
                    sim_to_a += cosine_similarity(emb_array, c_emb)[0][0]
            sim_to_a /= len(cluster_a_concepts) if cluster_a_concepts else 1

            sim_to_b = 0.0
            for c in cluster_b_concepts:
                if c.get("embedding"):
                    c_emb = np.array(c["embedding"]).reshape(1, -1)
                    sim_to_b += cosine_similarity(emb_array, c_emb)[0][0]
            sim_to_b /= len(cluster_b_concepts) if cluster_b_concepts else 1

            # Bridge score = geometric mean of similarities * betweenness
            avg_similarity = (sim_to_a * sim_to_b) ** 0.5
            betweenness = centrality_by_id.get(cid, CentralityMetrics(cid)).betweenness

            bridge_score = avg_similarity * (1 + betweenness)

            bridge_scores.append((cid, bridge_score))

        # Sort by bridge score and return top 5
        bridge_scores.sort(key=lambda x: x[1], reverse=True)
        return [cid for cid, _ in bridge_scores[:5]]

    def compute_potential_edges(
        self,
        gap: StructuralGap,
        concepts: list[dict],
        top_n: int = 5,
        min_similarity: float = 0.3,
    ) -> list[PotentialEdge]:
        """
        Compute potential (ghost) edges between two clusters in a gap.

        These represent semantically similar concept pairs that could be
        connected but aren't - visualized as dashed lines in InfraNodus style.

        Args:
            gap: The structural gap to analyze
            concepts: List of concept dicts with 'id', 'name', 'embedding'
            top_n: Maximum number of potential edges to return
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of PotentialEdge objects sorted by similarity (highest first)
        """
        # Build concept lookup
        concept_by_id = {c["id"]: c for c in concepts}

        # Get concepts from each cluster
        cluster_a_concepts = [
            concept_by_id[cid] for cid in gap.concept_a_ids
            if cid in concept_by_id and concept_by_id[cid].get("embedding")
        ]
        cluster_b_concepts = [
            concept_by_id[cid] for cid in gap.concept_b_ids
            if cid in concept_by_id and concept_by_id[cid].get("embedding")
        ]

        if not cluster_a_concepts or not cluster_b_concepts:
            return []

        # Calculate pairwise similarities between clusters
        similarity_pairs = []

        for concept_a in cluster_a_concepts:
            emb_a = np.array(concept_a["embedding"]).reshape(1, -1)

            for concept_b in cluster_b_concepts:
                emb_b = np.array(concept_b["embedding"]).reshape(1, -1)
                similarity = cosine_similarity(emb_a, emb_b)[0][0]

                if similarity >= min_similarity:
                    similarity_pairs.append((
                        concept_a["id"],
                        concept_b["id"],
                        concept_a["name"],
                        concept_b["name"],
                        float(similarity),
                    ))

        # Sort by similarity (highest first) and take top N
        similarity_pairs.sort(key=lambda x: x[4], reverse=True)
        top_pairs = similarity_pairs[:top_n]

        # Create PotentialEdge objects
        potential_edges = [
            PotentialEdge(
                source_id=source_id,
                target_id=target_id,
                similarity=sim,
                gap_id=gap.id,
                source_name=source_name,
                target_name=target_name,
            )
            for source_id, target_id, source_name, target_name, sim in top_pairs
        ]

        return potential_edges

    async def generate_bridge_hypotheses(
        self,
        gap: StructuralGap,
        cluster_a_names: list[str],
        cluster_b_names: list[str],
    ) -> dict:
        """
        Generate AI-powered bridge hypotheses to connect two clusters.

        This is the core "Bridge Idea Generator" feature from InfraNodus.
        Uses LLM to propose novel research hypotheses that could bridge
        the structural gap between concept clusters.

        Args:
            gap: The structural gap to bridge
            cluster_a_names: Concept names from cluster A
            cluster_b_names: Concept names from cluster B

        Returns:
            {
                "hypotheses": [
                    {
                        "title": str,
                        "description": str,
                        "methodology": str,
                        "connecting_concepts": [str],
                        "confidence": float
                    }
                ],
                "bridge_type": "theoretical" | "methodological" | "empirical",
                "key_insight": str
            }
        """
        # Default response if no LLM
        default_response = {
            "hypotheses": [
                {
                    "title": f"Exploring connections between {cluster_a_names[0] if cluster_a_names else 'Cluster A'} and {cluster_b_names[0] if cluster_b_names else 'Cluster B'}",
                    "description": "This gap represents an opportunity to investigate how these concept areas might inform each other.",
                    "methodology": "Literature review and conceptual analysis",
                    "connecting_concepts": cluster_a_names[:2] + cluster_b_names[:2],
                    "confidence": 0.5,
                }
            ],
            "bridge_type": "theoretical",
            "key_insight": "These clusters may share underlying principles worth investigating.",
        }

        if not self.llm:
            return default_response

        prompt = f"""You are a research methodology expert analyzing a knowledge graph of academic literature.

## GAP ANALYSIS
A structural gap has been detected between two clusters of concepts in the research literature:

**Cluster A ({len(cluster_a_names)} concepts)**: {', '.join(cluster_a_names[:10])}
**Cluster B ({len(cluster_b_names)} concepts)**: {', '.join(cluster_b_names[:10])}
**Gap Score**: {gap.gap_strength:.2f} (lower = larger gap, meaning less current research connecting these areas)

## TASK
Generate 3 specific, testable research hypotheses that BRIDGE these two concept clusters.
These should propose novel connections that haven't been explored in the literature.

For each hypothesis, provide:
1. **Title**: A concise, descriptive title (1 line)
2. **Description**: 2-3 sentences explaining the hypothesis and why it matters
3. **Methodology**: Suggested research approach to test this hypothesis
4. **Connecting concepts**: List 2-4 concepts from BOTH clusters that this hypothesis connects
5. **Confidence**: Score 0.0-1.0 indicating feasibility (higher = more feasible)

Also determine:
- **Bridge type**: Is this primarily "theoretical" (conceptual connection), "methodological" (methods can transfer), or "empirical" (data/findings connect)?
- **Key insight**: One sentence summarizing the main opportunity

Return your response in the following JSON format:
{{
  "hypotheses": [
    {{
      "title": "...",
      "description": "...",
      "methodology": "...",
      "connecting_concepts": ["concept1", "concept2"],
      "confidence": 0.7
    }}
  ],
  "bridge_type": "theoretical",
  "key_insight": "..."
}}

Return ONLY valid JSON, no other text.
"""

        try:
            response = await self.llm.generate(prompt)

            # Parse JSON response
            import json

            # Try to extract JSON from response
            response_text = response.strip()

            # Handle markdown code blocks
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])

            result = json.loads(response_text)

            # Validate structure
            if "hypotheses" not in result:
                result["hypotheses"] = default_response["hypotheses"]
            if "bridge_type" not in result:
                result["bridge_type"] = "theoretical"
            if "key_insight" not in result:
                result["key_insight"] = "Connection opportunity detected between these research areas."

            # Validate hypotheses structure
            validated_hypotheses = []
            for hyp in result.get("hypotheses", [])[:5]:  # Max 5 hypotheses
                validated_hyp = {
                    "title": hyp.get("title", "Untitled Hypothesis"),
                    "description": hyp.get("description", "No description provided."),
                    "methodology": hyp.get("methodology", "Further investigation needed."),
                    "connecting_concepts": hyp.get("connecting_concepts", [])[:6],  # Max 6 concepts
                    "confidence": min(1.0, max(0.0, float(hyp.get("confidence", 0.5)))),
                }
                validated_hypotheses.append(validated_hyp)

            result["hypotheses"] = validated_hypotheses

            return result

        except Exception as e:
            logger.error(f"Failed to generate bridge hypotheses: {e}")
            return default_response

    async def generate_research_questions(
        self,
        gap: StructuralGap,
        cluster_a_concepts: list[str],
        cluster_b_concepts: list[str],
    ) -> list[str]:
        """
        Use LLM to generate research questions that could bridge a gap.

        Args:
            gap: The structural gap
            cluster_a_concepts: Concept names from cluster A
            cluster_b_concepts: Concept names from cluster B

        Returns:
            List of suggested research questions
        """
        if not self.llm:
            # Return template questions without LLM
            return [
                f"How does {cluster_a_concepts[0] if cluster_a_concepts else 'concept A'} "
                f"relate to {cluster_b_concepts[0] if cluster_b_concepts else 'concept B'}?",
                f"What are the connections between {', '.join(cluster_a_concepts[:2])} "
                f"and {', '.join(cluster_b_concepts[:2])}?",
            ]

        prompt = f"""You are a research advisor analyzing a knowledge graph of academic literature.

A structural gap has been detected between two clusters of concepts:

**Cluster A concepts**: {', '.join(cluster_a_concepts)}
**Cluster B concepts**: {', '.join(cluster_b_concepts)}

These clusters are currently disconnected in the literature, suggesting a research opportunity.

Generate 3-5 specific, novel research questions that could bridge this gap.
The questions should:
1. Connect concepts from both clusters
2. Be specific and testable
3. Suggest new research directions not currently explored
4. Be formatted as clear research questions

Return ONLY the research questions, one per line, without numbering or bullets.
"""

        try:
            response = await self.llm.generate(prompt)

            # Parse response into individual questions
            questions = [
                q.strip() for q in response.strip().split("\n")
                if q.strip() and "?" in q
            ]

            return questions[:5]  # Max 5 questions

        except Exception as e:
            logger.error(f"Failed to generate research questions: {e}")
            return []

    async def analyze_graph(
        self,
        concepts: list[dict],
        relationships: list[dict],
    ) -> dict:
        """
        Perform full gap analysis on the knowledge graph.

        Returns:
            {
                "clusters": list of ConceptCluster,
                "gaps": list of StructuralGap,
                "centrality": list of CentralityMetrics,
                "summary": str
            }
        """
        logger.info(f"Analyzing graph with {len(concepts)} concepts and {len(relationships)} relationships")

        # Step 1: Cluster concepts
        clusters = self.cluster_concepts(concepts)

        # Step 2: Calculate centrality
        centrality = self.calculate_centrality(concepts, relationships)

        # Step 3: Detect gaps
        gaps = self.detect_gaps(clusters, relationships, concepts)

        # Step 4: Find bridge candidates and generate questions for top gaps
        concept_by_id = {c["id"]: c for c in concepts}

        for gap in gaps[:5]:  # Top 5 gaps only
            gap.bridge_concepts = self.find_bridge_candidates(gap, concepts, centrality)

            # Compute potential edges (ghost edges) for visualization
            gap.potential_edges = self.compute_potential_edges(gap, concepts, top_n=5)

            # Get concept names for LLM
            a_names = [concept_by_id[cid]["name"] for cid in gap.concept_a_ids if cid in concept_by_id]
            b_names = [concept_by_id[cid]["name"] for cid in gap.concept_b_ids if cid in concept_by_id]

            gap.suggested_research_questions = await self.generate_research_questions(
                gap, a_names, b_names
            )

        # Generate summary
        summary = self._generate_summary(clusters, gaps)

        return {
            "clusters": clusters,
            "gaps": gaps,
            "centrality": centrality,
            "summary": summary,
        }

    def _generate_summary(self, clusters: list[ConceptCluster], gaps: list[StructuralGap]) -> str:
        """
        Generate a text summary of the gap analysis.

        v0.6.0: Added explanation for well-connected (dense) graphs.
        """

        if not clusters:
            return "Insufficient data for gap analysis."

        lines = [
            f"Found {len(clusters)} concept clusters with {len(gaps)} structural gaps.",
            "",
            "**Top Clusters:**",
        ]

        for cluster in clusters[:5]:
            lines.append(f"- {cluster.name} ({len(cluster.concept_ids)} concepts)")

        if gaps:
            lines.extend([
                "",
                "**Research Opportunities (Structural Gaps):**",
            ])

            for gap in gaps[:3]:
                cluster_a = [c for c in clusters if c.id == gap.cluster_a_id]
                cluster_b = [c for c in clusters if c.id == gap.cluster_b_id]

                a_name = cluster_a[0].name if cluster_a else f"Cluster {gap.cluster_a_id}"
                b_name = cluster_b[0].name if cluster_b else f"Cluster {gap.cluster_b_id}"

                lines.append(f"- Gap between '{a_name}' and '{b_name}' (connectivity: {gap.gap_strength:.1%})")

            # v0.6.0: Add explanation for well-connected graphs
            avg_connectivity = sum(g.gap_strength for g in gaps) / len(gaps) if gaps else 0
            if avg_connectivity > 0.15:  # Higher than 15% average = well connected
                lines.extend([
                    "",
                    "*Note: This graph is well-connected. The gaps shown represent *relatively* weaker connections between topic clusters, not complete disconnections.*",
                ])

        return "\n".join(lines)
