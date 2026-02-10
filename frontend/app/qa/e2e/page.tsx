'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Graph3D } from '@/components/graph/Graph3D';
import { KnowledgeGraph3D } from '@/components/graph/KnowledgeGraph3D';
import { GapPanel } from '@/components/graph/GapPanel';
import { ImportProgress } from '@/components/import/ImportProgress';
import { api } from '@/lib/api';
import { useGraphStore } from '@/hooks/useGraphStore';
import { useGraph3DStore } from '@/hooks/useGraph3DStore';
import type {
  ConceptCluster,
  CentralityMetrics,
  GraphData,
  GraphEntity,
  ImportJob,
  ImportResumeInfo,
  StructuralGap,
  RelationshipEvidence,
  EvidenceChunk,
} from '@/types';
import { EdgeContextModal } from '@/components/graph/EdgeContextModal';
import { ChatInterface } from '@/components/chat/ChatInterface';

const QA_GRAPH_DATA: GraphData = {
  nodes: [
    { id: 'n1', entity_type: 'Concept', name: 'Trust', properties: { cluster_id: 0 } },
    { id: 'n2', entity_type: 'Method', name: 'Fine-tuning', properties: { cluster_id: 1 } },
    { id: 'n3', entity_type: 'Finding', name: 'Bias Reduction', properties: { cluster_id: 1 } },
    { id: 'n4', entity_type: 'Concept', name: 'Explainability', properties: { cluster_id: 0 } },
    { id: 'n5', entity_type: 'Concept', name: 'XAI', properties: { cluster_id: 0 } },
  ],
  edges: [
    {
      id: 'e1',
      source: 'n1',
      target: 'n2',
      relationship_type: 'APPLIES_TO',
      weight: 0.55,
      properties: { confidence: 0.52 },
    },
    {
      id: 'e2',
      source: 'n2',
      target: 'n3',
      relationship_type: 'SUPPORTS',
      weight: 0.86,
      properties: { confidence: 0.86 },
    },
    {
      id: 'e3',
      source: 'n4',
      target: 'n5',
      relationship_type: 'SAME_AS',
      weight: 0.95,
      properties: { confidence: 0.95 },
    },
  ],
};

const QA_CLUSTERS: ConceptCluster[] = [
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
    concepts: ['n2', 'n3'],
    concept_names: ['Fine-tuning', 'Bias Reduction'],
    size: 2,
    density: 0.6,
    label: 'Method+Finding',
  },
];

const QA_CENTRALITY: CentralityMetrics[] = [
  {
    concept_id: 'n1',
    concept_name: 'Trust',
    degree_centrality: 0.4,
    betweenness_centrality: 0.2,
    pagerank: 0.33,
    cluster_id: 0,
  },
  {
    concept_id: 'n2',
    concept_name: 'Fine-tuning',
    degree_centrality: 0.7,
    betweenness_centrality: 0.6,
    pagerank: 0.49,
    cluster_id: 1,
  },
  {
    concept_id: 'n3',
    concept_name: 'Bias Reduction',
    degree_centrality: 0.3,
    betweenness_centrality: 0.4,
    pagerank: 0.28,
    cluster_id: 1,
  },
];

const QA_GAPS: StructuralGap[] = [
  {
    id: 'gap-1',
    cluster_a_id: 0,
    cluster_b_id: 1,
    cluster_a_concepts: ['n1'],
    cluster_b_concepts: ['n2', 'n3'],
    cluster_a_names: ['Trust'],
    cluster_b_names: ['Fine-tuning', 'Bias Reduction'],
    gap_strength: 0.72,
    bridge_candidates: ['n2'],
    research_questions: ['How can trust-aware methods improve fine-tuning outcomes?'],
  },
];

const IMPORT_COMPLETED_FIXTURE: ImportJob = {
  job_id: 'qa-job',
  status: 'completed',
  progress: 1,
  current_step: 'finalize',
  project_id: 'qa-project',
  result: {
    project_id: 'qa-project',
    nodes_created: 42,
    edges_created: 88,
  },
  reliability_summary: {
    raw_entities_extracted: 160,
    entities_after_resolution: 72,
    merges_applied: 28,
    canonicalization_rate: 0.88,
    llm_pairs_reviewed: 12,
    llm_pairs_confirmed: 9,
    llm_confirmation_accept_rate: 0.75,
    potential_false_merge_count: 2,
    potential_false_merge_ratio: 0.03,
    potential_false_merge_samples: [],
    relationships_created: 88,
    evidence_backed_relationships: 73,
    provenance_coverage: 0.83,
    low_trust_edges: 6,
    low_trust_edge_ratio: 0.07,
  },
};

