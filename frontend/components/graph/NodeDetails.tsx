'use client';

import { useState } from 'react';
import { X, ExternalLink, MessageSquare, Share2, Loader2, ChevronDown, ChevronUp, Hexagon, Diamond, Pentagon, Square, Octagon } from 'lucide-react';
import type { GraphEntity, EntityType, PaperProperties, AuthorProperties, ConceptProperties, MethodProperties, FindingProperties } from '@/types';
import { api } from '@/lib/api';

/* ============================================================
   NodeDetails - VS Design Diverge Style
   Direction B (T-Score 0.4) "Editorial Research"

   Design Principles:
   - Line-based layout (minimal border-radius)
   - Left accent bar for entity type
   - Monospace labels and metadata
   - Polygon icons
   ============================================================ */

interface NodeDetailsProps {
  node: GraphEntity | null;
  projectId: string;
  onClose: () => void;
  onAskAbout?: (nodeId: string, nodeName: string) => void;
  onShowConnections?: (nodeId: string) => void;
}

// VS Design Diverge palette - matching PolygonNode.tsx exactly
const entityTypeConfig: Record<EntityType, { color: string; icon: React.ReactNode }> = {
  Paper: {
    color: '#6366F1', // Indigo - matches PolygonNode
    icon: <Square className="w-4 h-4" strokeWidth={1.5} />
  },
  Author: {
    color: '#A855F7', // Purple - matches PolygonNode
    icon: <Hexagon className="w-4 h-4" strokeWidth={1.5} />
  },
  Concept: {
    color: '#8B5CF6', // Violet - matches PolygonNode
    icon: <Hexagon className="w-4 h-4" strokeWidth={1.5} />
  },
  Method: {
    color: '#F59E0B', // Amber - matches PolygonNode
    icon: <Diamond className="w-4 h-4" strokeWidth={1.5} />
  },
  Finding: {
    color: '#10B981', // Emerald - matches PolygonNode
    icon: <Pentagon className="w-4 h-4" strokeWidth={1.5} />
  },
  Problem: {
    color: '#EF4444', // Red
    icon: <Square className="w-4 h-4" strokeWidth={1.5} />
  },
  Dataset: {
    color: '#3B82F6', // Blue
    icon: <Square className="w-4 h-4" strokeWidth={1.5} />
  },
  Metric: {
    color: '#EC4899', // Pink
    icon: <Diamond className="w-4 h-4" strokeWidth={1.5} />
  },
  Innovation: {
    color: '#14B8A6', // Teal
    icon: <Pentagon className="w-4 h-4" strokeWidth={1.5} />
  },
  Limitation: {
    color: '#F97316', // Orange
    icon: <Square className="w-4 h-4" strokeWidth={1.5} />
  },
};

