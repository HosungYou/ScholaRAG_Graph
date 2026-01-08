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

import { CustomNode } from './CustomNode';
import { useGraphStore } from '@/hooks/useGraphStore';
import { applyLayout, updateNodeHighlights, updateEdgeHighlights, LayoutType } from '@/lib/layout';
import type { GraphEntity, EntityType } from '@/types';
import { Grid, Workflow, RotateCcw } from 'lucide-react';

interface KnowledgeGraphProps {
  projectId: string;
  onNodeClick?: (nodeId: string, nodeData: GraphEntity) => void;
  highlightedNodes?: string[];
  highlightedEdges?: string[];
}

// Define custom node types
const nodeTypes: NodeTypes = {
  paper: CustomNode,
  author: CustomNode,
  concept: CustomNode,
  method: CustomNode,
  finding: CustomNode,
};

// Color mapping for node types
const nodeColorMap: Record<string, string> = {
  Paper: '#3B82F6',    // Blue
  Author: '#10B981',   // Green
  Concept: '#8B5CF6',  // Purple
  Method: '#F59E0B',   // Amber
  Finding: '#EF4444',  // Red
};

function KnowledgeGraphInner({
  projectId,
  onNodeClick,
  highlightedNodes = [],
  highlightedEdges = [],
}: KnowledgeGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [layoutType, setLayoutType] = useState<LayoutType>('force');
  const [isLayouting, setIsLayouting] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const { fitView } = useReactFlow();

  const { graphData, getFilteredData, fetchGraphData, isLoading, error } = useGraphStore();

  // Fetch graph data on mount
  useEffect(() => {
    fetchGraphData(projectId);
  }, [projectId, fetchGraphData]);

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
      fitView({ padding: 0.2, duration: 500 });
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
    fitView({ padding: 0.2, duration: 500 });
  }, [fitView]);

  // MiniMap node color
  const miniMapNodeColor = useCallback((node: Node) => {
    return nodeColorMap[node.data?.entityType] || '#94A3B8';
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading knowledge graph...</p>
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
    <div ref={containerRef} className="w-full h-full relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        defaultEdgeOptions={{
          type: 'smoothstep',
        }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
        <Controls position="bottom-right" />
        <MiniMap
          nodeColor={miniMapNodeColor}
          nodeStrokeWidth={3}
          zoomable
          pannable
          position="bottom-left"
        />

        {/* Layout Controls */}
        <Panel position="top-right" className="flex gap-2">
          <div className="bg-white rounded-lg shadow-md border p-1 flex gap-1">
            <button
              onClick={() => handleLayoutChange('force')}
              className={`p-2 rounded transition-colors ${
                layoutType === 'force'
                  ? 'bg-blue-100 text-blue-600'
                  : 'hover:bg-gray-100 text-gray-600'
              }`}
              title="Force-directed layout"
            >
              <Grid className="w-4 h-4" />
            </button>
            <button
              onClick={() => handleLayoutChange('hierarchical')}
              className={`p-2 rounded transition-colors ${
                layoutType === 'hierarchical'
                  ? 'bg-blue-100 text-blue-600'
                  : 'hover:bg-gray-100 text-gray-600'
              }`}
              title="Hierarchical layout"
            >
              <Workflow className="w-4 h-4" />
            </button>
            <div className="w-px bg-gray-200" />
            <button
              onClick={handleRecenter}
              className="p-2 rounded hover:bg-gray-100 text-gray-600 transition-colors"
              title="Recenter view"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </Panel>
      </ReactFlow>

      {/* Loading overlay for layout */}
      {isLayouting && (
        <div className="absolute inset-0 bg-white/50 flex items-center justify-center z-20">
          <div className="bg-white px-4 py-2 rounded-lg shadow-md flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span className="text-sm text-gray-600">Applying layout...</span>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute top-4 left-4 bg-white rounded-lg shadow-md p-3 text-sm z-10">
        <p className="font-semibold mb-2">Node Types</p>
        <div className="space-y-1">
          {Object.entries(nodeColorMap).map(([type, color]) => (
            <div key={type} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span>{type}</span>
              {nodeCounts[type] !== undefined && (
                <span className="text-gray-400 text-xs">({nodeCounts[type]})</span>
              )}
            </div>
          ))}
        </div>
        <div className="mt-2 pt-2 border-t text-xs text-gray-500">
          Total: {nodes.length} nodes, {edges.length} edges
        </div>
      </div>
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
