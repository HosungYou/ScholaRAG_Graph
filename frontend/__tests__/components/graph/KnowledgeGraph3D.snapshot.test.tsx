export {};

import React from 'react';
import { render } from '@testing-library/react';
import { KnowledgeGraph3D } from '@/components/graph/KnowledgeGraph3D';
import type { ConceptCluster, CentralityMetrics, GraphData, StructuralGap } from '@/types';

type StoreShape = ReturnType<typeof createGraphStoreState>;

let graphStoreState: StoreShape;
let graph3DStoreState: ReturnType<typeof createGraph3DStoreState>;

const createGraphStoreState = () => {
  const data: GraphData = {
    nodes: [
      { id: 'n1', entity_type: 'Concept', name: 'Trust', properties: { cluster_id: 0 } },
      { id: 'n2', entity_type: 'Method', name: 'Fine-tuning', properties: { cluster_id: 1 } },
    ],
    edges: [
      {
        id: 'e1',
        source: 'n1',
        target: 'n2',
        relationship_type: 'APPLIES_TO',
        weight: 0.82,
        properties: { confidence: 0.82 },
      },
    ],
  };

  const clusters: ConceptCluster[] = [
    {
      cluster_id: 0,
      concepts: ['n1'],
      concept_names: ['Trust'],
      size: 1,
      density: 0.4,
      label: 'Trust',
    },
    {
      cluster_id: 1,
      concepts: ['n2'],
      concept_names: ['Fine-tuning'],
      size: 1,
      density: 0.5,
      label: 'Method',
    },
  ];

  const centralityMetrics: CentralityMetrics[] = [
    {
      concept_id: 'n1',
      concept_name: 'Trust',
      degree_centrality: 0.3,
      betweenness_centrality: 0.4,
      pagerank: 0.2,
      cluster_id: 0,
    },
    {
      concept_id: 'n2',
      concept_name: 'Fine-tuning',
      degree_centrality: 0.5,
      betweenness_centrality: 0.6,
      pagerank: 0.3,
      cluster_id: 1,
    },
  ];

  const gaps: StructuralGap[] = [
    {
      id: 'gap-1',
      cluster_a_id: 0,
      cluster_b_id: 1,
      cluster_a_concepts: ['n1'],
      cluster_b_concepts: ['n2'],
      cluster_a_names: ['Trust'],
      cluster_b_names: ['Fine-tuning'],
      gap_strength: 0.72,
      bridge_candidates: ['n2'],
      research_questions: ['How can trust-oriented methods improve fine-tuning outcomes?'],
    },
  ];

  return {
    graphData: data,
    getFilteredData: jest.fn(() => data),
    fetchGraphData: jest.fn().mockResolvedValue(undefined),
    isLoading: false,
    error: null as string | null,
    gaps,
    clusters,
    centralityMetrics,
    isGapLoading: false,
    fetchGapAnalysis: jest.fn().mockResolvedValue(undefined),
    setHighlightedNodes: jest.fn(),
    setHighlightedEdges: jest.fn(),
    highlightedNodes: [] as string[],
    highlightedEdges: [] as string[],
    clearHighlights: jest.fn(),
    selectedGap: null as StructuralGap | null,
    setSelectedGap: jest.fn(),
    viewMode: '3d' as const,
    setViewMode: jest.fn(),
    filters: { entityTypes: ['Concept', 'Method'], yearRange: null as [number, number] | null, searchQuery: '' },
    pinnedNodes: [] as string[],
    addPinnedNode: jest.fn(),
    removePinnedNode: jest.fn(),
    clearPinnedNodes: jest.fn(),
  };
};

const createGraph3DStoreState = () => ({
  view3D: {
    mode: '3d' as const,
    backgroundColor: '#0d1117',
    lodEnabled: false,
    currentZoom: 1.0,
    bloom: {
      enabled: false,
      intensity: 0.5,
      glowSize: 1.3,
    },
    labelVisibility: 'important' as const,
  },
  centrality: new Map<string, number>(),
  fetchCentrality: jest.fn().mockResolvedValue(undefined),
  getVisiblePercentage: jest.fn(() => 1.0),
  toggleBloom: jest.fn(),
  cycleLabelVisibility: jest.fn(),
});

