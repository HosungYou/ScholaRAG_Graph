'use client';

import { useState } from 'react';
import { X, ExternalLink, MessageSquare, Share2, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import type { GraphEntity, EntityType, PaperProperties, AuthorProperties, ConceptProperties, MethodProperties, FindingProperties } from '@/types';
import { api } from '@/lib/api';

interface NodeDetailsProps {
  node: GraphEntity | null;
  projectId: string;
  onClose: () => void;
  onAskAbout?: (nodeId: string, nodeName: string) => void;
  onShowConnections?: (nodeId: string) => void;
}

const entityTypeConfig: Record<EntityType, { bg: string; border: string; text: string; icon: string }> = {
  Paper: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', icon: 'fa-file-text' },
  Author: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', icon: 'fa-user' },
  Concept: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', icon: 'fa-lightbulb' },
  Method: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', icon: 'fa-flask' },
  Finding: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', icon: 'fa-trophy' },
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
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    text: 'text-gray-700',
    icon: 'fa-circle',
  };

  const handleGetExplanation = async () => {
    setIsLoadingExplanation(true);
    try {
      const result = await api.explainNode(node.id, projectId);
      setAiExplanation(result.explanation);
    } catch (error) {
      console.error('Failed to get AI explanation:', error);
      setAiExplanation('AI 설명을 가져오는데 실패했습니다.');
    } finally {
      setIsLoadingExplanation(false);
    }
  };

  const renderPaperDetails = (props: PaperProperties) => (
    <div className="space-y-3">
      {props.abstract && (
        <div>
          <p className="text-sm font-medium text-gray-700 mb-1">Abstract</p>
          <p className={`text-sm text-gray-600 ${showFullAbstract ? '' : 'line-clamp-4'}`}>
            {props.abstract}
          </p>
          {props.abstract.length > 200 && (
            <button
              onClick={() => setShowFullAbstract(!showFullAbstract)}
              className="text-xs text-blue-600 hover:text-blue-800 mt-1 flex items-center gap-1"
            >
              {showFullAbstract ? (
                <>
                  <ChevronUp className="w-3 h-3" /> 접기
                </>
              ) : (
                <>
                  <ChevronDown className="w-3 h-3" /> 더 보기
                </>
              )}
            </button>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 text-sm">
        {props.year && (
          <div>
            <span className="text-gray-500">Year:</span>{' '}
            <span className="text-gray-900 font-medium">{props.year}</span>
          </div>
        )}
        {props.citation_count !== undefined && (
          <div>
            <span className="text-gray-500">Citations:</span>{' '}
            <span className="text-gray-900 font-medium">{props.citation_count}</span>
          </div>
        )}
        {props.source && (
          <div>
            <span className="text-gray-500">Source:</span>{' '}
            <span className="text-gray-900">{props.source}</span>
          </div>
        )}
        {props.authors && props.authors.length > 0 && (
          <div className="col-span-2">
            <span className="text-gray-500">Authors:</span>{' '}
            <span className="text-gray-900">{props.authors.slice(0, 3).join(', ')}{props.authors.length > 3 ? ` +${props.authors.length - 3}` : ''}</span>
          </div>
        )}
      </div>

      <div className="flex gap-2 pt-2">
        {props.doi && (
          <a
            href={`https://doi.org/${props.doi}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 px-2 py-1 bg-blue-50 rounded"
          >
            <ExternalLink className="w-4 h-4" />
            DOI
          </a>
        )}
        {props.arxiv_id && (
          <a
            href={`https://arxiv.org/abs/${props.arxiv_id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-orange-600 hover:text-orange-800 px-2 py-1 bg-orange-50 rounded"
          >
            <ExternalLink className="w-4 h-4" />
            arXiv
          </a>
        )}
        {props.url && !props.doi && !props.arxiv_id && (
          <a
            href={props.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-800 px-2 py-1 bg-gray-100 rounded"
          >
            <ExternalLink className="w-4 h-4" />
            Link
          </a>
        )}
      </div>
    </div>
  );

  const renderAuthorDetails = (props: AuthorProperties) => (
    <div className="space-y-2">
      {props.affiliation && (
        <div>
          <p className="text-sm text-gray-500">Affiliation</p>
          <p className="text-sm text-gray-900">{props.affiliation}</p>
        </div>
      )}
      {props.orcid && (
        <div>
          <p className="text-sm text-gray-500">ORCID</p>
          <a
            href={`https://orcid.org/${props.orcid}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-green-600 hover:text-green-800 flex items-center gap-1"
          >
            {props.orcid}
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      )}
      {props.paper_count !== undefined && (
        <div>
          <p className="text-sm text-gray-500">Papers in this collection</p>
          <p className="text-sm text-gray-900 font-medium">{props.paper_count}</p>
        </div>
      )}
    </div>
  );

  const renderConceptDetails = (props: ConceptProperties) => (
    <div className="space-y-2">
      {props.description && (
        <div>
          <p className="text-sm text-gray-500">Description</p>
          <p className="text-sm text-gray-900">{props.description}</p>
        </div>
      )}
      {props.domain && (
        <div>
          <p className="text-sm text-gray-500">Domain</p>
          <p className="text-sm text-gray-900">{props.domain}</p>
        </div>
      )}
      {props.synonyms && props.synonyms.length > 0 && (
        <div>
          <p className="text-sm text-gray-500">Related terms</p>
          <div className="flex flex-wrap gap-1 mt-1">
            {props.synonyms.map((s, i) => (
              <span key={i} className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
      {props.paper_count !== undefined && (
        <div>
          <p className="text-sm text-gray-500">Mentioned in</p>
          <p className="text-sm text-gray-900 font-medium">{props.paper_count} papers</p>
        </div>
      )}
    </div>
  );

  const renderMethodDetails = (props: MethodProperties) => (
    <div className="space-y-2">
      {props.description && (
        <div>
          <p className="text-sm text-gray-500">Description</p>
          <p className="text-sm text-gray-900">{props.description}</p>
        </div>
      )}
      {props.type && (
        <div>
          <p className="text-sm text-gray-500">Type</p>
          <span className={`text-xs px-2 py-0.5 rounded ${
            props.type === 'quantitative' ? 'bg-blue-100 text-blue-700' :
            props.type === 'qualitative' ? 'bg-green-100 text-green-700' :
            'bg-purple-100 text-purple-700'
          }`}>
            {props.type}
          </span>
        </div>
      )}
      {props.paper_count !== undefined && (
        <div>
          <p className="text-sm text-gray-500">Used in</p>
          <p className="text-sm text-gray-900 font-medium">{props.paper_count} papers</p>
        </div>
      )}
    </div>
  );

  const renderFindingDetails = (props: FindingProperties) => (
    <div className="space-y-2">
      {props.statement && (
        <div>
          <p className="text-sm text-gray-500">Statement</p>
          <p className="text-sm text-gray-900">{props.statement}</p>
        </div>
      )}
      <div className="grid grid-cols-2 gap-3 text-sm">
        {props.effect_size && (
          <div>
            <span className="text-gray-500">Effect Size:</span>{' '}
            <span className="text-gray-900 font-medium">{props.effect_size}</span>
          </div>
        )}
        {props.significance && (
          <div>
            <span className="text-gray-500">Significance:</span>{' '}
            <span className="text-gray-900">{props.significance}</span>
          </div>
        )}
        {props.confidence !== undefined && (
          <div>
            <span className="text-gray-500">Confidence:</span>{' '}
            <span className="text-gray-900">{Math.round(props.confidence * 100)}%</span>
          </div>
        )}
      </div>
      {props.paper_count !== undefined && (
        <div>
          <p className="text-sm text-gray-500">Supported by</p>
          <p className="text-sm text-gray-900 font-medium">{props.paper_count} papers</p>
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
      <div className="space-y-2">
        {Object.entries(props).map(([key, value]) => (
          <div key={key}>
            <p className="text-sm text-gray-500 capitalize">
              {key.replace(/_/g, ' ')}
            </p>
            <p className="text-sm text-gray-900">
              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
            </p>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="absolute bottom-4 left-4 right-4 max-w-md bg-white rounded-lg shadow-xl border overflow-hidden z-10">
      {/* Header */}
      <div className={`${config.bg} ${config.border} border-b px-4 py-3`}>
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${config.text} ${config.bg} border ${config.border}`}
              >
                {node.entity_type}
              </span>
            </div>
            <h3 className="font-semibold text-gray-900 truncate" title={node.name}>
              {node.name}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-white/50 rounded transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 max-h-64 overflow-y-auto">
        {renderDetails()}

        {/* AI Explanation Section */}
        {aiExplanation && (
          <div className="mt-4 p-3 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-100">
            <p className="text-xs font-medium text-blue-700 mb-1">AI Analysis</p>
            <p className="text-sm text-gray-700">{aiExplanation}</p>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="px-4 py-3 border-t bg-gray-50 flex gap-2">
        <button
          onClick={handleGetExplanation}
          disabled={isLoadingExplanation}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white text-sm rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all disabled:opacity-50"
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
            className="flex items-center justify-center gap-2 px-3 py-2 border text-gray-700 text-sm rounded-lg hover:bg-gray-100 transition-colors"
          >
            <MessageSquare className="w-4 h-4" />
            Chat
          </button>
        )}
        {onShowConnections && (
          <button
            onClick={() => onShowConnections(node.id)}
            className="flex items-center justify-center gap-2 px-3 py-2 border text-gray-700 text-sm rounded-lg hover:bg-gray-100 transition-colors"
          >
            <Share2 className="w-4 h-4" />
            Expand
          </button>
        )}
      </div>
    </div>
  );
}
