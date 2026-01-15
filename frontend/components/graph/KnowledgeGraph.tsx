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
import { useGraphStore } from '@/hooks/useGraphStore';
import { applyLayout, updateNodeHighlights, updateEdgeHighlights, LayoutType } from '@/lib/layout';
import type { GraphEntity, EntityType, StructuralGap } from '@/types';
import { Circle, Target, RotateCcw, Info, Sparkles } from 'lucide-react';

interface KnowledgeGraphProps {
  projectId: string;
  onNodeClick?: (nodeId: string, nodeData: GraphEntity) => void;
  highlightedNodes?: string[];
  highlightedEdges?: string[];
}

// Define custom node types - all use CircularNode now
const nodeTypes: NodeTypes = {
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
};

// Cluster color palette for minimap
const clusterColors = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
  '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
  '#BB8FCE', '#85C1E9', '#F8B500', '#82E0AA',
];

// Entity type colors for legend
const entityTypeColors: Record<string, string> = {
  Concept: '#8B5CF6',
  Method: '#F59E0B',
  Finding: '#10B981',
  Problem: '#EF4444',
  Dataset: '#3B82F6',
  Metric: '#EC4899',
  Innovation: '#14B8A6',
  Limitation: '#F97316',
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

  // Handle node click
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (onNodeClick) {
        const filteredData = getFilteredData();
        const entity = filteredData?.nodes.find(n => n.id === node.id);
        if (entity) {
          onNodeClick(node.id, entity);
        }
      }
    },
    [onNodeClick, getFilteredData]
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
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading concept network...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center text-red-600">
          <p>Failed to load graph data</p>
          <p className="text-sm mt-2">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="w-full h-full relative bg-gray-900">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.1}
        maxZoom={3}
        defaultEdgeOptions={{
          type: 'smoothstep',
        }}
        style={{ background: '#1a1a2e' }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={30}
          size={1}
          color="#2a2a4e"
        />
        <Controls
          position="bottom-right"
          className="!bg-gray-800 !border-gray-700"
        />
        <MiniMap
          nodeColor={miniMapNodeColor}
          nodeStrokeWidth={2}
          zoomable
          pannable
          position="bottom-left"
          className="!bg-gray-800 !border-gray-700"
          maskColor="rgba(0, 0, 0, 0.7)"
        />

        {/* Layout Controls */}
        <Panel position="top-right" className="flex gap-2">
          <div className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-1 flex gap-1">
            <button
              onClick={() => handleLayoutChange('cluster')}
              className={`p-2 rounded transition-colors ${
                layoutType === 'cluster'
                  ? 'bg-purple-600 text-white'
                  : 'hover:bg-gray-700 text-gray-300'
              }`}
              title="Cluster layout"
            >
              <Circle className="w-4 h-4" />
            </button>
            <button
              onClick={() => handleLayoutChange('radial')}
              className={`p-2 rounded transition-colors ${
                layoutType === 'radial'
                  ? 'bg-purple-600 text-white'
                  : 'hover:bg-gray-700 text-gray-300'
              }`}
              title="Radial layout (by importance)"
            >
              <Target className="w-4 h-4" />
            </button>
            <div className="w-px bg-gray-600" />
            <button
              onClick={handleRecenter}
              className="p-2 rounded hover:bg-gray-700 text-gray-300 transition-colors"
              title="Recenter view"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowLegend(!showLegend)}
              className={`p-2 rounded transition-colors ${
                showLegend ? 'bg-gray-700 text-white' : 'hover:bg-gray-700 text-gray-300'
              }`}
              title="Toggle legend"
            >
              <Info className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowGapPanel(!showGapPanel)}
              className={`p-2 rounded transition-colors ${
                showGapPanel ? 'bg-yellow-600 text-white' : 'hover:bg-gray-700 text-gray-300'
              }`}
              title="Toggle gap panel"
            >
              <Sparkles className="w-4 h-4" />
            </button>
          </div>
        </Panel>
      </ReactFlow>

      {/* Loading overlay for layout */}
      {isLayouting && (
        <div className="absolute inset-0 bg-gray-900/50 flex items-center justify-center z-20">
          <div className="bg-gray-800 px-4 py-2 rounded-lg shadow-lg border border-gray-700 flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-500"></div>
            <span className="text-sm text-gray-300">Arranging concepts...</span>
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
        />
      )}

      {/* Legend - positioned on the right side to avoid GapPanel overlap */}
      {showLegend && (
        <div className="absolute top-16 right-4 bg-gray-800/95 rounded-lg shadow-lg border border-gray-700 p-4 text-sm z-10 max-w-xs max-h-[calc(100vh-200px)] overflow-y-auto">
          {/* Entity Types */}
          <div className="mb-4">
            <p className="font-semibold text-gray-200 mb-2">Entity Types</p>
            <div className="grid grid-cols-2 gap-1">
              {Object.entries(entityTypeColors).map(([type, color]) => (
                <div key={type} className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-gray-300 text-xs">{type}</span>
                  {nodeCounts[type] !== undefined && (
                    <span className="text-gray-500 text-xs">({nodeCounts[type]})</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Clusters */}
          {clusterCounts.size > 0 && (
            <div className="mb-4 pt-3 border-t border-gray-700">
              <p className="font-semibold text-gray-200 mb-2">Concept Clusters</p>
              <div className="space-y-1">
                {Array.from(clusterCounts.entries()).map(([clusterId, count]) => (
                  <div key={clusterId} className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: clusterColors[clusterId % clusterColors.length] }}
                    />
                    <span className="text-gray-300 text-xs">Cluster {clusterId + 1}</span>
                    <span className="text-gray-500 text-xs">({count} concepts)</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Edge Legend */}
          <div className="pt-3 border-t border-gray-700">
            <p className="font-semibold text-gray-200 mb-2">Connections</p>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5 bg-gray-400"></div>
                <span className="text-gray-300 text-xs">Related</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5 bg-emerald-500"></div>
                <span className="text-gray-300 text-xs">Co-occurs</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5 bg-yellow-500" style={{ borderStyle: 'dashed', border: '1px dashed #FFD700' }}></div>
                <span className="text-gray-300 text-xs">Gap Bridge</span>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="mt-3 pt-3 border-t border-gray-700 text-xs text-gray-400">
            <div className="flex justify-between">
              <span>Concepts:</span>
              <span>{nodes.length}</span>
            </div>
            <div className="flex justify-between">
              <span>Connections:</span>
              <span>{edges.length}</span>
            </div>
            <div className="flex justify-between">
              <span>Clusters:</span>
              <span>{clusterCounts.size}</span>
            </div>
          </div>
        </div>
      )}
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
