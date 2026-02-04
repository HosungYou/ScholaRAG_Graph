import { create } from 'zustand';
import { api } from '@/lib/api';
import type { CentralityMetrics } from '@/types';

/**
 * LOD (Level of Detail) configuration for zoom-based node visibility
 */
export interface LODConfig {
  thresholds: {
    full: number;     // Show all nodes
    high: number;     // Show 80% of nodes (by centrality)
    medium: number;   // Show 50% of nodes
    low: number;      // Show 30% of nodes
  };
}

const DEFAULT_LOD_CONFIG: LODConfig = {
  thresholds: {
    full: 1.0,
    high: 0.6,
    medium: 0.3,
    low: 0.1,
  },
};

/**
 * Slicing configuration for node removal
 */
export interface SlicingConfig {
  removeCount: number;
  metric: 'betweenness' | 'degree' | 'eigenvector';
  isActive: boolean;
}

/**
 * Bloom/Glow configuration
 */
export interface BloomConfig {
  enabled: boolean;
  intensity: number;      // 0.0 - 1.0
  glowSize: number;       // Outer glow sphere multiplier (1.0 - 2.0)
}

/**
 * Label visibility mode (InfraNodus-style adaptive labeling)
 */
export type LabelVisibility = 'none' | 'important' | 'all';

/**
 * 3D View state
 */
export interface View3DState {
  mode: '2d' | '3d';
  showParticles: boolean;
  particleSpeed: number;
  backgroundColor: string;
  lodEnabled: boolean;
  currentZoom: number;
  bloom: BloomConfig;
  labelVisibility: LabelVisibility;
}

interface Graph3DStore {
  // 3D View State
  view3D: View3DState;
  lodConfig: LODConfig;

  // Slicing State
  slicing: SlicingConfig;
  slicedNodeIds: string[];
  topBridges: Array<{ id: string; name: string; score: number }>;

  // Centrality State
  centrality: Map<string, number>;
  isCentralityLoading: boolean;

  // Cluster Visualization State
  clusterCount: number;
  optimalK: number;

  // Actions
  setViewMode: (mode: '2d' | '3d') => void;
  toggleParticles: () => void;
  setParticleSpeed: (speed: number) => void;
  setBackgroundColor: (color: string) => void;
  toggleLOD: () => void;
  setCurrentZoom: (zoom: number) => void;
  toggleBloom: () => void;
  setBloomIntensity: (intensity: number) => void;
  setGlowSize: (size: number) => void;
  // v0.8.0: Label visibility actions
  cycleLabelVisibility: () => void;
  setLabelVisibility: (mode: LabelVisibility) => void;

  // Slicing Actions
  setSliceCount: (count: number) => void;
  setSliceMetric: (metric: 'betweenness' | 'degree' | 'eigenvector') => void;
  applySlicing: (projectId: string) => Promise<void>;
  resetSlicing: () => void;

  // Centrality Actions
  fetchCentrality: (projectId: string) => Promise<void>;

  // Cluster Actions
  setClusterCount: (count: number) => void;
  setOptimalK: (k: number) => void;

  // LOD Utility
  getVisiblePercentage: () => number;
}

