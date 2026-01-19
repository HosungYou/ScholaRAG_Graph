'use client';

import { useMemo, useState } from 'react';
import type { ConceptCluster } from '@/types';

// Cluster color palette (matches Graph3D)
const CLUSTER_COLORS = [
  '#FF6B6B', // Coral Red
  '#4ECDC4', // Turquoise
  '#45B7D1', // Sky Blue
  '#96CEB4', // Sage Green
  '#FFEAA7', // Soft Yellow
  '#DDA0DD', // Plum
  '#98D8C8', // Mint
  '#F7DC6F', // Gold
  '#BB8FCE', // Lavender
  '#85C1E9', // Light Blue
  '#F8B500', // Amber
  '#82E0AA', // Light Green
];

interface ClusterBarProps {
  cluster: ConceptCluster;
  percentage: number;
  color: string;
  isHovered: boolean;
  onHover: (clusterId: number | null) => void;
  onClick: (clusterId: number) => void;
}

function ClusterBar({
  cluster,
  percentage,
  color,
  isHovered,
  onHover,
  onClick,
}: ClusterBarProps) {
  return (
    <button
      className={`w-full text-left transition-all ${isHovered ? 'scale-[1.02]' : ''}`}
      onMouseEnter={() => onHover(cluster.cluster_id)}
      onMouseLeave={() => onHover(null)}
      onClick={() => onClick(cluster.cluster_id)}
    >
      <div className="flex items-center gap-2 mb-1">
        {/* Color indicator */}
        <div
          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
          style={{ backgroundColor: color }}
        />

        {/* Label */}
        <span
          className="text-xs font-mono truncate flex-1"
          style={{ color: isHovered ? color : '#8b949e' }}
          title={cluster.label || `Cluster ${cluster.cluster_id + 1}`}
        >
          {cluster.label || `Cluster ${cluster.cluster_id + 1}`}
        </span>

        {/* Percentage */}
        <span className="text-xs font-mono text-white flex-shrink-0">
          {percentage.toFixed(0)}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-white/10 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{
            width: `${percentage}%`,
            backgroundColor: color,
            opacity: isHovered ? 1 : 0.7,
          }}
        />
      </div>
    </button>
  );
}

interface MainTopicsPanelProps {
  clusters: ConceptCluster[];
  onFocusCluster: (clusterId: number) => void;
  onHighlightCluster?: (nodeIds: string[]) => void;
  onClearHighlight?: () => void;
  className?: string;
}

export function MainTopicsPanel({
  clusters,
  onFocusCluster,
  onHighlightCluster,
  onClearHighlight,
  className = '',
}: MainTopicsPanelProps) {
  const [hoveredClusterId, setHoveredClusterId] = useState<number | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Calculate percentages
  const clusterStats = useMemo(() => {
    const totalSize = clusters.reduce((sum, c) => sum + c.size, 0);
    if (totalSize === 0) return [];

    return clusters
      .map((cluster, index) => ({
        cluster,
        percentage: (cluster.size / totalSize) * 100,
        color: CLUSTER_COLORS[index % CLUSTER_COLORS.length],
      }))
      .sort((a, b) => b.percentage - a.percentage); // Sort by size descending
  }, [clusters]);

  // Handle hover
  const handleHover = (clusterId: number | null) => {
    setHoveredClusterId(clusterId);

    if (clusterId !== null && onHighlightCluster) {
      const cluster = clusters.find((c) => c.cluster_id === clusterId);
      if (cluster) {
        onHighlightCluster(cluster.concepts);
      }
    } else if (onClearHighlight) {
      onClearHighlight();
    }
  };

  // Handle click
  const handleClick = (clusterId: number) => {
    onFocusCluster(clusterId);
  };

  if (clusters.length === 0) {
    return null;
  }

  return (
    <div className={`bg-[#161b22]/90 backdrop-blur-sm border border-white/10 rounded-lg overflow-hidden w-56 ${className}`}>
      {/* Header */}
      <button
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-white/5 transition-colors"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <svg
            className="w-4 h-4 text-accent-violet"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
            />
          </svg>
          <span className="text-xs font-mono font-medium text-white">Main Topics</span>
          <span className="text-[10px] text-muted">({clusters.length})</span>
        </div>
        <svg
          className={`w-4 h-4 text-muted transition-transform ${isCollapsed ? '' : 'rotate-180'}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
        </svg>
      </button>

      {/* Content */}
      {!isCollapsed && (
        <div className="px-3 pb-3 space-y-3 max-h-64 overflow-y-auto">
          {clusterStats.map(({ cluster, percentage, color }) => (
            <ClusterBar
              key={cluster.cluster_id}
              cluster={cluster}
              percentage={percentage}
              color={color}
              isHovered={hoveredClusterId === cluster.cluster_id}
              onHover={handleHover}
              onClick={handleClick}
            />
          ))}

          {/* Total indicator */}
          <div className="pt-2 border-t border-white/10 flex justify-between items-center">
            <span className="text-[10px] text-muted uppercase tracking-wider">Total Concepts</span>
            <span className="text-xs font-mono text-white">
              {clusters.reduce((sum, c) => sum + c.size, 0)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default MainTopicsPanel;
