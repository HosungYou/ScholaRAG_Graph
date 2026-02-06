'use client';

import { useState } from 'react';
import { Filter, ChevronDown, ChevronUp, X, RotateCcw, Hexagon, Diamond, Square, Pentagon, Octagon } from 'lucide-react';
import type { EntityType } from '@/types';

/* ============================================================
   FilterPanel - VS Design Diverge Style
   Direction B (T-Score 0.4) "Editorial Research"

   Design Principles:
   - Line-based layout (no rounded corners)
   - Monospace labels
   - Left accent bar for active states
   - Polygon icons for entity types
   ============================================================ */

interface FilterPanelProps {
  entityTypes: EntityType[];
  selectedTypes: EntityType[];
  onTypeChange: (types: EntityType[]) => void;
  yearRange?: [number, number];
  onYearRangeChange?: (range: [number, number]) => void;
  minYear?: number;
  maxYear?: number;
  onReset?: () => void;
  nodeCountsByType?: Record<EntityType, number>;
  // Data source information
  dataSource?: 'zotero' | 'pdf' | 'scholarag' | null;
}

// VS Design Diverge palette - matching PolygonNode colors exactly
const entityTypeConfig: Record<string, { color: string; icon: React.ReactNode }> = {
  // Primary entities (Hybrid Mode: visualized)
  Paper: {
    color: '#6366F1', // Indigo - 논문 노드
    icon: <Square className="w-3 h-3" strokeWidth={2} />
  },
  Author: {
    color: '#A855F7', // Purple - 저자 노드
    icon: <Hexagon className="w-3 h-3" strokeWidth={2} />
  },
  // Concept-centric entities (always visualized)
  Concept: {
    color: '#8B5CF6', // Violet - matches PolygonNode
    icon: <Hexagon className="w-3 h-3" strokeWidth={2} />
  },
  Method: {
    color: '#F59E0B', // Amber - matches PolygonNode
    icon: <Diamond className="w-3 h-3" strokeWidth={2} />
  },
  Finding: {
    color: '#10B981', // Emerald - matches PolygonNode
    icon: <Pentagon className="w-3 h-3" strokeWidth={2} />
  },
  // Secondary entities
  Problem: {
    color: '#EF4444', // Red
    icon: <Octagon className="w-3 h-3" strokeWidth={2} />
  },
  Dataset: {
    color: '#3B82F6', // Blue
    icon: <Square className="w-3 h-3" strokeWidth={2} />
  },
  Metric: {
    color: '#EC4899', // Pink
    icon: <Diamond className="w-3 h-3" strokeWidth={2} />
  },
  Innovation: {
    color: '#14B8A6', // Teal
    icon: <Hexagon className="w-3 h-3" strokeWidth={2} />
  },
  Limitation: {
    color: '#F97316', // Orange
    icon: <Pentagon className="w-3 h-3" strokeWidth={2} />
  },
  // TTO entities
  Invention: {
    color: '#F59E0B',
    icon: <Hexagon className="w-3 h-3" strokeWidth={2} />
  },
  Patent: {
    color: '#6366F1',
    icon: <Square className="w-3 h-3" strokeWidth={2} />
  },
  Inventor: {
    color: '#8B5CF6',
    icon: <Hexagon className="w-3 h-3" strokeWidth={2} />
  },
  Technology: {
    color: '#06B6D4',
    icon: <Hexagon className="w-3 h-3" strokeWidth={2} />
  },
  License: {
    color: '#10B981',
    icon: <Diamond className="w-3 h-3" strokeWidth={2} />
  },
  Grant: {
    color: '#F97316',
    icon: <Pentagon className="w-3 h-3" strokeWidth={2} />
  },
  Department: {
    color: '#A855F7',
    icon: <Octagon className="w-3 h-3" strokeWidth={2} />
  },
};

// Data source badge styles
const dataSourceStyles: Record<string, { bg: string; text: string; label: string }> = {
  zotero: { bg: 'bg-purple-500/10', text: 'text-purple-400', label: 'ZOTERO' },
  pdf: { bg: 'bg-blue-500/10', text: 'text-blue-400', label: 'PDF' },
  scholarag: { bg: 'bg-accent-teal/10', text: 'text-accent-teal', label: 'SCHOLARAG' },
};

