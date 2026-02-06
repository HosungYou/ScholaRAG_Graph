'use client';

import { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  Lightbulb,
  Beaker,
  Trophy,
  AlertCircle,
  Database,
  Target,
  Sparkles,
  AlertTriangle,
  FileText,
  User,
  Hexagon,
  Diamond,
  Square,
  Pentagon,
  Octagon,
  Circle,
  Star,
  Triangle,
} from 'lucide-react';
import type { EntityType } from '@/types';

/* ============================================================
   GraphLegend - VS Design Diverge Style
   Direction B (T-Score 0.4) "Editorial Research"

   Design Principles:
   - Line-based layout (no rounded-lg)
   - Polygon shape previews matching actual nodes
   - Monospace labels
   - Collapsible sections
   ============================================================ */

interface GraphLegendProps {
  visibleTypes?: EntityType[];
  nodeCountsByType?: Record<EntityType, number>;
}

// VS Design Diverge palette - matching PolygonNode.tsx exactly
const entityTypeConfig: Record<string, {
  color: string;
  icon: React.ReactNode;
  shape: React.ReactNode;
  description: string;
}> = {
  // Hybrid Mode entities
  Paper: {
    color: '#6366F1',
    icon: <FileText className="w-3 h-3" />,
    shape: <Square className="w-4 h-4" strokeWidth={2} />,
    description: 'Academic papers',
  },
  Author: {
    color: '#A855F7',
    icon: <User className="w-3 h-3" />,
    shape: <Circle className="w-4 h-4" strokeWidth={2} />,
    description: 'Paper authors',
  },
  // Concept-centric entities
  Concept: {
    color: '#8B5CF6',
    icon: <Lightbulb className="w-3 h-3" />,
    shape: <Hexagon className="w-4 h-4" strokeWidth={2} />,
    description: 'Key concepts',
  },
  Method: {
    color: '#F59E0B',
    icon: <Beaker className="w-3 h-3" />,
    shape: <Diamond className="w-4 h-4" strokeWidth={2} />,
    description: 'Research methods',
  },
  Finding: {
    color: '#10B981',
    icon: <Trophy className="w-3 h-3" />,
    shape: <Square className="w-4 h-4" strokeWidth={2} />,
    description: 'Research findings',
  },
  Problem: {
    color: '#EF4444',
    icon: <AlertCircle className="w-3 h-3" />,
    shape: <Pentagon className="w-4 h-4" strokeWidth={2} />,
    description: 'Research problems',
  },
  Dataset: {
    color: '#3B82F6',
    icon: <Database className="w-3 h-3" />,
    shape: <Octagon className="w-4 h-4" strokeWidth={2} />,
    description: 'Datasets used',
  },
  Metric: {
    color: '#EC4899',
    icon: <Target className="w-3 h-3" />,
    shape: <Circle className="w-4 h-4" strokeWidth={2} />,
    description: 'Metrics/measures',
  },
  Innovation: {
    color: '#14B8A6',
    icon: <Sparkles className="w-3 h-3" />,
    shape: <Star className="w-4 h-4" strokeWidth={2} />,
    description: 'Innovations',
  },
  Limitation: {
    color: '#F97316',
    icon: <AlertTriangle className="w-3 h-3" />,
    shape: <Triangle className="w-4 h-4" strokeWidth={2} />,
    description: 'Limitations',
  },
  // TTO entities
  Invention: {
    color: '#F59E0B',
    icon: <Lightbulb className="w-3 h-3" />,
    shape: <Star className="w-4 h-4" strokeWidth={2} />,
    description: 'Inventions',
  },
  Patent: {
    color: '#6366F1',
    icon: <FileText className="w-3 h-3" />,
    shape: <Square className="w-4 h-4" strokeWidth={2} />,
    description: 'Patents',
  },
  Inventor: {
    color: '#8B5CF6',
    icon: <User className="w-3 h-3" />,
    shape: <Circle className="w-4 h-4" strokeWidth={2} />,
    description: 'Inventors',
  },
  Technology: {
    color: '#06B6D4',
    icon: <Lightbulb className="w-3 h-3" />,
    shape: <Hexagon className="w-4 h-4" strokeWidth={2} />,
    description: 'Technologies',
  },
  License: {
    color: '#10B981',
    icon: <FileText className="w-3 h-3" />,
    shape: <Diamond className="w-4 h-4" strokeWidth={2} />,
    description: 'Licenses',
  },
  Grant: {
    color: '#F97316',
    icon: <Sparkles className="w-3 h-3" />,
    shape: <Pentagon className="w-4 h-4" strokeWidth={2} />,
    description: 'Grants',
  },
  Department: {
    color: '#A855F7',
    icon: <User className="w-3 h-3" />,
    shape: <Octagon className="w-4 h-4" strokeWidth={2} />,
    description: 'Departments',
  },
};

