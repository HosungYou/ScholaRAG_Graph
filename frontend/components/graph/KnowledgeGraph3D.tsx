'use client';

import { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import { Graph3D, Graph3DRef } from './Graph3D';
import { GapPanel } from './GapPanel';
import { DraggablePanel, DragHandle } from '../ui/DraggablePanel';
import { CentralityPanel } from './CentralityPanel';
import { ClusterPanel } from './ClusterPanel';
import { GraphLegend } from './GraphLegend';
import { StatusBar } from './StatusBar';
import { NodeDetails } from './NodeDetails';
import { InsightHUD } from './InsightHUD';
import { MainTopicsPanel } from './MainTopicsPanel';
import { TopicViewMode } from './TopicViewMode';
import { GapsViewMode } from './GapsViewMode';  // UI-010: Gaps View Mode
import { EdgeContextModal } from './EdgeContextModal';  // UI-011: Relationship Evidence
import EntityTypeLegend from './EntityTypeLegend';  // v0.10.0: Entity type legend
import { useGraphStore } from '@/hooks/useGraphStore';
import { useGraph3DStore, applyLOD } from '@/hooks/useGraph3DStore';
import type { GraphEntity, EntityType, StructuralGap, GraphEdge, ViewMode } from '@/types';
import {
  Hexagon,
  Box,
  Grid3X3,
  Grid2X2,
  Sparkles,
  Info,
  RotateCcw,
  Layers,
  Scissors,
  BarChart3,
  PieChart,
  Sun,
  SunDim,
  Tag,
  Tags,
  Type,
} from 'lucide-react';

interface KnowledgeGraph3DProps {
  projectId: string;
  onNodeClick?: (nodeId: string, nodeData: GraphEntity) => void;
}

export function KnowledgeGraph3D({
  projectId,
  onNodeClick,
}: KnowledgeGraph3DProps) {
  const graph3DRef = useRef<Graph3DRef>(null);
  const [selectedNode, setSelectedNode] = useState<GraphEntity | null>(null);
  const [showLegend, setShowLegend] = useState(true);
  const [showGapPanel, setShowGapPanel] = useState(true);
  const [showCentralityPanel, setShowCentralityPanel] = useState(false);
  const [showClusterPanel, setShowClusterPanel] = useState(false);
  const [showInsightHUD, setShowInsightHUD] = useState(true);
  const [showMainTopics, setShowMainTopics] = useState(false);
  const [isGapPanelMinimized, setIsGapPanelMinimized] = useState(false);
  // UI-011: Edge context modal state for Relationship Evidence
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);
  const [edgeModalOpen, setEdgeModalOpen] = useState(false);

  // Graph store (existing)
  const {
    graphData,
    getFilteredData,
    fetchGraphData,
    isLoading,
    error,
    gaps,
    clusters,
    centralityMetrics,
    isGapLoading,
    fetchGapAnalysis,
    setHighlightedNodes,
    setHighlightedEdges,
    highlightedNodes,
    highlightedEdges,
    clearHighlights,
    selectedGap,
    setSelectedGap,
    viewMode,
    setViewMode,
    filters,  // Phase 4 FIX: Subscribe to filters for reactive filtering
    // v0.7.0: Node pinning
    pinnedNodes,
    addPinnedNode,
    removePinnedNode,
    clearPinnedNodes,
  } = useGraphStore();

  // 3D-specific store
  const {
    view3D,
    centrality,
    fetchCentrality,
    getVisiblePercentage,
    toggleBloom,
    cycleLabelVisibility,
  } = useGraph3DStore();

  // Fetch data on mount
  useEffect(() => {
    fetchGraphData(projectId);
    fetchGapAnalysis(projectId);
    fetchCentrality(projectId);
  }, [projectId, fetchGraphData, fetchGapAnalysis, fetchCentrality]);

  // Get filtered data with LOD applied
  const displayData = useMemo(() => {
    const filteredData = getFilteredData();
    if (!filteredData) return null;

    if (!view3D.lodEnabled) {
      return filteredData;
    }

    const visiblePercentage = getVisiblePercentage();
    const visibleNodes = applyLOD(filteredData.nodes, centrality, visiblePercentage);
    const visibleNodeIds = new Set(visibleNodes.map(n => n.id));

    return {
      nodes: visibleNodes,
      edges: filteredData.edges.filter(
        e => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)
      ),
    };
  }, [getFilteredData, view3D.lodEnabled, centrality, getVisiblePercentage, filters]);
  // Phase 4 FIX: Added `filters` to re-render when filter state changes

  // Handle node click
  const handleNodeClick = useCallback((node: GraphEntity) => {
    setSelectedNode(node);

    // Find connected edges
    const filteredData = getFilteredData();
    if (!filteredData) return;

    const connectedEdges = filteredData.edges.filter(
      e => e.source === node.id || e.target === node.id
    );

    // Collect connected node IDs
    const connectedNodeIds = new Set<string>();
    connectedNodeIds.add(node.id);
    connectedEdges.forEach(e => {
      connectedNodeIds.add(e.source);
      connectedNodeIds.add(e.target);
    });

    setHighlightedNodes(Array.from(connectedNodeIds));
    setHighlightedEdges(connectedEdges.map(e => e.id));

    onNodeClick?.(node.id, node);
  }, [getFilteredData, setHighlightedNodes, setHighlightedEdges, onNodeClick]);

  // Handle gap selection
  const handleGapSelect = useCallback((gap: StructuralGap) => {
    setSelectedGap(gap);

    // Highlight gap nodes
    const allNodes = [
      ...gap.cluster_a_concepts,
      ...gap.cluster_b_concepts,
      ...gap.bridge_candidates,
    ];
    setHighlightedNodes(allNodes);

    // Focus camera on gap
    graph3DRef.current?.focusOnGap(gap);
  }, [setSelectedGap, setHighlightedNodes]);

  // Handle gap highlight
  const handleGapHighlight = useCallback((nodeIds: string[]) => {
    setHighlightedNodes(nodeIds);
  }, [setHighlightedNodes]);

  // Handle clear highlights
  const handleClearGapHighlights = useCallback(() => {
    clearHighlights();
    setSelectedGap(null);
  }, [clearHighlights, setSelectedGap]);

  // Handle gap refresh
  const handleRefreshGaps = useCallback(async () => {
    await fetchGapAnalysis(projectId);
  }, [projectId, fetchGapAnalysis]);

  // Handle reset camera
  const handleResetCamera = useCallback(() => {
    graph3DRef.current?.resetCamera();
  }, []);

  // Handle background click
  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
    clearHighlights();
  }, [clearHighlights]);

  // UI-011: Handle edge click for Relationship Evidence modal
  const handleEdgeClick = useCallback((edge: GraphEdge) => {
    setSelectedEdge(edge);
    setEdgeModalOpen(true);
  }, []);

  // UI-011: Handle close edge modal
  const handleCloseEdgeModal = useCallback(() => {
    setEdgeModalOpen(false);
    setSelectedEdge(null);
  }, []);

  // Handle close node details
  const handleCloseNodeDetails = useCallback(() => {
    setSelectedNode(null);
  }, []);

  // Handle cluster focus from ClusterPanel
  const handleFocusCluster = useCallback((clusterId: number) => {
    graph3DRef.current?.focusOnCluster(clusterId);
  }, []);

  // Handle slicing applied - refresh graph view
  const handleSlicingApplied = useCallback(() => {
    // The graph will automatically update through the store
    // We could add visual feedback here if needed
  }, []);

  // Handle slicing reset
  const handleSlicingReset = useCallback(() => {
    // Reset highlights when slicing is reset
    clearHighlights();
  }, [clearHighlights]);

  // Count nodes by type for legend
  const nodeCounts = useMemo(() => {
    const filteredData = getFilteredData();
    if (!filteredData) return {};

    const counts: Record<string, number> = {};
    for (const node of filteredData.nodes) {
      counts[node.entity_type] = (counts[node.entity_type] || 0) + 1;
    }
    return counts;
  }, [getFilteredData]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-[#0d1117]">
        <div className="text-center">
          <div className="w-16 h-16 flex items-center justify-center mx-auto mb-4">
            <Box className="w-10 h-10 text-accent-teal animate-pulse" />
          </div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted">
            Loading 3D knowledge graph...
          </p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-[#0d1117]">
        <div className="text-center">
          <div className="w-16 h-16 flex items-center justify-center bg-accent-red/10 mx-auto mb-4">
            <span className="text-accent-red text-3xl">!</span>
          </div>
          <p className="font-mono text-xs uppercase tracking-wider text-accent-red mb-2">
            Failed to load graph
          </p>
          <p className="text-sm text-muted">{error}</p>
        </div>
      </div>
    );
  }

  // No data state
  if (!displayData || displayData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full bg-[#0d1117]">
        <div className="text-center">
          <div className="w-16 h-16 flex items-center justify-center bg-muted/10 mx-auto mb-4">
            <Grid3X3 className="w-8 h-8 text-muted" />
          </div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted">
            No graph data available
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      {/* Graph View (3D, Topic, or Gaps) */}
      {viewMode === '3d' && (
        <>
          <EntityTypeLegend visibleTypes={Object.keys(nodeCounts)} />
          <Graph3D
            ref={graph3DRef}
            nodes={displayData.nodes}
            edges={displayData.edges}
            clusters={clusters}
            centralityMetrics={centralityMetrics}
            highlightedNodes={highlightedNodes}
            highlightedEdges={highlightedEdges}
            selectedGap={selectedGap}
            onNodeClick={handleNodeClick}
            onBackgroundClick={handleBackgroundClick}
            onEdgeClick={handleEdgeClick}  // UI-011: Relationship Evidence
            bloomEnabled={view3D.bloom.enabled}
            bloomIntensity={view3D.bloom.intensity}
            glowSize={view3D.bloom.glowSize}
            // v0.7.0: Node pinning
            pinnedNodes={pinnedNodes}
            onNodePin={addPinnedNode}
            onNodeUnpin={removePinnedNode}
            onClearPinnedNodes={clearPinnedNodes}
            // v0.8.0: Adaptive label visibility
            labelVisibility={view3D.labelVisibility}
          />
        </>
      )}
      {viewMode === 'topic' && (
        <TopicViewMode
          clusters={clusters}
          gaps={gaps}
          edges={displayData.edges}
          onClusterClick={handleFocusCluster}
          onClusterHover={(clusterId) => {
            if (clusterId !== null) {
              const cluster = clusters.find((c) => c.cluster_id === clusterId);
              if (cluster) {
                setHighlightedNodes(cluster.concepts);
              }
            } else {
              clearHighlights();
            }
          }}
        />
      )}
      {viewMode === 'gaps' && (
        <GapsViewMode
          ref={graph3DRef}
          nodes={displayData.nodes}
          edges={displayData.edges}
          clusters={clusters}
          centralityMetrics={centralityMetrics}
          gaps={gaps}
          selectedGap={selectedGap}
          onGapSelect={setSelectedGap}
          onNodeClick={handleNodeClick}
          onBackgroundClick={handleBackgroundClick}
          onEdgeClick={handleEdgeClick}
          projectId={projectId}
          bloomEnabled={view3D.bloom.enabled}
          bloomIntensity={view3D.bloom.intensity}
          glowSize={view3D.bloom.glowSize}
          // v0.7.0: Node pinning
          pinnedNodes={pinnedNodes}
          onNodePin={addPinnedNode}
          onNodeUnpin={removePinnedNode}
          onClearPinnedNodes={clearPinnedNodes}
        />
      )}

      {/* Top Controls */}
      <div className="absolute top-4 right-4 flex gap-2">
        <div className="bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 p-1 flex gap-1">
          {/* 3D Mode Indicator */}
          <div className="p-2 bg-accent-teal text-white relative" title="3D 그래프 뷰 - 노드 드래그로 탐색, 스크롤로 줌">
            <Box className="w-4 h-4" />
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-white" />
          </div>

          <div className="w-px bg-ink/10 dark:bg-paper/10" />

          {/* Bloom/Glow Toggle */}
          <button
            onClick={toggleBloom}
            className={`p-2 transition-colors ${
              view3D.bloom.enabled
                ? 'bg-yellow-500/10 text-yellow-500'
                : 'hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
            }`}
            title={view3D.bloom.enabled ? '노드 발광 효과 끄기' : '노드 발광 효과 켜기 (중요 노드 강조)'}
          >
            {view3D.bloom.enabled ? (
              <Sun className="w-4 h-4" />
            ) : (
              <SunDim className="w-4 h-4" />
            )}
          </button>

          {/* v0.8.0: Label Visibility Toggle */}
          <button
            onClick={cycleLabelVisibility}
            className={`p-2 transition-colors ${
              view3D.labelVisibility === 'all'
                ? 'bg-accent-violet/10 text-accent-violet'
                : view3D.labelVisibility === 'important'
                ? 'bg-accent-teal/10 text-accent-teal'
                : 'hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
            }`}
            title={`라벨 표시: ${view3D.labelVisibility === 'all' ? '모든 노드' : view3D.labelVisibility === 'important' ? '상위 20% 노드' : '숨김'} (클릭하여 전환)`}
          >
            {view3D.labelVisibility === 'all' ? (
              <Tags className="w-4 h-4" />
            ) : view3D.labelVisibility === 'important' ? (
              <Tag className="w-4 h-4" />
            ) : (
              <Type className="w-4 h-4 opacity-50" />
            )}
          </button>

          <div className="w-px bg-ink/10 dark:bg-paper/10" />

          {/* Reset Camera */}
          <button
            onClick={handleResetCamera}
            className="p-2 hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper transition-colors"
            title="카메라 초기화"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Toggle Legend */}
          <button
            onClick={() => setShowLegend(!showLegend)}
            className={`p-2 transition-colors ${
              showLegend
                ? 'bg-accent-teal/10 text-accent-teal'
                : 'hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
            }`}
            title="개체 타입 범례 표시/숨김"
          >
            <Info className="w-4 h-4" />
          </button>

          {/* Toggle Gap Panel */}
          <button
            onClick={() => setShowGapPanel(!showGapPanel)}
            className={`p-2 transition-colors ${
              showGapPanel
                ? 'bg-accent-amber/10 text-accent-amber'
                : 'hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
            }`}
            title="연구 갭 패널 표시/숨김 (지식 구조의 구멍)"
          >
            <Sparkles className="w-4 h-4" />
          </button>

          {/* Toggle Centrality Panel */}
          <button
            onClick={() => setShowCentralityPanel(!showCentralityPanel)}
            className={`p-2 transition-colors ${
              showCentralityPanel
                ? 'bg-accent-teal/10 text-accent-teal'
                : 'hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
            }`}
            title="노드 중요도 패널 표시/숨김 (고중심성 브릿지 제거)"
          >
            <Scissors className="w-4 h-4" />
          </button>

          {/* Toggle Cluster Panel */}
          <button
            onClick={() => setShowClusterPanel(!showClusterPanel)}
            className={`p-2 transition-colors ${
              showClusterPanel
                ? 'bg-accent-violet/10 text-accent-violet'
                : 'hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
            }`}
            title="토픽 클러스터 패널 표시/숨김 (그룹화 조정)"
          >
            <Layers className="w-4 h-4" />
          </button>

          {/* Toggle Insight HUD */}
          <button
            onClick={() => setShowInsightHUD(!showInsightHUD)}
            className={`p-2 transition-colors ${
              showInsightHUD
                ? 'bg-accent-teal/10 text-accent-teal'
                : 'hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
            }`}
            title="그래프 분석 HUD 표시/숨김 (다양성, 모듈성)"
          >
            <BarChart3 className="w-4 h-4" />
          </button>

          {/* Toggle Main Topics */}
          <button
            onClick={() => setShowMainTopics(!showMainTopics)}
            className={`p-2 transition-colors ${
              showMainTopics
                ? 'bg-accent-violet/10 text-accent-violet'
                : 'hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
            }`}
            title="주요 토픽 패널 표시/숨김 (지배적 주제)"
          >
            <PieChart className="w-4 h-4" />
          </button>

          <div className="w-px bg-ink/10 dark:bg-paper/10" />

          {/* UI-012: View Mode Toggle - 3 modes: 3D, Topic, Gaps */}
          <div className="flex items-center bg-ink/15 dark:bg-paper/15 rounded-lg p-1 gap-1 border border-ink/20 dark:border-paper/20">
            {/* 3D Mode */}
            <button
              onClick={() => setViewMode('3d')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-all ${
                viewMode === '3d'
                  ? 'bg-accent-teal text-white shadow-sm'
                  : 'text-ink/70 dark:text-paper/70 hover:text-ink dark:hover:text-paper hover:bg-ink/10 dark:hover:bg-paper/10'
              }`}
              title="3D 그래프 뷰 - 물리 시뮬레이션 기반 지식 그래프"
            >
              <Box className="w-4 h-4" />
              <span className="font-mono text-xs uppercase tracking-wider">3D</span>
            </button>

            {/* Topic Mode */}
            <button
              onClick={() => setViewMode('topic')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-all ${
                viewMode === 'topic'
                  ? 'bg-accent-purple text-white shadow-sm'
                  : 'text-ink/70 dark:text-paper/70 hover:text-ink dark:hover:text-paper hover:bg-ink/10 dark:hover:bg-paper/10'
              }`}
              title="토픽 뷰 - 클러스터 및 커뮤니티 시각화"
            >
              <Grid2X2 className="w-4 h-4" />
              <span className="font-mono text-xs uppercase tracking-wider">Topics</span>
            </button>

            {/* Gaps Mode */}
            <button
              onClick={() => setViewMode('gaps')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-all ${
                viewMode === 'gaps'
                  ? 'bg-accent-amber text-white shadow-sm'
                  : 'text-ink/70 dark:text-paper/70 hover:text-ink dark:hover:text-paper hover:bg-ink/10 dark:hover:bg-paper/10'
              }`}
              title="갭 뷰 - 연구 공백 및 브릿지 가설 탐색"
            >
              <Sparkles className="w-4 h-4" />
              <span className="font-mono text-xs uppercase tracking-wider">Gaps</span>
            </button>
          </div>
        </div>
      </div>

      {/* Gap Panel - Hidden in Gaps mode (GapsViewMode has integrated gap list) */}
      {showGapPanel && viewMode !== 'gaps' && (
        <DraggablePanel panelId="gap" projectId={projectId} defaultPosition={{ x: 16, y: 16 }}>
        <GapPanel
          projectId={projectId}
          gaps={gaps}
          clusters={clusters}
          nodes={displayData.nodes}
          onGapSelect={handleGapSelect}
          onHighlightNodes={handleGapHighlight}
          onClearHighlights={handleClearGapHighlights}
          isLoading={isGapLoading}
          onRefresh={handleRefreshGaps}
          isMinimized={isGapPanelMinimized}
          onToggleMinimize={() => setIsGapPanelMinimized(!isGapPanelMinimized)}
        />
        </DraggablePanel>
      )}

      {/* Right-side panels - stacked */}
      {(showCentralityPanel || showClusterPanel) && (
        <DraggablePanel panelId="right-stack" projectId={projectId} defaultPosition={{ x: window?.innerWidth ? window.innerWidth - 300 : 900, y: 80 }}>
        <div className="flex flex-col gap-2 max-h-[calc(100vh-120px)] overflow-y-auto">
          {showCentralityPanel && (
            <CentralityPanel
              projectId={projectId}
              onSlicingApplied={handleSlicingApplied}
              onSlicingReset={handleSlicingReset}
            />
          )}
          {showClusterPanel && (
            <ClusterPanel
              projectId={projectId}
              onFocusCluster={handleFocusCluster}
            />
          )}
        </div>
        </DraggablePanel>
      )}

      {/* Legend */}
      {showLegend && (
        <GraphLegend
          visibleTypes={Object.keys(nodeCounts) as EntityType[]}
          nodeCountsByType={nodeCounts as Record<EntityType, number>}
        />
      )}

      {/* Node Details Panel */}
      {selectedNode && (
        <NodeDetails
          node={selectedNode}
          onClose={handleCloseNodeDetails}
          projectId={projectId}
        />
      )}

      {/* Status Bar */}
      <StatusBar projectId={projectId} />

      {/* Insight HUD - v0.8.0: Repositioned to right side (InfraNodus-style Analytics) */}
      {/* Dynamic positioning: below CentralityPanel and ClusterPanel if visible */}
      {showInsightHUD && (
        <DraggablePanel
          panelId="insight-hud"
          projectId={projectId}
          defaultPosition={{ x: window?.innerWidth ? window.innerWidth - 220 : 900, y: showCentralityPanel || showClusterPanel ? 400 : 80 }}
          zIndex={15}
        >
        <InsightHUD
          projectId={projectId}
        />
        </DraggablePanel>
      )}

      {/* Main Topics Panel - Bottom Left (InsightHUD moved to right side) */}
      {showMainTopics && (
        <MainTopicsPanel
          clusters={clusters}
          onFocusCluster={handleFocusCluster}
          onHighlightCluster={setHighlightedNodes}
          onClearHighlight={clearHighlights}
          className="absolute z-20 bottom-4 left-4"
        />
      )}

      {/* v0.10.0: View Mode Badge with Active Indicator - Hidden in Gaps mode */}
      {viewMode !== 'gaps' && (
        <div className="absolute top-4 left-4 bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 px-3 py-1.5">
          <div className="flex items-center gap-2">
            {viewMode === '3d' && (
              <>
                {/* Pulsing active indicator */}
                <div className="relative flex items-center justify-center">
                  <div className="absolute w-2 h-2 bg-accent-teal rounded-full animate-ping opacity-75" />
                  <div className="w-2 h-2 bg-accent-teal rounded-full" />
                </div>
                <Box className="w-4 h-4 text-accent-teal" />
                <span className="font-mono text-xs uppercase tracking-wider text-muted">
                  3D Mode
                </span>
                <span className="text-xs text-muted">
                  • {displayData.nodes.length} nodes
                </span>
              </>
            )}
            {viewMode === 'topic' && (
              <>
                {/* Pulsing active indicator */}
                <div className="relative flex items-center justify-center">
                  <div className="absolute w-2 h-2 bg-accent-purple rounded-full animate-ping opacity-75" />
                  <div className="w-2 h-2 bg-accent-purple rounded-full" />
                </div>
                <Grid2X2 className="w-4 h-4 text-accent-purple" />
                <span className="font-mono text-xs uppercase tracking-wider text-muted">
                  Topic View
                </span>
                <span className="text-xs text-muted">
                  • {clusters.length} clusters
                </span>
              </>
            )}
          </div>
        </div>
      )}

      {/* UI-011: Edge Context Modal - Relationship Evidence */}
      <EdgeContextModal
        isOpen={edgeModalOpen}
        onClose={handleCloseEdgeModal}
        relationshipId={selectedEdge?.id || null}
      />
    </div>
  );
}

export default KnowledgeGraph3D;
