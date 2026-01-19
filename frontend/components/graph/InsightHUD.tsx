'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

interface GraphMetrics {
  modularity: number;
  diversity: number;
  density: number;
  avg_clustering: number;
  num_components: number;
  node_count: number;
  edge_count: number;
  cluster_count: number;
}

interface MetricBarProps {
  label: string;
  value: number;
  color: string;
  tooltip?: string;
}

function MetricBar({ label, value, color, tooltip }: MetricBarProps) {
  const percentage = Math.round(value * 100);

  return (
    <div className="mb-3" title={tooltip}>
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs font-mono text-muted">{label}</span>
        <span className="text-xs font-mono text-white">{percentage}%</span>
      </div>
      <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${percentage}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  );
}

interface InsightHUDProps {
  projectId: string;
  className?: string;
}

export function InsightHUD({ projectId, className = '' }: InsightHUDProps) {
  const [metrics, setMetrics] = useState<GraphMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    async function fetchMetrics() {
      if (!projectId) return;

      setIsLoading(true);
      setError(null);

      try {
        const data = await api.getGraphMetrics(projectId);
        setMetrics(data);
      } catch (err) {
        console.error('Failed to fetch graph metrics:', err);
        setError(err instanceof Error ? err.message : 'Failed to load metrics');
      } finally {
        setIsLoading(false);
      }
    }

    fetchMetrics();
  }, [projectId]);

  if (isLoading) {
    return (
      <div className={`absolute bottom-4 left-4 z-20 ${className}`}>
        <div className="bg-[#161b22]/90 backdrop-blur-sm border border-white/10 rounded-lg p-3 w-48">
          <div className="animate-pulse space-y-2">
            <div className="h-3 bg-white/10 rounded w-20" />
            <div className="h-1.5 bg-white/10 rounded" />
            <div className="h-3 bg-white/10 rounded w-16 mt-2" />
            <div className="h-1.5 bg-white/10 rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !metrics) {
    return null; // Silently fail - HUD is optional
  }

  return (
    <div className={`absolute bottom-4 left-4 z-20 ${className}`}>
      <div className="bg-[#161b22]/90 backdrop-blur-sm border border-white/10 rounded-lg overflow-hidden w-52">
        {/* Header */}
        <button
          className="w-full px-3 py-2 flex items-center justify-between hover:bg-white/5 transition-colors"
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          <div className="flex items-center gap-2">
            <svg
              className="w-4 h-4 text-accent-teal"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <span className="text-xs font-mono font-medium text-white">Insight HUD</span>
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
          <div className="px-3 pb-3">
            {/* Quality Metrics */}
            <div className="mb-4">
              <MetricBar
                label="Modularity"
                value={metrics.modularity}
                color="#4ECDC4"
                tooltip="Cluster separation quality (higher = more distinct clusters)"
              />
              <MetricBar
                label="Diversity"
                value={metrics.diversity}
                color="#96CEB4"
                tooltip="Cluster size balance (higher = more even distribution)"
              />
              <MetricBar
                label="Density"
                value={metrics.density}
                color="#45B7D1"
                tooltip="Connection density (higher = more interconnected)"
              />
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/10">
              <div className="text-center">
                <div className="text-lg font-bold text-white">{metrics.node_count}</div>
                <div className="text-[10px] text-muted uppercase tracking-wider">Nodes</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-white">{metrics.edge_count}</div>
                <div className="text-[10px] text-muted uppercase tracking-wider">Edges</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-accent-teal">{metrics.cluster_count}</div>
                <div className="text-[10px] text-muted uppercase tracking-wider">Clusters</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-accent-purple">{metrics.num_components}</div>
                <div className="text-[10px] text-muted uppercase tracking-wider">Components</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default InsightHUD;