jest.mock('@/hooks/useGraphStore', () => ({
  useGraphStore: () => graphStoreState,
}));

jest.mock('@/hooks/useGraph3DStore', () => ({
  useGraph3DStore: () => graph3DStoreState,
  applyLOD: (nodes: unknown[]) => nodes,
}));

jest.mock('@/components/graph/Graph3D', () => ({
  Graph3D: React.forwardRef((_props: unknown, _ref) => <div data-testid="graph3d">Graph3D</div>),
}));

jest.mock('@/components/graph/GapPanel', () => ({
  GapPanel: () => <div data-testid="gap-panel">GapPanel</div>,
}));

jest.mock('@/components/ui/DraggablePanel', () => ({
  DraggablePanel: ({ children }: { children: React.ReactNode }) => <div data-testid="draggable">{children}</div>,
  DragHandle: () => <div data-testid="drag-handle" />,
}));

jest.mock('@/components/graph/CentralityPanel', () => ({
  CentralityPanel: () => <div data-testid="centrality-panel">CentralityPanel</div>,
}));

jest.mock('@/components/graph/ClusterPanel', () => ({
  ClusterPanel: () => <div data-testid="cluster-panel">ClusterPanel</div>,
}));

jest.mock('@/components/graph/GraphLegend', () => ({
  GraphLegend: () => <div data-testid="graph-legend">GraphLegend</div>,
}));

jest.mock('@/components/graph/StatusBar', () => ({
  StatusBar: () => <div data-testid="status-bar">StatusBar</div>,
}));

jest.mock('@/components/graph/NodeDetails', () => ({
  NodeDetails: () => <div data-testid="node-details">NodeDetails</div>,
}));

jest.mock('@/components/graph/InsightHUD', () => ({
  InsightHUD: () => <div data-testid="insight-hud">InsightHUD</div>,
}));

jest.mock('@/components/graph/MainTopicsPanel', () => ({
  MainTopicsPanel: () => <div data-testid="main-topics-panel">MainTopicsPanel</div>,
}));

jest.mock('@/components/graph/TopicViewMode', () => ({
  TopicViewMode: () => <div data-testid="topic-view">TopicViewMode</div>,
}));

jest.mock('@/components/graph/GapsViewMode', () => ({
  GapsViewMode: React.forwardRef((_props: unknown, _ref) => <div data-testid="gaps-view">GapsViewMode</div>),
}));

jest.mock('@/components/graph/TemporalView', () => ({
  TemporalView: () => <div data-testid="temporal-view">TemporalView</div>,
}));

jest.mock('@/components/graph/EdgeContextModal', () => ({
  EdgeContextModal: () => <div data-testid="edge-context-modal">EdgeContextModal</div>,
}));

jest.mock('@/components/graph/EntityTypeLegend', () => ({
  __esModule: true,
  default: () => <div data-testid="entity-type-legend">EntityTypeLegend</div>,
}));

jest.mock('lucide-react', () => {
  const React = require('react');
  const Icon = ({ className }: { className?: string }) => <svg data-testid="icon" className={className} />;
  return new Proxy({}, { get: () => Icon });
});

describe('KnowledgeGraph3D snapshots', () => {
  beforeEach(() => {
    graphStoreState = createGraphStoreState();
    graph3DStoreState = createGraph3DStoreState();
  });

  it('matches loading state snapshot', () => {
    graphStoreState.isLoading = true;

    const { container } = render(<KnowledgeGraph3D projectId="project-1" />);
    expect(container.firstChild).toMatchSnapshot();
  });

  it('matches error state snapshot', () => {
    graphStoreState.error = 'Graph API unavailable';

    const { container } = render(<KnowledgeGraph3D projectId="project-1" />);
    expect(container.firstChild).toMatchSnapshot();
  });

  it('matches 3D view shell snapshot', () => {
    const { container } = render(<KnowledgeGraph3D projectId="project-1" />);
    expect(container.firstChild).toMatchSnapshot();
  });
});
