'use client';

import { useState, useCallback, useEffect, useMemo } from 'react';
import {
  Scissors,
  RotateCcw,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  Loader2,
  Network,
  Target,
  Share2,
  Eye,
  EyeOff,
  AlertTriangle,
} from 'lucide-react';
import { useGraph3DStore } from '@/hooks/useGraph3DStore';
import { api } from '@/lib/api';

interface CentralityPanelProps {
  projectId: string;
  className?: string;
  onSlicingApplied?: () => void;
  onSlicingReset?: () => void;
}

type CentralityMetric = 'betweenness' | 'degree' | 'eigenvector';

const metricInfo: Record<CentralityMetric, { label: string; icon: React.ReactNode; description: string }> = {
  betweenness: {
    label: 'Betweenness',
    icon: <Share2 className="w-3 h-3" />,
    description: 'Bridge nodes connecting clusters',
  },
  degree: {
    label: 'Degree',
    icon: <Network className="w-3 h-3" />,
    description: 'Hub nodes with most connections',
  },
  eigenvector: {
    label: 'Eigenvector',
    icon: <Target className="w-3 h-3" />,
    description: 'Influential nodes in the network',
  },
};

export function CentralityPanel({
  projectId,
  className = '',
  onSlicingApplied,
  onSlicingReset,
}: CentralityPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [sliceCount, setSliceCount] = useState(5);
  const [metric, setMetric] = useState<CentralityMetric>('betweenness');
  // v0.8.0: Preview mode state
  const [showPreview, setShowPreview] = useState(true);

  const {
    slicing,
    slicedNodeIds,
    topBridges,
    setSliceCount: setStoreSliceCount,
    setSliceMetric,
    applySlicing,
    resetSlicing,
    fetchCentrality,
  } = useGraph3DStore();

  // Fetch initial centrality data
  useEffect(() => {
    fetchCentrality(projectId);
  }, [projectId, fetchCentrality]);

  // v0.8.0: Calculate preview nodes (nodes that will be removed)
  const previewNodeIds = useMemo(() => {
    if (!showPreview || topBridges.length === 0) return [];
    return topBridges.slice(0, sliceCount).map(b => b.id);
  }, [topBridges, sliceCount, showPreview]);

  const handleSlice = useCallback(async () => {
    setIsLoading(true);
    try {
      setStoreSliceCount(sliceCount);
      setSliceMetric(metric);
      await applySlicing(projectId);
      onSlicingApplied?.();
    } catch (error) {
      console.error('Failed to apply slicing:', error);
    } finally {
      setIsLoading(false);
    }
  }, [sliceCount, metric, projectId, setStoreSliceCount, setSliceMetric, applySlicing, onSlicingApplied]);

  const handleReset = useCallback(() => {
    resetSlicing();
    onSlicingReset?.();
  }, [resetSlicing, onSlicingReset]);

  return (
    <div
      className={`bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 ${className}`}
      style={{ width: '280px' }}
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-surface/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Scissors className="w-4 h-4 text-accent-teal" />
          <span className="font-mono text-xs uppercase tracking-wider text-ink dark:text-paper">
            Node Slicing
          </span>
          {slicing.isActive && (
            <span className="px-1.5 py-0.5 bg-accent-amber/20 text-accent-amber font-mono text-[10px]">
              ACTIVE
            </span>
          )}
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
          {/* Metric Selection */}
          <div>
            <p className="font-mono text-[10px] uppercase tracking-wider text-muted mb-2">
              Centrality Metric
            </p>
            <div className="flex gap-1">
              {(Object.keys(metricInfo) as CentralityMetric[]).map((m) => (
                <button
                  key={m}
                  onClick={() => setMetric(m)}
                  className={`flex-1 px-2 py-1.5 text-xs transition-colors ${
                    metric === m
                      ? 'bg-accent-teal text-white'
                      : 'bg-surface/5 hover:bg-surface/10 text-muted hover:text-ink dark:hover:text-paper'
                  }`}
                  title={metricInfo[m].description}
                >
                  <div className="flex items-center justify-center gap-1">
                    {metricInfo[m].icon}
                    <span className="hidden sm:inline">{metricInfo[m].label}</span>
                  </div>
                </button>
              ))}
            </div>
            <p className="text-[10px] text-muted mt-1">{metricInfo[metric].description}</p>
          </div>

          {/* Slider */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <p className="font-mono text-[10px] uppercase tracking-wider text-muted">
                Remove Top Nodes
              </p>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm text-accent-teal">{sliceCount}</span>
                {/* v0.8.0: Preview toggle */}
                <button
                  onClick={() => setShowPreview(!showPreview)}
                  className={`p-1 transition-colors ${
                    showPreview
                      ? 'text-accent-amber'
                      : 'text-muted hover:text-ink dark:hover:text-paper'
                  }`}
                  title={showPreview ? 'Hide preview' : 'Show preview'}
                >
                  {showPreview ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                </button>
              </div>
            </div>
            <input
              type="range"
              min={1}
              max={20}
              step={1}
              value={sliceCount}
              onChange={(e) => setSliceCount(parseInt(e.target.value))}
              className="w-full h-2 bg-surface/20 rounded-none appearance-none cursor-pointer
                [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                [&::-webkit-slider-thumb]:bg-accent-teal [&::-webkit-slider-thumb]:rounded-none
                [&::-webkit-slider-thumb]:border-0 [&::-webkit-slider-thumb]:cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-muted mt-1">
              <span>1</span>
              <span>20</span>
            </div>
            {/* v0.8.0: Preview indicator */}
            {showPreview && previewNodeIds.length > 0 && !slicing.isActive && (
              <div className="mt-2 px-2 py-1 bg-accent-amber/10 border-l-2 border-accent-amber">
                <div className="flex items-center gap-1.5">
                  <AlertTriangle className="w-3 h-3 text-accent-amber" />
                  <span className="text-[10px] text-accent-amber">
                    Preview: {previewNodeIds.length} node{previewNodeIds.length !== 1 ? 's' : ''} will be removed
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button
              onClick={handleSlice}
              disabled={isLoading || topBridges.length === 0}
              className={`flex-1 px-3 py-2 font-mono text-xs uppercase tracking-wider transition-colors
                ${slicing.isActive
                  ? 'bg-surface/10 text-muted cursor-not-allowed'
                  : 'bg-accent-teal text-white hover:bg-accent-teal/90'
                }
                disabled:opacity-50 disabled:cursor-not-allowed`}
              title={slicing.isActive ? 'Reset first to change slicing' : `Remove top ${sliceCount} nodes`}
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin mx-auto" />
              ) : (
                <div className="flex items-center justify-center gap-1.5">
                  <Scissors className="w-3.5 h-3.5" />
                  {slicing.isActive ? 'Applied' : 'Apply Slicing'}
                </div>
              )}
            </button>
            <button
              onClick={handleReset}
              disabled={!slicing.isActive}
              className="px-3 py-2 bg-surface/10 hover:bg-surface/20 text-muted hover:text-ink dark:hover:text-paper
                font-mono text-xs uppercase tracking-wider transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed"
              title="Reset to original graph"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

          {/* v0.8.0: Reset hint when slicing is active */}
          {slicing.isActive && (
            <p className="text-[10px] text-muted text-center">
              Click Reset to restore nodes and try different settings
            </p>
          )}

          {/* Top Bridges List */}
          {topBridges.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <TrendingUp className="w-3 h-3 text-accent-amber" />
                <p className="font-mono text-[10px] uppercase tracking-wider text-muted">
                  Top Bridge Nodes
                </p>
              </div>
              <ul className="space-y-1 max-h-40 overflow-y-auto">
                {topBridges.slice(0, Math.max(sliceCount, 5)).map((bridge, index) => {
                  // v0.8.0: Determine node state for styling
                  const isSliced = slicedNodeIds.includes(bridge.id);
                  const isInPreview = showPreview && index < sliceCount && !slicing.isActive;
                  const isAboveThreshold = index < sliceCount;

                  return (
                    <li
                      key={bridge.id}
                      className={`flex items-center justify-between text-xs px-2 py-1.5 transition-colors ${
                        isSliced
                          ? 'bg-accent-amber/20 border-l-2 border-accent-amber'
                          : isInPreview
                          ? 'bg-accent-amber/10 border-l-2 border-accent-amber/50'
                          : isAboveThreshold
                          ? 'bg-surface/10'
                          : 'bg-surface/5'
                      }`}
                    >
                      <span className="flex items-center gap-2 truncate">
                        <span className={`font-mono ${isAboveThreshold ? 'text-accent-amber' : 'text-muted'}`}>
                          {index + 1}.
                        </span>
                        <span className={`truncate ${
                          isSliced || isInPreview
                            ? 'text-accent-amber'
                            : 'text-ink dark:text-paper'
                        }`}>
                          {bridge.name || bridge.id}
                        </span>
                        {/* v0.8.0: Preview badge */}
                        {isInPreview && (
                          <span className="px-1 py-0.5 bg-accent-amber/20 text-accent-amber text-[8px] font-mono uppercase">
                            Remove
                          </span>
                        )}
                      </span>
                      <span className="font-mono text-[10px] text-muted ml-2">
                        {(bridge.score * 100).toFixed(1)}%
                      </span>
                    </li>
                  );
                })}
              </ul>
              {topBridges.length > Math.max(sliceCount, 5) && (
                <p className="text-[10px] text-muted mt-1 text-center">
                  +{topBridges.length - Math.max(sliceCount, 5)} more
                </p>
              )}
            </div>
          )}

          {/* Status */}
          {slicing.isActive && (
            <div className="bg-accent-amber/10 border-l-2 border-accent-amber px-3 py-2">
              <p className="text-xs text-accent-amber">
                {slicedNodeIds.length} node{slicedNodeIds.length !== 1 ? 's' : ''} removed
              </p>
              <p className="text-[10px] text-muted mt-0.5">
                Hidden connections may now be visible
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default CentralityPanel;