export function NodeDetails({
  node,
  projectId,
  onClose,
  onAskAbout,
  onShowConnections,
}: NodeDetailsProps) {
  const [aiExplanation, setAiExplanation] = useState<string | null>(null);
  const [isLoadingExplanation, setIsLoadingExplanation] = useState(false);
  const [showFullAbstract, setShowFullAbstract] = useState(false);

  if (!node) return null;

  const config = entityTypeConfig[node.entity_type] || {
    color: '#64748B',
    icon: <Square className="w-4 h-4" />,
  };

  const handleGetExplanation = async () => {
    setIsLoadingExplanation(true);
    try {
      // v0.9.0: Pass node name and type to avoid UUID in AI response
      const result = await api.explainNode(
        node.id,
        projectId,
        node.name,
        node.entity_type
      );
      setAiExplanation(result.explanation);
    } catch (error) {
      console.error('Failed to get AI explanation:', error);
      setAiExplanation('AI 설명을 가져오는데 실패했습니다.');
    } finally {
      setIsLoadingExplanation(false);
    }
  };

  const renderPaperDetails = (props: PaperProperties) => (
    <div className="space-y-4">
      {props.abstract && (
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted mb-2">Abstract</p>
          <p className={`text-sm text-ink dark:text-paper leading-relaxed ${showFullAbstract ? '' : 'line-clamp-4'}`}>
            {props.abstract}
          </p>
          {props.abstract.length > 200 && (
            <button
              onClick={() => setShowFullAbstract(!showFullAbstract)}
              className="font-mono text-xs text-accent-teal hover:text-accent-teal/80 mt-2 flex items-center gap-1 transition-colors"
            >
              {showFullAbstract ? (
                <>
                  <ChevronUp className="w-3 h-3" /> Collapse
                </>
              ) : (
                <>
                  <ChevronDown className="w-3 h-3" /> Expand
                </>
              )}
            </button>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 text-sm">
        {props.year && (
          <div>
            <span className="font-mono text-xs text-muted uppercase tracking-wider">Year</span>
            <p className="font-mono text-ink dark:text-paper">{props.year}</p>
          </div>
        )}
        {props.citation_count !== undefined && (
          <div>
            <span className="font-mono text-xs text-muted uppercase tracking-wider">Citations</span>
            <p className="font-mono text-ink dark:text-paper">{props.citation_count}</p>
          </div>
        )}
        {props.source && (
          <div className="col-span-2">
            <span className="font-mono text-xs text-muted uppercase tracking-wider">Source</span>
            <p className="text-ink dark:text-paper">{props.source}</p>
          </div>
        )}
        {props.authors && props.authors.length > 0 && (
          <div className="col-span-2">
            <span className="font-mono text-xs text-muted uppercase tracking-wider">Authors</span>
            <p className="text-ink dark:text-paper">
              {props.authors.slice(0, 3).join(', ')}
              {props.authors.length > 3 ? ` +${props.authors.length - 3}` : ''}
            </p>
          </div>
        )}
      </div>

      <div className="flex gap-2 pt-2">
        {props.doi && (
          <a
            href={`https://doi.org/${props.doi}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 font-mono text-xs text-accent-teal hover:text-accent-teal/80 px-2 py-1 border border-accent-teal/30 hover:border-accent-teal transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            DOI
          </a>
        )}
        {props.arxiv_id && (
          <a
            href={`https://arxiv.org/abs/${props.arxiv_id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 font-mono text-xs text-accent-amber hover:text-accent-amber/80 px-2 py-1 border border-accent-amber/30 hover:border-accent-amber transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            arXiv
          </a>
        )}
        {props.url && !props.doi && !props.arxiv_id && (
          <a
            href={props.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 font-mono text-xs text-muted hover:text-ink dark:hover:text-paper px-2 py-1 border border-ink/10 dark:border-paper/10 hover:border-ink/30 dark:hover:border-paper/30 transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            Link
          </a>
        )}
      </div>
    </div>
  );

  const renderAuthorDetails = (props: AuthorProperties) => (
    <div className="space-y-4">
      {props.affiliation && (
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted mb-1">Affiliation</p>
          <p className="text-sm text-ink dark:text-paper">{props.affiliation}</p>
        </div>
      )}
      {props.orcid && (
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted mb-1">ORCID</p>
          <a
            href={`https://orcid.org/${props.orcid}`}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-sm text-accent-teal hover:text-accent-teal/80 flex items-center gap-1 transition-colors"
          >
            {props.orcid}
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      )}
      {props.paper_count !== undefined && (
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted mb-1">Papers</p>
          <p className="font-mono text-lg text-ink dark:text-paper">{props.paper_count}</p>
        </div>
      )}
    </div>
  );

  const renderConceptDetails = (props: ConceptProperties) => (
    <div className="space-y-4">
      {props.description && (
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted mb-1">Description</p>
          <p className="text-sm text-ink dark:text-paper leading-relaxed">{props.description}</p>
        </div>
      )}
      {props.domain && (
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted mb-1">Domain</p>
          <p className="text-sm text-ink dark:text-paper">{props.domain}</p>
        </div>
      )}
      {props.synonyms && props.synonyms.length > 0 && (
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted mb-2">Related Terms</p>
          <div className="flex flex-wrap gap-1">
            {props.synonyms.map((s, i) => (
              <span key={i} className="font-mono text-xs text-accent-teal px-2 py-0.5 border border-accent-teal/30">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
      {props.paper_count !== undefined && (
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted mb-1">Mentioned In</p>
          <p className="font-mono text-lg text-ink dark:text-paper">{props.paper_count} <span className="text-sm text-muted">papers</span></p>
        </div>
      )}
    </div>
  );

  const renderMethodDetails = (props: MethodProperties) => (
    <div className="space-y-4">
      {props.description && (
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted mb-1">Description</p>
          <p className="text-sm text-ink dark:text-paper leading-relaxed">{props.description}</p>
        </div>
      )}
      {props.type && (
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted mb-1">Type</p>
          <span className={`font-mono text-xs px-2 py-0.5 border ${
            props.type === 'quantitative' ? 'text-accent-teal border-accent-teal/30' :
            props.type === 'qualitative' ? 'text-accent-amber border-accent-amber/30' :
            'text-accent-red border-accent-red/30'
          }`}>
            {props.type}
          </span>
        </div>
      )}
      {props.paper_count !== undefined && (
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted mb-1">Used In</p>
          <p className="font-mono text-lg text-ink dark:text-paper">{props.paper_count} <span className="text-sm text-muted">papers</span></p>
        </div>
      )}
    </div>
  );

  const renderFindingDetails = (props: FindingProperties) => (
    <div className="space-y-4">
      {props.statement && (
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted mb-1">Statement</p>
          <p className="text-sm text-ink dark:text-paper leading-relaxed">{props.statement}</p>
        </div>
      )}
      <div className="grid grid-cols-2 gap-4 text-sm">
        {props.effect_size && (
          <div>
            <span className="font-mono text-xs text-muted uppercase tracking-wider">Effect Size</span>
            <p className="font-mono text-ink dark:text-paper">{props.effect_size}</p>
          </div>
        )}
        {props.significance && (
          <div>
            <span className="font-mono text-xs text-muted uppercase tracking-wider">Significance</span>
            <p className="text-ink dark:text-paper">{props.significance}</p>
          </div>
        )}
        {props.confidence !== undefined && (
          <div>
            <span className="font-mono text-xs text-muted uppercase tracking-wider">Confidence</span>
            <p className="font-mono text-ink dark:text-paper">{Math.round(props.confidence * 100)}%</p>
          </div>
        )}
      </div>
      {props.paper_count !== undefined && (
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted mb-1">Supported By</p>
          <p className="font-mono text-lg text-ink dark:text-paper">{props.paper_count} <span className="text-sm text-muted">papers</span></p>
        </div>
      )}
    </div>
  );

  const renderDetails = () => {
    const entityType = node.entity_type;

    if (entityType === 'Paper') {
      return renderPaperDetails(node.properties as PaperProperties);
    }
    if (entityType === 'Author') {
      return renderAuthorDetails(node.properties as AuthorProperties);
    }
    if (entityType === 'Concept') {
      return renderConceptDetails(node.properties as ConceptProperties);
    }
    if (entityType === 'Method') {
      return renderMethodDetails(node.properties as MethodProperties);
    }
    if (entityType === 'Finding') {
      return renderFindingDetails(node.properties as FindingProperties);
    }

    // Fallback for unknown entity types
    const props = node.properties as Record<string, unknown>;
    return (
      <div className="space-y-3">
        {Object.entries(props).map(([key, value]) => (
          <div key={key}>
            <p className="font-mono text-xs uppercase tracking-wider text-muted mb-1">
              {key.replace(/_/g, ' ')}
            </p>
            <p className="text-sm text-ink dark:text-paper">
              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
            </p>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="absolute bottom-4 left-4 right-4 max-w-md bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 overflow-hidden z-10">
      {/* Header with left accent bar */}
      <div className="relative border-b border-ink/10 dark:border-paper/10 px-4 py-3">
        {/* Left accent bar */}
        <div
          className="absolute left-0 top-0 bottom-0 w-1"
          style={{ backgroundColor: config.color }}
        />

        <div className="flex items-start justify-between pl-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span style={{ color: config.color }}>
                {config.icon}
              </span>
              <span
                className="font-mono text-xs uppercase tracking-wider"
                style={{ color: config.color }}
              >
                {node.entity_type}
              </span>
            </div>
            <h3 className="font-display text-lg text-ink dark:text-paper truncate" title={node.name}>
              {node.name}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-muted hover:text-accent-red transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 max-h-64 overflow-y-auto">
        {renderDetails()}

        {/* AI Explanation Section */}
        {aiExplanation && (
          <div className="mt-4 pt-4 border-t border-ink/10 dark:border-paper/10">
            <div className="relative pl-3">
              <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-accent-teal" />
              <p className="font-mono text-xs uppercase tracking-wider text-accent-teal mb-2">AI Analysis</p>
              <p className="text-sm text-ink dark:text-paper leading-relaxed">{aiExplanation}</p>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="px-4 py-3 border-t border-ink/10 dark:border-paper/10 flex gap-2">
        <button
          onClick={handleGetExplanation}
          disabled={isLoadingExplanation}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-accent-teal text-ink text-sm font-mono uppercase tracking-wider hover:bg-accent-teal/90 transition-colors disabled:opacity-50"
        >
          {isLoadingExplanation ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <MessageSquare className="w-4 h-4" />
              AI Explain
            </>
          )}
        </button>
        {onAskAbout && (
          <button
            onClick={() => onAskAbout(node.id, node.name)}
            className="flex items-center justify-center gap-2 px-3 py-2 border border-ink/10 dark:border-paper/10 text-muted text-sm hover:text-ink dark:hover:text-paper hover:border-ink/30 dark:hover:border-paper/30 transition-colors"
          >
            <MessageSquare className="w-4 h-4" />
          </button>
        )}
        {onShowConnections && (
          <button
            onClick={() => onShowConnections(node.id)}
            className="flex items-center justify-center gap-2 px-3 py-2 border border-ink/10 dark:border-paper/10 text-muted text-sm hover:text-ink dark:hover:text-paper hover:border-ink/30 dark:hover:border-paper/30 transition-colors"
          >
            <Share2 className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
