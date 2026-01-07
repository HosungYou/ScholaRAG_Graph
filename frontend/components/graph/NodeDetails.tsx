'use client';

import { X, ExternalLink, MessageSquare, Share2, BookOpen } from 'lucide-react';

interface NodeDetailsProps {
  node: {
    id: string;
    entity_type: string;
    name: string;
    properties?: Record<string, any>;
  } | null;
  onClose: () => void;
  onAskAbout?: (nodeId: string) => void;
  onShowConnections?: (nodeId: string) => void;
}

const entityTypeColors: Record<string, { bg: string; border: string; text: string }> = {
  Paper: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700' },
  Author: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700' },
  Concept: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700' },
  Method: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700' },
  Finding: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700' },
};

export function NodeDetails({
  node,
  onClose,
  onAskAbout,
  onShowConnections,
}: NodeDetailsProps) {
  if (!node) return null;

  const colors = entityTypeColors[node.entity_type] || {
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    text: 'text-gray-700',
  };

  const properties = node.properties || {};

  return (
    <div className="absolute bottom-4 left-4 right-4 max-w-md bg-white rounded-lg shadow-lg border overflow-hidden z-10">
      {/* Header */}
      <div className={`${colors.bg} ${colors.border} border-b px-4 py-3`}>
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${colors.text} ${colors.bg}`}
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
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 max-h-64 overflow-y-auto">
        {/* Paper-specific fields */}
        {node.entity_type === 'Paper' && (
          <div className="space-y-3">
            {properties.abstract && (
              <div>
                <p className="text-sm font-medium text-gray-700 mb-1">Abstract</p>
                <p className="text-sm text-gray-600 line-clamp-4">
                  {properties.abstract}
                </p>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 text-sm">
              {properties.year && (
                <div>
                  <span className="text-gray-500">Year:</span>{' '}
                  <span className="text-gray-900">{properties.year}</span>
                </div>
              )}
              {properties.citation_count !== undefined && (
                <div>
                  <span className="text-gray-500">Citations:</span>{' '}
                  <span className="text-gray-900">{properties.citation_count}</span>
                </div>
              )}
              {properties.source && (
                <div>
                  <span className="text-gray-500">Source:</span>{' '}
                  <span className="text-gray-900">{properties.source}</span>
                </div>
              )}
            </div>

            {properties.doi && (
              <a
                href={`https://doi.org/${properties.doi}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
              >
                <ExternalLink className="w-4 h-4" />
                View on DOI
              </a>
            )}
          </div>
        )}

        {/* Author-specific fields */}
        {node.entity_type === 'Author' && (
          <div className="space-y-2">
            {properties.affiliation && (
              <div>
                <p className="text-sm text-gray-500">Affiliation</p>
                <p className="text-sm text-gray-900">{properties.affiliation}</p>
              </div>
            )}
            {properties.paper_count && (
              <div>
                <p className="text-sm text-gray-500">Papers in this collection</p>
                <p className="text-sm text-gray-900">{properties.paper_count}</p>
              </div>
            )}
          </div>
        )}

        {/* Concept/Method/Finding fields */}
        {['Concept', 'Method', 'Finding'].includes(node.entity_type) && (
          <div className="space-y-2">
            {properties.description && (
              <div>
                <p className="text-sm text-gray-500">Description</p>
                <p className="text-sm text-gray-900">{properties.description}</p>
              </div>
            )}
            {properties.paper_count && (
              <div>
                <p className="text-sm text-gray-500">Mentioned in</p>
                <p className="text-sm text-gray-900">
                  {properties.paper_count} papers
                </p>
              </div>
            )}
          </div>
        )}

        {/* Generic properties fallback */}
        {!['Paper', 'Author', 'Concept', 'Method', 'Finding'].includes(
          node.entity_type
        ) && (
          <div className="space-y-2">
            {Object.entries(properties).map(([key, value]) => (
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
        )}
      </div>

      {/* Actions */}
      <div className="px-4 py-3 border-t bg-gray-50 flex gap-2">
        {onAskAbout && (
          <button
            onClick={() => onAskAbout(node.id)}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
          >
            <MessageSquare className="w-4 h-4" />
            Ask AI
          </button>
        )}
        {onShowConnections && (
          <button
            onClick={() => onShowConnections(node.id)}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border text-gray-700 text-sm rounded-lg hover:bg-gray-100 transition-colors"
          >
            <Share2 className="w-4 h-4" />
            Show Connections
          </button>
        )}
      </div>
    </div>
  );
}
