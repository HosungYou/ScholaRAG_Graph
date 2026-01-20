'use client';

import { useState, useEffect, useMemo } from 'react';
import {
  GitCompare,
  Loader2,
  Circle,
  ArrowRight,
  BarChart3,
  Layers,
  Minus,
  Plus,
  Link2,
} from 'lucide-react';
import { api } from '@/lib/api';
import type { Project } from '@/types';

/* ============================================================
   GraphComparison - Compare Two Knowledge Graphs
   Phase 5: InfraNodus Integration

   Split view comparison of two project graphs showing:
   - Common entities (intersection)
   - Unique entities to each project (difference)
   - Venn diagram visualization
   - Similarity metrics

   Design: VS Design Diverge Style (Direction B - Editorial Research)
   ============================================================ */

interface ComparisonData {
  project_a_id: string;
  project_a_name: string;
  project_b_id: string;
  project_b_name: string;
  common_entities: number;
  unique_to_a: number;
  unique_to_b: number;
  common_entity_names: string[];
  jaccard_similarity: number;
  overlap_coefficient: number;
  nodes: Array<{
    id: string;
    name: string;
    entity_type: string;
    in_project_a: boolean;
    in_project_b: boolean;
    is_common: boolean;
  }>;
}

interface GraphComparisonProps {
  projects: Project[];
  initialProjectA?: string;
  initialProjectB?: string;
}