const IMPORT_INTERRUPTED_FIXTURE: ImportJob = {
  job_id: 'qa-job',
  status: 'interrupted',
  progress: 0.42,
  current_step: 'extract_entities',
  error: 'Import interrupted for QA simulation',
};

const IMPORT_RESUME_INFO_FIXTURE: ImportResumeInfo = {
  job_id: 'qa-job',
  status: 'interrupted',
  can_resume: true,
  checkpoint: {
    processed_count: 5,
    total_papers: 12,
    last_processed_index: 4,
    project_id: 'qa-project-partial',
    stage: 'extract_entities',
  },
};

const QA_EVIDENCE_FIXTURE: RelationshipEvidence = {
  relationship_id: 'e1',
  source_name: 'Trust',
  target_name: 'Fine-tuning',
  relationship_type: 'APPLIES_TO',
  total_evidence: 3,
  provenance_source: 'source_chunk_ids',
  evidence_chunks: [
    {
      evidence_id: 'ev1',
      chunk_id: 'chunk1',
      text: 'Trust mechanisms are essential when applying fine-tuning strategies to language models, as they ensure model reliability during adaptation.',
      section_type: 'introduction',
      paper_id: 'paper1',
      paper_title: 'Trust-Aware Fine-Tuning for LLMs',
      paper_authors: 'Smith et al.',
      paper_year: 2024,
      relevance_score: 0.92,
    },
    {
      evidence_id: 'ev2',
      chunk_id: 'chunk2',
      text: 'We demonstrate that incorporating trust scores into the fine-tuning objective function improves model robustness by 23%.',
      section_type: 'results',
      paper_id: 'paper1',
      paper_title: 'Trust-Aware Fine-Tuning for LLMs',
      paper_authors: 'Smith et al.',
      paper_year: 2024,
      relevance_score: 0.88,
    },
    {
      evidence_id: 'ev3',
      chunk_id: 'chunk3',
      text: 'The relationship between trust and fine-tuning effectiveness has been understudied despite its critical role in deployment scenarios.',
      section_type: 'discussion',
      paper_id: 'paper2',
      paper_title: 'Trustworthy AI in Practice',
      paper_authors: 'Johnson & Lee',
      paper_year: 2023,
      relevance_score: 0.85,
    },
  ],
};

