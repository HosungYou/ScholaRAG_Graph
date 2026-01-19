'use client';

import { useCallback, useRef, useMemo, useEffect, useState, forwardRef, useImperativeHandle } from 'react';
import dynamic from 'next/dynamic';
import * as THREE from 'three';
import type { GraphEntity, GraphEdge, ConceptCluster, CentralityMetrics, StructuralGap } from '@/types';

// Dynamic import to avoid SSR issues with Three.js
const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-[#0d1117]">
      <div className="text-center">
        <div className="w-12 h-12 border-2 border-accent-teal border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="font-mono text-xs text-muted">Loading 3D visualization...</p>
      </div>
    </div>
  ),
});

// Node data structure for ForceGraph
interface ForceGraphNode {
  id: string;
  name: string;
  val: number;
  color: string;
  entityType: string;
  clusterId?: number;
  centrality?: number;
  isHighlighted?: boolean;
  isBridge?: boolean;
  properties?: Record<string, unknown>;
  // Position props added by force graph
  x?: number;
  y?: number;
  z?: number;
  fx?: number;
  fy?: number;
  fz?: number;
}

// Link data structure for ForceGraph
interface ForceGraphLink {
  id: string;
  source: string | ForceGraphNode;
  target: string | ForceGraphNode;
  weight: number;
  relationshipType: string;
  isHighlighted?: boolean;
}

// Graph data for ForceGraph
interface ForceGraphData {
  nodes: ForceGraphNode[];
  links: ForceGraphLink[];
}

// Cluster color palette (InfraNodus style - vibrant, distinguishable)
const CLUSTER_COLORS = [
  '#FF6B6B', // Coral Red
  '#4ECDC4', // Turquoise
  '#45B7D1', // Sky Blue
  '#96CEB4', // Sage Green
  '#FFEAA7', // Soft Yellow
  '#DDA0DD', // Plum
  '#98D8C8', // Mint
  '#F7DC6F', // Gold
  '#BB8FCE', // Lavender
  '#85C1E9', // Light Blue
  '#F8B500', // Amber
  '#82E0AA', // Light Green
];

// Entity type colors (fallback when no cluster assigned)
const ENTITY_TYPE_COLORS: Record<string, string> = {
  Paper: '#6366F1',
  Author: '#A855F7',
  Concept: '#8B5CF6',
  Method: '#F59E0B',
  Finding: '#10B981',
  Problem: '#EF4444',
  Dataset: '#3B82F6',
  Metric: '#EC4899',
  Innovation: '#14B8A6',
  Limitation: '#F97316',
};

export interface Graph3DProps {
  nodes: GraphEntity[];
  edges: GraphEdge[];
  clusters?: ConceptCluster[];
  centralityMetrics?: CentralityMetrics[];
  highlightedNodes?: string[];
  highlightedEdges?: string[];
  selectedGap?: StructuralGap | null;
  onNodeClick?: (node: GraphEntity) => void;
  onNodeHover?: (node: GraphEntity | null) => void;
  onBackgroundClick?: () => void;
  showParticles?: boolean;
  particleSpeed?: number;
}

export interface Graph3DRef {
  focusOnNode: (nodeId: string) => void;
  focusOnCluster: (clusterId: number) => void;
  focusOnGap: (gap: StructuralGap) => void;
  resetCamera: () => void;
  getCamera: () => THREE.Camera | undefined;
}

