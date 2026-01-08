/**
 * Graph layout algorithms for Knowledge Graph visualization
 * Uses D3-force simulation for force-directed layout
 */

import type { GraphEntity, GraphEdge, EntityType } from '@/types';
import { Node, Edge } from 'reactflow';

interface LayoutNode {
  id: string;
  x: number;
  y: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
  entityType: EntityType;
}

interface LayoutLink {
  source: string | LayoutNode;
  target: string | LayoutNode;
}

interface LayoutOptions {
  width?: number;
  height?: number;
  centerStrength?: number;
  linkStrength?: number;
  chargeStrength?: number;
  iterations?: number;
}

// Entity type grouping for clustered layout
const entityTypeGroups: Record<EntityType, { angle: number; radius: number }> = {
  Paper: { angle: 0, radius: 0.4 },
  Author: { angle: Math.PI * 0.4, radius: 0.7 },
  Concept: { angle: Math.PI * 0.8, radius: 0.6 },
  Method: { angle: Math.PI * 1.2, radius: 0.5 },
  Finding: { angle: Math.PI * 1.6, radius: 0.6 },
};

/**
 * Simple force-directed layout without D3 dependency
 * Uses custom implementation for better bundle size
 */
export function forceDirectedLayout(
  nodes: GraphEntity[],
  edges: GraphEdge[],
  options: LayoutOptions = {}
): { nodes: Node[]; edges: Edge[] } {
  const {
    width = 1200,
    height = 800,
    chargeStrength = -300,
    linkStrength = 0.3,
    iterations = 100,
  } = options;

  const centerX = width / 2;
  const centerY = height / 2;

  // Initialize node positions using entity type clustering
  const layoutNodes: LayoutNode[] = nodes.map((node, i) => {
    const group = entityTypeGroups[node.entity_type];
    const jitter = Math.random() * 100 - 50;
    const radiusOffset = Math.random() * 100;

    return {
      id: node.id,
      x: centerX + Math.cos(group.angle) * (group.radius * width / 2 + radiusOffset) + jitter,
      y: centerY + Math.sin(group.angle) * (group.radius * height / 2 + radiusOffset) + jitter,
      vx: 0,
      vy: 0,
      entityType: node.entity_type,
    };
  });

  // Create node lookup map
  const nodeMap = new Map(layoutNodes.map(n => [n.id, n]));

  // Create links
  const links: LayoutLink[] = edges
    .filter(e => nodeMap.has(e.source) && nodeMap.has(e.target))
    .map(e => ({
      source: nodeMap.get(e.source)!,
      target: nodeMap.get(e.target)!,
    }));

  // Run simulation
  for (let i = 0; i < iterations; i++) {
    const alpha = 1 - i / iterations;

    // Apply charge force (repulsion between all nodes)
    for (let a = 0; a < layoutNodes.length; a++) {
      for (let b = a + 1; b < layoutNodes.length; b++) {
        const nodeA = layoutNodes[a];
        const nodeB = layoutNodes[b];

        const dx = nodeB.x - nodeA.x;
        const dy = nodeB.y - nodeA.y;
        const distance = Math.sqrt(dx * dx + dy * dy) || 1;

        // Repulsion force inversely proportional to distance
        const force = (chargeStrength * alpha) / (distance * distance);
        const fx = (dx / distance) * force;
        const fy = (dy / distance) * force;

        nodeA.vx! -= fx;
        nodeA.vy! -= fy;
        nodeB.vx! += fx;
        nodeB.vy! += fy;
      }
    }

    // Apply link force (attraction between connected nodes)
    for (const link of links) {
      const source = link.source as LayoutNode;
      const target = link.target as LayoutNode;

      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const distance = Math.sqrt(dx * dx + dy * dy) || 1;

      // Ideal link distance based on entity types
      const idealDistance = getIdealDistance(source.entityType, target.entityType);
      const diff = (distance - idealDistance) * linkStrength * alpha;

      const fx = (dx / distance) * diff;
      const fy = (dy / distance) * diff;

      source.vx! += fx;
      source.vy! += fy;
      target.vx! -= fx;
      target.vy! -= fy;
    }

    // Apply center force
    for (const node of layoutNodes) {
      const dx = centerX - node.x;
      const dy = centerY - node.y;
      node.vx! += dx * 0.01 * alpha;
      node.vy! += dy * 0.01 * alpha;
    }

    // Update positions
    for (const node of layoutNodes) {
      // Apply velocity with damping
      node.x += node.vx! * 0.9;
      node.y += node.vy! * 0.9;

      // Dampen velocity
      node.vx! *= 0.9;
      node.vy! *= 0.9;

      // Keep within bounds
      node.x = Math.max(50, Math.min(width - 50, node.x));
      node.y = Math.max(50, Math.min(height - 50, node.y));
    }
  }

  // Convert to React Flow format
  const flowNodes: Node[] = nodes.map((node) => {
    const layoutNode = nodeMap.get(node.id)!;
    return {
      id: node.id,
      type: node.entity_type.toLowerCase(),
      position: { x: layoutNode.x, y: layoutNode.y },
      data: {
        label: node.name,
        entityType: node.entity_type,
        properties: node.properties,
        isHighlighted: false,
      },
    };
  });

  const flowEdges: Edge[] = edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.relationship_type.replace(/_/g, ' '),
    type: 'smoothstep',
    animated: false,
    style: {
      stroke: '#94A3B8',
      strokeWidth: 1,
    },
  }));

  return { nodes: flowNodes, edges: flowEdges };
}

