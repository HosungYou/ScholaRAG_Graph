import { create } from 'zustand';
import { api } from '@/lib/api';
import type {
  GraphData,
  GraphEntity,
  EntityType,
  StructuralGap,
  ConceptCluster,
  CentralityMetrics,
  GapAnalysisResult,
  PotentialEdge,
} from '@/types';

interface FilterState {
  entityTypes: EntityType[];
  yearRange: [number, number] | null;
  searchQuery: string;
}

interface GraphStore {
  // State
  graphData: GraphData | null;
  selectedNode: GraphEntity | null;
  highlightedNodes: string[];
  highlightedEdges: string[];
  isLoading: boolean;
  error: string | null;
  filters: FilterState;

  // Gap Detection State
  gaps: StructuralGap[];
  clusters: ConceptCluster[];
  centralityMetrics: CentralityMetrics[];
  isGapLoading: boolean;
  selectedGap: StructuralGap | null;

  // Ghost Edge State (InfraNodus-style)
  showGhostEdges: boolean;
  potentialEdges: PotentialEdge[];

  // Actions
  fetchGraphData: (projectId: string) => Promise<void>;
  setSelectedNode: (node: GraphEntity | null) => void;
  setHighlightedNodes: (nodeIds: string[]) => void;
  setHighlightedEdges: (edgeIds: string[]) => void;
  clearHighlights: () => void;
  expandNode: (nodeId: string) => Promise<void>;
  setFilters: (filters: Partial<FilterState>) => void;
  resetFilters: () => void;
  getFilteredData: () => GraphData | null;

  // Gap Detection Actions
  fetchGapAnalysis: (projectId: string) => Promise<void>;
  setSelectedGap: (gap: StructuralGap | null) => void;
  highlightGapConcepts: (gap: StructuralGap) => void;

  // Ghost Edge Actions
  toggleGhostEdges: () => void;
  setShowGhostEdges: (show: boolean) => void;
  getPotentialEdgesForGap: (gap: StructuralGap) => PotentialEdge[];
}

// Default filters (Hybrid Mode: Paper/Author + Concept-Centric)
const defaultFilters: FilterState = {
  entityTypes: [
    'Paper', 'Author',  // Hybrid Mode entities
    'Concept', 'Method', 'Finding',  // Primary concept-centric
    'Problem', 'Dataset', 'Metric', 'Innovation', 'Limitation'  // Secondary
  ] as EntityType[],
  yearRange: null,
  searchQuery: '',
};

export const useGraphStore = create<GraphStore>((set, get) => ({
  // Initial state
  graphData: null,
  selectedNode: null,
  highlightedNodes: [],
  highlightedEdges: [],
  isLoading: false,
  error: null,
  filters: { ...defaultFilters },

  // Gap Detection State
  gaps: [],
  clusters: [],
  centralityMetrics: [],
  isGapLoading: false,
  selectedGap: null,

  // Ghost Edge State
  showGhostEdges: false,
  potentialEdges: [],

  // Actions
  fetchGraphData: async (projectId: string) => {
    set({ isLoading: true, error: null });
    try {
      const data = await api.getVisualizationData(projectId);
      set({ graphData: data, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch graph data',
        isLoading: false,
      });
    }
  },

  setSelectedNode: (node) => {
    set({ selectedNode: node });
  },

  setHighlightedNodes: (nodeIds) => {
    set({ highlightedNodes: nodeIds });
  },

  setHighlightedEdges: (edgeIds) => {
    set({ highlightedEdges: edgeIds });
  },

  clearHighlights: () => {
    set({ highlightedNodes: [], highlightedEdges: [] });
  },

  expandNode: async (nodeId: string) => {
    const { graphData } = get();
    if (!graphData) return;

    try {
      const subgraph = await api.getSubgraph(nodeId, 1);

      // Merge subgraph with existing data
      const existingNodeIds = new Set(graphData.nodes.map((n) => n.id));
      const newNodes = subgraph.nodes.filter((n: GraphEntity) => !existingNodeIds.has(n.id));

      const existingEdgeIds = new Set(graphData.edges.map((e) => e.id));
      const newEdges = subgraph.edges.filter((e: { id: string }) => !existingEdgeIds.has(e.id));

      set({
        graphData: {
          nodes: [...graphData.nodes, ...newNodes],
          edges: [...graphData.edges, ...newEdges],
        },
      });
    } catch (error) {
      console.error('Failed to expand node:', error);
    }
  },

  setFilters: (newFilters) => {
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
    }));
  },

  resetFilters: () => {
    set({ filters: { ...defaultFilters } });
  },

  getFilteredData: () => {
    const { graphData, filters } = get();
    if (!graphData) return null;

    // Filter nodes
    const filteredNodes = graphData.nodes.filter((node) => {
      // Filter by entity type
      if (!filters.entityTypes.includes(node.entity_type)) {
        return false;
      }

      // Filter by year range (only for Papers)
      if (filters.yearRange && node.entity_type === 'Paper') {
        const year = (node.properties as { year?: number }).year;
        if (year && (year < filters.yearRange[0] || year > filters.yearRange[1])) {
          return false;
        }
      }

      // Filter by search query
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase();
        const nameMatch = node.name.toLowerCase().includes(query);
        const propsMatch = Object.values(node.properties || {}).some(
          (v) => typeof v === 'string' && v.toLowerCase().includes(query)
        );
        if (!nameMatch && !propsMatch) {
          return false;
        }
      }

      return true;
    });

    // Get IDs of filtered nodes
    const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));

    // Filter edges to only include those connecting filtered nodes
    const filteredEdges = graphData.edges.filter(
      (edge) => filteredNodeIds.has(edge.source) && filteredNodeIds.has(edge.target)
    );

    return { nodes: filteredNodes, edges: filteredEdges };
  },

  // Gap Detection Actions
  fetchGapAnalysis: async (projectId: string) => {
    set({ isGapLoading: true });
    try {
      const analysis = await api.getGapAnalysis(projectId);
      set({
        gaps: analysis.gaps,
        clusters: analysis.clusters,
        centralityMetrics: analysis.centrality_metrics,
        isGapLoading: false,
      });
    } catch (error) {
      console.error('Failed to fetch gap analysis:', error);
      set({ isGapLoading: false });
    }
  },

  setSelectedGap: (gap) => {
    set({ selectedGap: gap });
  },

  highlightGapConcepts: (gap) => {
    // Highlight all concepts in the gap
    const allConceptIds = [
      ...gap.cluster_a_concepts,
      ...gap.cluster_b_concepts,
      ...gap.bridge_candidates,
    ];
    set({
      highlightedNodes: allConceptIds,
      selectedGap: gap,
      // Also set potential edges for the selected gap
      potentialEdges: gap.potential_edges || [],
    });
  },

  // Ghost Edge Actions
  toggleGhostEdges: () => {
    set((state) => ({ showGhostEdges: !state.showGhostEdges }));
  },

  setShowGhostEdges: (show) => {
    set({ showGhostEdges: show });
  },

  getPotentialEdgesForGap: (gap) => {
    return gap.potential_edges || [];
  },
}));