export const Graph3D = forwardRef<Graph3DRef, Graph3DProps>(({
  nodes,
  edges,
  clusters = [],
  centralityMetrics = [],
  highlightedNodes = [],
  highlightedEdges = [],
  selectedGap,
  onNodeClick,
  onNodeHover,
  onBackgroundClick,
  showParticles = true,
  particleSpeed = 0.005,
}, ref) => {
  const fgRef = useRef<any>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // Build cluster color map
  const clusterColorMap = useMemo(() => {
    const colorMap = new Map<number, string>();
    clusters.forEach((cluster, index) => {
      colorMap.set(cluster.cluster_id, CLUSTER_COLORS[index % CLUSTER_COLORS.length]);
    });
    return colorMap;
  }, [clusters]);

  // Build centrality map
  const centralityMap = useMemo(() => {
    const map = new Map<string, number>();
    centralityMetrics.forEach(metric => {
      map.set(metric.concept_id, metric.betweenness_centrality);
    });
    return map;
  }, [centralityMetrics]);

  // Build highlighted sets for O(1) lookup
  const highlightedNodeSet = useMemo(() => new Set(highlightedNodes), [highlightedNodes]);
  const highlightedEdgeSet = useMemo(() => new Set(highlightedEdges), [highlightedEdges]);

  // Transform data for ForceGraph3D
  const graphData = useMemo<ForceGraphData>(() => {
    const forceNodes: ForceGraphNode[] = nodes.map(node => {
      const clusterId = (node.properties as { cluster_id?: number })?.cluster_id;
      const centrality = centralityMap.get(node.id) || 0;
      const isBridge = (node.properties as { is_gap_bridge?: boolean })?.is_gap_bridge || false;
      const isHighlighted = highlightedNodeSet.has(node.id);

      // Determine color: highlighted > cluster > entity type
      let color: string;
      if (isHighlighted) {
        color = '#FFD700'; // Gold for highlighted
      } else if (clusterId !== undefined && clusterColorMap.has(clusterId)) {
        color = clusterColorMap.get(clusterId)!;
      } else {
        color = ENTITY_TYPE_COLORS[node.entity_type] || '#888888';
      }

      // Size based on centrality (sqrt for visual balance)
      const baseSize = 3;
      const centralityBoost = Math.sqrt(centrality * 100) * 2;
      const bridgeBoost = isBridge ? 2 : 0;
      const nodeSize = baseSize + centralityBoost + bridgeBoost;

      return {
        id: node.id,
        name: node.name,
        val: nodeSize,
        color,
        entityType: node.entity_type,
        clusterId,
        centrality,
        isHighlighted,
        isBridge,
        properties: node.properties,
      };
    });

    const forceLinks: ForceGraphLink[] = edges.map(edge => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      weight: edge.weight || 1,
      relationshipType: edge.relationship_type,
      isHighlighted: highlightedEdgeSet.has(edge.id),
    }));

    return { nodes: forceNodes, links: forceLinks };
  }, [nodes, edges, clusterColorMap, centralityMap, highlightedNodeSet, highlightedEdgeSet]);

  // Custom node rendering with glow effect
  const nodeThreeObject = useCallback((node: ForceGraphNode) => {
    const group = new THREE.Group();

    // Main sphere
    const geometry = new THREE.SphereGeometry(node.val, 16, 16);
    const material = new THREE.MeshPhongMaterial({
      color: node.color,
      emissive: node.color,
      emissiveIntensity: node.isHighlighted ? 0.6 : 0.2,
      transparent: true,
      opacity: node.isHighlighted || hoveredNode === node.id ? 1 : 0.85,
    });
    const sphere = new THREE.Mesh(geometry, material);
    group.add(sphere);

    // Outer glow for bridge nodes
    if (node.isBridge) {
      const glowGeometry = new THREE.SphereGeometry(node.val * 1.4, 16, 16);
      const glowMaterial = new THREE.MeshBasicMaterial({
        color: '#FFD700',
        transparent: true,
        opacity: 0.2,
      });
      const glow = new THREE.Mesh(glowGeometry, glowMaterial);
      group.add(glow);
    }

    // Highlight ring for selected nodes
    if (node.isHighlighted) {
      const ringGeometry = new THREE.RingGeometry(node.val * 1.3, node.val * 1.5, 32);
      const ringMaterial = new THREE.MeshBasicMaterial({
        color: '#FFD700',
        transparent: true,
        opacity: 0.6,
        side: THREE.DoubleSide,
      });
      const ring = new THREE.Mesh(ringGeometry, ringMaterial);
      ring.rotation.x = Math.PI / 2;
      group.add(ring);
    }

    return group;
  }, [hoveredNode]);

  // Link width based on weight
  const linkWidth = useCallback((link: ForceGraphLink) => {
    const baseWidth = Math.max(0.3, link.weight * 0.5);
    return link.isHighlighted ? baseWidth * 2 : baseWidth;
  }, []);

  // Link color
  const linkColor = useCallback((link: ForceGraphLink) => {
    if (link.isHighlighted) {
      return 'rgba(255, 215, 0, 0.8)'; // Gold
    }
    return 'rgba(255, 255, 255, 0.15)';
  }, []);

  // Node click handler
  const handleNodeClick = useCallback((node: ForceGraphNode) => {
    if (onNodeClick) {
      const originalNode = nodes.find(n => n.id === node.id);
      if (originalNode) {
        onNodeClick(originalNode);
      }
    }

    // Focus camera on clicked node
    if (fgRef.current && node.x !== undefined && node.y !== undefined && node.z !== undefined) {
      const distance = 200;
      fgRef.current.cameraPosition(
        { x: node.x, y: node.y, z: node.z + distance },
        { x: node.x, y: node.y, z: node.z },
        1000
      );
    }
  }, [nodes, onNodeClick]);

  // Node hover handler
  const handleNodeHover = useCallback((node: ForceGraphNode | null) => {
    setHoveredNode(node?.id || null);
    if (onNodeHover) {
      if (node) {
        const originalNode = nodes.find(n => n.id === node.id);
        onNodeHover(originalNode || null);
      } else {
        onNodeHover(null);
      }
    }
  }, [nodes, onNodeHover]);

  // Background click handler
  const handleBackgroundClick = useCallback(() => {
    onBackgroundClick?.();
  }, [onBackgroundClick]);

  // Expose ref methods
  useImperativeHandle(ref, () => ({
    focusOnNode: (nodeId: string) => {
      if (!fgRef.current) return;
      const node = graphData.nodes.find(n => n.id === nodeId);
      if (node && node.x !== undefined && node.y !== undefined && node.z !== undefined) {
        fgRef.current.cameraPosition(
          { x: node.x, y: node.y, z: node.z + 200 },
          { x: node.x, y: node.y, z: node.z },
          1000
        );
      }
    },
    focusOnCluster: (clusterId: number) => {
      if (!fgRef.current) return;
      const clusterNodes = graphData.nodes.filter(n => n.clusterId === clusterId);
      if (clusterNodes.length === 0) return;

      // Calculate cluster centroid
      let sumX = 0, sumY = 0, sumZ = 0;
      clusterNodes.forEach(n => {
        sumX += n.x || 0;
        sumY += n.y || 0;
        sumZ += n.z || 0;
      });
      const centroid = {
        x: sumX / clusterNodes.length,
        y: sumY / clusterNodes.length,
        z: sumZ / clusterNodes.length,
      };

      fgRef.current.cameraPosition(
        { x: centroid.x, y: centroid.y, z: centroid.z + 400 },
        centroid,
        1000
      );
    },
    focusOnGap: (gap: StructuralGap) => {
      if (!fgRef.current) return;

      // Find nodes in both clusters
      const clusterANodes = graphData.nodes.filter(n =>
        gap.cluster_a_concepts.includes(n.id)
      );
      const clusterBNodes = graphData.nodes.filter(n =>
        gap.cluster_b_concepts.includes(n.id)
      );

      const allNodes = [...clusterANodes, ...clusterBNodes];
      if (allNodes.length === 0) return;

      // Calculate midpoint between clusters
      let sumX = 0, sumY = 0, sumZ = 0;
      allNodes.forEach(n => {
        sumX += n.x || 0;
        sumY += n.y || 0;
        sumZ += n.z || 0;
      });
      const midpoint = {
        x: sumX / allNodes.length,
        y: sumY / allNodes.length,
        z: sumZ / allNodes.length,
      };

      fgRef.current.cameraPosition(
        { x: midpoint.x, y: midpoint.y, z: midpoint.z + 350 },
        midpoint,
        1000
      );
    },
    resetCamera: () => {
      if (fgRef.current) {
        fgRef.current.cameraPosition({ x: 0, y: 0, z: 500 }, { x: 0, y: 0, z: 0 }, 1000);
      }
    },
    getCamera: () => fgRef.current?.camera(),
  }), [graphData]);

  // Auto-focus on gap when selected
  useEffect(() => {
    if (selectedGap && fgRef.current) {
      // Small delay to ensure graph is rendered
      setTimeout(() => {
        const allGapNodes = [
          ...selectedGap.cluster_a_concepts,
          ...selectedGap.cluster_b_concepts,
          ...selectedGap.bridge_candidates,
        ];

        const gapNodes = graphData.nodes.filter(n => allGapNodes.includes(n.id));
        if (gapNodes.length === 0) return;

        let sumX = 0, sumY = 0, sumZ = 0;
        gapNodes.forEach(n => {
          sumX += n.x || 0;
          sumY += n.y || 0;
          sumZ += n.z || 0;
        });
        const center = {
          x: sumX / gapNodes.length,
          y: sumY / gapNodes.length,
          z: sumZ / gapNodes.length,
        };

        fgRef.current.cameraPosition(
          { x: center.x, y: center.y, z: center.z + 300 },
          center,
          1000
        );
      }, 100);
    }
  }, [selectedGap, graphData.nodes]);

  // Initial camera setup
  useEffect(() => {
    if (fgRef.current) {
      // Set initial camera distance
      setTimeout(() => {
        fgRef.current?.cameraPosition({ x: 0, y: 0, z: 500 });
      }, 500);
    }
  }, []);

  return (
    <div className="w-full h-full bg-[#0d1117]">
      <ForceGraph3D
        ref={fgRef}
        graphData={graphData}
        nodeThreeObject={nodeThreeObject}
        nodeLabel={(node: ForceGraphNode) => `
          <div style="background: rgba(0,0,0,0.8); padding: 8px 12px; border-radius: 4px; font-family: monospace; font-size: 12px;">
            <div style="font-weight: bold; color: ${node.color};">${node.name}</div>
            <div style="color: #888; margin-top: 4px;">${node.entityType}</div>
            ${node.centrality ? `<div style="color: #4ECDC4; margin-top: 2px;">Centrality: ${(node.centrality * 100).toFixed(1)}%</div>` : ''}
            ${node.isBridge ? '<div style="color: #FFD700; margin-top: 2px;">Bridge Node</div>' : ''}
          </div>
        `}
        linkWidth={linkWidth}
        linkColor={linkColor}
        linkOpacity={0.6}
        linkDirectionalParticles={showParticles ? 2 : 0}
        linkDirectionalParticleSpeed={particleSpeed}
        linkDirectionalParticleWidth={1.5}
        linkDirectionalParticleColor={() => '#FFD700'}
        backgroundColor="#0d1117"
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        onBackgroundClick={handleBackgroundClick}
        // Force simulation parameters
        cooldownTicks={100}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        // Zoom controls
        enableZoomInteraction={true}
        enableNavigationControls={true}
        // Performance optimizations
        warmupTicks={50}
        onEngineStop={() => console.log('Force simulation stabilized')}
      />
    </div>
  );
});

Graph3D.displayName = 'Graph3D';

export default Graph3D;
