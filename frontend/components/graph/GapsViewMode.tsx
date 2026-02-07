'use client';

import { useCallback, useMemo, useState } from 'react';
import { Graph3D, Graph3DRef } from './Graph3D';
import { GapQueryPanel } from './GapQueryPanel';
import type {
  GraphEntity,
  GraphEdge,
  ConceptCluster,
  CentralityMetrics,
  StructuralGap,
  GapsViewConfig,
  PotentialEdge,
} from '@/types';
import { Sparkles, ChevronLeft, ChevronRight, X } from 'lucide-react';
import { forwardRef } from 'react';

interface GapsViewModeProps {
  nodes: GraphEntity[];
  edges: GraphEdge[];
  clusters: ConceptCluster[];
  centralityMetrics: CentralityMetrics[];
  gaps: StructuralGap[];
  selectedGap: StructuralGap | null;
  onGapSelect: (gap: StructuralGap | null) => void;
  onNodeClick?: (node: GraphEntity) => void;
  onBackgroundClick?: () => void;
  onEdgeClick?: (edge: GraphEdge) => void;
  projectId: string;
  config?: Partial<GapsViewConfig>;
  bloomEnabled?: boolean;
  bloomIntensity?: number;
  glowSize?: number;
  // v0.7.0: Node pinning
  pinnedNodes?: string[];
  onNodePin?: (nodeId: string) => void;
  onNodeUnpin?: (nodeId: string) => void;
  onClearPinnedNodes?: () => void;
}

const DEFAULT_CONFIG: GapsViewConfig = {
  selectedGapId: null,
  showAllGaps: false,
  highlightBridges: true,
  dimInactiveNodes: true,
  inactiveOpacity: 0.2,
  bridgeGlowIntensity: 1.5,
};

