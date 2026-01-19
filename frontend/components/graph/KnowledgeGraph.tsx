'use client';

import { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  MiniMap,
  Background,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  NodeTypes,
  ConnectionMode,
  Panel,
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { CircularNode } from './CircularNode';
import { GapPanel } from './GapPanel';
import { GraphLegend } from './GraphLegend';
import { StatusBar } from './StatusBar';
import { useGraphStore } from '@/hooks/useGraphStore';
import { applyLayout, updateNodeHighlights, updateEdgeHighlights, LayoutType } from '@/lib/layout';
import type { GraphEntity, EntityType, StructuralGap } from '@/types';
import { Circle, Target, RotateCcw, Info, Sparkles, Hexagon } from 'lucide-react';

interface KnowledgeGraphProps {
  projectId: string;
  onNodeClick?: (nodeId: string, nodeData: GraphEntity) => void;
  highlightedNodes?: string[];
  highlightedEdges?: string[];
}

// Define custom node types OUTSIDE component to prevent React Flow warning
// "It looks like you've created a new nodeTypes or edgeTypes object"
// This ensures stable reference across re-renders
const NODE_TYPES: NodeTypes = {
  circular: CircularNode,
  // Legacy types redirect to circular
  concept: CircularNode,
  method: CircularNode,
  finding: CircularNode,
  problem: CircularNode,
  dataset: CircularNode,
  metric: CircularNode,
  innovation: CircularNode,
  limitation: CircularNode,
} as const;

// Cluster color palette for minimap
const clusterColors = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
  '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
  '#BB8FCE', '#85C1E9', '#F8B500', '#82E0AA',
];

// Entity type colors for legend (Hybrid Mode - matches FilterPanel/PolygonNode)
const entityTypeColors: Record<string, string> = {
  // Hybrid Mode entities
  Paper: '#6366F1',     // Indigo
  Author: '#A855F7',    // Purple
  // Concept-centric entities
  Concept: '#8B5CF6',   // Violet
  Method: '#F59E0B',    // Amber
  Finding: '#10B981',   // Emerald
  Problem: '#EF4444',   // Red
  Dataset: '#3B82F6',   // Blue
  Metric: '#EC4899',    // Pink
  Innovation: '#14B8A6', // Teal
  Limitation: '#F97316', // Orange
};

