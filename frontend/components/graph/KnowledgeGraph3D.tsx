'use client';

import { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import { Graph3D, Graph3DRef } from './Graph3D';
import { GapPanel } from './GapPanel';
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
          <div className="p-2 bg-accent-teal text-white relative" title="3D Graph View - Drag nodes to explore, scroll to zoom">
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
            title={view3D.bloom.enabled ? 'Disable node glow effect' : 'Enable node glow effect (highlights important nodes)'}
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
            title={`Labels: ${view3D.labelVisibility === 'all' ? 'All nodes labeled' : view3D.labelVisibility === 'important' ? 'Top 20% nodes labeled' : 'Labels hidden'} (click to cycle)`}
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
            title="Reset camera to default view"
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
            title="Toggle entity type legend"
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
            title="Toggle research gaps panel (structural holes in knowledge)"
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
            title="Toggle node importance panel (remove high-centrality bridges)"
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
            title="Toggle topic clusters panel (adjust grouping)"
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
            title="Toggle graph analytics HUD (diversity, modularity)"
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
            title="Toggle main topics panel (dominant themes)"
          >
            <PieChart className="w-4 h-4" />
          </button>

          <div className="w-px bg-ink/10 dark:bg-paper/10" />

          {/* UI-012: View Mode Toggle - 3 modes: 3D, Topic, Gaps */}
          <div className="flex items-center gap-1">
            {/* 3D Mode */}
            <button
              onClick={() => setViewMode('3d')}
              className={`flex items-center gap-1.5 px-2 py-2 transition-all ${
                viewMode === '3d'
                  ? 'bg-accent-teal text-white'
                  : 'hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
              }`}
              title="3D Graph View - Full knowledge graph exploration with physics"
            >
              <Box className="w-4 h-4" />
              <span className="font-mono text-xs uppercase tracking-wider">3D</span>
            </button>

            {/* Topic Mode */}
            <button
              onClick={() => setViewMode('topic')}
              className={`flex items-center gap-1.5 px-2 py-2 transition-all ${
                viewMode === 'topic'
                  ? 'bg-accent-purple text-white'
                  : 'hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
              }`}
              title="Topic View - Clusters and communities visualization"
            >
              <Grid2X2 className="w-4 h-4" />
              <span className="font-mono text-xs uppercase tracking-wider">Topics</span>
            </button>

            {/* Gaps Mode */}
            <button
              onClick={() => setViewMode('gaps')}
              className={`flex items-center gap-1.5 px-2 py-2 transition-all ${
                viewMode === 'gaps'
                  ? 'bg-accent-amber text-white'
                  : 'hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
              }`}
              title="Gaps View - Research gap identification and bridge hypotheses"
            >
              <Sparkles className="w-4 h-4" />
              <span className="font-mono text-xs uppercase tracking-wider">Gaps</span>
            </button>
          </div>
        </div>
      </div>

      {/* Gap Panel - Hidden in Gaps mode (GapsViewMode has integrated gap list) */}
      {showGapPanel && viewMode !== 'gaps' && (
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
      )}

      {/* Centrality Panel - Right side below controls */}
      {showCentralityPanel && (
        <CentralityPanel
          projectId={projectId}
          className="absolute top-20 right-4 z-10"
          onSlicingApplied={handleSlicingApplied}
          onSlicingReset={handleSlicingReset}
        />
      )}

      {/* Cluster Panel - Right side below Centrality Panel */}
      {showClusterPanel && (
        <ClusterPanel
          projectId={projectId}
          className={`absolute right-4 z-10 ${showCentralityPanel ? 'top-[340px]' : 'top-20'}`}
          onFocusCluster={handleFocusCluster}
        />
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
        <InsightHUD
          projectId={projectId}
          className={`right-4 ${
            showCentralityPanel && showClusterPanel
              ? 'top-[580px]'  // Below both panels
              : showCentralityPanel
              ? 'top-[340px]'  // Below CentralityPanel only
              : showClusterPanel
              ? 'top-[340px]'  // Below ClusterPanel only
              : 'top-20'       // Just below top controls
          }`}
        />
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

      {/* View Mode Badge - Hidden in Gaps mode (GapsViewMode has its own badge) */}
      {viewMode !== 'gaps' && (
        <div className="absolute top-4 left-4 bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 px-3 py-1.5">
          <div className="flex items-center gap-2">
            {viewMode === '3d' && (
              <>
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
