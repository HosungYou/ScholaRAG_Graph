/**
 * Graph layout algorithms for Concept-Centric Knowledge Graph
 * Enhanced with cluster-aware force simulation and centrality-based sizing
 */

import type { GraphEntity, GraphEdge, EntityType } from '@/types';
import { Node, Edge, MarkerType } from 'reactflow';

interface LayoutNode {
  id: string;
  x: number;
  y: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
  entityType: EntityType;
  clusterId?: number;
  centrality?: number;
}

interface LayoutLink {
  source: string | LayoutNode;
  target: string | LayoutNode;
  weight?: number;
}

interface LayoutOptions {
  width?: number;
  height?: number;
  centerStrength?: number;
  linkStrength?: number;
  chargeStrength?: number;
  clusterStrength?: number;
  iterations?: number;
}

// Cluster colors - visually distinct palette
const clusterColors = [
  '#FF6B6B', // Red
  '#4ECDC4', // Teal
  '#45B7D1', // Sky Blue
  '#96CEB4', // Sage Green
  '#FFEAA7', // Yellow
  '#DDA0DD', // Plum
  '#98D8C8', // Mint
  '#F7DC6F', // Gold
  '#BB8FCE', // Lavender
  '#85C1E9', // Light Blue
  '#F8B500', // Orange
  '#82E0AA', // Light Green
];

// Entity type colors (Hybrid Mode - matches FilterPanel/PolygonNode)
const entityTypeColors: Record<string, string> = {
  // Hybrid Mode entities
  Paper: '#6366F1',      // Indigo
  Author: '#A855F7',     // Purple
  // Concept-centric entities
  Concept: '#8B5CF6',    // Violet
  Method: '#F59E0B',     // Amber
  Finding: '#10B981',    // Emerald
  Problem: '#EF4444',    // Red
  Dataset: '#3B82F6',    // Blue
  Metric: '#EC4899',     // Pink
  Innovation: '#14B8A6', // Teal
  Limitation: '#F97316', // Orange
};

// Edge colors by relationship type (ResearchRabbit style)
const edgeColors: Record<string, string> = {
  'DISCUSSES_CONCEPT': '#8B5CF6',  // Violet - Paper discusses concept
  'USES_METHOD': '#F59E0B',        // Amber - Uses methodology
  'SUPPORTS': '#10B981',           // Green - Supporting evidence
  'CONTRADICTS': '#EF4444',        // Red - Contradicting evidence
  'CITES': '#3B82F6',              // Blue - Citation relationship
  'CO_OCCURS_WITH': '#EC4899',     // Pink - Co-occurrence
  'RELATED_TO': '#94A3B8',         // Slate - General relation
  'BRIDGES_GAP': '#FFD700',        // Gold - Gap bridge (special)
  'HAS_AUTHOR': '#A855F7',         // Purple - Author relationship
  'default': '#94A3B8',            // Slate - Default
};

/**
 * Get edge color based on relationship type
 */
function getEdgeColor(relationshipType: string): string {
  return edgeColors[relationshipType] || edgeColors.default;
}

/**
 * Cluster-aware force-directed layout
 * Groups nodes by cluster with force attraction to cluster centroids
 */