/**
 * Get ideal distance between two node types
 */
function getIdealDistance(typeA: EntityType, typeB: EntityType): number {
  // Paper-Paper: further apart
  if (typeA === 'Paper' && typeB === 'Paper') return 200;

  // Paper-Author: medium distance
  if ((typeA === 'Paper' && typeB === 'Author') || (typeA === 'Author' && typeB === 'Paper')) {
    return 150;
  }

  // Paper-Concept/Method/Finding: closer
  if (typeA === 'Paper' || typeB === 'Paper') return 120;

  // Same type clustering
  if (typeA === typeB) return 180;

  // Default
  return 150;
}

/**
 * Hierarchical layout - Papers in center, related entities radiate out
 */
export function hierarchicalLayout(
  nodes: GraphEntity[],
  edges: GraphEdge[],
  options: LayoutOptions = {}
): { nodes: Node[]; edges: Edge[] } {
  const { width = 1200, height = 800 } = options;
  const centerX = width / 2;
  const centerY = height / 2;

  // Separate nodes by type
  const papers = nodes.filter(n => n.entity_type === 'Paper');
  const others = nodes.filter(n => n.entity_type !== 'Paper');

  // Build adjacency list
  const adjacency = new Map<string, Set<string>>();
  for (const edge of edges) {
    if (!adjacency.has(edge.source)) adjacency.set(edge.source, new Set());
    if (!adjacency.has(edge.target)) adjacency.set(edge.target, new Set());
    adjacency.get(edge.source)!.add(edge.target);
    adjacency.get(edge.target)!.add(edge.source);
  }

  const positions = new Map<string, { x: number; y: number }>();

  // Layout papers in a grid in the center
  const papersPerRow = Math.ceil(Math.sqrt(papers.length));
  const paperSpacing = 250;
  const paperStartX = centerX - ((papersPerRow - 1) * paperSpacing) / 2;
  const paperStartY = centerY - ((Math.ceil(papers.length / papersPerRow) - 1) * paperSpacing) / 2;

  papers.forEach((paper, i) => {
    const row = Math.floor(i / papersPerRow);
    const col = i % papersPerRow;
    positions.set(paper.id, {
      x: paperStartX + col * paperSpacing,
      y: paperStartY + row * paperSpacing,
    });
  });

  // Layout other nodes around their connected papers
  others.forEach((node) => {
    const connectedPapers = papers.filter(p =>
      adjacency.get(node.id)?.has(p.id) || adjacency.get(p.id)?.has(node.id)
    );

    if (connectedPapers.length > 0) {
      // Average position of connected papers
      const avgX = connectedPapers.reduce((sum, p) => sum + positions.get(p.id)!.x, 0) / connectedPapers.length;
      const avgY = connectedPapers.reduce((sum, p) => sum + positions.get(p.id)!.y, 0) / connectedPapers.length;

      // Offset based on entity type
      const group = entityTypeGroups[node.entity_type];
      const radius = 100 + Math.random() * 50;

      positions.set(node.id, {
        x: avgX + Math.cos(group.angle + Math.random() * 0.5) * radius,
        y: avgY + Math.sin(group.angle + Math.random() * 0.5) * radius,
      });
    } else {
      // Orphan nodes go to edges
      const group = entityTypeGroups[node.entity_type];
      positions.set(node.id, {
        x: centerX + Math.cos(group.angle) * (width * 0.4) + Math.random() * 50,
        y: centerY + Math.sin(group.angle) * (height * 0.4) + Math.random() * 50,
      });
    }
  });

  // Convert to React Flow format
  const flowNodes: Node[] = nodes.map((node) => ({
    id: node.id,
    type: node.entity_type.toLowerCase(),
    position: positions.get(node.id) || { x: centerX, y: centerY },
    data: {
      label: node.name,
      entityType: node.entity_type,
      properties: node.properties,
      isHighlighted: false,
    },
  }));

  const flowEdges: Edge[] = edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.relationship_type.replace(/_/g, ' '),
    type: 'smoothstep',
    animated: false,
    style: {
      stroke: '#94A3B8',
      strokeWidth: 1,
    },
  }));

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
    animated: highlightSet.has(edge.id),
    style: {
      stroke: highlightSet.has(edge.id) ? '#F59E0B' : '#94A3B8',
      strokeWidth: highlightSet.has(edge.id) ? 2 : 1,
    },
  }));
}

export type LayoutType = 'force' | 'hierarchical';

export function applyLayout(
  nodes: GraphEntity[],
  edges: GraphEdge[],
  layoutType: LayoutType = 'force',
  options?: LayoutOptions
): { nodes: Node[]; edges: Edge[] } {
  switch (layoutType) {
    case 'hierarchical':
      return hierarchicalLayout(nodes, edges, options);
    case 'force':
    default:
      return forceDirectedLayout(nodes, edges, options);
  }
}
