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

interface DiversityMetrics {
  shannon_entropy: number;
  normalized_entropy: number;
  modularity: number;
  bias_score: number;
  diversity_rating: 'high' | 'medium' | 'low';
  cluster_sizes: number[];
  dominant_cluster_ratio: number;
  gini_coefficient: number;
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

// Circular Diversity Gauge Component (Phase 4)
interface DiversityGaugeProps {
  rating: 'high' | 'medium' | 'low';
  entropy: number;
  biasScore: number;
}

function DiversityGauge({ rating, entropy, biasScore }: DiversityGaugeProps) {
  // Determine colors based on rating
  // v0.5.0: Changed "Low Diversity" → "Focused" for research context clarity
  const colors = {
    high: { primary: '#10B981', bg: '#10B981/20', label: 'Diverse Topics', desc: 'Broad coverage' },
    medium: { primary: '#F59E0B', bg: '#F59E0B/20', label: 'Balanced', desc: 'Mixed focus' },
    low: { primary: '#6366F1', bg: '#6366F1/20', label: 'Focused', desc: 'Specialized' }, // Changed from red to indigo
  };

  const { primary, label, desc } = colors[rating];

  // Calculate arc for gauge (based on entropy 0-1)
  const circumference = 2 * Math.PI * 28; // radius = 28
  const strokeDasharray = `${entropy * circumference * 0.75} ${circumference}`;

  return (
    <div className="flex flex-col items-center py-2">
      <div className="relative w-20 h-20">
        {/* Background arc */}
        <svg className="w-full h-full -rotate-90" viewBox="0 0 64 64">
          <circle
            cx="32"
            cy="32"
            r="28"
            fill="none"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="4"
            strokeDasharray={`${0.75 * circumference} ${circumference}`}
            strokeLinecap="round"
          />
          <circle
            cx="32"
            cy="32"
            r="28"
            fill="none"
            stroke={primary}
            strokeWidth="4"
            strokeDasharray={strokeDasharray}
            strokeLinecap="round"
            className="transition-all duration-1000"
          />
        </svg>

        {/* Center content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-lg font-bold" style={{ color: primary }}>
            {Math.round(entropy * 100)}%
          </span>
        </div>
      </div>

      <span className="text-xs font-mono mt-1" style={{ color: primary }}>
        {label}
      </span>
      <span className="text-[10px] text-muted mt-0.5">
        {desc}
      </span>

      {/* Focus indicator - v0.5.0: Changed from "Bias Detected" to "Focused Research" */}
      {biasScore > 0.5 && (
        <div className="mt-2 px-2 py-1 bg-indigo-500/10 text-indigo-400 text-xs font-mono rounded" title="Your research collection is concentrated on specific topics, which is typical for focused systematic reviews">
          Focused Research
        </div>
      )}
    </div>
  );
}

interface InsightHUDProps {
  projectId: string;
  className?: string;
}

export function InsightHUD({ projectId, className = '' }: InsightHUDProps) {
  const [metrics, setMetrics] = useState<GraphMetrics | null>(null);
  const [diversityMetrics, setDiversityMetrics] = useState<DiversityMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showDiversityPanel, setShowDiversityPanel] = useState(false);

  useEffect(() => {
    async function fetchMetrics() {
      if (!projectId) return;

      setIsLoading(true);
      setError(null);

      try {
        // Fetch both metrics in parallel
        const [graphData, diversityData] = await Promise.all([
          api.getGraphMetrics(projectId),
          api.getDiversityMetrics(projectId).catch(() => null), // Graceful fallback
        ]);

        setMetrics(graphData);
        setDiversityMetrics(diversityData);
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
            {/* Diversity Gauge (Phase 4) */}
            {diversityMetrics && (
              <div className="mb-4 pb-3 border-b border-white/10">
                <button
                  className="w-full"
                  onClick={() => setShowDiversityPanel(!showDiversityPanel)}
                >
                  <DiversityGauge
                    rating={diversityMetrics.diversity_rating as 'high' | 'medium' | 'low'}
                    entropy={diversityMetrics.normalized_entropy}
                    biasScore={diversityMetrics.bias_score}
                  />
                </button>

                {/* Expanded diversity details - v0.5.0: Simplified with explanations */}
                {showDiversityPanel && (
                  <div className="mt-3 pt-3 border-t border-white/5 space-y-2">
                    <div className="text-[10px] text-muted/70 mb-2">
                      📊 Advanced Metrics (click to collapse)
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-muted" title="Measures topic variety (higher = more topics)">Shannon Entropy</span>
                      <span className="text-white font-mono">{diversityMetrics.shannon_entropy.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-muted" title="Cluster size inequality (0 = equal, 1 = one dominant)">Gini Coefficient</span>
                      <span className="text-white font-mono">{diversityMetrics.gini_coefficient.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-muted" title="Largest topic cluster proportion">Main Topic</span>
                      <span className="text-white font-mono">{Math.round(diversityMetrics.dominant_cluster_ratio * 100)}%</span>
                    </div>
                    {/* Cluster size distribution */}
                    {diversityMetrics.cluster_sizes.length > 0 && (
                      <div className="mt-2">
                        <span className="text-xs text-muted block mb-1">Topic Distribution</span>
                        <div className="flex gap-1 h-4">
                          {diversityMetrics.cluster_sizes.map((size, i) => {
                            const maxSize = Math.max(...diversityMetrics.cluster_sizes);
                            const height = maxSize > 0 ? (size / maxSize) * 100 : 0;
                            return (
                              <div
                                key={i}
                                className="flex-1 bg-accent-teal/50 rounded-t"
                                style={{ height: `${height}%` }}
                                title={`Topic ${i + 1}: ${size} concepts`}
                              />
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

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
