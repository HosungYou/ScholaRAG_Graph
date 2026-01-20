'use client';

import { useState, useEffect } from 'react';
import {
  X,
  FileText,
  User,
  Calendar,
  ArrowRight,
  Loader2,
  BookOpen,
  Link2,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { api } from '@/lib/api';
import type { RelationshipEvidence, EvidenceChunk } from '@/types';

/* ============================================================
   EdgeContextModal - Contextual Edge Exploration
   Phase 1: InfraNodus Integration

   When user clicks an edge in the graph, this modal shows the
   source text passages that support/justify the relationship.

   Design: VS Design Diverge Style (Direction B - Editorial Research)
   ============================================================ */

interface EdgeContextModalProps {
  isOpen: boolean;
  onClose: () => void;
  relationshipId: string | null;
  sourceName?: string;
  targetName?: string;
  relationshipType?: string;
}

// Highlight text that matches entity names
function highlightEntities(text: string, entities: string[]): JSX.Element {
  if (!text || entities.length === 0) return <>{text}</>;

  let result = text;
  const parts: JSX.Element[] = [];
  let lastIndex = 0;

  // Sort entities by length (longer first) to avoid partial matches
  const sortedEntities = [...entities].sort((a, b) => b.length - a.length);

  // Simple highlighting - find all occurrences
  for (const entity of sortedEntities) {
    if (!entity) continue;
    const regex = new RegExp(`(${entity.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    result = result.replace(regex, '|||HIGHLIGHT|||$1|||/HIGHLIGHT|||');
  }

  // Split and render
  const segments = result.split(/\|\|\|HIGHLIGHT\|\|\||\|\|\|\/HIGHLIGHT\|\|\|/);
  let isHighlight = false;

  return (
    <>
      {segments.map((segment, i) => {
        if (segment === '') {
          isHighlight = !isHighlight;
          return null;
        }
        const isEntityMatch = sortedEntities.some(
          e => e && segment.toLowerCase() === e.toLowerCase()
        );
        if (isEntityMatch) {
          return (
            <span key={i} className="bg-accent-amber/30 text-accent-amber font-medium px-0.5">
              {segment}
            </span>
          );
        }
        return <span key={i}>{segment}</span>;
      })}
    </>
  );
}

// Format section type for display
function formatSectionType(sectionType: string): string {
  const mapping: Record<string, string> = {
    abstract: 'Abstract',
    introduction: 'Introduction',
    methodology: 'Methodology',
    methods: 'Methods',
    results: 'Results',
    discussion: 'Discussion',
    conclusion: 'Conclusion',
    literature_review: 'Literature Review',
    background: 'Background',
    unknown: 'Content',
  };
  return mapping[sectionType] || sectionType;
}

// Section type colors
function getSectionColor(sectionType: string): string {
  const colors: Record<string, string> = {
    abstract: 'bg-accent-teal/20 text-accent-teal',
    introduction: 'bg-accent-violet/20 text-accent-violet',
    methodology: 'bg-accent-amber/20 text-accent-amber',
    methods: 'bg-accent-amber/20 text-accent-amber',
    results: 'bg-accent-emerald/20 text-accent-emerald',
    discussion: 'bg-accent-blue/20 text-accent-blue',
    conclusion: 'bg-accent-pink/20 text-accent-pink',
    literature_review: 'bg-accent-indigo/20 text-accent-indigo',
    background: 'bg-accent-indigo/20 text-accent-indigo',
  };
  return colors[sectionType] || 'bg-surface/20 text-muted';
}

// Individual evidence card component
function EvidenceCard({
  evidence,
  sourceName,
  targetName,
  isExpanded,
  onToggle,
}: {
  evidence: EvidenceChunk;
  sourceName: string;
  targetName: string;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(evidence.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="border border-ink/10 dark:border-paper/10 bg-surface/5 relative">
      {/* Left accent bar based on section type */}
      <div
        className={`absolute left-0 top-0 bottom-0 w-1 ${
          evidence.section_type === 'abstract'
            ? 'bg-accent-teal'
            : evidence.section_type === 'methodology' || evidence.section_type === 'methods'
            ? 'bg-accent-amber'
            : evidence.section_type === 'results'
            ? 'bg-accent-emerald'
            : evidence.section_type === 'discussion'
            ? 'bg-accent-blue'
            : 'bg-accent-violet'
        }`}
      />

      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full p-4 pl-5 text-left hover:bg-surface/5 transition-colors"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            {/* Paper info */}
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className={`px-2 py-0.5 font-mono text-xs ${getSectionColor(evidence.section_type)}`}>
                {formatSectionType(evidence.section_type)}
              </span>
              {evidence.paper_year && (
                <span className="flex items-center gap-1 text-xs text-muted">
                  <Calendar className="w-3 h-3" />
                  {evidence.paper_year}
                </span>
              )}
              <span className="px-1.5 py-0.5 text-xs font-mono bg-accent-teal/10 text-accent-teal">
                {Math.round(evidence.relevance_score * 100)}% relevant
              </span>
            </div>

            {/* Paper title */}
            {evidence.paper_title && (
              <p className="font-mono text-xs text-ink dark:text-paper truncate mb-1">
                {evidence.paper_title}
              </p>
            )}

            {/* Authors */}
            {evidence.paper_authors && (
              <p className="flex items-center gap-1 text-xs text-muted truncate">
                <User className="w-3 h-3 flex-shrink-0" />
                {evidence.paper_authors}
              </p>
            )}
          </div>

          <div className="flex items-center gap-2">
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-muted" />
            ) : (
              <ChevronDown className="w-4 h-4 text-muted" />
            )}
          </div>
        </div>

        {/* Preview text (when collapsed) */}
        {!isExpanded && (
          <p className="text-sm text-muted mt-2 line-clamp-2">
            {evidence.context_snippet || evidence.text.slice(0, 150)}...
          </p>
        )}
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pl-5 pb-4 border-t border-ink/5 dark:border-paper/5">
          {/* Full text with highlights */}
          <div className="mt-4 p-4 bg-paper dark:bg-ink border border-ink/5 dark:border-paper/5">
            <p className="text-sm text-ink dark:text-paper leading-relaxed">
              {highlightEntities(evidence.text, [sourceName, targetName])}
            </p>
          </div>

          {/* Actions */}
          <div className="mt-3 flex items-center justify-end gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 px-3 py-1.5 font-mono text-xs text-muted hover:text-ink dark:hover:text-paper hover:bg-surface/10 transition-colors"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-accent-teal" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  Copy
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export function EdgeContextModal({
  isOpen,
  onClose,
  relationshipId,
  sourceName: initialSourceName,
  targetName: initialTargetName,
  relationshipType: initialRelationshipType,
}: EdgeContextModalProps) {
  const [evidence, setEvidence] = useState<RelationshipEvidence | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(0);

  // Fetch evidence when modal opens
  useEffect(() => {
    if (!isOpen || !relationshipId) {
      setEvidence(null);
      setError(null);
      return;
    }

    const fetchEvidence = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await api.fetchRelationshipEvidence(relationshipId);
        setEvidence(data);
        setExpandedIndex(0); // Auto-expand first evidence
      } catch (err) {
        console.error('Failed to fetch relationship evidence:', err);
        setError(err instanceof Error ? err.message : 'Failed to load evidence');
      } finally {
        setIsLoading(false);
      }
    };

    fetchEvidence();
  }, [isOpen, relationshipId]);

  if (!isOpen) return null;

  const sourceName = evidence?.source_name || initialSourceName || 'Source';
  const targetName = evidence?.target_name || initialTargetName || 'Target';
  const relationshipType = evidence?.relationship_type || initialRelationshipType || 'RELATED_TO';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-ink/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl max-h-[80vh] bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 flex flex-col overflow-hidden">
        {/* Decorative corner accent */}
        <div className="absolute top-0 right-0 w-24 h-24 bg-accent-teal/10 transform rotate-45 translate-x-12 -translate-y-12" />

        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-ink/10 dark:border-paper/10 relative">
          <div className="flex-1 min-w-0 pr-8">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 flex items-center justify-center bg-accent-teal/10">
                <Link2 className="w-4 h-4 text-accent-teal" />
              </div>
              <span className="font-mono text-xs uppercase tracking-wider text-muted">
                Relationship Evidence
              </span>
            </div>

            {/* Relationship visualization */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-3 py-1.5 bg-accent-violet/10 text-accent-violet font-mono text-sm">
                {sourceName}
              </span>
              <div className="flex items-center gap-1 text-muted">
                <div className="w-8 h-px bg-current" />
                <span className="font-mono text-xs uppercase">{relationshipType.replace(/_/g, ' ')}</span>
                <ArrowRight className="w-3 h-3" />
                <div className="w-8 h-px bg-current" />
              </div>
              <span className="px-3 py-1.5 bg-accent-amber/10 text-accent-amber font-mono text-sm">
                {targetName}
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 hover:bg-surface/10 transition-colors"
            title="Close"
          >
            <X className="w-5 h-5 text-muted hover:text-ink dark:hover:text-paper" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <Loader2 className="w-8 h-8 text-accent-teal animate-spin mx-auto mb-3" />
                <p className="font-mono text-xs text-muted uppercase tracking-wider">
                  Loading evidence...
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="w-12 h-12 flex items-center justify-center bg-accent-red/10 mx-auto mb-3">
                  <span className="text-accent-red text-xl">!</span>
                </div>
                <p className="font-mono text-xs text-accent-red uppercase tracking-wider mb-2">
                  Error
                </p>
                <p className="text-sm text-muted">{error}</p>
              </div>
            </div>
          )}

          {!isLoading && !error && evidence && (
            <>
              {/* Evidence count */}
              <div className="flex items-center gap-2 mb-4">
                <BookOpen className="w-4 h-4 text-accent-teal" />
                <span className="font-mono text-xs text-muted">
                  {evidence.total_evidence} source{evidence.total_evidence !== 1 ? 's' : ''} found
                </span>
              </div>

              {/* Evidence list */}
              {evidence.evidence_chunks.length > 0 ? (
                <div className="space-y-3">
                  {evidence.evidence_chunks.map((chunk, index) => (
                    <EvidenceCard
                      key={chunk.evidence_id}
                      evidence={chunk}
                      sourceName={sourceName}
                      targetName={targetName}
                      isExpanded={expandedIndex === index}
                      onToggle={() => setExpandedIndex(expandedIndex === index ? null : index)}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <div className="w-16 h-16 flex items-center justify-center bg-surface/5 mx-auto mb-4">
                    <FileText className="w-8 h-8 text-muted" />
                  </div>
                  <p className="font-mono text-xs text-muted uppercase tracking-wider mb-2">
                    No Evidence Found
                  </p>
                  <p className="text-sm text-muted">
                    This relationship was inferred from embeddings or metadata.
                    No specific text passages are available.
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-ink/10 dark:border-paper/10 bg-surface/5">
          <p className="text-xs text-muted">
            Evidence shows source text passages where these concepts appear together.
            Higher relevance scores indicate stronger contextual support.
          </p>
        </div>
      </div>
    </div>
  );
}
