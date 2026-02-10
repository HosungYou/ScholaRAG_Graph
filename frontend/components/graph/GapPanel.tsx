'use client';

import { useState, useCallback } from 'react';
import {
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Lightbulb,
  ArrowRight,
  Eye,
  EyeOff,
  RefreshCw,
  HelpCircle,
  Loader2,
  Copy,
  Check,
  Hexagon,
  Zap,
  BookOpen,
  Download,
} from 'lucide-react';
import type { StructuralGap, ConceptCluster, GraphEntity, BridgeHypothesis, BridgeGenerationResult } from '@/types';
import { api } from '@/lib/api';
import { BridgeHypothesisList } from './BridgeHypothesisCard';

/* ============================================================
   GapPanel - VS Design Diverge Style
   Direction B (T-Score 0.4) "Editorial Research"

   Design Principles:
   - Line-based layout (no rounded-lg, minimal border-radius)
   - Left accent bars for emphasis
   - Monospace labels and metadata
   - High-contrast cluster colors
   - Decorative corner accents
   ============================================================ */

// VS Design Diverge high-contrast cluster colors
const clusterColors = [
  '#E63946', '#2EC4B6', '#F4A261', '#457B9D', '#A8DADC',
  '#9D4EDD', '#06D6A0', '#118AB2', '#EF476F', '#FFD166',
  '#073B4C', '#7209B7',
];

interface GapPanelProps {
  projectId: string;
  gaps: StructuralGap[];
  clusters: ConceptCluster[];
  nodes?: GraphEntity[];  // For mapping bridge candidate UUIDs to names
  onGapSelect: (gap: StructuralGap) => void;
  onHighlightNodes: (nodeIds: string[]) => void;
  onClearHighlights: () => void;
  isLoading?: boolean;
  onRefresh?: () => Promise<void>;
  // Minimize toggle - controlled by parent for MiniMap offset coordination
  isMinimized?: boolean;
  onToggleMinimize?: () => void;
}