// Edge relationship colors
const edgeTypeConfig: Record<string, { color: string; description: string }> = {
  DISCUSSES_CONCEPT: { color: '#8B5CF6', description: 'Paper discusses concept' },
  USES_METHOD: { color: '#F59E0B', description: 'Paper uses method' },
  SUPPORTS: { color: '#10B981', description: 'Finding supports' },
  CONTRADICTS: { color: '#EF4444', description: 'Finding contradicts' },
  CITES: { color: '#3B82F6', description: 'Paper cites paper' },
  CO_OCCURS_WITH: { color: '#EC4899', description: 'Concepts co-occur' },
  BRIDGES_GAP: { color: '#FFD700', description: 'Bridges research gap' },
  // TTO relationship types
  INVENTED_BY: { color: '#8B5CF6', description: 'Invented by' },
  CITES_PRIOR_ART: { color: '#3B82F6', description: 'Cites prior art' },
  USES_TECHNOLOGY: { color: '#06B6D4', description: 'Uses technology' },
  LICENSED_TO: { color: '#10B981', description: 'Licensed to' },
  FUNDED_BY: { color: '#F97316', description: 'Funded by' },
  PATENT_OF: { color: '#6366F1', description: 'Patent of invention' },
  DEVELOPED_IN: { color: '#A855F7', description: 'Developed in department' },
  LICENSE_OF: { color: '#10B981', description: 'License of invention' },
};

export function GraphLegend({
  visibleTypes,
  nodeCountsByType,
}: GraphLegendProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showEdges, setShowEdges] = useState(false);

  // Filter to only show visible types if provided
  const displayTypes = visibleTypes
    ? Object.keys(entityTypeConfig).filter(type => visibleTypes.includes(type as EntityType))
    : Object.keys(entityTypeConfig);

  return (
    <div className="absolute bottom-4 left-4 bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 w-64 overflow-hidden z-10">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-surface/5 transition-colors border-b border-ink/10 dark:border-paper/10"
      >
        <div className="flex items-center gap-2">
          <Hexagon className="w-4 h-4 text-accent-teal" />
          <span className="font-mono text-xs uppercase tracking-wider text-ink dark:text-paper">
            Legend
          </span>
        </div>
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-muted" />
        ) : (
          <ChevronUp className="w-4 h-4 text-muted" />
        )}
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="p-3 space-y-4 max-h-80 overflow-y-auto">
          {/* Node Types */}
          <div>
            <p className="font-mono text-xs uppercase tracking-wider text-muted mb-2">
              Node Types
            </p>
            <div className="space-y-1">
              {displayTypes.map((type) => {
                const config = entityTypeConfig[type];
                const count = nodeCountsByType?.[type as EntityType];

                return (
                  <div
                    key={type}
                    className="flex items-center justify-between py-1.5 px-2 hover:bg-surface/5 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      {/* Shape preview */}
                      <div
                        className="flex items-center justify-center w-5 h-5"
                        style={{ color: config.color }}
                      >
                        {config.shape}
                      </div>
                      {/* Icon + Label */}
                      <div className="flex items-center gap-1.5">
                        <span style={{ color: config.color }}>{config.icon}</span>
                        <span className="text-xs text-ink dark:text-paper">{type}</span>
                      </div>
                    </div>
                    {count !== undefined && (
                      <span className="font-mono text-xs text-muted">{count}</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Edge Types Toggle */}
          <div>
            <button
              onClick={() => setShowEdges(!showEdges)}
              className="w-full flex items-center justify-between font-mono text-xs uppercase tracking-wider text-muted hover:text-ink dark:hover:text-paper transition-colors"
            >
              <span>Relationship Types</span>
              {showEdges ? (
                <ChevronUp className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              )}
            </button>

            {showEdges && (
              <div className="mt-2 space-y-1">
                {Object.entries(edgeTypeConfig).map(([type, config]) => (
                  <div
                    key={type}
                    className="flex items-center gap-2 py-1.5 px-2"
                  >
                    {/* Line preview */}
                    <div className="w-6 h-0.5 relative">
                      <div
                        className="absolute inset-0"
                        style={{ backgroundColor: config.color }}
                      />
                      {/* Arrow head */}
                      <div
                        className="absolute right-0 top-1/2 -translate-y-1/2 w-0 h-0"
                        style={{
                          borderLeft: `4px solid ${config.color}`,
                          borderTop: '2px solid transparent',
                          borderBottom: '2px solid transparent',
                        }}
                      />
                    </div>
                    <span className="text-xs text-muted truncate flex-1" title={config.description}>
                      {type.replace(/_/g, ' ')}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Size Legend */}
          <div className="pt-3 border-t border-ink/10 dark:border-paper/10">
            <p className="font-mono text-xs uppercase tracking-wider text-muted mb-2">
              Node Size
            </p>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full bg-accent-teal/50" />
                <span className="text-xs text-muted">Low</span>
              </div>
              <div className="flex-1 h-0.5 bg-gradient-to-r from-accent-teal/30 via-accent-teal/60 to-accent-teal" />
              <div className="flex items-center gap-1">
                <div className="w-5 h-5 rounded-full bg-accent-teal" />
                <span className="text-xs text-muted">High</span>
              </div>
            </div>
            <p className="text-xs text-muted mt-1">Based on PageRank importance</p>
          </div>

          {/* Interaction Hint */}
          <div className="pt-3 border-t border-ink/10 dark:border-paper/10">
            <p className="font-mono text-xs uppercase tracking-wider text-muted mb-2">
              Interactions
            </p>
            <div className="space-y-1 text-xs text-muted">
              <div className="flex items-center gap-2">
                <span className="font-mono text-accent-teal">Click</span>
                <span>Highlight connections</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-accent-amber">Hover</span>
                <span>View details</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-accent-red">Drag</span>
                <span>Move node</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