export function clusterForceLayout(
  nodes: GraphEntity[],
  edges: GraphEdge[],
  options: LayoutOptions = {}
): { nodes: Node[]; edges: Edge[] } {
  const {
    width = 1200,
    height = 800,
    chargeStrength = -400,  // Increased repulsion for better node dispersion
    linkStrength = 0.4,
    clusterStrength = 0.1,
    iterations = 200,  // More iterations for stable layout
  } = options;

  const centerX = width / 2;
  const centerY = height / 2;

  // Group nodes by cluster for initial positioning
  const clusterMap = new Map<number, GraphEntity[]>();
  const unclustered: GraphEntity[] = [];

  for (const node of nodes) {
    const clusterId = node.properties?.cluster_id;
    if (clusterId !== undefined && clusterId !== null && typeof clusterId === 'number') {
      if (!clusterMap.has(clusterId)) {
        clusterMap.set(clusterId, []);
      }
      clusterMap.get(clusterId)!.push(node);
    } else {
      unclustered.push(node);
    }
  }

  // Calculate cluster centroid positions (arranged in a circle)
  const clusterCentroids = new Map<number, { x: number; y: number }>();
  const clusterIds = Array.from(clusterMap.keys());
  const clusterRadius = Math.min(width, height) * 0.35;

  clusterIds.forEach((clusterId, i) => {
    const angle = (2 * Math.PI * i) / clusterIds.length - Math.PI / 2;
    clusterCentroids.set(clusterId, {
      x: centerX + Math.cos(angle) * clusterRadius,
      y: centerY + Math.sin(angle) * clusterRadius,
    });
  });

  // Initialize node positions near their cluster centroid
  const layoutNodes: LayoutNode[] = nodes.map((node) => {
    const rawClusterId = node.properties?.cluster_id;
    const clusterId = typeof rawClusterId === 'number' ? rawClusterId : undefined;
    const rawCentrality = node.properties?.centrality_pagerank;
    const centrality = typeof rawCentrality === 'number' ? rawCentrality : 0;
    let x: number, y: number;

    if (clusterId !== undefined && clusterCentroids.has(clusterId)) {
      const centroid = clusterCentroids.get(clusterId)!;
      const jitter = 100 * (1 - centrality); // High centrality = less jitter
      x = centroid.x + (Math.random() - 0.5) * jitter;
      y = centroid.y + (Math.random() - 0.5) * jitter;
    } else {
      // Unclustered nodes start near center
      x = centerX + (Math.random() - 0.5) * 200;
      y = centerY + (Math.random() - 0.5) * 200;
    }

    return {
      id: node.id,
      x,
      y,
      vx: 0,
      vy: 0,
      entityType: node.entity_type,
      clusterId,
      centrality,
    };
  });

  // Create node lookup map
  const nodeMap = new Map(layoutNodes.map(n => [n.id, n]));

  // Create links with weight based on relationship properties
  const links: LayoutLink[] = edges
    .filter(e => nodeMap.has(e.source) && nodeMap.has(e.target))
    .map(e => {
      const rawWeight = e.properties?.weight ?? e.properties?.confidence;
      const weight = typeof rawWeight === 'number' ? rawWeight : 1;
      return {
        source: nodeMap.get(e.source)!,
        target: nodeMap.get(e.target)!,
        weight,
      };
    });

  // Run simulation
  for (let i = 0; i < iterations; i++) {
    const alpha = Math.pow(1 - i / iterations, 2); // Quadratic decay

    // Apply charge force (repulsion between nodes)
    for (let a = 0; a < layoutNodes.length; a++) {
      for (let b = a + 1; b < layoutNodes.length; b++) {
        const nodeA = layoutNodes[a];
        const nodeB = layoutNodes[b];

        const dx = nodeB.x - nodeA.x;
        const dy = nodeB.y - nodeA.y;
        const distance = Math.sqrt(dx * dx + dy * dy) || 1;

        // Weaker repulsion within same cluster
        const sameCluster = nodeA.clusterId !== undefined &&
                           nodeA.clusterId === nodeB.clusterId;
        const chargeMultiplier = sameCluster ? 0.5 : 1.0;

        const force = (chargeStrength * chargeMultiplier * alpha) / (distance * distance);
        const fx = (dx / distance) * force;
        const fy = (dy / distance) * force;

        nodeA.vx! -= fx;
        nodeA.vy! -= fy;
        nodeB.vx! += fx;
        nodeB.vy! += fy;

        // Minimum distance constraint - prevent node overlap
        const minDistance = 60;
        if (distance < minDistance) {
          const pushForce = (minDistance - distance) * 0.5 * alpha;
          const px = (dx / distance) * pushForce;
          const py = (dy / distance) * pushForce;
          nodeA.vx! -= px;
          nodeA.vy! -= py;
          nodeB.vx! += px;
          nodeB.vy! += py;
        }
      }
    }

    // Apply link force (attraction between connected nodes)
    for (const link of links) {
      const source = link.source as LayoutNode;
      const target = link.target as LayoutNode;

      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const distance = Math.sqrt(dx * dx + dy * dy) || 1;

      // Ideal distance based on weight
      const idealDistance = 100 / (link.weight ?? 1);
      const diff = (distance - idealDistance) * linkStrength * alpha;

      const fx = (dx / distance) * diff;
      const fy = (dy / distance) * diff;

      source.vx! += fx;
      source.vy! += fy;
      target.vx! -= fx;
      target.vy! -= fy;
    }

    // Apply cluster force (attraction to cluster centroid)
    for (const node of layoutNodes) {
      if (node.clusterId !== undefined && clusterCentroids.has(node.clusterId)) {
        const centroid = clusterCentroids.get(node.clusterId)!;
        const dx = centroid.x - node.x;
        const dy = centroid.y - node.y;

        node.vx! += dx * clusterStrength * alpha;
        node.vy! += dy * clusterStrength * alpha;
      } else {
        // Unclustered nodes attracted to center (reduced force)
        const dx = centerX - node.x;
        const dy = centerY - node.y;
        node.vx! += dx * 0.002 * alpha;  // Reduced from 0.005
        node.vy! += dy * 0.002 * alpha;
      }
    }

    // Apply center gravity (very weak - allows more dispersion)
    for (const node of layoutNodes) {
      const dx = centerX - node.x;
      const dy = centerY - node.y;
      node.vx! += dx * 0.001 * alpha;  // Reduced from 0.002
      node.vy! += dy * 0.001 * alpha;
    }

    // Update positions with velocity
    for (const node of layoutNodes) {
      node.x += node.vx! * 0.8;
      node.y += node.vy! * 0.8;

      // Dampen velocity
      node.vx! *= 0.85;
      node.vy! *= 0.85;

      // Keep within bounds with padding
      const padding = 80;
      node.x = Math.max(padding, Math.min(width - padding, node.x));
      node.y = Math.max(padding, Math.min(height - padding, node.y));
    }
  }

  // Convert to React Flow format with circular node type
  const flowNodes: Node[] = nodes.map((node) => {
    const layoutNode = nodeMap.get(node.id)!;
    const rawClusterId = node.properties?.cluster_id;
    const clusterId = typeof rawClusterId === 'number' ? rawClusterId : undefined;

    return {
      id: node.id,
      type: 'circular', // Use circular node type
      position: { x: layoutNode.x, y: layoutNode.y },
      data: {
        label: node.name,
        entityType: node.entity_type,
        properties: node.properties,
        isHighlighted: false,
        // Centrality metrics
        centralityDegree: node.properties?.centrality_degree,
        centralityBetweenness: node.properties?.centrality_betweenness,
        centralityPagerank: node.properties?.centrality_pagerank,
        // Cluster info
        clusterId: clusterId,
        clusterColor: clusterId !== undefined
          ? clusterColors[clusterId % clusterColors.length]
          : undefined,
        // Definition
        definition: node.properties?.definition,
        // Paper count
        paperCount: Array.isArray(node.properties?.source_paper_ids)
          ? node.properties.source_paper_ids.length
          : undefined,
        // Gap bridge
        isGapBridge: node.properties?.is_gap_bridge,
      },
    };
  });

  // Create edges with arrows and styling (ResearchRabbit style)
  const flowEdges: Edge[] = edges.map((edge) => {
    const isGapBridge = edge.relationship_type === 'BRIDGES_GAP';
    const edgeColor = getEdgeColor(edge.relationship_type);
    const rawWeight = edge.properties?.weight ?? edge.properties?.confidence;
    const weight = typeof rawWeight === 'number' ? rawWeight : 1;

    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'default',  // Straight line (Bezier curve) for better visibility
      animated: isGapBridge,
      // Arrow marker at target end
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: edgeColor,
        width: 16,
        height: 16,
      },
      style: {
        stroke: edgeColor,
        strokeWidth: isGapBridge ? 2 : Math.max(1, weight * 2),
        strokeDasharray: isGapBridge ? '5,5' : undefined,
        opacity: 0.7,
      },
      // Optional: show relationship type as label
      label: edge.relationship_type?.replace(/_/g, ' '),
      labelStyle: {
        fontSize: 9,
        fill: '#9CA3AF',
        fontWeight: 500,
      },
      labelBgStyle: {
        fill: '#1a1a2e',
        fillOpacity: 0.8,
      },
      labelBgPadding: [4, 2] as [number, number],
    };
  });

  return { nodes: flowNodes, edges: flowEdges };
}

