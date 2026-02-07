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

// v0.10.0: Entity type shape mapping for visual differentiation
// Each type gets a distinct Three.js geometry for at-a-glance recognition
type EntityShape = 'sphere' | 'box' | 'octahedron' | 'cone' | 'dodecahedron' | 'cylinder' | 'torus' | 'tetrahedron';

const ENTITY_TYPE_SHAPES: Record<string, EntityShape> = {
  Concept: 'sphere',          // Default - round, fundamental
  Method: 'box',              // Structured, systematic
  Finding: 'octahedron',      // Diamond-like, valuable
  Problem: 'cone',            // Pointed, directional
  Innovation: 'dodecahedron', // Complex, multifaceted
  Limitation: 'tetrahedron',  // Simple, constrained
  Dataset: 'cylinder',        // Container-like
  Metric: 'torus',            // Measurement, cyclical
  Paper: 'sphere',            // Fallback
  Author: 'sphere',           // Fallback
};

// v0.9.0: InfraNodus-style labeling configuration
const LABEL_CONFIG = {
  minFontSize: 10,
  maxFontSize: 28,
  minOpacity: 0.3,
  maxOpacity: 1.0,
  alwaysVisiblePercentile: 0.8,  // Top 20% always show labels
  hoverRevealPercentile: 0.5,     // Top 50% on hover
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
  // Ghost Edge props (InfraNodus-style)
  showGhostEdges?: boolean;
  potentialEdges?: PotentialEdge[];
  // Bloom/Glow effect props
  bloomEnabled?: boolean;
  bloomIntensity?: number;
  glowSize?: number;
  // v0.7.0: Adaptive labeling props
  labelVisibility?: 'none' | 'important' | 'all';
  onLabelVisibilityChange?: (mode: 'none' | 'important' | 'all') => void;
  // v0.7.0: Node pinning props
  pinnedNodes?: string[];
  onNodePin?: (nodeId: string) => void;
  onNodeUnpin?: (nodeId: string) => void;
  onClearPinnedNodes?: () => void;
}

