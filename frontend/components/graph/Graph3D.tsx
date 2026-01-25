'use client';

import { useCallback, useRef, useMemo, useEffect, useState, forwardRef, useImperativeHandle } from 'react';
import dynamic from 'next/dynamic';
import * as THREE from 'three';
import type { GraphEntity, GraphEdge, ConceptCluster, CentralityMetrics, StructuralGap, PotentialEdge } from '@/types';

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
  isGhost?: boolean;  // Ghost edge (potential edge) for InfraNodus-style visualization
  similarity?: number;  // Similarity score for ghost edges
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
  // UI-011: Edge click handler for Relationship Evidence
  onEdgeClick?: (edge: GraphEdge) => void;
  showParticles?: boolean;
  particleSpeed?: number;
  // Ghost Edge props (InfraNodus-style)
  showGhostEdges?: boolean;
  potentialEdges?: PotentialEdge[];
  // Bloom/Glow effect props
  bloomEnabled?: boolean;
  bloomIntensity?: number;
  glowSize?: number;
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
  onEdgeClick,  // UI-011: Edge click handler for Relationship Evidence
  showParticles = false,  // Disabled by default - particles have no academic meaning in knowledge graphs
  particleSpeed = 0.005,
  showGhostEdges = false,
  potentialEdges = [],
  bloomEnabled = false,
  bloomIntensity = 0.5,
  glowSize = 1.3,
}, ref) => {
  const fgRef = useRef<any>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // UI-010 FIX: Store node positions to persist across re-renders
  // This prevents the simulation from restarting when graphData is recreated
  const nodePositionsRef = useRef<Map<string, { x: number; y: number; z: number; fx?: number; fy?: number; fz?: number }>>(new Map());

  // UI-010 FIX: Track if this is the initial render
  const isInitialRenderRef = useRef(true);

  // Double-click detection state
  const lastClickRef = useRef<{ nodeId: string; timestamp: number } | null>(null);
  const DOUBLE_CLICK_THRESHOLD = 300; // ms

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

  // Calculate top 20% centrality threshold for label display
  const labelCentralityThreshold = useMemo(() => {
    if (centralityMetrics.length === 0) {
      // No centrality data - show labels for all nodes
      return 0;
    }
    const sortedCentralities = [...centralityMetrics]
      .map(m => m.betweenness_centrality)
      .sort((a, b) => b - a);
    const top20Index = Math.floor(sortedCentralities.length * 0.2);
    return sortedCentralities[top20Index] || 0;
  }, [centralityMetrics]);

  // Helper function: Create text sprite for node labels
  const createTextSprite = useCallback((text: string, color: string, fontSize: number = 14) => {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    if (!context) return null;

    // Set canvas size for high resolution
    const scale = 2;
    canvas.width = 256 * scale;
    canvas.height = 64 * scale;
    context.scale(scale, scale);

    // Text styling
    context.font = `bold ${fontSize}px Arial, sans-serif`;
    context.fillStyle = color;
    context.textAlign = 'center';
    context.textBaseline = 'middle';

    // Background for readability
    const textWidth = context.measureText(text).width;
    const padding = 8;
    const bgX = (canvas.width / scale - textWidth) / 2 - padding;
    const bgWidth = textWidth + padding * 2;

    context.fillStyle = 'rgba(13, 17, 23, 0.85)';
    context.roundRect(bgX, 12, bgWidth, 40, 4);
    context.fill();

    // Draw text
    context.fillStyle = color;
    context.fillText(text, canvas.width / scale / 2, canvas.height / scale / 2);

    // Create sprite
    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;

    const spriteMaterial = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false,
    });

    const sprite = new THREE.Sprite(spriteMaterial);
    sprite.scale.set(40, 10, 1);

    return sprite;
  }, []);

  // Build highlighted sets for O(1) lookup
  const highlightedNodeSet = useMemo(() => new Set(highlightedNodes), [highlightedNodes]);
  const highlightedEdgeSet = useMemo(() => new Set(highlightedEdges), [highlightedEdges]);

  // Build node -> cluster mapping for edge coloring
  const nodeClusterMap = useMemo(() => {
    const map = new Map<string, number>();
    nodes.forEach(node => {
      const clusterId = (node.properties as { cluster_id?: number })?.cluster_id;
      if (clusterId !== undefined) {
        map.set(node.id, clusterId);
      }
    });
    return map;
  }, [nodes]);

  // Helper function: Convert hex to rgba
  const hexToRgba = useCallback((hex: string, alpha: number): string => {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }, []);

  // Helper function: Blend two hex colors
  const blendColors = useCallback((color1: string, color2: string, ratio: number = 0.5): string => {
    const r1 = parseInt(color1.slice(1, 3), 16);
    const g1 = parseInt(color1.slice(3, 5), 16);
    const b1 = parseInt(color1.slice(5, 7), 16);
    const r2 = parseInt(color2.slice(1, 3), 16);
    const g2 = parseInt(color2.slice(3, 5), 16);
    const b2 = parseInt(color2.slice(5, 7), 16);

    const r = Math.round(r1 * (1 - ratio) + r2 * ratio);
    const g = Math.round(g1 * (1 - ratio) + g2 * ratio);
    const b = Math.round(b1 * (1 - ratio) + b2 * ratio);

    return `rgba(${r}, ${g}, ${b}, 0.35)`;
  }, []);

  // UI-010 FIX: Separate base graph data from styling to prevent simulation reset
  // KEY INSIGHT: ForceGraph3D resets physics when graphData reference changes
  // Solution: Keep graphData stable, apply styles through separate maps
  const baseGraphData = useMemo<ForceGraphData>(() => {
    const forceNodes: ForceGraphNode[] = nodes.map(node => {
      const clusterId = (node.properties as { cluster_id?: number })?.cluster_id;
      const centrality = centralityMap.get(node.id) || 0;
      const isBridge = (node.properties as { is_gap_bridge?: boolean })?.is_gap_bridge || false;

      // Base color (NO highlight logic here - handled in nodeStyleMap)
      let color: string;
      if (clusterId !== undefined && clusterColorMap.has(clusterId)) {
        color = clusterColorMap.get(clusterId)!;
      } else {
        color = ENTITY_TYPE_COLORS[node.entity_type] || '#888888';
      }

      // Size based on centrality (sqrt for visual balance)
      const baseSize = 3;
      const centralityBoost = Math.sqrt(centrality * 100) * 2;
      const bridgeBoost = isBridge ? 2 : 0;
      const nodeSize = baseSize + centralityBoost + bridgeBoost;

      // UI-010 FIX: Restore position from ref if available
      const savedPosition = nodePositionsRef.current.get(node.id);

      const forceNode: ForceGraphNode = {
        id: node.id,
        name: node.name,
        val: nodeSize,
        color,
        entityType: node.entity_type,
        clusterId,
        centrality,
        isHighlighted: false, // Always false here - use nodeStyleMap for actual state
        isBridge,
        properties: node.properties,
      };

      // Restore saved positions to prevent simulation restart
      if (savedPosition) {
        forceNode.x = savedPosition.x;
        forceNode.y = savedPosition.y;
        forceNode.z = savedPosition.z;
        // Restore pinned positions (fx, fy, fz) if they were set
        if (savedPosition.fx !== undefined) forceNode.fx = savedPosition.fx;
        if (savedPosition.fy !== undefined) forceNode.fy = savedPosition.fy;
        if (savedPosition.fz !== undefined) forceNode.fz = savedPosition.fz;
      }

      return forceNode;
    });

    const forceLinks: ForceGraphLink[] = edges.map(edge => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      weight: edge.weight || 1,
      relationshipType: edge.relationship_type,
      isHighlighted: false, // Always false here - use edgeStyleMap for actual state
      isGhost: false,
    }));

    // Add ghost edges (potential edges) if enabled
    if (showGhostEdges && potentialEdges.length > 0) {
      const ghostLinks: ForceGraphLink[] = potentialEdges.map((pe, index) => ({
        id: `ghost-${pe.source_id}-${pe.target_id}-${index}`,
        source: pe.source_id,
        target: pe.target_id,
        weight: pe.similarity,
        relationshipType: 'POTENTIAL',
        isHighlighted: true,  // Ghost edges are always highlighted
        isGhost: true,
        similarity: pe.similarity,
      }));
      forceLinks.push(...ghostLinks);
    }

    return { nodes: forceNodes, links: forceLinks };
  }, [nodes, edges, clusterColorMap, centralityMap, showGhostEdges, potentialEdges]);
  // ⚠️ CRITICAL: highlightedNodeSet and highlightedEdgeSet REMOVED from dependencies!

  // UI-010 FIX: Separate style maps for highlighting (changes without triggering graph rebuild)
  const nodeStyleMap = useMemo(() => {
    const styleMap = new Map<string, { isHighlighted: boolean; baseColor: string }>();
    // Pre-populate with all nodes to ensure consistent lookup
    baseGraphData.nodes.forEach(node => {
      styleMap.set(node.id, {
        isHighlighted: highlightedNodeSet.has(node.id),
        baseColor: node.color,
      });
    });
    return styleMap;
  }, [baseGraphData.nodes, highlightedNodeSet]);

  const edgeStyleMap = useMemo(() => {
    const styleMap = new Map<string, { isHighlighted: boolean }>();
    baseGraphData.links.forEach(link => {
      styleMap.set(link.id, {
        isHighlighted: highlightedEdgeSet.has(link.id) || link.isGhost === true,
      });
    });
    return styleMap;
  }, [baseGraphData.links, highlightedEdgeSet]);

  // Backward compatibility: graphData reference for ForceGraph3D
  // This is now stable - only changes when nodes/edges/clusters change, NOT when highlights change
  const graphData = baseGraphData;

  // UI-010 FIX: Save node positions periodically to preserve across re-renders
  useEffect(() => {
    const savePositions = () => {
      if (fgRef.current) {
        const currentNodes = fgRef.current.graphData()?.nodes;
        if (currentNodes) {
          currentNodes.forEach((node: ForceGraphNode) => {
            if (node.x !== undefined && node.y !== undefined && node.z !== undefined) {
              nodePositionsRef.current.set(node.id, {
                x: node.x,
                y: node.y,
                z: node.z,
                fx: node.fx,
                fy: node.fy,
                fz: node.fz,
              });
            }
          });
        }
      }
    };

    // Save positions every 500ms while simulation is running
    const intervalId = setInterval(savePositions, 500);
    return () => clearInterval(intervalId);
  }, []);

  // Custom node rendering with glow effect and bloom support
  // UI-010 FIX: Uses nodeStyleMap instead of node.isHighlighted to prevent stale renders
  const nodeThreeObject = useCallback((nodeData: unknown) => {
    const node = nodeData as ForceGraphNode;
    const group = new THREE.Group();
    const nodeSize = node.val || 5;

    // UI-010 FIX: Get highlight state from style map, not from node object
    const nodeStyle = nodeStyleMap.get(node.id);
    const isHighlighted = nodeStyle?.isHighlighted || false;
    const displayColor = isHighlighted ? '#FFD700' : (node.color || '#888888');

    // Calculate emissive intensity based on bloom settings
    let emissiveIntensity = isHighlighted ? 0.6 : 0.2;
    if (bloomEnabled) {
      // Boost emissive intensity when bloom is enabled
      emissiveIntensity = isHighlighted
        ? 0.4 + bloomIntensity * 0.6
        : 0.15 + bloomIntensity * 0.45;
    }

    // Main sphere
    const geometry = new THREE.SphereGeometry(nodeSize, 16, 16);
    const material = new THREE.MeshPhongMaterial({
      color: displayColor,
      emissive: displayColor,
      emissiveIntensity,
      transparent: true,
      opacity: isHighlighted || hoveredNode === node.id ? 1 : 0.85,
      shininess: bloomEnabled ? 50 : 30,
    });
    const sphere = new THREE.Mesh(geometry, material);
    group.add(sphere);

    // Bloom outer glow sphere (always show when bloom is enabled)
    if (bloomEnabled) {
      const glowGeometry = new THREE.SphereGeometry(nodeSize * glowSize, 16, 16);
      const glowOpacity = 0.08 + bloomIntensity * 0.12;
      const glowMaterial = new THREE.MeshBasicMaterial({
        color: displayColor,
        transparent: true,
        opacity: glowOpacity,
      });
      const glow = new THREE.Mesh(glowGeometry, glowMaterial);
      group.add(glow);
    }

    // Bridge nodes: additional gold glow
    if (node.isBridge) {
      const bridgeGlowSize = bloomEnabled ? nodeSize * glowSize * 1.2 : nodeSize * 1.4;
      const bridgeOpacity = bloomEnabled ? 0.15 + bloomIntensity * 0.15 : 0.2;
      const bridgeGlowGeometry = new THREE.SphereGeometry(bridgeGlowSize, 16, 16);
      const bridgeGlowMaterial = new THREE.MeshBasicMaterial({
        color: '#FFD700',
        transparent: true,
        opacity: bridgeOpacity,
      });
      const bridgeGlow = new THREE.Mesh(bridgeGlowGeometry, bridgeGlowMaterial);
      group.add(bridgeGlow);
    }

    // Highlight ring for selected nodes
    if (isHighlighted) {
      const ringSize = bloomEnabled ? nodeSize * glowSize * 0.95 : nodeSize * 1.3;
      const ringGeometry = new THREE.RingGeometry(ringSize, ringSize + nodeSize * 0.2, 32);
      const ringOpacity = bloomEnabled ? 0.4 + bloomIntensity * 0.3 : 0.6;
      const ringMaterial = new THREE.MeshBasicMaterial({
        color: '#FFD700',
        transparent: true,
        opacity: ringOpacity,
        side: THREE.DoubleSide,
      });
      const ring = new THREE.Mesh(ringGeometry, ringMaterial);
      ring.rotation.x = Math.PI / 2;
      group.add(ring);
    }

    // UI-009 FIX: InfraNodus-style labels
    // Show labels based on node SIZE (which reflects centrality), not centrality threshold
    // This ensures labels show even when centralityMetrics is empty or IDs don't match
    const nodeSizeThreshold = 4;  // Show labels for nodes larger than this
    const shouldShowLabel = nodeSize >= nodeSizeThreshold && node.name;

    if (shouldShowLabel) {
      // Truncate long names
      const maxLabelLength = 15;
      const displayName = node.name.length > maxLabelLength
        ? node.name.substring(0, maxLabelLength - 2) + '..'
        : node.name;

      // Scale font size by node size (InfraNodus style: bigger nodes = bigger labels)
      const minFontSize = 10;
      const maxFontSize = 24;
      const sizeNormalized = Math.min(1, (nodeSize - nodeSizeThreshold) / 10);
      const fontSize = Math.round(minFontSize + (maxFontSize - minFontSize) * sizeNormalized);

      // InfraNodus style: Label color matches cluster color
      // Highlighted nodes get gold, otherwise use node's cluster color
      const labelColor = isHighlighted ? '#FFD700' : (node.color || '#FFFFFF');
      const labelSprite = createTextSprite(displayName, labelColor, fontSize);

      if (labelSprite) {
        // Position label above the node - scale position with font size
        const labelOffset = nodeSize + 4 + (fontSize - minFontSize) * 0.2;
        labelSprite.position.set(0, labelOffset, 0);
        group.add(labelSprite);
      }
    }

    return group;
  }, [nodeStyleMap, hoveredNode, bloomEnabled, bloomIntensity, glowSize, createTextSprite]);

  // Link width based on weight
  // UI-010 FIX: Uses edgeStyleMap for highlight state
  const linkWidth = useCallback((linkData: unknown) => {
    const link = linkData as ForceGraphLink;
    if (link.isGhost) {
      // Ghost edges are thinner with dashed appearance feel
      return 1.5;
    }
    const baseWidth = Math.max(0.3, (link.weight || 1) * 0.5);
    // Get highlight state from style map
    const edgeStyle = edgeStyleMap.get(link.id);
    const isHighlighted = edgeStyle?.isHighlighted || false;
    return isHighlighted ? baseWidth * 2 : baseWidth;
  }, [edgeStyleMap]);

  // Link color - Cluster-based coloring (InfraNodus-style)
  // UI-010 FIX: Uses edgeStyleMap for highlight state
  const linkColor = useCallback((linkData: unknown) => {
    const link = linkData as ForceGraphLink;

    // Ghost edges: amber/orange with transparency based on similarity
    if (link.isGhost) {
      const alpha = 0.4 + (link.similarity || 0.5) * 0.4;
      return `rgba(255, 170, 0, ${alpha})`;
    }

    // UI-010 FIX: Get highlight state from style map
    const edgeStyle = edgeStyleMap.get(link.id);
    const isHighlighted = edgeStyle?.isHighlighted || false;

    // Highlighted edges: gold
    if (isHighlighted) {
      return 'rgba(255, 215, 0, 0.8)';
    }

    // Get source and target node IDs
    const sourceId = typeof link.source === 'string' ? link.source : (link.source as ForceGraphNode).id;
    const targetId = typeof link.target === 'string' ? link.target : (link.target as ForceGraphNode).id;

    // Get cluster IDs for source and target
    const sourceCluster = nodeClusterMap.get(sourceId);
    const targetCluster = nodeClusterMap.get(targetId);

    // Same cluster: use cluster color with low opacity
    if (sourceCluster !== undefined && sourceCluster === targetCluster) {
      const clusterColor = clusterColorMap.get(sourceCluster);
      if (clusterColor) {
        return hexToRgba(clusterColor, 0.35);
      }
    }

    // Cross-cluster: blend colors if both have cluster assignments
    if (sourceCluster !== undefined && targetCluster !== undefined && sourceCluster !== targetCluster) {
      const sourceColor = clusterColorMap.get(sourceCluster);
      const targetColor = clusterColorMap.get(targetCluster);
      if (sourceColor && targetColor) {
        return blendColors(sourceColor, targetColor, 0.5);
      }
    }

    // Default: white with low opacity
    return 'rgba(255, 255, 255, 0.15)';
  }, [edgeStyleMap, nodeClusterMap, clusterColorMap, hexToRgba, blendColors]);

  // Custom link rendering for ghost edges (dashed lines)
  const linkThreeObject = useCallback((linkData: unknown) => {
    const link = linkData as ForceGraphLink;

    if (!link.isGhost) {
      return null; // Use default rendering for regular edges
    }

    // Create dashed line for ghost edges
    const geometry = new THREE.BufferGeometry();
    const material = new THREE.LineDashedMaterial({
      color: 0xffaa00,
      dashSize: 3,
      gapSize: 2,
      opacity: 0.6,
      transparent: true,
    });

    const line = new THREE.Line(geometry, material);
    line.computeLineDistances();

    return line;
  }, []);

  // Update ghost edge positions
  const linkPositionUpdate = useCallback((line: THREE.Object3D, coords: { start: { x: number; y: number; z: number }; end: { x: number; y: number; z: number } }, linkData: unknown) => {
    const link = linkData as ForceGraphLink;

    if (link.isGhost && line instanceof THREE.Line) {
      const positions = new Float32Array([
        coords.start.x, coords.start.y, coords.start.z,
        coords.end.x, coords.end.y, coords.end.z
      ]);
      line.geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      line.computeLineDistances();
      return true;
    }
    return false;
  }, []);

  // Focus camera on node helper function
  const focusCameraOnNode = useCallback((node: ForceGraphNode) => {
    if (fgRef.current && node.x !== undefined && node.y !== undefined && node.z !== undefined) {
      const distance = 200;
      fgRef.current.cameraPosition(
        { x: node.x, y: node.y, z: node.z + distance },
        { x: node.x, y: node.y, z: node.z },
        1000
      );
    }
  }, []);

  // Node click handler - selects node, double-click focuses camera
  const handleNodeClick = useCallback((nodeData: unknown) => {
    const node = nodeData as ForceGraphNode;
    const now = Date.now();

    // Check for double-click
    if (
      lastClickRef.current &&
      lastClickRef.current.nodeId === node.id &&
      now - lastClickRef.current.timestamp < DOUBLE_CLICK_THRESHOLD
    ) {
      // Double-click detected - focus camera on node AND unpin it
      focusCameraOnNode(node);
      // UI-010: Unpin node on double-click (allows user to release pinned nodes)
      node.fx = undefined;
      node.fy = undefined;
      node.fz = undefined;
      lastClickRef.current = null; // Reset after double-click
      return;
    }

    // Single click - update last click reference and trigger selection
    lastClickRef.current = { nodeId: node.id, timestamp: now };

    if (onNodeClick) {
      const originalNode = nodes.find(n => n.id === node.id);
      if (originalNode) {
        onNodeClick(originalNode);
      }
    }
    // Note: Camera focus only happens on double-click for stable UX
  }, [nodes, onNodeClick, focusCameraOnNode]);

  // Node right-click handler - alternative way to focus camera on node
  const handleNodeRightClick = useCallback((nodeData: unknown) => {
    const node = nodeData as ForceGraphNode;
    focusCameraOnNode(node);
  }, [focusCameraOnNode]);

  // Node hover handler
  const handleNodeHover = useCallback((nodeData: unknown) => {
    const node = nodeData as ForceGraphNode | null;
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

  // UI-011: Edge click handler for Relationship Evidence modal
  const handleEdgeClick = useCallback((linkData: unknown) => {
    const link = linkData as ForceGraphLink;
    if (!onEdgeClick || link.isGhost) return; // Don't trigger for ghost edges

    // Find the original edge
    const originalEdge = edges.find(e => e.id === link.id);
    if (originalEdge) {
      onEdgeClick(originalEdge);
    }
  }, [edges, onEdgeClick]);

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
        // UI-010 FIX: Explicit node ID prop for stable tracking
        nodeId="id"
        nodeThreeObject={nodeThreeObject}
        nodeLabel={(nodeData: unknown) => {
          const node = nodeData as ForceGraphNode;
          return `
            <div style="background: rgba(0,0,0,0.8); padding: 8px 12px; border-radius: 4px; font-family: monospace; font-size: 12px;">
              <div style="font-weight: bold; color: ${node.color || '#888'};">${node.name || 'Unknown'}</div>
              <div style="color: #888; margin-top: 4px;">${node.entityType || 'Entity'}</div>
              ${node.centrality ? `<div style="color: #4ECDC4; margin-top: 2px;">Centrality: ${(node.centrality * 100).toFixed(1)}%</div>` : ''}
              ${node.isBridge ? '<div style="color: #FFD700; margin-top: 2px;">Bridge Node</div>' : ''}
            </div>
          `;
        }}
        linkWidth={linkWidth}
        linkColor={linkColor}
        linkOpacity={0.6}
        linkThreeObject={linkThreeObject as never}
        linkPositionUpdate={linkPositionUpdate as never}
        linkDirectionalParticles={showParticles ? 2 : 0}
        linkDirectionalParticleSpeed={particleSpeed}
        linkDirectionalParticleWidth={1.5}
        linkDirectionalParticleColor={() => '#FFD700'}
        backgroundColor="#0d1117"
        onNodeClick={handleNodeClick}
        onNodeRightClick={handleNodeRightClick}  // Right-click also focuses camera on node
        onNodeHover={handleNodeHover}
        onBackgroundClick={handleBackgroundClick}
        // UI-011: Edge click handler for Relationship Evidence modal
        onLinkClick={handleEdgeClick}
        // UI-010 COMPREHENSIVE FIX: Drag handlers with proper simulation control
        // Key insight: The node object must have fx/fy/fz set to prevent physics from moving it
        onNodeDrag={(node) => {
          // Pin node to cursor position during drag
          // This is crucial - fx/fy/fz tells the physics engine "don't touch this node"
          node.fx = node.x;
          node.fy = node.y;
          node.fz = node.z;
          // Save to ref for persistence across re-renders
          const nodeId = String(node.id);
          if (nodeId && node.x !== undefined && node.y !== undefined && node.z !== undefined) {
            nodePositionsRef.current.set(nodeId, {
              x: node.x,
              y: node.y,
              z: node.z,
              fx: node.fx,
              fy: node.fy,
              fz: node.fz,
            });
          }
        }}
        onNodeDragEnd={(node) => {
          // CRITICAL: Keep node pinned after drag - this prevents snap-back!
          // Setting fx/fy/fz to current position locks the node in place
          node.fx = node.x;
          node.fy = node.y;
          node.fz = node.z;
          // Save final position to ref for persistence
          const nodeId = String(node.id);
          if (nodeId && node.x !== undefined && node.y !== undefined && node.z !== undefined) {
            nodePositionsRef.current.set(nodeId, {
              x: node.x,
              y: node.y,
              z: node.z,
              fx: node.fx,
              fy: node.fy,
              fz: node.fz,
            });
          }
        }}
        // UI-010 ENHANCED: Force simulation parameters for smooth, stable interaction
        // Problem: Nodes vibrate rapidly, rubber-banding effect, struggling to settle
        // Solution: HIGH damping + MODERATE cooling = stable without being sluggish
        //
        // UI-010 FIX: Use isInitialRenderRef to determine warmup/cooldown behavior
        // - Initial render: More warmup for stable layout
        // - Subsequent renders: Minimal warmup to prevent simulation restart
        warmupTicks={isInitialRenderRef.current ? 50 : 0}
        cooldownTicks={isInitialRenderRef.current ? 200 : 50}
        d3AlphaDecay={0.02}         // Slower cooldown (0.02 instead of 0.05) for smoother settling
        d3VelocityDecay={0.9}       // Very high damping (0.9 = strong friction, kills oscillation)
        d3AlphaMin={0.001}          // Lower threshold for finer settling
        // CRITICAL: Disable auto-refresh of simulation when data changes
        // This prevents the "explosion" effect when highlighting changes
        enableNodeDrag={true}
        onEngineStop={() => {
          // Mark initial render as complete
          isInitialRenderRef.current = false;
          // Save all positions when simulation stops
          if (fgRef.current) {
            const currentNodes = fgRef.current.graphData()?.nodes;
            if (currentNodes) {
              currentNodes.forEach((n: ForceGraphNode) => {
                if (n.x !== undefined && n.y !== undefined && n.z !== undefined) {
                  nodePositionsRef.current.set(n.id, {
                    x: n.x, y: n.y, z: n.z,
                    fx: n.fx, fy: n.fy, fz: n.fz,
                  });
                }
              });
            }
          }
        }}
      />
    </div>
  );
});

Graph3D.displayName = 'Graph3D';

export default Graph3D;