function QAE2EContent() {
  const searchParams = useSearchParams();
  const scenario = searchParams.get('scenario') || 'knowledge';

  const pinnedCount = useGraphStore((state) => state.pinnedNodes.length);
  const selectedGapId = useGraphStore((state) => state.selectedGap?.id || 'none');

  const [cameraResetCount, setCameraResetCount] = useState(0);
  const [ready, setReady] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState<Array<{
    id: string;
    role: 'user' | 'assistant';
    content: string;
    citations?: string[];
    highlighted_nodes?: string[];
    highlighted_edges?: string[];
    timestamp: Date;
    searchStrategy?: 'vector' | 'graph_traversal' | 'hybrid';
    hopCount?: number;
  }>>([]);

  useEffect(() => {
    const originalGetImportStatus = api.getImportStatus.bind(api);
    const originalGetResumeInfo = api.getResumeInfo.bind(api);
    const originalResumeImport = api.resumeImport.bind(api);
    const originalGetGapRecommendations = api.getGapRecommendations.bind(api);
    const originalGenerateBridgeHypotheses = api.generateBridgeHypotheses.bind(api);
    const originalCreateBridge = api.createBridge.bind(api);
    const originalFetchRelationshipEvidence = api.fetchRelationshipEvidence.bind(api);

    api.getImportStatus = async () => (
      scenario === 'import-interrupted' ? IMPORT_INTERRUPTED_FIXTURE : IMPORT_COMPLETED_FIXTURE
    );
    api.getResumeInfo = async () => IMPORT_RESUME_INFO_FIXTURE;
    api.resumeImport = async () => ({
      ...IMPORT_COMPLETED_FIXTURE,
      status: 'running',
      progress: 0.55,
      current_step: 'build_relationships',
    });
    api.getGapRecommendations = async () => ({
      gap_id: 'gap-1',
      query_used: 'trust fine tuning bridge',
      papers: [],
    });
    api.generateBridgeHypotheses = async () => ({
      hypotheses: [],
      bridge_type: 'methodological',
      key_insight: 'QA deterministic bridge hypothesis fixture',
    });
    api.createBridge = async () => ({
      success: true,
      relationships_created: 1,
      relationship_ids: ['bridge-qa-1'],
      message: 'QA bridge created',
    });
    api.fetchRelationshipEvidence = async () => QA_EVIDENCE_FIXTURE;

    const currentGraphStore = useGraphStore.getState();
    useGraphStore.setState({
      ...currentGraphStore,
      graphData: QA_GRAPH_DATA,
      gaps: QA_GAPS,
      clusters: QA_CLUSTERS,
      centralityMetrics: QA_CENTRALITY,
      selectedGap: null,
      highlightedNodes: [],
      highlightedEdges: [],
      pinnedNodes: [],
      viewMode: '3d',
      isLoading: false,
      isGapLoading: false,
      error: null,
      fetchGraphData: async () => {},
      fetchGapAnalysis: async () => {},
    });

    const currentGraph3DStore = useGraph3DStore.getState();
    useGraph3DStore.setState({
      ...currentGraph3DStore,
      centrality: new Map(QA_CENTRALITY.map((item) => [item.concept_id, item.betweenness_centrality])),
      fetchCentrality: async () => {},
      getVisiblePercentage: () => 1,
      view3D: {
        ...currentGraph3DStore.view3D,
        lodEnabled: false,
        labelVisibility: 'all',
      },
    });

    setReady(true);

    return () => {
      api.getImportStatus = originalGetImportStatus;
      api.getResumeInfo = originalGetResumeInfo;
      api.resumeImport = originalResumeImport;
      api.getGapRecommendations = originalGetGapRecommendations;
      api.generateBridgeHypotheses = originalGenerateBridgeHypotheses;
      api.createBridge = originalCreateBridge;
      api.fetchRelationshipEvidence = originalFetchRelationshipEvidence;
    };
  }, [scenario]);

  const scenarioNodeMap = useMemo<Record<string, GraphEntity>>(() => {
    return QA_GRAPH_DATA.nodes.reduce<Record<string, GraphEntity>>((acc, node) => {
      acc[node.id] = node;
      return acc;
    }, {});
  }, []);

  if (!ready) {
    return (
      <main className="min-h-screen bg-[#0d1117] text-white p-6">
        <div data-testid="qa-loading" className="font-mono text-sm">Initializing QA fixtures...</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0d1117] text-white p-6">
      <div className="mb-4 border border-white/10 bg-black/20 p-3 text-xs font-mono">
        <div>Scenario: <span data-testid="qa-scenario">{scenario}</span></div>
        <div>pinned_nodes: <span data-testid="pinned-count">{pinnedCount}</span></div>
        <div>selected_gap: <span data-testid="selected-gap-id">{selectedGapId}</span></div>
        <div>camera_resets: <span data-testid="camera-reset-count">{cameraResetCount}</span></div>
      </div>

      {scenario === 'graph3d' && (
        <section data-testid="qa-scenario-root" className="h-[560px] border border-white/10">
          <Graph3D
            nodes={QA_GRAPH_DATA.nodes}
            edges={QA_GRAPH_DATA.edges}
            clusters={QA_CLUSTERS}
            centralityMetrics={QA_CENTRALITY}
            highlightedNodes={['n1']}
            highlightedEdges={['e1']}
            showGhostEdges
            potentialEdges={[
              {
                source_id: 'n1',
                target_id: 'n3',
                similarity: 0.83,
                gap_id: 'gap-1',
                source_name: 'Trust',
                target_name: 'Bias Reduction',
              },
            ]}
            onNodeClick={(node) => useGraphStore.getState().setSelectedNode(scenarioNodeMap[node.id] || null)}
          />
        </section>
      )}

      {scenario === 'knowledge' && (
        <section data-testid="qa-scenario-root" className="relative h-[900px] border border-white/10">
          <div className="absolute top-3 left-3 z-50 flex gap-2">
            <button
              data-testid="qa-pin-node"
              onClick={() => useGraphStore.getState().addPinnedNode('n1')}
              className="px-2 py-1 text-xs border border-white/20 bg-black/50"
            >
              Simulate Drag Pin n1
            </button>
            <button
              data-testid="qa-unpin-node"
              onClick={() => useGraphStore.getState().removePinnedNode('n1')}
              className="px-2 py-1 text-xs border border-white/20 bg-black/50"
            >
              Simulate Drag Release n1
            </button>
          </div>
          <KnowledgeGraph3D
            projectId="qa-project"
            onDebugCameraReset={() => setCameraResetCount((prev) => prev + 1)}
            onDebugGapFocus={() => {}}
          />
        </section>
      )}

      {scenario === 'gap-panel' && (
        <section data-testid="qa-scenario-root" className="max-w-md">
          <GapPanel
            projectId="qa-project"
            gaps={QA_GAPS}
            clusters={QA_CLUSTERS}
            nodes={QA_GRAPH_DATA.nodes}
            onGapSelect={(gap) => useGraphStore.getState().setSelectedGap(gap)}
            onHighlightNodes={(nodeIds) => useGraphStore.getState().setHighlightedNodes(nodeIds)}
            onClearHighlights={() => useGraphStore.getState().clearHighlights()}
          />
        </section>
      )}

      {scenario === 'import-completed' && (
        <section data-testid="qa-scenario-root" className="max-w-3xl">
          <ImportProgress jobId="qa-job" />
        </section>
      )}

      {scenario === 'import-interrupted' && (
        <section data-testid="qa-scenario-root" className="max-w-3xl">
          <ImportProgress jobId="qa-job" />
        </section>
      )}

      {scenario === 'provenance-chain' && (
        <section data-testid="qa-scenario-root" className="max-w-3xl">
          <div className="mb-4">
            <button
              onClick={() => setIsModalOpen(true)}
              className="px-4 py-2 bg-teal-600 text-white rounded"
              data-testid="qa-open-modal"
            >
              Open Edge Context Modal
            </button>
          </div>
          <EdgeContextModal
            isOpen={isModalOpen}
            onClose={() => setIsModalOpen(false)}
            relationshipId="e1"
            sourceName="Trust"
            targetName="Fine-tuning"
            relationshipType="APPLIES_TO"
            relationshipConfidence={0.52}
            isLowTrust={true}
          />
        </section>
      )}

      {scenario === 'strategy-badge' && (
        <section data-testid="qa-scenario-root" className="max-w-3xl h-[600px]">
          <ChatInterface
            projectId="qa-project"
            onSendMessage={async (message) => {
              const response = {
                content: `Response to: ${message}`,
                citations: ['Paper 1', 'Paper 2'],
                searchStrategy: chatMessages.length === 0 ? 'hybrid' as const : 'graph_traversal' as const,
                hopCount: chatMessages.length === 0 ? undefined : 2,
              };
              setChatMessages(prev => [
                ...prev,
                {
                  id: `user-${Date.now()}`,
                  role: 'user',
                  content: message,
                  timestamp: new Date(),
                },
                {
                  id: `assistant-${Date.now()}`,
                  role: 'assistant',
                  content: response.content,
                  citations: response.citations,
                  timestamp: new Date(),
                  searchStrategy: response.searchStrategy,
                  hopCount: response.hopCount,
                },
              ]);
              return response;
            }}
            initialMessages={chatMessages}
          />
        </section>
      )}

      {scenario === 'same-as-edges' && (
        <section data-testid="qa-scenario-root" className="h-[560px] border border-white/10">
          <Graph3D
            nodes={QA_GRAPH_DATA.nodes}
            edges={QA_GRAPH_DATA.edges}
            clusters={QA_CLUSTERS}
            centralityMetrics={QA_CENTRALITY}
            highlightedNodes={[]}
            highlightedEdges={[]}
            onNodeClick={(node) => useGraphStore.getState().setSelectedNode(scenarioNodeMap[node.id] || null)}
          />
        </section>
      )}
    </main>
  );
}

export default function QAE2EPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#0d1117] text-white p-6 font-mono text-sm">Loading QA...</div>}>
      <QAE2EContent />
    </Suspense>
  );
}