export interface Graph3DRef {
  focusOnNode: (nodeId: string) => void;
  focusOnCluster: (clusterId: number) => void;
  focusOnGap: (gap: StructuralGap) => void;
  resetCamera: () => void;
  getCamera: () => THREE.Camera | undefined;
  clearPinnedNodes: () => void;
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
  showGhostEdges = false,
  potentialEdges = [],
  bloomEnabled = false,
  bloomIntensity = 0.5,
  glowSize = 1.3,
  labelVisibility: labelVisibilityProp = 'important',
  onLabelVisibilityChange,
  pinnedNodes = [],
  onNodePin,
  onNodeUnpin,
  onClearPinnedNodes,
}, ref) => {
  const fgRef = useRef<any>(null);
  const textureCache = useRef(new Map<string, THREE.CanvasTexture>());
  // v0.14.1: nodeObjectCache removed — it cached grey nodes before cluster colors arrived
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // v0.11.0: Debounced hover to prevent jitter
  const hoveredNodeRef = useRef<string | null>(null);
  const hoverTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // v0.7.0: Adaptive labeling state
  const [labelVisibility, setLabelVisibility] = useState<'none' | 'important' | 'all'>('important');
  const [currentZoom, setCurrentZoom] = useState<number>(500);
  const currentZoomRef = useRef<number>(500);

  // v0.7.0: Calculate label threshold based on zoom level
  const calculateLabelThreshold = useCallback((zoomLevel: number): number => {
    // zoomLevel: 100 (close) to 800 (far)
    // Returns size threshold: higher = fewer labels shown
    if (zoomLevel < 200) return 2;      // Very close: show most labels
    if (zoomLevel < 350) return 4;      // Medium close: show important
    if (zoomLevel < 500) return 5;      // Medium: show main topics
    if (zoomLevel < 650) return 6;      // Far: show only major nodes
    return 8;                           // Very far: show only largest nodes
  }, []);

  // v0.7.0: Sync label visibility with external prop
  useEffect(() => {
    setLabelVisibility(labelVisibilityProp);
  }, [labelVisibilityProp]);

  // UI-010 FIX: Store node positions to persist across re-renders
  // This prevents the simulation from restarting when graphData is recreated
  const nodePositionsRef = useRef<Map<string, { x: number; y: number; z: number; fx?: number; fy?: number; fz?: number }>>(new Map());

  // UI-010 FIX: Track if this is the initial render
  const isInitialRenderRef = useRef(true);

  // Double-click detection state
  const lastClickRef = useRef<{ nodeId: string; timestamp: number } | null>(null);
  const DOUBLE_CLICK_THRESHOLD = 300; // ms

  // v0.8.0: Hash function for stable cluster color assignment
  // Using cluster_id ensures same cluster always gets same color across refreshes
  const hashClusterId = useCallback((clusterId: number): number => {
    let hash = 0;
    const str = `cluster_${clusterId}`;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash);
  }, []);

  // Build cluster color map with hash-based color assignment for stability
  const clusterColorMap = useMemo(() => {
    const colorMap = new Map<number, string>();
    clusters.forEach((cluster) => {
      // v0.8.0: Use hash-based color selection instead of array index
      // This ensures same cluster_id always gets same color regardless of array order
      const colorIndex = hashClusterId(cluster.cluster_id) % CLUSTER_COLORS.length;
      colorMap.set(cluster.cluster_id, CLUSTER_COLORS[colorIndex]);
    });
    return colorMap;
  }, [clusters, hashClusterId]);

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

  // v0.9.0: Centrality percentile map for InfraNodus-style labeling
  const centralityPercentileMap = useMemo(() => {
    const map = new Map<string, number>();
    if (centralityMetrics.length === 0) {
      // No centrality data - assign default percentile
      nodes.forEach(n => map.set(n.id, 0.5));
      return map;
    }
    const sorted = [...centralityMetrics].sort(
      (a, b) => a.betweenness_centrality - b.betweenness_centrality
    );
    sorted.forEach((m, i) => {
      map.set(m.concept_id, i / (sorted.length - 1 || 1));
    });
    return map;
  }, [centralityMetrics, nodes]);

  // Helper function: Create text sprite for node labels (InfraNodus-style)
  const createTextSprite = useCallback((text: string, color: string, fontSize: number = 14, opacity: number = 1.0) => {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    if (!context) return null;

    // Set canvas size for high resolution
    const scale = 2;
    canvas.width = 256 * scale;
    canvas.height = 64 * scale;
    context.scale(scale, scale);

    // v0.9.0: Text styling with shadow (no background box - InfraNodus style)
    context.font = `bold ${fontSize}px Arial, sans-serif`;

    // Shadow for readability (instead of background box)
    context.shadowColor = 'rgba(0, 0, 0, 0.9)';
    context.shadowBlur = 6;
    context.shadowOffsetX = 1;
    context.shadowOffsetY = 2;

    // Draw text with opacity
    context.fillStyle = color;
    context.globalAlpha = opacity;
    context.textAlign = 'center';
    context.textBaseline = 'middle';
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

  // v0.7.0: Pinned nodes set for O(1) lookup
  const pinnedNodeSet = useMemo(() => new Set(pinnedNodes), [pinnedNodes]);

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
    const styleMap = new Map<string, { isHighlighted: boolean; isPinned: boolean; baseColor: string }>();
    // Pre-populate with all nodes to ensure consistent lookup
    baseGraphData.nodes.forEach(node => {
      styleMap.set(node.id, {
        isHighlighted: highlightedNodeSet.has(node.id),
        isPinned: pinnedNodeSet.has(node.id),
        baseColor: node.color,
      });
    });
    return styleMap;
  }, [baseGraphData.nodes, highlightedNodeSet, pinnedNodeSet]);

  const edgeStyleMap = useMemo(() => {
    const styleMap = new Map<string, { isHighlighted: boolean; isPinnedEdge: boolean }>();
    baseGraphData.links.forEach(link => {
      const sourceId = typeof link.source === 'string' ? link.source : (link.source as ForceGraphNode).id;
      const targetId = typeof link.target === 'string' ? link.target : (link.target as ForceGraphNode).id;

      // v0.7.0: Edge is pinned if both source and target are pinned
      const isPinnedEdge = pinnedNodeSet.has(sourceId) && pinnedNodeSet.has(targetId);

      styleMap.set(link.id, {
        isHighlighted: highlightedEdgeSet.has(link.id) || link.isGhost === true,
        isPinnedEdge,
      });
    });
    return styleMap;
  }, [baseGraphData.links, highlightedEdgeSet, pinnedNodeSet]);

  // Backward compatibility: graphData reference for ForceGraph3D
  // This is now stable - only changes when nodes/edges/clusters change, NOT when highlights change
  const graphData = baseGraphData;

  // UI-010 FIX: Save node positions periodically to preserve across re-renders
  useEffect(() => {
    const savePositions = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
        return;
      }
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

    // Save positions less aggressively to reduce CPU/memory pressure.
    const intervalId = setInterval(savePositions, 2000);
    return () => clearInterval(intervalId);
  }, []);

  // Custom node rendering with glow effect and bloom support
  // UI-010 FIX: Uses nodeStyleMap instead of node.isHighlighted to prevent stale renders
  const nodeThreeObject = useCallback((nodeData: unknown) => {
    const node = nodeData as ForceGraphNode;

    const group = new THREE.Group();
    group.userData.nodeId = node.id;
    const nodeSize = node.val || 5;

    // UI-010 FIX: Get highlight state from style map, not from node object
    const nodeStyle = nodeStyleMap.get(node.id);
    const isHighlighted = nodeStyle?.isHighlighted || false;
    const isPinned = nodeStyle?.isPinned || false;

    // v0.7.0: Color priority: highlighted > pinned > normal
    let displayColor: string;
    if (isHighlighted) {
      displayColor = '#FFD700'; // Gold for highlighted
    } else if (isPinned) {
      displayColor = '#00E5FF'; // Cyan for pinned
    } else {
      displayColor = node.color || '#888888';
    }

    // Calculate emissive intensity based on bloom settings
    let emissiveIntensity = isHighlighted ? 0.6 : 0.2;
    if (bloomEnabled) {
      // Boost emissive intensity when bloom is enabled
      emissiveIntensity = isHighlighted
        ? 0.4 + bloomIntensity * 0.6
        : 0.15 + bloomIntensity * 0.45;
    }

    // v0.10.0: Entity type-based geometry
    const entityShape = ENTITY_TYPE_SHAPES[node.entityType] || 'sphere';
    let geometry: THREE.BufferGeometry;

    switch (entityShape) {
      case 'box':
        geometry = new THREE.BoxGeometry(nodeSize * 1.6, nodeSize * 1.6, nodeSize * 1.6);
        break;
      case 'octahedron':
        geometry = new THREE.OctahedronGeometry(nodeSize * 1.1);
        break;
      case 'cone':
        geometry = new THREE.ConeGeometry(nodeSize, nodeSize * 2, 8);
        break;
      case 'dodecahedron':
        geometry = new THREE.DodecahedronGeometry(nodeSize * 1.1);
        break;
      case 'tetrahedron':
        geometry = new THREE.TetrahedronGeometry(nodeSize * 1.2);
        break;
      case 'cylinder':
        geometry = new THREE.CylinderGeometry(nodeSize * 0.8, nodeSize * 0.8, nodeSize * 1.6, 8);
        break;
      case 'torus':
        geometry = new THREE.TorusGeometry(nodeSize * 0.8, nodeSize * 0.35, 8, 16);
        break;
      default:
        geometry = new THREE.SphereGeometry(nodeSize, 16, 16);
    }

    const material = new THREE.MeshPhongMaterial({
      color: displayColor,
      emissive: displayColor,
      emissiveIntensity,
      transparent: true,
      opacity: isHighlighted ? 1 : 0.85,
      shininess: bloomEnabled ? 50 : 30,
    });
    const mainMesh = new THREE.Mesh(geometry, material);
    group.add(mainMesh);

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

    // v0.7.0: Pinned node indicator (cyan ring)
    if (isPinned && !isHighlighted) {
      const pinnedRingSize = bloomEnabled ? nodeSize * glowSize * 0.9 : nodeSize * 1.25;
      const pinnedRingGeometry = new THREE.RingGeometry(pinnedRingSize, pinnedRingSize + nodeSize * 0.15, 32);
      const pinnedRingMaterial = new THREE.MeshBasicMaterial({
        color: '#00E5FF',
        transparent: true,
        opacity: bloomEnabled ? 0.5 + bloomIntensity * 0.2 : 0.6,
        side: THREE.DoubleSide,
      });
      const pinnedRing = new THREE.Mesh(pinnedRingGeometry, pinnedRingMaterial);
      pinnedRing.rotation.x = Math.PI / 2;
      group.add(pinnedRing);
    }

    // v0.9.0: InfraNodus-style labeling based on centrality percentile
    const nodePercentile = centralityPercentileMap.get(node.id) || 0.3;
    const isTopPercentile = nodePercentile >= LABEL_CONFIG.alwaysVisiblePercentile;

    const shouldShowLabel = node.name && (
      labelVisibility === 'all' ||
      (labelVisibility === 'important' && (isTopPercentile || isHighlighted || isPinned || node.isBridge)) ||
      (labelVisibility === 'none' && (isHighlighted || isPinned))
    );

    if (shouldShowLabel) {
      // Truncate long names
      const maxLabelLength = 15;
      const displayName = node.name.length > maxLabelLength
        ? node.name.substring(0, maxLabelLength - 2) + '..'
        : node.name;

      // v0.9.0: Font size proportional to centrality percentile (InfraNodus style)
      const fontSize = Math.round(
        LABEL_CONFIG.minFontSize +
        (LABEL_CONFIG.maxFontSize - LABEL_CONFIG.minFontSize) * nodePercentile
      );

      // v0.9.0: Opacity proportional to centrality (highlighted/pinned override to 1.0)
      const labelOpacity = isHighlighted || isPinned ? 1.0 :
        LABEL_CONFIG.minOpacity +
        (LABEL_CONFIG.maxOpacity - LABEL_CONFIG.minOpacity) * nodePercentile;

      // InfraNodus style: Label color matches cluster color
      // Highlighted nodes get gold, pinned nodes get cyan
      const labelColor = isHighlighted ? '#FFD700' : isPinned ? '#00E5FF' : (node.color || '#FFFFFF');
      const labelSprite = createTextSprite(displayName, labelColor, fontSize, labelOpacity);

      if (labelSprite) {
        // Position label above the node - scale position with font size
        const labelOffset = nodeSize + 4 + (fontSize - LABEL_CONFIG.minFontSize) * 0.2;
        labelSprite.position.set(0, labelOffset, 0);
        group.add(labelSprite);
      }
    }

    return group;
  }, [bloomEnabled, bloomIntensity, glowSize, createTextSprite, labelVisibility, centralityPercentileMap]);
  // ⚠️ CRITICAL FIX: hoveredNode removed from dependencies to prevent full graph rebuild on hover
  // Hover effect is now handled via CSS cursor only (see container div style below)
  // v0.9.0: Replaced currentZoom/calculateLabelThreshold with centralityPercentileMap for InfraNodus-style labeling

  // v0.14.0: Update highlights without recreating node objects (prevents simulation reheat)
  useEffect(() => {
    if (!fgRef.current) return;
    const scene = fgRef.current.scene();
    if (!scene) return;

    scene.traverse((obj: THREE.Object3D) => {
      if (obj instanceof THREE.Mesh && obj.parent?.userData?.nodeId) {
        const nodeId = obj.parent.userData.nodeId;
        const style = nodeStyleMap.get(nodeId);
        if (!style) return;

        const mat = obj.material as THREE.MeshStandardMaterial;
        if (!mat || !mat.color) return;

        let targetColor: string;
        if (style.isHighlighted) {
          targetColor = '#FFD700';
        } else if (style.isPinned) {
          targetColor = '#00E5FF';
        } else {
          targetColor = style.baseColor || '#888888';
        }

        mat.color.set(targetColor);
        mat.emissive.set(targetColor);
        mat.emissiveIntensity = style.isHighlighted ? 0.6 : 0.2;
      }
    });
  }, [nodeStyleMap]);

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
    const isPinnedEdge = edgeStyle?.isPinnedEdge || false;

    // v0.7.0: Pinned edges are thicker
    if (isHighlighted) return baseWidth * 2;
    if (isPinnedEdge) return baseWidth * 1.5;
    return baseWidth;
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

    // v0.7.0: Pinned edges (between pinned nodes) - cyan
    if (edgeStyle?.isPinnedEdge) {
      return 'rgba(0, 229, 255, 0.7)';  // Cyan for pinned edges
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
  const handleNodeClick = useCallback((nodeData: unknown, event: MouseEvent) => {
    const node = nodeData as ForceGraphNode;
    const now = Date.now();

    // v0.7.0: Shift+click to toggle pin
    if (event.shiftKey) {
      if (pinnedNodeSet.has(node.id)) {
        onNodeUnpin?.(node.id);
      } else {
        onNodePin?.(node.id);
      }
      return; // Don't proceed with normal click behavior
    }

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
  }, [nodes, onNodeClick, focusCameraOnNode, pinnedNodeSet, onNodePin, onNodeUnpin]);

  // Node right-click handler - alternative way to focus camera on node
  const handleNodeRightClick = useCallback((nodeData: unknown) => {
    const node = nodeData as ForceGraphNode;
    focusCameraOnNode(node);
  }, [focusCameraOnNode]);

  // Node hover handler - v0.11.0: debounced to prevent jitter
  const handleNodeHover = useCallback((nodeData: unknown) => {
    const node = nodeData as ForceGraphNode | null;
    const newId = node?.id || null;

    // Only process if actually changed
    if (newId !== hoveredNodeRef.current) {
      hoveredNodeRef.current = newId;

      // Debounce the state update to prevent jitter
      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = setTimeout(() => {
        setHoveredNode(newId);
        if (onNodeHover) {
          if (node) {
            const originalNode = nodes.find(n => n.id === node.id);
            onNodeHover(originalNode || null);
          } else {
            onNodeHover(null);
          }
        }
      }, 50);
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
    clearPinnedNodes: () => {
      onClearPinnedNodes?.();
    },
  }), [graphData, onClearPinnedNodes]);

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

  // v0.7.0: Track camera zoom level for adaptive labels
  // v0.10.0: Bucket-based updates to prevent jitter (only update state on threshold change)
  useEffect(() => {
    if (!fgRef.current) return;

    const checkCameraDistance = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
        return;
      }
      const camera = fgRef.current?.camera();
      if (camera) {
        const distance = camera.position.length();
        // Only update React state when zoom crosses a 50-unit bucket boundary
        const bucket = Math.round(distance / 50) * 50;
        if (bucket !== currentZoomRef.current) {
          currentZoomRef.current = bucket;
          setCurrentZoom(bucket);
        }
      }
    };

    // Check periodically (controls event listener may not be accessible)
    const intervalId = setInterval(checkCameraDistance, 750);

    return () => clearInterval(intervalId);
  }, []);

  // Cleanup hover timeout on unmount
  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    };
  }, []);

  // v0.14.1: Hardened WebGL cleanup — try-catch prevents INVALID_OPERATION on context change
  useEffect(() => {
    return () => {
      // 1. Dispose all cached textures
      textureCache.current.forEach((texture) => {
        try { texture.dispose(); } catch { /* context changed */ }
      });
      textureCache.current.clear();

      // 2. Dispose scene resources
      if (fgRef.current) {
        try {
          const scene = fgRef.current.scene();
          if (scene) {
            scene.traverse((obj: THREE.Object3D) => {
              try {
                if (obj instanceof THREE.Mesh) {
                  obj.geometry?.dispose();
                  if (obj.material instanceof THREE.Material) {
                    (obj.material as any).map?.dispose();
                    obj.material.dispose();
                  } else if (Array.isArray(obj.material)) {
                    obj.material.forEach((m) => {
                      try { (m as any).map?.dispose(); m.dispose(); } catch { /* already disposed */ }
                    });
                  }
                }
                if (obj instanceof THREE.Sprite) {
                  obj.material.map?.dispose();
                  obj.material.dispose();
                }
              } catch { /* disposed or wrong context */ }
            });
          }
        } catch { /* scene unavailable */ }

        // 3. Renderer explicit disposal
        try {
          const renderer = fgRef.current.renderer();
          if (renderer) {
            renderer.dispose();
            renderer.forceContextLoss();
          }
        } catch { /* already disposed */ }
      }

      // 4. Clear position cache
      nodePositionsRef.current.clear();
    };
  }, []);

  return (
    <div
      className="w-full h-full bg-[#0d1117]"
      style={{ cursor: hoveredNode ? 'pointer' : 'default' }}
    >
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
          // v0.9.0: Release node to physics after drag (user can re-drag to reposition)
          node.fx = undefined;
          node.fy = undefined;
          node.fz = undefined;
          // Save position but don't pin
          const nodeId = String(node.id);
          if (nodeId && node.x !== undefined && node.y !== undefined && node.z !== undefined) {
            nodePositionsRef.current.set(nodeId, {
              x: node.x,
              y: node.y,
              z: node.z,
              fx: undefined,
              fy: undefined,
              fz: undefined,
            });
          }
        }}
        // UI-010 ENHANCED: Force simulation parameters for smooth, stable interaction
        // Problem: Nodes vibrate rapidly, rubber-banding effect, struggling to settle
        // Solution: HIGH damping + MODERATE cooling = stable without being sluggish
        //
        // v0.9.0: Physics parameters optimized for natural floating feel
        warmupTicks={50}
        cooldownTicks={200}            // Fast stabilization, freeze after
        d3AlphaDecay={0.0228}          // D3 default
        d3VelocityDecay={0.75}         // Strong damping, minimal drift
        d3AlphaMin={0.001}             // Lower threshold for finer settling
        // CRITICAL: Disable auto-refresh of simulation when data changes
        // This prevents the "explosion" effect when highlighting changes
        enableNodeDrag={true}
        onEngineStop={() => {
          // Mark initial render as complete
          isInitialRenderRef.current = false;
          // Freeze all nodes in place to prevent micro-drift
          if (fgRef.current) {
            const currentNodes = fgRef.current.graphData()?.nodes;
            if (currentNodes) {
              currentNodes.forEach((n: ForceGraphNode) => {
                if (n.x !== undefined && n.y !== undefined && n.z !== undefined) {
                  // Pin nodes at their final positions
                  n.fx = n.x;
                  n.fy = n.y;
                  n.fz = n.z;
                  nodePositionsRef.current.set(n.id, {
                    x: n.x, y: n.y, z: n.z,
                    fx: n.x, fy: n.y, fz: n.z,
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
