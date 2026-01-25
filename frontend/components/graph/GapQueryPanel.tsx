'use client';

import { useState, useCallback } from 'react';
import {
  Sparkles,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  Link2,
  Users,
} from 'lucide-react';
import { BridgeHypothesisList } from './BridgeHypothesisCard';
import type { StructuralGap, ConceptCluster, BridgeGenerationResult, BridgeHypothesis } from '@/types';

/* ============================================================
   GapQueryPanel - Research Question Generation Panel
   InfraNodus-style AI Bridge Hypothesis Generator

   Displays gap information and generates research questions
   that could bridge the structural gap between clusters.
   ============================================================ */

interface GapQueryPanelProps {
  gap: StructuralGap;
  clusters: ConceptCluster[];
  projectId: string;
  onAcceptHypothesis?: (hypothesis: BridgeHypothesis) => void;
}

export function GapQueryPanel({
  gap,
  clusters,
  projectId,
  onAcceptHypothesis,
}: GapQueryPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<BridgeGenerationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Get cluster names
  const getClusterName = useCallback((clusterId: number) => {
    const cluster = clusters.find(c => c.cluster_id === clusterId);
    return cluster?.label || `Cluster ${clusterId + 1}`;
  }, [clusters]);

  // Get cluster concepts (first 5)
  const getClusterConcepts = useCallback((clusterId: number) => {
    const cluster = clusters.find(c => c.cluster_id === clusterId);
    if (!cluster) return [];
    return cluster.concept_names.slice(0, 5);
  }, [clusters]);

  // Generate bridge hypotheses
  const handleGenerate = useCallback(async () => {
    setIsGenerating(true);
    setError(null);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/graph/gaps/${gap.id}/generate-bridge`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            project_id: projectId,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to generate bridge hypotheses: ${response.statusText}`);
      }

      const data: BridgeGenerationResult = await response.json();
      setResult(data);
    } catch (err) {
      console.error('Error generating bridge hypotheses:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate research questions');
    } finally {
      setIsGenerating(false);
    }
  }, [gap.id, projectId]);

  const clusterAName = getClusterName(gap.cluster_a_id);
  const clusterBName = getClusterName(gap.cluster_b_id);
  const clusterAConcepts = getClusterConcepts(gap.cluster_a_id);
  const clusterBConcepts = getClusterConcepts(gap.cluster_b_id);

  return (
    <div className="absolute bottom-20 right-4 w-96 bg-[#161b22]/95 backdrop-blur-sm border border-white/10 rounded-lg overflow-hidden shadow-xl">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-3 flex items-center justify-between hover:bg-white/5 transition-colors border-b border-white/10"
      >
        <div className="flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-accent-amber" />
          <span className="font-mono text-xs uppercase tracking-wider text-white">
            Gap Analysis
          </span>
          <span className="text-xs px-1.5 py-0.5 bg-amber-500/20 text-amber-400 rounded">
            {(gap.gap_strength * 100).toFixed(0)}%
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted" />
        )}
      </button>

      {isExpanded && (
        <div className="max-h-[500px] overflow-y-auto">
          {/* Gap Info */}
          <div className="p-4 space-y-4 border-b border-white/10">
            {/* Cluster A */}
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 flex items-center justify-center bg-accent-coral/20 text-accent-coral font-mono text-xs rounded">
                A
              </div>
              <div className="flex-1">
                <div className="text-sm text-white font-medium mb-1">{clusterAName}</div>
                <div className="flex flex-wrap gap-1">
                  {clusterAConcepts.map((concept, i) => (
                    <span key={i} className="text-xs px-1.5 py-0.5 bg-white/10 text-white/70 rounded">
                      {concept}
                    </span>
                  ))}
                  {gap.cluster_a_concepts.length > 5 && (
                    <span className="text-xs text-muted">
                      +{gap.cluster_a_concepts.length - 5} more
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Gap indicator */}
            <div className="flex items-center justify-center gap-2 py-2">
              <div className="flex-1 h-px bg-white/20" />
              <Link2 className="w-4 h-4 text-amber-400 rotate-90" />
              <span className="text-xs text-amber-400 font-mono">STRUCTURAL GAP</span>
              <Link2 className="w-4 h-4 text-amber-400 rotate-90" />
              <div className="flex-1 h-px bg-white/20" />
            </div>

            {/* Cluster B */}
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 flex items-center justify-center bg-accent-teal/20 text-accent-teal font-mono text-xs rounded">
                B
              </div>
              <div className="flex-1">
                <div className="text-sm text-white font-medium mb-1">{clusterBName}</div>
                <div className="flex flex-wrap gap-1">
                  {clusterBConcepts.map((concept, i) => (
                    <span key={i} className="text-xs px-1.5 py-0.5 bg-white/10 text-white/70 rounded">
                      {concept}
                    </span>
                  ))}
                  {gap.cluster_b_concepts.length > 5 && (
                    <span className="text-xs text-muted">
                      +{gap.cluster_b_concepts.length - 5} more
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Bridge Candidates */}
            {gap.bridge_candidates.length > 0 && (
              <div className="p-3 bg-accent-amber/5 border border-accent-amber/20 rounded">
                <div className="flex items-center gap-2 mb-2">
                  <Users className="w-4 h-4 text-accent-amber" />
                  <span className="font-mono text-xs uppercase tracking-wider text-accent-amber">
                    Bridge Candidates ({gap.bridge_candidates.length})
                  </span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {gap.bridge_candidates.slice(0, 3).map((candidate, i) => {
                    // Try to find the concept name
                    const clusterA = clusters.find(c => c.cluster_id === gap.cluster_a_id);
                    const clusterB = clusters.find(c => c.cluster_id === gap.cluster_b_id);
                    const indexA = clusterA?.concepts.indexOf(candidate);
                    const indexB = clusterB?.concepts.indexOf(candidate);
                    const name = indexA !== undefined && indexA >= 0
                      ? clusterA?.concept_names[indexA]
                      : indexB !== undefined && indexB >= 0
                        ? clusterB?.concept_names[indexB]
                        : candidate;

                    return (
                      <span
                        key={i}
                        className="text-xs px-2 py-1 bg-accent-amber/20 text-accent-amber border border-accent-amber/30 rounded"
                      >
                        {name}
                      </span>
                    );
                  })}
                  {gap.bridge_candidates.length > 3 && (
                    <span className="text-xs text-muted self-center">
                      +{gap.bridge_candidates.length - 3} more
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Research Questions Section */}
          <div className="p-4">
            {/* Generate Button */}
            {!result && (
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className={`w-full p-3 flex items-center justify-center gap-2 font-mono text-sm uppercase tracking-wider transition-colors ${
                  isGenerating
                    ? 'bg-white/5 text-muted cursor-not-allowed'
                    : 'bg-accent-amber/10 hover:bg-accent-amber/20 text-accent-amber'
                }`}
              >
                {isGenerating ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Generate Research Questions
                  </>
                )}
              </button>
            )}

            {/* Error */}
            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded text-sm text-red-400">
                {error}
              </div>
            )}

            {/* Results */}
            {result && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs uppercase tracking-wider text-muted">
                    Generated Hypotheses
                  </span>
                  <button
                    onClick={handleGenerate}
                    disabled={isGenerating}
                    className="p-1.5 hover:bg-white/10 rounded transition-colors"
                    title="Regenerate"
                  >
                    <RefreshCw className={`w-4 h-4 text-muted ${isGenerating ? 'animate-spin' : ''}`} />
                  </button>
                </div>

                <BridgeHypothesisList
                  hypotheses={result.hypotheses}
                  bridgeType={result.bridge_type}
                  keyInsight={result.key_insight}
                  onAccept={onAcceptHypothesis}
                />
              </div>
            )}

            {/* Pre-defined research questions from gap */}
            {gap.research_questions && gap.research_questions.length > 0 && !result && (
              <div className="mt-4 space-y-2">
                <span className="font-mono text-xs uppercase tracking-wider text-muted">
                  Suggested Research Questions
                </span>
                {gap.research_questions.map((question, i) => (
                  <div
                    key={i}
                    className="p-3 bg-white/5 border border-white/10 rounded text-sm text-white/80"
                  >
                    {question}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default GapQueryPanel;
