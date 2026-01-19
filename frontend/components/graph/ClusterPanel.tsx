'use client';

import { useState, useCallback } from 'react';
import {
  Layers,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Loader2,
  Eye,
  EyeOff,
  Hexagon,
} from 'lucide-react';
import { useGraph3DStore } from '@/hooks/useGraph3DStore';
import { useGraphStore } from '@/hooks/useGraphStore';
import { api } from '@/lib/api';
import type { ConceptCluster } from '@/types';

interface ClusterPanelProps {
  projectId: string;
  className?: string;
  onClusterSelect?: (clusterId: number) => void;
  onFocusCluster?: (clusterId: number) => void;
}

// Cluster color palette (matches Graph3D)
const CLUSTER_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
  '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
  '#BB8FCE', '#85C1E9', '#F8B500', '#82E0AA',
];

export function ClusterPanel({
  projectId,
  className = '',
  onClusterSelect,
  onFocusCluster,
}: ClusterPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [hiddenClusters, setHiddenClusters] = useState<Set<number>>(new Set());

  const { clusterCount, setClusterCount, optimalK, setOptimalK } = useGraph3DStore();
  const { clusters, setHighlightedNodes, clearHighlights } = useGraphStore();

  const handleRecomputeClusters = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await api.recomputeClusters(projectId, clusterCount);
      setOptimalK(result.optimal_k);
      // Clusters will be refetched via the graphStore
      // For now, just trigger a refresh
      window.location.reload(); // Simple refresh for now
    } catch (error) {
      console.error('Failed to recompute clusters:', error);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, clusterCount, setOptimalK]);

  const handleClusterClick = useCallback((cluster: ConceptCluster) => {
    // Highlight all nodes in this cluster
    setHighlightedNodes(cluster.concepts);
    onClusterSelect?.(cluster.cluster_id);
  }, [setHighlightedNodes, onClusterSelect]);

  const handleFocusCluster = useCallback((clusterId: number) => {
    onFocusCluster?.(clusterId);
  }, [onFocusCluster]);

  const toggleClusterVisibility = useCallback((clusterId: number, event: React.MouseEvent) => {
    event.stopPropagation();
    setHiddenClusters(prev => {
      const newSet = new Set(prev);
      if (newSet.has(clusterId)) {
        newSet.delete(clusterId);
      } else {
        newSet.add(clusterId);
      }
      return newSet;
    });
  }, []);

  const handleClearSelection = useCallback(() => {
    clearHighlights();
  }, [clearHighlights]);

  return (
    <div
      className={`bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 ${className}`}
      style={{ width: '260px' }}
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-surface/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-accent-violet" />
          <span className="font-mono text-xs uppercase tracking-wider text-ink dark:text-paper">
            Semantic Clusters
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted" />
        )}
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4">
          {/* Cluster Count Slider */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <p className="font-mono text-[10px] uppercase tracking-wider text-muted">
                Number of Clusters
              </p>
              <span className="font-mono text-sm text-accent-violet">{clusterCount}</span>
            </div>
            <input
              type="range"
              min={2}
              max={12}
              step={1}
              value={clusterCount}
              onChange={(e) => setClusterCount(parseInt(e.target.value))}
              className="w-full h-2 bg-surface/20 rounded-none appearance-none cursor-pointer
                [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                [&::-webkit-slider-thumb]:bg-accent-violet [&::-webkit-slider-thumb]:rounded-none
                [&::-webkit-slider-thumb]:border-0 [&::-webkit-slider-thumb]:cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-muted mt-1">
              <span>2</span>
              <span className="text-accent-violet">
                Optimal: {optimalK}
              </span>
              <span>12</span>
            </div>
          </div>

          {/* Apply Button */}
          <button
            onClick={handleRecomputeClusters}
            disabled={isLoading}
            className="w-full px-3 py-2 bg-accent-violet text-white font-mono text-xs uppercase tracking-wider
              hover:bg-accent-violet/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin mx-auto" />
            ) : (
              <div className="flex items-center justify-center gap-1.5">
                <RefreshCw className="w-3.5 h-3.5" />
                Apply Clustering
              </div>
            )}
          </button>

          {/* Cluster Legend */}
          {clusters.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="font-mono text-[10px] uppercase tracking-wider text-muted">
                  Cluster Legend
                </p>
                <button
                  onClick={handleClearSelection}
                  className="text-[10px] text-muted hover:text-ink dark:hover:text-paper transition-colors"
                >
                  Clear
                </button>
              </div>
              <ul className="space-y-1 max-h-48 overflow-y-auto">
                {clusters.map((cluster, index) => {
                  const color = CLUSTER_COLORS[cluster.cluster_id % CLUSTER_COLORS.length];
                  const isHidden = hiddenClusters.has(cluster.cluster_id);

                  return (
                    <li
                      key={cluster.cluster_id}
                      onClick={() => handleClusterClick(cluster)}
                      className={`flex items-center justify-between px-2 py-1.5 cursor-pointer transition-colors
                        ${isHidden ? 'opacity-50' : 'hover:bg-surface/10'}`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <div
                          className="w-3 h-3 flex-shrink-0"
                          style={{ backgroundColor: color }}
                        />
                        <span className="text-xs text-ink dark:text-paper truncate">
                          {cluster.label || `Cluster ${cluster.cluster_id + 1}`}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] text-muted">
                          {cluster.size}
                        </span>
                        <button
                          onClick={(e) => toggleClusterVisibility(cluster.cluster_id, e)}
                          className="text-muted hover:text-ink dark:hover:text-paper transition-colors"
                          title={isHidden ? 'Show cluster' : 'Hide cluster'}
                        >
                          {isHidden ? (
                            <EyeOff className="w-3 h-3" />
                          ) : (
                            <Eye className="w-3 h-3" />
                          )}
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleFocusCluster(cluster.cluster_id);
                          }}
                          className="text-muted hover:text-accent-violet transition-colors"
                          title="Focus on cluster"
                        >
                          <Hexagon className="w-3 h-3" />
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {/* Empty State */}
          {clusters.length === 0 && (
            <div className="text-center py-4">
              <Layers className="w-8 h-8 text-muted mx-auto mb-2" />
              <p className="text-xs text-muted">
                No clusters detected
              </p>
              <p className="text-[10px] text-muted mt-1">
                Run gap analysis to generate clusters
              </p>
            </div>
          )}

          {/* Stats */}
          {clusters.length > 0 && (
            <div className="bg-surface/5 px-3 py-2">
              <div className="flex justify-between text-[10px]">
                <span className="text-muted">Total Clusters</span>
                <span className="font-mono text-ink dark:text-paper">{clusters.length}</span>
              </div>
              <div className="flex justify-between text-[10px] mt-1">
                <span className="text-muted">Total Concepts</span>
                <span className="font-mono text-ink dark:text-paper">
                  {clusters.reduce((sum, c) => sum + c.size, 0)}
                </span>
              </div>
              <div className="flex justify-between text-[10px] mt-1">
                <span className="text-muted">Avg. Cluster Size</span>
                <span className="font-mono text-ink dark:text-paper">
                  {(clusters.reduce((sum, c) => sum + c.size, 0) / clusters.length).toFixed(1)}
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ClusterPanel;