/**
 * Simple force-directed layout (legacy, for fallback)
 */
export function forceDirectedLayout(
  nodes: GraphEntity[],
  edges: GraphEdge[],
  options: LayoutOptions = {}
): { nodes: Node[]; edges: Edge[] } {
  // Use cluster force layout by default
  return clusterForceLayout(nodes, edges, options);
}

/**
 * Radial layout - Concepts arranged by importance from center
 */
export function radialLayout(
  nodes: GraphEntity[],
  edges: GraphEdge[],
  options: LayoutOptions = {}
): { nodes: Node[]; edges: Edge[] } {
  const { width = 1200, height = 800 } = options;
  const centerX = width / 2;
  const centerY = height / 2;

  // Sort by centrality (highest first)
  const sortedNodes = [...nodes].sort((a, b) => {
    const aRankRaw = a.properties?.centrality_pagerank;
    const bRankRaw = b.properties?.centrality_pagerank;
    const aRank = typeof aRankRaw === 'number' ? aRankRaw : 0;
    const bRank = typeof bRankRaw === 'number' ? bRankRaw : 0;
    return bRank - aRank;
  });

  // Arrange in concentric circles
  const positions = new Map<string, { x: number; y: number }>();
  let currentRadius = 0;
  let nodesInRing = 1;
  let nodeIndex = 0;
  let ringStart = 0;

  for (let i = 0; i < sortedNodes.length; i++) {
    if (nodeIndex >= nodesInRing) {
      // Move to next ring
      currentRadius += 120;
      ringStart = i;
      nodesInRing = Math.min(
        Math.ceil(2 * Math.PI * currentRadius / 80),
        sortedNodes.length - i
      );
      nodeIndex = 0;
    }

    const node = sortedNodes[i];
    const angle = (2 * Math.PI * nodeIndex) / nodesInRing - Math.PI / 2;

    positions.set(node.id, {
      x: centerX + Math.cos(angle) * currentRadius,
      y: centerY + Math.sin(angle) * currentRadius,
    });

    nodeIndex++;
  }

  // Convert to React Flow format
  const flowNodes: Node[] = nodes.map((node) => {
    const pos = positions.get(node.id) || { x: centerX, y: centerY };
    const rawClusterId = node.properties?.cluster_id;
    const clusterId = typeof rawClusterId === 'number' ? rawClusterId : undefined;

    return {
      id: node.id,
      type: 'circular',
      position: pos,
      data: {
        label: node.name,
        entityType: node.entity_type,
        properties: node.properties,
        isHighlighted: false,
        centralityDegree: node.properties?.centrality_degree,
        centralityBetweenness: node.properties?.centrality_betweenness,
        centralityPagerank: node.properties?.centrality_pagerank,
        clusterId: clusterId,
        clusterColor: clusterId !== undefined
          ? clusterColors[clusterId % clusterColors.length]
          : undefined,
        definition: node.properties?.definition,
        paperCount: Array.isArray(node.properties?.source_paper_ids)
          ? node.properties.source_paper_ids.length
          : undefined,
        isGapBridge: node.properties?.is_gap_bridge,
      },
    };
  });

  const flowEdges: Edge[] = edges.map((edge) => {
    const isGapBridge = edge.relationship_type === 'BRIDGES_GAP';
    const edgeColor = getEdgeColor(edge.relationship_type);
    const rawWeight = edge.properties?.weight ?? edge.properties?.confidence;
    const weight = typeof rawWeight === 'number' ? rawWeight : 1;

    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'default',  // Straight line (Bezier curve) for better visibility
      animated: isGapBridge,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: edgeColor,
        width: 16,
        height: 16,
      },
      style: {
        stroke: edgeColor,
        strokeWidth: isGapBridge ? 2 : Math.max(1, weight * 2),
        strokeDasharray: isGapBridge ? '5,5' : undefined,
        opacity: 0.6,
      },
      label: edge.relationship_type?.replace(/_/g, ' '),
      labelStyle: {
        fontSize: 9,
        fill: '#9CA3AF',
        fontWeight: 500,
      },
      labelBgStyle: {
        fill: '#1a1a2e',
        fillOpacity: 0.8,
      },
      labelBgPadding: [4, 2] as [number, number],
    };
  });

  return { nodes: flowNodes, edges: flowEdges };
}

