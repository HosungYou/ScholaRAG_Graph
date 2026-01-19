/**
 * Level of Detail (LOD) Optimization for 3D Graph Visualization
 *
 * Implements zoom-based node visibility to improve performance with large graphs.
 * As the user zooms out, less important nodes (by centrality) are hidden.
 */

export interface LODConfig {
  thresholds: {
    full: number;     // Zoom level for showing all nodes (100%)
    high: number;     // Zoom level for showing 80% of nodes
    medium: number;   // Zoom level for showing 50% of nodes
    low: number;      // Zoom level for showing 30% of nodes
  };
  minNodeSize: number;      // Minimum node size to render
  fadeTransition: boolean;  // Whether to fade nodes in/out
  fadeDistance: number;     // Distance over which to fade
}

export const DEFAULT_LOD_CONFIG: LODConfig = {
  thresholds: {
    full: 1.0,
    high: 0.6,
    medium: 0.3,
    low: 0.1,
  },
  minNodeSize: 2,
  fadeTransition: true,
  fadeDistance: 0.1,
};

/**
 * Calculate the visible percentage of nodes based on zoom level.
 *
 * @param zoom - Current zoom level (0 = far, 1 = close)
 * @param config - LOD configuration
 * @returns Percentage of nodes to show (0-1)
 */
export function getVisiblePercentage(
  zoom: number,
  config: LODConfig = DEFAULT_LOD_CONFIG
): number {
  const { thresholds } = config;

  if (zoom >= thresholds.full) return 1.0;
  if (zoom >= thresholds.high) return 0.8;
  if (zoom >= thresholds.medium) return 0.5;
  if (zoom >= thresholds.low) return 0.3;
  return 0.2; // Minimum visibility
}

/**
 * Calculate node opacity based on zoom level and centrality.
 *
 * Higher centrality nodes stay visible longer when zooming out.
 *
 * @param zoom - Current zoom level
 * @param centrality - Node's centrality score (0-1)
 * @param config - LOD configuration
 * @returns Opacity value (0-1)
 */
export function getNodeOpacity(
  zoom: number,
  centrality: number,
  config: LODConfig = DEFAULT_LOD_CONFIG
): number {
  if (!config.fadeTransition) {
    return 1.0;
  }

  const visiblePercentage = getVisiblePercentage(zoom, config);

  // High centrality nodes always visible
  if (centrality >= visiblePercentage) {
    return 1.0;
  }

  // Calculate fade based on distance from visibility threshold
  const fadeStart = visiblePercentage - config.fadeDistance;
  if (centrality >= fadeStart) {
    const fadeProgress = (centrality - fadeStart) / config.fadeDistance;
    return Math.max(0.2, fadeProgress);
  }

  return 0; // Fully hidden
}

/**
 * Filter nodes by LOD based on centrality scores.
 *
 * @param nodes - Array of nodes
 * @param centrality - Map of node IDs to centrality scores
 * @param visiblePercentage - Percentage of nodes to show
 * @returns Filtered array of visible nodes
 */
export function applyLOD<T extends { id: string }>(
  nodes: T[],
  centrality: Map<string, number>,
  visiblePercentage: number
): T[] {
  if (visiblePercentage >= 1.0) return nodes;
  if (nodes.length === 0) return nodes;

  // Sort by centrality descending
  const sorted = [...nodes].sort((a, b) => {
    const aScore = centrality.get(a.id) || 0;
    const bScore = centrality.get(b.id) || 0;
    return bScore - aScore;
  });

  const visibleCount = Math.ceil(sorted.length * visiblePercentage);
  return sorted.slice(0, visibleCount);
}

/**
 * Filter edges by LOD - only keep edges where both endpoints are visible.
 *
 * @param edges - Array of edges
 * @param visibleNodeIds - Set of visible node IDs
 * @returns Filtered array of visible edges
 */
export function filterEdgesByLOD<T extends { source: string; target: string }>(
  edges: T[],
  visibleNodeIds: Set<string>
): T[] {
  return edges.filter(
    edge => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)
  );
}

/**
 * Calculate node size based on centrality and zoom level.
 *
 * @param baseSiz - Base node size
 * @param centrality - Node's centrality score
 * @param zoom - Current zoom level
 * @returns Adjusted node size
 */