export const GapsViewMode = forwardRef<Graph3DRef, GapsViewModeProps>(({
  nodes,
  edges,
  clusters,
  centralityMetrics,
  gaps,
  selectedGap,
  onGapSelect,
  onNodeClick,
  onBackgroundClick,
  onEdgeClick,
  projectId,
  config: userConfig,
  bloomEnabled = true,
  bloomIntensity = 0.5,
  glowSize = 1.3,
  // v0.7.0: Node pinning
  pinnedNodes = [],
  onNodePin,
  onNodeUnpin,
  onClearPinnedNodes,
}, ref) => {
  const config = { ...DEFAULT_CONFIG, ...userConfig };
  const [showGapList, setShowGapList] = useState(true);
  const [currentGapIndex, setCurrentGapIndex] = useState(0);

  // Compute highlighted nodes based on selected gap
  const highlightedNodes = useMemo(() => {
    if (!selectedGap) return [];

    const nodes = new Set<string>();

    // Add cluster A concepts
    selectedGap.cluster_a_concepts.forEach(id => nodes.add(id));

    // Add cluster B concepts
    selectedGap.cluster_b_concepts.forEach(id => nodes.add(id));

    // Add bridge candidates
    selectedGap.bridge_candidates.forEach(id => nodes.add(id));

    return Array.from(nodes);
  }, [selectedGap]);

  // Compute highlighted edges based on selected gap
  const highlightedEdges = useMemo(() => {
    if (!selectedGap) return [];

    // Find edges that connect nodes in the gap
    const gapNodeIds = new Set([
      ...selectedGap.cluster_a_concepts,
      ...selectedGap.cluster_b_concepts,
      ...selectedGap.bridge_candidates,
    ]);

    return edges
      .filter(e => gapNodeIds.has(e.source) && gapNodeIds.has(e.target))
      .map(e => e.id);
  }, [selectedGap, edges]);

  // Get potential edges (ghost edges) for the selected gap
  const potentialEdges = useMemo((): PotentialEdge[] => {
    if (!selectedGap || !selectedGap.potential_edges) return [];
    return selectedGap.potential_edges;
  }, [selectedGap]);

  // Navigate between gaps
  const handlePrevGap = useCallback(() => {
    if (gaps.length === 0) return;
    const newIndex = (currentGapIndex - 1 + gaps.length) % gaps.length;
    setCurrentGapIndex(newIndex);
    onGapSelect(gaps[newIndex]);
  }, [gaps, currentGapIndex, onGapSelect]);

  const handleNextGap = useCallback(() => {
    if (gaps.length === 0) return;
    const newIndex = (currentGapIndex + 1) % gaps.length;
    setCurrentGapIndex(newIndex);
    onGapSelect(gaps[newIndex]);
  }, [gaps, currentGapIndex, onGapSelect]);

  // Select a gap from the list
  const handleSelectGap = useCallback((gap: StructuralGap, index: number) => {
    setCurrentGapIndex(index);
    onGapSelect(gap);
  }, [onGapSelect]);

  // Clear gap selection
  const handleClearSelection = useCallback(() => {
    onGapSelect(null);
  }, [onGapSelect]);

  // Get cluster names for display
  const getClusterName = useCallback((clusterId: number) => {
    const cluster = clusters.find(c => c.cluster_id === clusterId);
    const label = cluster?.label;
    if (label && label.replace(/[\s/,]+/g, '').length > 0) return label;
    return `Cluster ${clusterId + 1}`;
  }, [clusters]);

  return (
    <div className="relative w-full h-full">
      {/* 3D Graph with Gap-specific highlighting */}
      <Graph3D
        ref={ref}
        nodes={nodes}
        edges={edges}
        clusters={clusters}
        centralityMetrics={centralityMetrics}
        highlightedNodes={highlightedNodes}
        highlightedEdges={highlightedEdges}
        selectedGap={selectedGap}
        onNodeClick={onNodeClick}
        onBackgroundClick={onBackgroundClick}
        onEdgeClick={onEdgeClick}
        showGhostEdges={selectedGap !== null && potentialEdges.length > 0}
        potentialEdges={potentialEdges}
        bloomEnabled={bloomEnabled}
        bloomIntensity={bloomIntensity}
        glowSize={glowSize}
        // v0.7.0: Node pinning
        pinnedNodes={pinnedNodes}
        onNodePin={onNodePin}
        onNodeUnpin={onNodeUnpin}
        onClearPinnedNodes={onClearPinnedNodes}
      />

      {/* Gaps View Badge */}
      <div className="absolute top-4 left-4 bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 px-3 py-1.5">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-accent-amber" />
          <span className="font-mono text-xs uppercase tracking-wider text-muted">
            Gaps View
          </span>
          <span className="text-xs text-muted">
            • {gaps.length} structural gaps
          </span>
        </div>
      </div>

      {/* Gap Navigator */}
      {gaps.length > 0 && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-[#161b22]/95 backdrop-blur-sm border border-white/10 rounded-lg p-2">
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrevGap}
              className="p-1.5 hover:bg-white/10 rounded transition-colors"
              title="Previous gap"
            >
              <ChevronLeft className="w-4 h-4 text-white/70" />
            </button>

            <div className="min-w-[200px] text-center">
              {selectedGap ? (
                <div className="flex flex-col">
                  <span className="text-xs text-amber-400 font-mono">
                    Gap {currentGapIndex + 1} of {gaps.length}
                  </span>
                  <span className="text-sm text-white truncate" title={`${getClusterName(selectedGap.cluster_a_id)} ↔ ${getClusterName(selectedGap.cluster_b_id)}`}>
                    {getClusterName(selectedGap.cluster_a_id)} ↔ {getClusterName(selectedGap.cluster_b_id)}
                  </span>
                </div>
              ) : (
                <span className="text-xs text-muted">
                  Select a gap to explore
                </span>
              )}
            </div>

            <button
              onClick={handleNextGap}
              className="p-1.5 hover:bg-white/10 rounded transition-colors"
              title="Next gap"
            >
              <ChevronRight className="w-4 h-4 text-white/70" />
            </button>

            {selectedGap && (
              <button
                onClick={handleClearSelection}
                className="p-1.5 hover:bg-white/10 rounded transition-colors ml-1"
                title="Clear selection"
              >
                <X className="w-4 h-4 text-white/70" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Gap List Sidebar */}
      {showGapList && gaps.length > 0 && (
        <div className="absolute bottom-20 left-4 w-80 bg-[#161b22]/95 backdrop-blur-sm border border-white/10 rounded-lg overflow-hidden">
          <div className="p-3 border-b border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-accent-amber" />
              <span className="font-mono text-xs uppercase tracking-wider text-white">
                Structural Gaps
              </span>
              <span className="font-mono text-[10px] px-1.5 py-0.5 bg-accent-amber/20 text-accent-amber rounded">
                {gaps.length}
              </span>
            </div>
            <button
              onClick={() => setShowGapList(false)}
              className="p-1 hover:bg-white/10 rounded transition-colors"
            >
              <X className="w-3 h-3 text-muted" />
            </button>
          </div>

          <div className="max-h-64 overflow-y-auto">
            {gaps.map((gap, index) => (
              <button
                key={gap.id}
                onClick={() => handleSelectGap(gap, index)}
                className={`w-full p-3 text-left border-b border-white/5 hover:bg-white/8 hover:border-l-2 hover:border-l-amber-500/50 transition-all ${
                  selectedGap?.id === gap.id ? 'bg-amber-500/10 border-l-2 border-l-amber-500' : ''
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-muted">Gap #{index + 1}</span>
                  <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                    gap.gap_strength > 0.7
                      ? 'bg-red-500/25 text-red-300'
                      : gap.gap_strength > 0.4
                        ? 'bg-amber-500/25 text-amber-300'
                        : 'bg-green-500/25 text-green-300'
                  }`}>
                    {(gap.gap_strength * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="text-sm text-white truncate" title={`${getClusterName(gap.cluster_a_id)} ↔ ${getClusterName(gap.cluster_b_id)}`}>
                  {getClusterName(gap.cluster_a_id)} ↔ {getClusterName(gap.cluster_b_id)}
                </div>
                <div className="text-xs text-muted mt-1">
                  {gap.bridge_candidates.length} bridge candidate{gap.bridge_candidates.length !== 1 ? 's' : ''}
                </div>
              </button>
            ))}
          </div>
          <div className="px-3 py-2 border-t border-white/5 flex items-center justify-center gap-1">
            <span className="text-[10px] text-muted/50 font-mono">Click a gap to highlight in graph</span>
          </div>
        </div>
      )}

      {/* Empty state when no gaps */}
      {showGapList && gaps.length === 0 && (
        <div className="absolute bottom-20 left-4 w-80 bg-[#161b22]/95 backdrop-blur-sm border border-white/10 rounded-lg p-6 text-center">
          <Sparkles className="w-6 h-6 text-accent-amber/40 mx-auto mb-2" />
          <p className="font-mono text-xs text-muted">No structural gaps detected in this graph</p>
        </div>
      )}

      {/* Gap Query Panel (Research Question Generation) */}
      {selectedGap && (
        <GapQueryPanel
          gap={selectedGap}
          clusters={clusters}
          projectId={projectId}
        />
      )}

      {/* Toggle Gap List Button */}
      {!showGapList && gaps.length > 0 && (
        <button
          onClick={() => setShowGapList(true)}
          className="absolute bottom-20 left-4 p-2 bg-[#161b22]/95 backdrop-blur-sm border border-white/10 rounded-lg hover:bg-white/10 transition-colors"
          title="Show gap list"
        >
          <Sparkles className="w-4 h-4 text-accent-amber" />
        </button>
      )}

      {/* Legend */}
      <div className="absolute bottom-4 right-4 bg-[#161b22]/90 backdrop-blur-sm border border-white/10 rounded-lg p-3">
        <div className="text-xs font-mono text-muted mb-2">Gaps View Legend</div>
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-amber-500" />
            <span className="text-xs text-white/70">Highlighted nodes</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-amber-500 ring-2 ring-amber-500/50 ring-offset-1 ring-offset-[#161b22]" />
            <span className="text-xs text-white/70">Bridge candidates</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 border-t-2 border-dashed border-amber-500" />
            <span className="text-xs text-white/70">Potential connections</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-white/20" />
            <span className="text-xs text-white/70">Inactive nodes</span>
          </div>
        </div>
      </div>
    </div>
  );
});

GapsViewMode.displayName = 'GapsViewMode';

export default GapsViewMode;