function KnowledgeGraphInner({
  projectId,
  onNodeClick,
  highlightedNodes = [],
  highlightedEdges = [],
}: KnowledgeGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [layoutType, setLayoutType] = useState<LayoutType>('cluster');
  const [isLayouting, setIsLayouting] = useState(false);
  const [showLegend, setShowLegend] = useState(true);
  const [showGapPanel, setShowGapPanel] = useState(true);
  const [isGapPanelMinimized, setIsGapPanelMinimized] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const { fitView } = useReactFlow();

  const {
    graphData,
    getFilteredData,
    fetchGraphData,
    isLoading,
    error,
    // Gap Detection
    gaps,
    clusters,
    isGapLoading,
    fetchGapAnalysis,
    setHighlightedNodes,
    setHighlightedEdges,
    clearHighlights,
  } = useGraphStore();

  // Fetch graph data on mount
  useEffect(() => {
    fetchGraphData(projectId);
    fetchGapAnalysis(projectId);
  }, [projectId, fetchGraphData, fetchGapAnalysis]);

  // Apply layout when graph data changes
  useEffect(() => {
    const filteredData = getFilteredData();
    if (!filteredData || filteredData.nodes.length === 0) return;

    setIsLayouting(true);

    // Get container dimensions
    const width = containerRef.current?.clientWidth || 1200;
    const height = containerRef.current?.clientHeight || 800;

    // Apply layout
    const { nodes: layoutNodes, edges: layoutEdges } = applyLayout(
      filteredData.nodes,
      filteredData.edges,
      layoutType,
      { width, height }
    );

    setNodes(layoutNodes);
    setEdges(layoutEdges);

    // Fit view after layout
    setTimeout(() => {
      fitView({ padding: 0.15, duration: 500 });
      setIsLayouting(false);
    }, 100);
  }, [graphData, layoutType, getFilteredData, setNodes, setEdges, fitView]);

  // Update highlights when they change
  useEffect(() => {
    if (highlightedNodes.length > 0 || highlightedEdges.length > 0) {
      setNodes(nds => updateNodeHighlights(nds, highlightedNodes));
      setEdges(eds => updateEdgeHighlights(eds, highlightedEdges));
    }
  }, [highlightedNodes, highlightedEdges, setNodes, setEdges]);

  // Handle node click - ResearchRabbit style highlighting
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, clickedNode: Node) => {
      // 1. Find connected edges
      const connectedEdgeList = edges.filter(
        e => e.source === clickedNode.id || e.target === clickedNode.id
      );

      // 2. Collect connected node IDs
      const connectedNodeIds = new Set<string>();
      connectedNodeIds.add(clickedNode.id); // Include clicked node
      connectedEdgeList.forEach(e => {
        connectedNodeIds.add(e.source);
        connectedNodeIds.add(e.target);
      });

      // 3. Apply highlights via store (for persistence)
      const nodeIdsArray = Array.from(connectedNodeIds);
      const edgeIdsArray = connectedEdgeList.map(e => e.id);

      setHighlightedNodes(nodeIdsArray);
      setHighlightedEdges(edgeIdsArray);

      // 4. Update visual highlights on nodes and edges
      setNodes(nds => updateNodeHighlights(nds, nodeIdsArray));
      setEdges(eds => updateEdgeHighlights(eds, edgeIdsArray));

      // 5. Call onNodeClick callback for detail panel
      if (onNodeClick) {
        const filteredData = getFilteredData();
        const entity = filteredData?.nodes.find(n => n.id === clickedNode.id);
        if (entity) {
          onNodeClick(clickedNode.id, entity);
        }
      }
    },
    [edges, onNodeClick, getFilteredData, setHighlightedNodes, setHighlightedEdges, setNodes, setEdges]
  );

  // Handle layout change
  const handleLayoutChange = useCallback((type: LayoutType) => {
    setLayoutType(type);
  }, []);

  // Handle recenter
  const handleRecenter = useCallback(() => {
    fitView({ padding: 0.15, duration: 500 });
  }, [fitView]);

  // Handle gap selection
  const handleGapSelect = useCallback((gap: StructuralGap) => {
    // This triggers highlighting via the store
    console.log('Gap selected:', gap.id);
  }, []);

  // Handle gap node highlighting
  const handleGapHighlight = useCallback((nodeIds: string[]) => {
    setHighlightedNodes(nodeIds);
    setNodes(nds => updateNodeHighlights(nds, nodeIds));
  }, [setHighlightedNodes, setNodes]);

  // Handle clear gap highlights
  const handleClearGapHighlights = useCallback(() => {
    clearHighlights();
    setNodes(nds => updateNodeHighlights(nds, []));
    setEdges(eds => updateEdgeHighlights(eds, []));
  }, [clearHighlights, setNodes, setEdges]);

  // Handle gap refresh
  const handleRefreshGaps = useCallback(async () => {
    await fetchGapAnalysis(projectId);
  }, [projectId, fetchGapAnalysis]);

  // MiniMap node color based on cluster
  const miniMapNodeColor = useCallback((node: Node) => {
    const clusterId = node.data?.clusterId;
    if (clusterId !== undefined) {
      return clusterColors[clusterId % clusterColors.length];
    }
    return entityTypeColors[node.data?.entityType] || '#94A3B8';
  }, []);

  // Count nodes by type
  const nodeCounts = useMemo(() => {
    const filteredData = getFilteredData();
    if (!filteredData) return {};

    const counts: Record<string, number> = {};
    for (const node of filteredData.nodes) {
      counts[node.entity_type] = (counts[node.entity_type] || 0) + 1;
    }
    return counts;
  }, [getFilteredData]);

  // Count clusters
  const clusterCounts = useMemo(() => {
    const filteredData = getFilteredData();
    if (!filteredData) return new Map<number, number>();

    const counts = new Map<number, number>();
    for (const node of filteredData.nodes) {
      const clusterId = node.properties?.cluster_id;
      if (clusterId !== undefined && typeof clusterId === 'number') {
        counts.set(clusterId, (counts.get(clusterId) || 0) + 1);
      }
    }
    return counts;
  }, [getFilteredData]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-paper dark:bg-ink">
        <div className="text-center">
          <div className="w-16 h-16 flex items-center justify-center bg-accent-teal/10 mx-auto mb-4">
            <Hexagon className="w-8 h-8 text-accent-teal animate-pulse" />
          </div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted">Loading concept network...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-paper dark:bg-ink">
        <div className="text-center">
          <div className="w-16 h-16 flex items-center justify-center bg-accent-red/10 mx-auto mb-4">
            <span className="text-accent-red text-3xl">!</span>
          </div>
          <p className="font-mono text-xs uppercase tracking-wider text-accent-red mb-2">Failed to load graph</p>
          <p className="text-sm text-muted">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="w-full h-full relative" style={{ backgroundColor: '#0D0D1A' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={NODE_TYPES}
        connectionMode={ConnectionMode.Loose}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.1}
        maxZoom={3}
        defaultEdgeOptions={{
          type: 'default',  // Straight line (Bezier curve) for better visibility
        }}
        style={{ background: 'linear-gradient(180deg, #0D0D1A 0%, #1A1A2E 100%)' }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={30}
          size={1}
          color="rgba(139, 92, 246, 0.15)"
        />
        <Controls
          position="bottom-right"
          className="!bg-paper dark:!bg-ink !border-ink/10 dark:!border-paper/10 !rounded-none"
        />
        <MiniMap
          nodeColor={miniMapNodeColor}
          nodeStrokeWidth={2}
          zoomable
          pannable
          position="bottom-left"
          className="!bg-paper dark:!bg-ink !border-ink/10 dark:!border-paper/10 !rounded-none"
          maskColor="rgba(0, 0, 0, 0.7)"
          style={{
            marginLeft: showGapPanel
              ? isGapPanelMinimized ? '64px' : '272px'  // Dynamic offset for GapPanel state
              : '16px'
          }}
        />

        {/* Layout Controls - VS Design Diverge Style */}
        <Panel position="top-right" className="flex gap-2">
          <div className="bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 p-1 flex gap-1">
            <button
              onClick={() => handleLayoutChange('cluster')}
              className={`p-2 transition-colors relative ${
                layoutType === 'cluster'
                  ? 'bg-accent-teal text-white'
                  : 'hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
              }`}
              title="Cluster layout"
            >
              <Circle className="w-4 h-4" />
              {layoutType === 'cluster' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-white" />
              )}
            </button>
            <button
              onClick={() => handleLayoutChange('radial')}
              className={`p-2 transition-colors relative ${
                layoutType === 'radial'
                  ? 'bg-accent-teal text-white'
                  : 'hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
              }`}
              title="Radial layout (by importance)"
            >
              <Target className="w-4 h-4" />
              {layoutType === 'radial' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-white" />
              )}
            </button>
            <div className="w-px bg-ink/10 dark:bg-paper/10" />
            <button
              onClick={handleRecenter}
              className="p-2 hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper transition-colors"
              title="Recenter view"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowLegend(!showLegend)}
              className={`p-2 transition-colors ${
                showLegend ? 'bg-accent-teal/10 text-accent-teal' : 'hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
              }`}
              title="Toggle legend"
            >
              <Info className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowGapPanel(!showGapPanel)}
              className={`p-2 transition-colors ${
                showGapPanel ? 'bg-accent-amber/10 text-accent-amber' : 'hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
              }`}
              title="Toggle gap panel"
            >
              <Sparkles className="w-4 h-4" />
            </button>
          </div>
        </Panel>
      </ReactFlow>

      {/* Loading overlay for layout - VS Design Diverge Style */}
      {isLayouting && (
        <div className="absolute inset-0 bg-ink/50 flex items-center justify-center z-20">
          <div className="bg-paper dark:bg-ink px-5 py-3 border border-ink/10 dark:border-paper/10 flex items-center gap-3">
            <Hexagon className="w-5 h-5 text-accent-teal animate-pulse" />
            <span className="font-mono text-xs uppercase tracking-wider text-ink dark:text-paper">Arranging concepts...</span>
          </div>
        </div>
      )}

      {/* Gap Panel */}
      {showGapPanel && (
        <GapPanel
          projectId={projectId}
          gaps={gaps}
          clusters={clusters}
          onGapSelect={handleGapSelect}
          onHighlightNodes={handleGapHighlight}
          onClearHighlights={handleClearGapHighlights}
          isLoading={isGapLoading}
          onRefresh={handleRefreshGaps}
          isMinimized={isGapPanelMinimized}
          onToggleMinimize={() => setIsGapPanelMinimized(!isGapPanelMinimized)}
        />
      )}

      {/* Legend - VS Design Diverge GraphLegend Component */}
      {showLegend && (
        <GraphLegend
          visibleTypes={Object.keys(nodeCounts) as EntityType[]}
          nodeCountsByType={nodeCounts as Record<EntityType, number>}
        />
      )}

      {/* StatusBar - LLM/Vector/Source Status */}
      <StatusBar projectId={projectId} />
    </div>
  );
}

// Wrap with ReactFlowProvider
export function KnowledgeGraph(props: KnowledgeGraphProps) {
  return (
    <ReactFlowProvider>
      <KnowledgeGraphInner {...props} />
    </ReactFlowProvider>
  );
}