export function FilterPanel({
  entityTypes,
  selectedTypes,
  onTypeChange,
  yearRange,
  onYearRangeChange,
  minYear = 2015,
  maxYear = 2025,
  onReset,
  nodeCountsByType,
  dataSource,
}: FilterPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const toggleType = (type: EntityType) => {
    if (selectedTypes.includes(type)) {
      onTypeChange(selectedTypes.filter((t) => t !== type));
    } else {
      onTypeChange([...selectedTypes, type]);
    }
  };

  const selectAll = () => {
    onTypeChange([...entityTypes]);
  };

  const clearAll = () => {
    onTypeChange([]);
  };

  const hasActiveFilters = selectedTypes.length < entityTypes.length || yearRange !== null;

  return (
    <div className="absolute top-4 right-4 bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 w-64 z-10">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-surface/5 transition-colors border-b border-ink/10 dark:border-paper/10"
      >
        <div className="flex items-center gap-2">
          <Filter className={`w-4 h-4 ${hasActiveFilters ? 'text-accent-teal' : 'text-muted'}`} />
          <span className="font-mono text-xs uppercase tracking-wider text-ink dark:text-paper">
            Filters
          </span>
          {/* Data Source Badge */}
          {dataSource && dataSourceStyles[dataSource] && (
            <span className={`px-1.5 py-0.5 ${dataSourceStyles[dataSource].bg} ${dataSourceStyles[dataSource].text} text-xs font-mono`}>
              {dataSourceStyles[dataSource].label}
            </span>
          )}
          {hasActiveFilters && !dataSource && (
            <span className="px-1.5 py-0.5 bg-accent-teal/10 text-accent-teal text-xs font-mono">
              ON
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
        <div className="p-3 space-y-4">
          {/* Entity Types */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="font-mono text-xs uppercase tracking-wider text-muted">
                Node Types
              </span>
              <div className="flex gap-3">
                <button
                  onClick={selectAll}
                  className="font-mono text-xs text-accent-teal hover:text-accent-teal/80 transition-colors"
                >
                  All
                </button>
                <button
                  onClick={clearAll}
                  className="font-mono text-xs text-muted hover:text-ink dark:hover:text-paper transition-colors"
                >
                  None
                </button>
              </div>
            </div>

            <div className="space-y-1">
              {entityTypes.map((type) => {
                const config = entityTypeConfig[type] || {
                  color: '#64748B',
                  icon: <Square className="w-3 h-3" />,
                };
                const isSelected = selectedTypes.includes(type);
                const count = nodeCountsByType?.[type] || 0;

                return (
                  <button
                    key={type}
                    onClick={() => toggleType(type)}
                    className={`w-full flex items-center justify-between px-3 py-2 text-sm transition-all relative ${
                      isSelected
                        ? 'bg-surface/5'
                        : 'hover:bg-surface/5'
                    }`}
                  >
                    {/* Left accent bar for selected */}
                    {isSelected && (
                      <div
                        className="absolute left-0 top-0 bottom-0 w-0.5"
                        style={{ backgroundColor: config.color }}
                      />
                    )}

                    <div className="flex items-center gap-2">
                      <span style={{ color: isSelected ? config.color : 'var(--color-muted)' }}>
                        {config.icon}
                      </span>
                      <span className={`${isSelected ? 'text-ink dark:text-paper' : 'text-muted'}`}>
                        {type}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-muted">{count}</span>
                      {isSelected && (
                        <X className="w-3 h-3 text-muted hover:text-accent-red transition-colors" />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Year Range */}
          {onYearRangeChange && yearRange && (
            <div className="pt-3 border-t border-ink/10 dark:border-paper/10">
              <span className="font-mono text-xs uppercase tracking-wider text-muted block mb-3">
                Year Range
              </span>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={minYear}
                  max={yearRange[1]}
                  value={yearRange[0]}
                  onChange={(e) =>
                    onYearRangeChange([parseInt(e.target.value), yearRange[1]])
                  }
                  className="w-20 px-2 py-1.5 bg-transparent border-b border-ink/20 dark:border-paper/20 focus:border-accent-teal focus:outline-none text-sm font-mono text-ink dark:text-paper"
                />
                <span className="text-muted">—</span>
                <input
                  type="number"
                  min={yearRange[0]}
                  max={maxYear}
                  value={yearRange[1]}
                  onChange={(e) =>
                    onYearRangeChange([yearRange[0], parseInt(e.target.value)])
                  }
                  className="w-20 px-2 py-1.5 bg-transparent border-b border-ink/20 dark:border-paper/20 focus:border-accent-teal focus:outline-none text-sm font-mono text-ink dark:text-paper"
                />
              </div>
            </div>
          )}

          {/* Active Filters Summary */}
          {hasActiveFilters && (
            <div className="pt-3 border-t border-ink/10 dark:border-paper/10">
              <div className="flex items-center justify-between">
                <p className="font-mono text-xs text-muted">
                  {selectedTypes.length}/{entityTypes.length} types
                </p>
                {onReset && (
                  <button
                    onClick={onReset}
                    className="flex items-center gap-1 font-mono text-xs text-accent-red hover:text-accent-red/80 transition-colors"
                  >
                    <RotateCcw className="w-3 h-3" />
                    Reset
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