export function getNodeSize(
  baseSize: number,
  centrality: number,
  zoom: number
): number {
  // Centrality boost: more central nodes are larger
  const centralityBoost = Math.sqrt(centrality * 100) * 2;

  // Zoom compensation: nodes appear smaller when zoomed out
  const zoomFactor = Math.max(0.5, Math.min(2, zoom));

  return (baseSize + centralityBoost) * zoomFactor;
}

/**
 * Calculate camera distance from graph center.
 *
 * @param camera - Three.js camera
 * @param graphCenter - Center point of the graph
 * @returns Distance from camera to graph center
 */
export function getCameraDistance(
  camera: { position: { x: number; y: number; z: number } },
  graphCenter: { x: number; y: number; z: number } = { x: 0, y: 0, z: 0 }
): number {
  const dx = camera.position.x - graphCenter.x;
  const dy = camera.position.y - graphCenter.y;
  const dz = camera.position.z - graphCenter.z;
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

/**
 * Normalize camera distance to zoom level.
 *
 * @param distance - Camera distance
 * @param minDistance - Minimum distance (full zoom)
 * @param maxDistance - Maximum distance (minimum zoom)
 * @returns Normalized zoom level (0-1)
 */
export function normalizeZoom(
  distance: number,
  minDistance: number = 100,
  maxDistance: number = 1000
): number {
  // Invert: closer = higher zoom
  const normalized = 1 - (distance - minDistance) / (maxDistance - minDistance);
  return Math.max(0, Math.min(1, normalized));
}

/**
 * Performance-optimized LOD state manager.
 *
 * Caches LOD calculations and only updates when zoom changes significantly.
 */
export class LODManager {
  private lastZoom: number = 1.0;
  private lastVisibleNodes: Set<string> = new Set();
  private zoomThreshold: number = 0.05; // Minimum zoom change to trigger update

  constructor(
    private config: LODConfig = DEFAULT_LOD_CONFIG,
    private centrality: Map<string, number> = new Map()
  ) {}

  setCentrality(centrality: Map<string, number>): void {
    this.centrality = centrality;
  }

  /**
   * Update LOD state if zoom has changed significantly.
   *
   * @param nodes - All nodes
   * @param zoom - Current zoom level
   * @returns Updated visible nodes, or null if no update needed
   */
  update<T extends { id: string }>(
    nodes: T[],
    zoom: number
  ): { nodes: T[]; changed: boolean } {
    // Skip if zoom hasn't changed enough
    if (Math.abs(zoom - this.lastZoom) < this.zoomThreshold) {
      const filteredNodes = nodes.filter(n => this.lastVisibleNodes.has(n.id));
      return { nodes: filteredNodes, changed: false };
    }

    // Calculate new visible nodes
    const visiblePercentage = getVisiblePercentage(zoom, this.config);
    const visibleNodes = applyLOD(nodes, this.centrality, visiblePercentage);

    // Update cache
    this.lastZoom = zoom;
    this.lastVisibleNodes = new Set(visibleNodes.map(n => n.id));

    return { nodes: visibleNodes, changed: true };
  }

  /**
   * Get node opacity for rendering.
   */
  getOpacity(nodeId: string, zoom: number): number {
    const centrality = this.centrality.get(nodeId) || 0;
    return getNodeOpacity(zoom, centrality, this.config);
  }

  /**
   * Check if a node should be visible at current zoom.
   */
  isVisible(nodeId: string): boolean {
    return this.lastVisibleNodes.has(nodeId);
  }

  /**
   * Reset LOD state.
   */
  reset(): void {
    this.lastZoom = 1.0;
    this.lastVisibleNodes.clear();
  }
}

/**
 * Hook-friendly LOD state interface.
 */
export interface LODState {
  visiblePercentage: number;
  visibleNodeIds: Set<string>;
  zoom: number;
}

/**
 * Create initial LOD state.
 */
export function createLODState(): LODState {
  return {
    visiblePercentage: 1.0,
    visibleNodeIds: new Set(),
    zoom: 1.0,
  };
}

/**
 * Update LOD state based on new zoom level.
 */
export function updateLODState<T extends { id: string }>(
  state: LODState,
  nodes: T[],
  centrality: Map<string, number>,
  zoom: number,
  config: LODConfig = DEFAULT_LOD_CONFIG
): LODState {
  const visiblePercentage = getVisiblePercentage(zoom, config);
  const visibleNodes = applyLOD(nodes, centrality, visiblePercentage);

  return {
    visiblePercentage,
    visibleNodeIds: new Set(visibleNodes.map(n => n.id)),
    zoom,
  };
}