/**
 * Update node positions with highlight state
 */
export function updateNodeHighlights(
  nodes: Node[],
  highlightedNodeIds: string[]
): Node[] {
  const highlightSet = new Set(highlightedNodeIds);
  return nodes.map(node => ({
    ...node,
    data: {
      ...node.data,
      isHighlighted: highlightSet.has(node.id),
    },
  }));
}

/**
 * Update edge styles with highlight state
 */
export function updateEdgeHighlights(
  edges: Edge[],
  highlightedEdgeIds: string[]
): Edge[] {
  const highlightSet = new Set(highlightedEdgeIds);
  return edges.map(edge => ({
    ...edge,
    animated: highlightSet.has(edge.id) || edge.animated,
    style: {
      ...edge.style,
      stroke: highlightSet.has(edge.id) ? '#F59E0B' : (edge.style?.stroke ?? '#94A3B8'),
      strokeWidth: highlightSet.has(edge.id) ? 3 : (edge.style?.strokeWidth ?? 1),
      opacity: highlightSet.has(edge.id) ? 1 : (edge.style?.opacity ?? 0.6),
    },
  }));
}

export type LayoutType = 'force' | 'cluster' | 'radial';

export function applyLayout(
  nodes: GraphEntity[],
  edges: GraphEdge[],
  layoutType: LayoutType = 'cluster',
  options?: LayoutOptions
): { nodes: Node[]; edges: Edge[] } {
  switch (layoutType) {
    case 'radial':
      return radialLayout(nodes, edges, options);
    case 'cluster':
    case 'force':
    default:
      return clusterForceLayout(nodes, edges, options);
  }
}