export const useGraph3DStore = create<Graph3DStore>((set, get) => ({
  // Initial 3D View State
  view3D: {
    mode: '3d',
    showParticles: true,
    particleSpeed: 0.005,
    backgroundColor: '#0d1117',
    lodEnabled: true,
    currentZoom: 1.0,
    bloom: {
      enabled: false,
      intensity: 0.5,
      glowSize: 1.3,
    },
    labelVisibility: 'important' as LabelVisibility,  // v0.8.0: Default to 'important'
  },
  lodConfig: DEFAULT_LOD_CONFIG,

  // Initial Slicing State
  slicing: {
    removeCount: 5,
    metric: 'betweenness',
    isActive: false,
  },
  slicedNodeIds: [],
  topBridges: [],

  // Initial Centrality State
  centrality: new Map(),
  isCentralityLoading: false,

  // Initial Cluster State
  clusterCount: 5,
  optimalK: 5,

  // View Actions
  setViewMode: (mode) => {
    set(state => ({
      view3D: { ...state.view3D, mode },
    }));
  },

  toggleParticles: () => {
    set(state => ({
      view3D: { ...state.view3D, showParticles: !state.view3D.showParticles },
    }));
  },

  setParticleSpeed: (speed) => {
    set(state => ({
      view3D: { ...state.view3D, particleSpeed: speed },
    }));
  },

  setBackgroundColor: (color) => {
    set(state => ({
      view3D: { ...state.view3D, backgroundColor: color },
    }));
  },

  toggleLOD: () => {
    set(state => ({
      view3D: { ...state.view3D, lodEnabled: !state.view3D.lodEnabled },
    }));
  },

  setCurrentZoom: (zoom) => {
    set(state => ({
      view3D: { ...state.view3D, currentZoom: zoom },
    }));
  },

  // Bloom Actions
  toggleBloom: () => {
    set(state => ({
      view3D: {
        ...state.view3D,
        bloom: { ...state.view3D.bloom, enabled: !state.view3D.bloom.enabled },
      },
    }));
  },

  setBloomIntensity: (intensity) => {
    set(state => ({
      view3D: {
        ...state.view3D,
        bloom: { ...state.view3D.bloom, intensity: Math.max(0, Math.min(1, intensity)) },
      },
    }));
  },

  setGlowSize: (size) => {
    set(state => ({
      view3D: {
        ...state.view3D,
        bloom: { ...state.view3D.bloom, glowSize: Math.max(1, Math.min(2, size)) },
      },
    }));
  },

  // v0.8.0: Label Visibility Actions
  cycleLabelVisibility: () => {
    set(state => {
      const currentMode = state.view3D.labelVisibility;
      // Cycle: none -> important -> all -> none
      const nextMode: LabelVisibility =
        currentMode === 'none' ? 'important' :
        currentMode === 'important' ? 'all' : 'none';
      return {
        view3D: { ...state.view3D, labelVisibility: nextMode },
      };
    });
  },

  setLabelVisibility: (mode) => {
    set(state => ({
      view3D: { ...state.view3D, labelVisibility: mode },
    }));
  },

  // Slicing Actions
  setSliceCount: (count) => {
    set(state => ({
      slicing: { ...state.slicing, removeCount: count },
    }));
  },

  setSliceMetric: (metric) => {
    set(state => ({
      slicing: { ...state.slicing, metric },
    }));
  },

  applySlicing: async (projectId: string) => {
    const { slicing } = get();
    try {
      const result = await api.sliceGraph(projectId, slicing.removeCount, slicing.metric);
      set({
        slicedNodeIds: result.removed_node_ids,
        topBridges: result.top_bridges || [],
        slicing: { ...slicing, isActive: true },
      });
    } catch (error) {
      console.error('Failed to apply slicing:', error);
    }
  },

  resetSlicing: () => {
    set(state => ({
      slicedNodeIds: [],
      slicing: { ...state.slicing, isActive: false },
    }));
  },

  // Centrality Actions
  fetchCentrality: async (projectId: string) => {
    set({ isCentralityLoading: true });
    try {
      const result = await api.getCentrality(projectId);
      const centralityMap = new Map<string, number>();
      Object.entries(result.centrality).forEach(([id, score]) => {
        centralityMap.set(id, score as number);
      });
      set({
        centrality: centralityMap,
        topBridges: result.top_bridges.map(([id, score]: [string, number]) => ({
          id,
          name: id,
          score,
        })),
        isCentralityLoading: false,
      });
    } catch (error) {
      console.error('Failed to fetch centrality:', error);
      set({ isCentralityLoading: false });
    }
  },

  // Cluster Actions
  setClusterCount: (count) => {
    set({ clusterCount: count });
  },

  setOptimalK: (k) => {
    set({ optimalK: k });
  },

  // LOD Utility
  getVisiblePercentage: () => {
    const { view3D, lodConfig } = get();
    if (!view3D.lodEnabled) return 1.0;

    const { thresholds } = lodConfig;
    const zoom = view3D.currentZoom;

    if (zoom >= thresholds.full) return 1.0;
    if (zoom >= thresholds.high) return 0.8;
    if (zoom >= thresholds.medium) return 0.5;
    return 0.3;
  },
}));

/**
 * Utility: Filter nodes by LOD based on centrality
 */
export function applyLOD<T extends { id: string }>(
  nodes: T[],
  centrality: Map<string, number>,
  visiblePercentage: number
): T[] {
  if (visiblePercentage >= 1.0) return nodes;

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
 * Utility: Get cluster center position
 */
export function getClusterCenter(
  nodes: Array<{ x?: number; y?: number; z?: number; clusterId?: number }>,
  clusterId: number
): { x: number; y: number; z: number } {
  const clusterNodes = nodes.filter(n => n.clusterId === clusterId);
  if (clusterNodes.length === 0) return { x: 0, y: 0, z: 0 };

  let sumX = 0, sumY = 0, sumZ = 0;
  clusterNodes.forEach(n => {
    sumX += n.x || 0;
    sumY += n.y || 0;
    sumZ += n.z || 0;
  });

  return {
    x: sumX / clusterNodes.length,
    y: sumY / clusterNodes.length,
    z: sumZ / clusterNodes.length,
  };
}