export function GapPanel({
  projectId,
  gaps,
  clusters,
  nodes = [],
  onGapSelect,
  onHighlightNodes,
  onClearHighlights,
  isLoading = false,
  onRefresh,
  isMinimized = false,
  onToggleMinimize,
}: GapPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [selectedGap, setSelectedGap] = useState<StructuralGap | null>(null);
  const [expandedGapId, setExpandedGapId] = useState<string | null>(null);
  const [copiedQuestionId, setCopiedQuestionId] = useState<string | null>(null);
  const [showAllGaps, setShowAllGaps] = useState(false);
  // Bridge Hypothesis state (Phase 3)
  const [bridgeResults, setBridgeResults] = useState<Record<string, BridgeGenerationResult>>({});
  const [generatingBridgeFor, setGeneratingBridgeFor] = useState<string | null>(null);
  const [showBridgeFor, setShowBridgeFor] = useState<string | null>(null);
  // Paper Recommendations state (Phase 2)
  const [recommendations, setRecommendations] = useState<Record<string, {
    papers: Array<{ title: string; year: number | null; citation_count: number; url: string | null; abstract_snippet: string }>;
    query_used: string;
    error: string | null;
  }>>({});
  const [loadingRecsFor, setLoadingRecsFor] = useState<string | null>(null);

  // Sort gaps by strength (highest first)
  const sortedGaps = [...gaps].sort((a, b) => b.gap_strength - a.gap_strength);
  const displayedGaps = showAllGaps ? sortedGaps : sortedGaps.slice(0, 5);

  // Get cluster label or generate one
  const getClusterLabel = useCallback((clusterId: number) => {
    const cluster = clusters.find(c => c.cluster_id === clusterId);
    // Priority 1: LLM-generated label (skip UUID-like strings)
    if (cluster?.label && !/^[0-9a-f]{8}-[0-9a-f]{4}-/.test(cluster.label)) {
      return cluster.label;
    }
    // Priority 2: concept_names from cluster
    if (cluster?.concept_names && cluster.concept_names.length > 0) {
      const filtered = cluster.concept_names.filter((n: string) => n && n.trim());
      if (filtered.length > 0) return filtered.slice(0, 3).join(' / ');
    }
    // Priority 3: names from gaps data (always populated)
    for (const gap of gaps) {
      if (gap.cluster_a_id === clusterId && gap.cluster_a_names?.length > 0) {
        return gap.cluster_a_names.slice(0, 3).join(' / ');
      }
      if (gap.cluster_b_id === clusterId && gap.cluster_b_names?.length > 0) {
        return gap.cluster_b_names.slice(0, 3).join(' / ');
      }
    }
    return `Cluster ${clusterId + 1}`;
  }, [clusters, gaps]);

  // Get cluster color
  const getClusterColor = useCallback((clusterId: number) => {
    return clusterColors[clusterId % clusterColors.length];
  }, []);

  // Get node name from UUID (for bridge candidates)
  const getNodeName = useCallback((nodeId: string): string => {
    const node = nodes.find(n => n.id === nodeId);
    return node?.name || nodeId.slice(0, 8) + '...';  // Fallback to truncated UUID
  }, [nodes]);

  // Handle gap click
  const handleGapClick = useCallback((gap: StructuralGap) => {
    setSelectedGap(gap);
    setExpandedGapId(gap.id === expandedGapId ? null : gap.id);
    onGapSelect(gap);

    // Highlight all concepts in both clusters
    const allConceptIds = [
      ...gap.cluster_a_concepts,
      ...gap.cluster_b_concepts,
      ...gap.bridge_candidates,
    ];
    onHighlightNodes(allConceptIds);
  }, [expandedGapId, onGapSelect, onHighlightNodes]);

  // Handle clear highlights
  const handleClearHighlights = useCallback(() => {
    setSelectedGap(null);
    setExpandedGapId(null);
    onClearHighlights();
  }, [onClearHighlights]);

  // Handle copy question
  const handleCopyQuestion = useCallback(async (question: string, gapId: string, qIndex: number) => {
    try {
      await navigator.clipboard.writeText(question);
      setCopiedQuestionId(`${gapId}-${qIndex}`);
      setTimeout(() => setCopiedQuestionId(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, []);

  // Format gap strength as percentage
  const formatGapStrength = useCallback((strength: number) => {
    return `${Math.round(strength * 100)}%`;
  }, []);

  // Generate bridge hypotheses (Phase 3)
  const handleGenerateBridge = useCallback(async (gapId: string) => {
    if (generatingBridgeFor) return; // Prevent multiple simultaneous requests

    setGeneratingBridgeFor(gapId);
    try {
      const result = await api.generateBridgeHypotheses(gapId);
      setBridgeResults(prev => ({
        ...prev,
        [gapId]: result,
      }));
      setShowBridgeFor(gapId);
    } catch (error) {
      console.error('Failed to generate bridge hypotheses:', error);
    } finally {
      setGeneratingBridgeFor(null);
    }
  }, [generatingBridgeFor]);

  // State for bridge creation
  const [creatingBridge, setCreatingBridge] = useState(false);
  const [bridgeCreationResult, setBridgeCreationResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  // Handle accepting a bridge hypothesis
  const handleAcceptBridge = useCallback(async (hypothesis: BridgeHypothesis) => {
    if (!selectedGap || creatingBridge) return;

    setCreatingBridge(true);
    setBridgeCreationResult(null);

    try {
      const result = await api.createBridge(selectedGap.id, {
        hypothesis_title: hypothesis.title,
        hypothesis_description: hypothesis.description,
        connecting_concepts: hypothesis.connecting_concepts,
        confidence: hypothesis.confidence,
      });

      setBridgeCreationResult({
        success: result.success,
        message: result.message,
      });

      // Refresh gap analysis to reflect new bridges
      if (result.success && onRefresh) {
        await onRefresh();
      }
    } catch (error) {
      console.error('Failed to create bridge:', error);
      setBridgeCreationResult({
        success: false,
        message: error instanceof Error ? error.message : 'Failed to create bridge',
      });
    } finally {
      setCreatingBridge(false);
    }
  }, [selectedGap, creatingBridge, onRefresh]);

  // Find papers for a gap (Phase 2)
  const handleFindPapers = useCallback(async (gapId: string) => {
    if (loadingRecsFor || recommendations[gapId]) return;
    setLoadingRecsFor(gapId);
    try {
      const result = await api.getGapRecommendations(projectId, gapId, 5);
      setRecommendations(prev => ({ ...prev, [gapId]: result }));
    } catch (error) {
      console.error('Failed to fetch recommendations:', error);
      setRecommendations(prev => ({
        ...prev,
        [gapId]: { papers: [], query_used: '', error: 'Failed to load recommendations' },
      }));
    } finally {
      setLoadingRecsFor(null);
    }
  }, [loadingRecsFor, projectId, recommendations]);

  return (
    <div className={`absolute top-4 left-4 bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 max-h-[80vh] overflow-hidden z-20 transition-all duration-300 ${
      isMinimized ? 'w-12' : 'w-64'
    }`}>
      {/* Decorative corner accent - only show when not minimized */}
      {!isMinimized && (
        <div className="absolute top-0 right-0 w-16 h-16 bg-accent-amber/10 transform rotate-45 translate-x-8 -translate-y-8" />
      )}

      {/* Minimize Toggle Button */}
      {onToggleMinimize && (
        <button
          onClick={onToggleMinimize}
          className="absolute top-2 -right-3 w-6 h-6 bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 flex items-center justify-center z-30 hover:bg-surface/10 transition-colors"
          title={isMinimized ? 'Expand panel' : 'Minimize panel'}
        >
          {isMinimized ? (
            <ChevronRight className="w-3 h-3 text-muted" />
          ) : (
            <ChevronLeft className="w-3 h-3 text-muted" />
          )}
        </button>
      )}

      {/* Minimized State - Icon only */}
      {isMinimized ? (
        <div className="p-3 flex flex-col items-center gap-2">
          <div className="w-6 h-6 flex items-center justify-center bg-accent-amber/10">
            <Sparkles className="w-3 h-3 text-accent-amber" />
          </div>
          {gaps.length > 0 && (
            <span className="font-mono text-xs text-accent-amber">{gaps.length}</span>
          )}
        </div>
      ) : (
        <>
          {/* Header */}
          <div
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full flex items-center justify-between p-3 hover:bg-surface/5 transition-colors border-b border-ink/10 dark:border-paper/10 relative cursor-pointer"
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && setIsExpanded(!isExpanded)}
          >
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 flex items-center justify-center bg-accent-amber/10">
                <Sparkles className="w-3 h-3 text-accent-amber" />
              </div>
              <div className="text-left">
                <span className="font-mono text-xs uppercase tracking-wider text-ink dark:text-paper block">
                  Research Gaps
                </span>
                {gaps.length > 0 && (
                  <span className="font-mono text-xs text-accent-amber">
                    {gaps.length} detected
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1">
              {isLoading && <Loader2 className="w-3 h-3 text-accent-teal animate-spin" />}
              {onRefresh && !isLoading && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onRefresh();
                  }}
                  className="p-1 hover:bg-surface/10 transition-colors"
                  title="Refresh gap analysis"
                >
                  <RefreshCw className="w-3 h-3 text-muted hover:text-accent-teal transition-colors" />
                </button>
              )}
              {isExpanded ? (
                <ChevronUp className="w-3 h-3 text-muted" />
              ) : (
                <ChevronDown className="w-3 h-3 text-muted" />
              )}
            </div>
          </div>

      {/* Content */}
      {isExpanded && (
        <div className="overflow-y-auto max-h-[calc(80vh-80px)]">
          {/* Description */}
          <div className="p-4 border-b border-ink/10 dark:border-paper/10 relative">
            <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-accent-teal/50" />
            <div className="flex items-start gap-2 pl-3">
              <HelpCircle className="w-4 h-4 text-accent-teal mt-0.5 flex-shrink-0" />
              <p className="text-xs text-muted leading-relaxed">
                Research gaps are areas where concept clusters have weak connections.
                Click a gap to see AI-suggested research questions.
              </p>
            </div>
          </div>

          {/* Gaps List */}
          {gaps.length === 0 ? (
            <div className="p-8 text-center">
              <div className="w-16 h-16 flex items-center justify-center bg-surface/5 mx-auto mb-4">
                <Sparkles className="w-8 h-8 text-muted" />
              </div>
              <p className="font-mono text-xs text-muted uppercase tracking-wider mb-2">No Gaps Detected</p>
              <p className="text-sm text-muted">
                Import more papers to discover potential research opportunities
              </p>
            </div>
          ) : (
            <div className="p-3 space-y-2">
              {displayedGaps.map((gap, gapIndex) => {
                const isSelected = selectedGap?.id === gap.id;
                const isExpandedItem = expandedGapId === gap.id;

                return (
                  <div
                    key={gap.id}
                    className={`border transition-all relative ${
                      isSelected
                        ? 'border-accent-amber/50 bg-accent-amber/5'
                        : 'border-ink/10 dark:border-paper/10 hover:border-ink/20 dark:hover:border-paper/20'
                    }`}
                  >
                    {/* Gap number badge */}
                    <div className="absolute -top-2 -left-2 w-6 h-6 flex items-center justify-center bg-surface text-white font-mono text-xs">
                      {String(gapIndex + 1).padStart(2, '0')}
                    </div>

                    {/* Gap Header */}
                    <button
                      onClick={() => handleGapClick(gap)}
                      className="w-full p-4 pt-3 text-left"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <div
                            className="w-3 h-3"
                            style={{ backgroundColor: getClusterColor(gap.cluster_a_id) }}
                          />
                          <span className="font-mono text-xs text-ink dark:text-paper truncate max-w-[70px]">
                            {getClusterLabel(gap.cluster_a_id)}
                          </span>
                          <ArrowRight className="w-3 h-3 text-muted" />
                          <div
                            className="w-3 h-3"
                            style={{ backgroundColor: getClusterColor(gap.cluster_b_id) }}
                          />
                          <span className="font-mono text-xs text-ink dark:text-paper truncate max-w-[70px]">
                            {getClusterLabel(gap.cluster_b_id)}
                          </span>
                        </div>
                        <span className={`font-mono text-xs px-2 py-0.5 ${
                          gap.gap_strength > 0.7
                            ? 'bg-accent-red/10 text-accent-red'
                            : gap.gap_strength > 0.4
                            ? 'bg-accent-amber/10 text-accent-amber'
                            : 'bg-accent-teal/10 text-accent-teal'
                        }`}>
                          {formatGapStrength(gap.gap_strength)}
                        </span>
                      </div>

                      {/* Gap Preview */}
                      <div className="flex items-center justify-between">
                        <p className="text-xs text-muted truncate flex-1 mr-2">
                          {gap.cluster_a_names.slice(0, 2).join(', ')} ↔ {gap.cluster_b_names.slice(0, 2).join(', ')}
                        </p>
                        {isExpandedItem ? (
                          <ChevronUp className="w-3 h-3 text-muted flex-shrink-0" />
                        ) : (
                          <ChevronDown className="w-3 h-3 text-muted flex-shrink-0" />
                        )}
                      </div>
                    </button>

                    {/* Expanded Content */}
                    {isExpandedItem && (
                      <div className="px-4 pb-4 space-y-4 border-t border-ink/10 dark:border-paper/10 pt-4">
                        {/* Bridge Candidates */}
                        {gap.bridge_candidates.length > 0 && (
                          <div>
                            <p className="font-mono text-xs uppercase tracking-wider text-accent-amber mb-2 flex items-center gap-1">
                              <Sparkles className="w-3 h-3" />
                              Bridge Concepts
                            </p>
                            <div className="flex flex-wrap gap-1">
                              {gap.bridge_candidates.slice(0, 5).map((candidate, idx) => (
                                <span
                                  key={idx}
                                  className="font-mono text-xs px-2 py-1 bg-accent-amber/10 text-accent-amber border border-accent-amber/30"
                                  title={candidate}  // Show full UUID on hover
                                >
                                  {getNodeName(candidate)}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Generate Bridge Button (Phase 3) */}
                        <div className="pt-2 border-t border-ink/5 dark:border-paper/5">
                          <button
                            onClick={() => handleGenerateBridge(gap.id)}
                            disabled={generatingBridgeFor === gap.id}
                            className={`w-full py-2.5 px-4 font-mono text-xs uppercase tracking-wider transition-colors flex items-center justify-center gap-2 ${
                              generatingBridgeFor === gap.id
                                ? 'bg-accent-amber/20 text-accent-amber cursor-wait'
                                : bridgeResults[gap.id]
                                ? 'bg-accent-teal/10 hover:bg-accent-teal/20 text-accent-teal border border-accent-teal/30'
                                : 'bg-accent-amber/10 hover:bg-accent-amber/20 text-accent-amber border border-accent-amber/30'
                            }`}
                          >
                            {generatingBridgeFor === gap.id ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Generating Bridge Ideas...
                              </>
                            ) : bridgeResults[gap.id] ? (
                              <>
                                <Eye className="w-4 h-4" />
                                {showBridgeFor === gap.id ? 'Hide' : 'Show'} Bridge Ideas
                              </>
                            ) : (
                              <>
                                <Zap className="w-4 h-4" />
                                Generate Bridge Ideas
                              </>
                            )}
                          </button>

                          {/* Toggle show/hide if results exist */}
                          {bridgeResults[gap.id] && (
                            <button
                              onClick={() => setShowBridgeFor(showBridgeFor === gap.id ? null : gap.id)}
                              className="w-full mt-2 py-1 text-xs text-muted hover:text-ink dark:hover:text-paper transition-colors"
                            >
                              {showBridgeFor === gap.id ? 'Hide' : 'Show'} {bridgeResults[gap.id].hypotheses.length} hypotheses
                            </button>
                          )}
                        </div>

                        {/* Bridge Hypotheses Display */}
                        {showBridgeFor === gap.id && bridgeResults[gap.id] && (
                          <div className="pt-4 mt-4 border-t border-ink/10 dark:border-paper/10">
                            {/* Bridge Creation Result Notification */}
                            {bridgeCreationResult && (
                              <div className={`mb-4 p-3 border-l-2 ${
                                bridgeCreationResult.success
                                  ? 'border-accent-teal bg-accent-teal/10 text-accent-teal'
                                  : 'border-accent-red bg-accent-red/10 text-accent-red'
                              }`}>
                                <p className="font-mono text-xs">
                                  {bridgeCreationResult.success ? '✓' : '✗'} {bridgeCreationResult.message}
                                </p>
                              </div>
                            )}

                            {/* Creating Bridge Loading State */}
                            {creatingBridge && (
                              <div className="mb-4 p-3 border-l-2 border-accent-amber bg-accent-amber/10">
                                <p className="font-mono text-xs text-accent-amber flex items-center gap-2">
                                  <Loader2 className="w-3 h-3 animate-spin" />
                                  Creating bridge relationships...
                                </p>
                              </div>
                            )}

                            <BridgeHypothesisList
                              hypotheses={bridgeResults[gap.id].hypotheses}
                              bridgeType={bridgeResults[gap.id].bridge_type as 'theoretical' | 'methodological' | 'empirical'}
                              keyInsight={bridgeResults[gap.id].key_insight}
                              onAccept={handleAcceptBridge}
                            />
                          </div>
                        )}

                        {/* Find Papers Button (Phase 2) */}
                        <div className="pt-2 border-t border-ink/5 dark:border-paper/5">
                          <button
                            onClick={() => handleFindPapers(gap.id)}
                            disabled={!!loadingRecsFor || !!recommendations[gap.id]}
                            className="w-full py-2 px-4 font-mono text-xs uppercase tracking-wider
                              bg-accent-teal/10 hover:bg-accent-teal/20 text-accent-teal
                              border border-accent-teal/30 transition-colors disabled:opacity-50
                              flex items-center justify-center gap-2"
                          >
                            {loadingRecsFor === gap.id ? (
                              <><Loader2 className="w-4 h-4 animate-spin" /> Searching...</>
                            ) : recommendations[gap.id] ? (
                              <><BookOpen className="w-4 h-4" /> {recommendations[gap.id].papers.length} Papers Found</>
                            ) : (
                              <><BookOpen className="w-4 h-4" /> Find Papers</>
                            )}
                          </button>
                        </div>

                        {/* Recommendation Results (Phase 2) */}
                        {recommendations[gap.id] && (
                          <div className="space-y-2 mt-2">
                            {recommendations[gap.id].error && (
                              <p className="text-xs text-accent-red font-mono px-2">
                                {recommendations[gap.id].error}
                              </p>
                            )}
                            {!recommendations[gap.id].error && recommendations[gap.id].papers.length === 0 && (
                              <p className="text-xs text-muted font-mono px-2">
                                No matching papers found for this gap.
                              </p>
                            )}
                            {recommendations[gap.id].papers.map((paper, idx) => (
                              <div key={idx} className="p-3 border border-ink/10 dark:border-paper/10 bg-surface/5">
                                <a href={paper.url || '#'} target="_blank" rel="noopener noreferrer"
                                   className="text-xs font-medium text-accent-teal hover:underline block mb-1">
                                  {paper.title}
                                </a>
                                <div className="flex items-center gap-3 font-mono text-xs text-muted">
                                  {paper.year && <span>{paper.year}</span>}
                                  <span>{paper.citation_count} citations</span>
                                </div>
                                {paper.abstract_snippet && (
                                  <p className="text-xs text-muted mt-1 line-clamp-2">{paper.abstract_snippet}</p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Research Questions */}
                        {gap.research_questions.length > 0 && (
                          <div className="pt-4 mt-4 border-t border-ink/10 dark:border-paper/10">
                            <p className="font-mono text-xs uppercase tracking-wider text-accent-teal mb-2 flex items-center gap-1">
                              <Lightbulb className="w-3 h-3" />
                              AI Research Questions
                            </p>
                            <div className="space-y-2">
                              {gap.research_questions.map((question, qIdx) => (
                                <div
                                  key={qIdx}
                                  className="relative bg-surface/5 p-3 group border-l-2 border-accent-teal/50"
                                >
                                  <div className="flex items-start justify-between gap-2">
                                    <p className="text-xs text-ink dark:text-paper leading-relaxed pr-6">
                                      {question}
                                    </p>
                                    <button
                                      onClick={() => handleCopyQuestion(question, gap.id, qIdx)}
                                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-surface/10"
                                      title="Copy question"
                                    >
                                      {copiedQuestionId === `${gap.id}-${qIdx}` ? (
                                        <Check className="w-3 h-3 text-accent-teal" />
                                      ) : (
                                        <Copy className="w-3 h-3 text-muted hover:text-ink dark:hover:text-paper" />
                                      )}
                                    </button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Concepts in each cluster */}
                        <div className="grid grid-cols-2 gap-3">
                          <div className="border border-ink/10 dark:border-paper/10 p-2">
                            <p className="font-mono text-xs text-muted mb-2 flex items-center gap-1">
                              <span
                                className="inline-block w-2 h-2"
                                style={{ backgroundColor: getClusterColor(gap.cluster_a_id) }}
                              />
                              Cluster A ({gap.cluster_a_names.length})
                            </p>
                            <div className="text-xs text-ink dark:text-paper space-y-1 max-h-24 overflow-y-auto">
                              {gap.cluster_a_names.slice(0, 5).map((name, idx) => (
                                <div key={idx} className="truncate font-mono">{name}</div>
                              ))}
                              {gap.cluster_a_names.length > 5 && (
                                <div className="text-muted font-mono">
                                  +{gap.cluster_a_names.length - 5} more
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="border border-ink/10 dark:border-paper/10 p-2">
                            <p className="font-mono text-xs text-muted mb-2 flex items-center gap-1">
                              <span
                                className="inline-block w-2 h-2"
                                style={{ backgroundColor: getClusterColor(gap.cluster_b_id) }}
                              />
                              Cluster B ({gap.cluster_b_names.length})
                            </p>
                            <div className="text-xs text-ink dark:text-paper space-y-1 max-h-24 overflow-y-auto">
                              {gap.cluster_b_names.slice(0, 5).map((name, idx) => (
                                <div key={idx} className="truncate font-mono">{name}</div>
                              ))}
                              {gap.cluster_b_names.length > 5 && (
                                <div className="text-muted font-mono">
                                  +{gap.cluster_b_names.length - 5} more
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Show More/Less */}
              {gaps.length > 5 && (
                <button
                  onClick={() => setShowAllGaps(!showAllGaps)}
                  className="w-full py-2 font-mono text-xs text-muted hover:text-accent-teal transition-colors flex items-center justify-center gap-2 border border-ink/10 dark:border-paper/10 hover:border-accent-teal/30"
                >
                  {showAllGaps ? (
                    <>
                      <EyeOff className="w-3 h-3" />
                      Show fewer gaps
                    </>
                  ) : (
                    <>
                      <Eye className="w-3 h-3" />
                      Show all {gaps.length} gaps
                    </>
                  )}
                </button>
              )}
            </div>
          )}

          {/* Clear Highlights Button */}
          {selectedGap && (
            <div className="p-3 border-t border-ink/10 dark:border-paper/10">
              <button
                onClick={handleClearHighlights}
                className="w-full py-2.5 px-3 bg-surface/10 hover:bg-surface/20 font-mono text-xs text-ink dark:text-paper uppercase tracking-wider transition-colors flex items-center justify-center gap-2"
              >
                <EyeOff className="w-4 h-4" />
                Clear Highlights
              </button>
            </div>
          )}

          {/* Cluster Overview */}
          {clusters.length > 0 && (
            <div className="p-4 border-t border-ink/10 dark:border-paper/10">
              <div className="flex items-center gap-2 mb-3">
                <Hexagon className="w-4 h-4 text-accent-teal" />
                <p className="font-mono text-xs uppercase tracking-wider text-ink dark:text-paper">
                  Concept Clusters
                </p>
              </div>
              <div className="grid grid-cols-2 gap-1">
                {clusters.slice(0, 12).map((cluster) => (
                  <div
                    key={cluster.cluster_id}
                    className="flex items-center gap-1.5 p-1.5 bg-surface/5 border border-ink/5 dark:border-paper/5 overflow-hidden"
                    title={`${getClusterLabel(cluster.cluster_id)}: ${cluster.size} concepts`}
                  >
                    <div
                      className="w-2 h-2 flex-shrink-0 rounded-sm"
                      style={{ backgroundColor: getClusterColor(cluster.cluster_id) }}
                    />
                    <span className="font-mono text-xs text-muted truncate">
                      {getClusterLabel(cluster.cluster_id)}
                    </span>
                    <span className="font-mono text-[10px] text-muted/50 flex-shrink-0 ml-auto">
                      {cluster.size}
                    </span>
                  </div>
                ))}
              </div>
              <p className="font-mono text-xs text-muted mt-3">
                {clusters.reduce((sum, c) => sum + c.size, 0)} concepts in {clusters.length} clusters
              </p>
            </div>
          )}

            {/* Export Report Button (Phase 3) */}
            {gaps.length > 0 && (
              <div className="p-4 border-t border-ink/10 dark:border-paper/10">
                <button
                  onClick={async () => {
                    try {
                      await api.exportGapReport(projectId);
                    } catch (error) {
                      console.error('Export failed:', error);
                    }
                  }}
                  className="w-full py-2.5 px-3 bg-surface/10 hover:bg-surface/20
                    font-mono text-xs text-ink dark:text-paper uppercase tracking-wider
                    transition-colors flex items-center justify-center gap-2
                    border border-ink/10 dark:border-paper/10"
                >
                  <Download className="w-4 h-4" />
                  Export Report
                </button>
              </div>
            )}
        </div>
      )}
        </>
      )}
    </div>
  );
}