// Venn Diagram Component
function VennDiagram({
  uniqueA,
  uniqueB,
  common,
  labelA,
  labelB,
}: {
  uniqueA: number;
  uniqueB: number;
  common: number;
  labelA: string;
  labelB: string;
}) {
  const total = uniqueA + uniqueB + common;
  const maxCount = Math.max(uniqueA, uniqueB, common);

  // Scale sizes based on counts (with minimum size)
  const sizeA = Math.max(80, Math.min(150, (uniqueA + common) / total * 200));
  const sizeB = Math.max(80, Math.min(150, (uniqueB + common) / total * 200));

  return (
    <div className="relative w-80 h-48 mx-auto">
      {/* Circle A - Left */}
      <div
        className="absolute top-1/2 -translate-y-1/2 rounded-full bg-accent-violet/30 border-2 border-accent-violet flex items-center justify-center"
        style={{
          left: '20%',
          width: `${sizeA}px`,
          height: `${sizeA}px`,
        }}
      >
        <div className="text-center relative -left-4">
          <span className="block text-2xl font-bold text-accent-violet">{uniqueA}</span>
          <span className="text-xs text-muted">Unique</span>
        </div>
      </div>

      {/* Circle B - Right */}
      <div
        className="absolute top-1/2 -translate-y-1/2 rounded-full bg-accent-amber/30 border-2 border-accent-amber flex items-center justify-center"
        style={{
          right: '20%',
          width: `${sizeB}px`,
          height: `${sizeB}px`,
        }}
      >
        <div className="text-center relative left-4">
          <span className="block text-2xl font-bold text-accent-amber">{uniqueB}</span>
          <span className="text-xs text-muted">Unique</span>
        </div>
      </div>

      {/* Intersection - Center */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
        <div className="w-20 h-20 rounded-full bg-accent-teal/50 border-2 border-accent-teal flex items-center justify-center">
          <div className="text-center">
            <span className="block text-2xl font-bold text-accent-teal">{common}</span>
            <span className="text-xs text-white">Common</span>
          </div>
        </div>
      </div>

      {/* Labels */}
      <div className="absolute top-0 left-0 text-xs font-mono text-accent-violet truncate max-w-[100px]">
        {labelA}
      </div>
      <div className="absolute top-0 right-0 text-xs font-mono text-accent-amber truncate max-w-[100px] text-right">
        {labelB}
      </div>
    </div>
  );
}

// Similarity Gauge Component
function SimilarityGauge({ value, label }: { value: number; label: string }) {
  const percentage = Math.round(value * 100);

  return (
    <div className="text-center">
      <div className="relative w-20 h-20 mx-auto mb-2">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 64 64">
          <circle
            cx="32"
            cy="32"
            r="28"
            fill="none"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="4"
          />
          <circle
            cx="32"
            cy="32"
            r="28"
            fill="none"
            stroke="#4ECDC4"
            strokeWidth="4"
            strokeDasharray={`${value * 175.93} 175.93`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-bold text-accent-teal">{percentage}%</span>
        </div>
      </div>
      <span className="text-xs text-muted font-mono">{label}</span>
    </div>
  );
}

export function GraphComparison({
  projects,
  initialProjectA,
  initialProjectB,
}: GraphComparisonProps) {
  const [projectAId, setProjectAId] = useState<string>(initialProjectA || '');
  const [projectBId, setProjectBId] = useState<string>(initialProjectB || '');
  const [comparison, setComparison] = useState<ComparisonData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'common' | 'unique_a' | 'unique_b'>('common');

  // Fetch comparison when both projects are selected
  useEffect(() => {
    if (!projectAId || !projectBId || projectAId === projectBId) {
      setComparison(null);
      return;
    }

    const fetchComparison = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await api.compareGraphs(projectAId, projectBId);
        setComparison(data);
      } catch (err) {
        console.error('Failed to compare graphs:', err);
        setError(err instanceof Error ? err.message : 'Failed to compare graphs');
      } finally {
        setIsLoading(false);
      }
    };

    fetchComparison();
  }, [projectAId, projectBId]);

  // Filter nodes based on active tab
  const filteredNodes = useMemo(() => {
    if (!comparison) return [];

    switch (activeTab) {
      case 'common':
        return comparison.nodes.filter(n => n.is_common);
      case 'unique_a':
        return comparison.nodes.filter(n => n.in_project_a && !n.in_project_b);
      case 'unique_b':
        return comparison.nodes.filter(n => n.in_project_b && !n.in_project_a);
      default:
        return comparison.nodes;
    }
  }, [comparison, activeTab]);

  return (
    <div className="min-h-screen bg-ink text-paper">
      {/* Header */}
      <div className="border-b border-paper/10 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 flex items-center justify-center bg-accent-teal/10">
            <GitCompare className="w-5 h-5 text-accent-teal" />
          </div>
          <div>
            <h1 className="text-xl font-mono font-bold">Graph Comparison</h1>
            <p className="text-sm text-muted">Compare knowledge graphs from different projects</p>
          </div>
        </div>

        {/* Project Selectors */}
        <div className="flex items-center gap-4">
          {/* Project A Selector */}
          <div className="flex-1">
            <label className="block text-xs font-mono text-muted mb-2">Project A</label>
            <select
              value={projectAId}
              onChange={(e) => setProjectAId(e.target.value)}
              className="w-full bg-surface/10 border border-paper/10 px-4 py-2.5 font-mono text-sm focus:outline-none focus:border-accent-violet"
            >
              <option value="">Select project...</option>
              {projects.map(p => (
                <option key={p.id} value={p.id} disabled={p.id === projectBId}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Arrow */}
          <div className="pt-6">
            <ArrowRight className="w-6 h-6 text-muted" />
          </div>

          {/* Project B Selector */}
          <div className="flex-1">
            <label className="block text-xs font-mono text-muted mb-2">Project B</label>
            <select
              value={projectBId}
              onChange={(e) => setProjectBId(e.target.value)}
              className="w-full bg-surface/10 border border-paper/10 px-4 py-2.5 font-mono text-sm focus:outline-none focus:border-accent-amber"
            >
              <option value="">Select project...</option>
              {projects.map(p => (
                <option key={p.id} value={p.id} disabled={p.id === projectAId}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <Loader2 className="w-10 h-10 text-accent-teal animate-spin mx-auto mb-4" />
              <p className="font-mono text-sm text-muted">Comparing graphs...</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="text-center py-20">
            <div className="w-16 h-16 flex items-center justify-center bg-accent-red/10 mx-auto mb-4">
              <span className="text-accent-red text-2xl">!</span>
            </div>
            <p className="text-accent-red font-mono text-sm mb-2">Comparison Failed</p>
            <p className="text-muted text-sm">{error}</p>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && !comparison && (
          <div className="text-center py-20">
            <div className="w-20 h-20 flex items-center justify-center bg-surface/5 mx-auto mb-4">
              <Layers className="w-10 h-10 text-muted" />
            </div>
            <p className="font-mono text-sm text-muted">
              Select two projects to compare their knowledge graphs
            </p>
          </div>
        )}

        {/* Comparison Results */}
        {comparison && !isLoading && (
          <div className="space-y-8">
            {/* Venn Diagram */}
            <div className="bg-surface/5 border border-paper/10 p-6">
              <h2 className="font-mono text-sm uppercase tracking-wider text-muted mb-6 text-center">
                Entity Overlap
              </h2>
              <VennDiagram
                uniqueA={comparison.unique_to_a}
                uniqueB={comparison.unique_to_b}
                common={comparison.common_entities}
                labelA={comparison.project_a_name}
                labelB={comparison.project_b_name}
              />
            </div>

            {/* Similarity Metrics */}
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-surface/5 border border-paper/10 p-6">
                <SimilarityGauge
                  value={comparison.jaccard_similarity}
                  label="Jaccard Similarity"
                />
              </div>
              <div className="bg-surface/5 border border-paper/10 p-6">
                <SimilarityGauge
                  value={comparison.overlap_coefficient}
                  label="Overlap Coefficient"
                />
              </div>
            </div>

            {/* Statistics Bar */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-accent-violet/10 border border-accent-violet/30 p-4 text-center">
                <Minus className="w-5 h-5 text-accent-violet mx-auto mb-2" />
                <span className="block text-2xl font-bold text-accent-violet">{comparison.unique_to_a}</span>
                <span className="text-xs text-muted">Unique to {comparison.project_a_name}</span>
              </div>
              <div className="bg-accent-teal/10 border border-accent-teal/30 p-4 text-center">
                <Link2 className="w-5 h-5 text-accent-teal mx-auto mb-2" />
                <span className="block text-2xl font-bold text-accent-teal">{comparison.common_entities}</span>
                <span className="text-xs text-muted">Common Entities</span>
              </div>
              <div className="bg-accent-amber/10 border border-accent-amber/30 p-4 text-center">
                <Plus className="w-5 h-5 text-accent-amber mx-auto mb-2" />
                <span className="block text-2xl font-bold text-accent-amber">{comparison.unique_to_b}</span>
                <span className="text-xs text-muted">Unique to {comparison.project_b_name}</span>
              </div>
            </div>

            {/* Entity List with Tabs */}
            <div className="bg-surface/5 border border-paper/10">
              {/* Tabs */}
              <div className="flex border-b border-paper/10">
                <button
                  onClick={() => setActiveTab('common')}
                  className={`flex-1 px-4 py-3 font-mono text-xs uppercase tracking-wider transition-colors ${
                    activeTab === 'common'
                      ? 'bg-accent-teal/10 text-accent-teal border-b-2 border-accent-teal'
                      : 'text-muted hover:text-paper'
                  }`}
                >
                  Common ({comparison.common_entities})
                </button>
                <button
                  onClick={() => setActiveTab('unique_a')}
                  className={`flex-1 px-4 py-3 font-mono text-xs uppercase tracking-wider transition-colors ${
                    activeTab === 'unique_a'
                      ? 'bg-accent-violet/10 text-accent-violet border-b-2 border-accent-violet'
                      : 'text-muted hover:text-paper'
                  }`}
                >
                  Only in A ({comparison.unique_to_a})
                </button>
                <button
                  onClick={() => setActiveTab('unique_b')}
                  className={`flex-1 px-4 py-3 font-mono text-xs uppercase tracking-wider transition-colors ${
                    activeTab === 'unique_b'
                      ? 'bg-accent-amber/10 text-accent-amber border-b-2 border-accent-amber'
                      : 'text-muted hover:text-paper'
                  }`}
                >
                  Only in B ({comparison.unique_to_b})
                </button>
              </div>

              {/* Entity List */}
              <div className="p-4 max-h-80 overflow-y-auto">
                {filteredNodes.length === 0 ? (
                  <p className="text-center text-muted text-sm py-8">No entities in this category</p>
                ) : (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {filteredNodes.slice(0, 60).map((node) => (
                      <div
                        key={node.id}
                        className={`px-3 py-2 text-xs font-mono truncate border ${
                          node.is_common
                            ? 'border-accent-teal/30 bg-accent-teal/5 text-accent-teal'
                            : node.in_project_a
                            ? 'border-accent-violet/30 bg-accent-violet/5 text-accent-violet'
                            : 'border-accent-amber/30 bg-accent-amber/5 text-accent-amber'
                        }`}
                        title={`${node.name} (${node.entity_type})`}
                      >
                        {node.name}
                      </div>
                    ))}
                    {filteredNodes.length > 60 && (
                      <div className="px-3 py-2 text-xs text-muted">
                        +{filteredNodes.length - 60} more...
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
