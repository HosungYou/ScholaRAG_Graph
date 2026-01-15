'use client';

import { useState } from 'react';
import { Filter, ChevronDown, ChevronUp, X, RotateCcw } from 'lucide-react';
import type { EntityType } from '@/types';

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
}

// Concept-centric entity type colors
const entityTypeColors: Record<string, { bg: string; text: string; border: string; color: string }> = {
  Concept: { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-300', color: '#8B5CF6' },
  Method: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-300', color: '#F59E0B' },
  Finding: { bg: 'bg-emerald-100', text: 'text-emerald-700', border: 'border-emerald-300', color: '#10B981' },
  Problem: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-300', color: '#EF4444' },
  Dataset: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-300', color: '#3B82F6' },
  Metric: { bg: 'bg-pink-100', text: 'text-pink-700', border: 'border-pink-300', color: '#EC4899' },
  Innovation: { bg: 'bg-teal-100', text: 'text-teal-700', border: 'border-teal-300', color: '#14B8A6' },
  Limitation: { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-300', color: '#F97316' },
  // Legacy types (hidden in UI but kept for compatibility)
  Paper: { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-300', color: '#64748B' },
  Author: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-300', color: '#22C55E' },
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
    <div className="absolute top-4 right-4 bg-white rounded-lg shadow-lg border w-72 z-10">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Filter className={`w-4 h-4 ${hasActiveFilters ? 'text-blue-600' : 'text-gray-500'}`} />
          <span className="font-medium text-gray-900">Filters</span>
          {hasActiveFilters && (
            <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
              Active
            </span>
          )}
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        )}
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="p-3 border-t space-y-4">
          {/* Entity Types */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Node Types</span>
              <div className="flex gap-2">
                <button
                  onClick={selectAll}
                  className="text-xs text-blue-600 hover:text-blue-800"
                >
                  All
                </button>
                <button
                  onClick={clearAll}
                  className="text-xs text-gray-500 hover:text-gray-700"
                >
                  None
                </button>
              </div>
            </div>
            <div className="space-y-1">
              {entityTypes.map((type) => {
                const colors = entityTypeColors[type] || {
                  bg: 'bg-gray-100',
                  text: 'text-gray-700',
                  border: 'border-gray-300',
                };
                const isSelected = selectedTypes.includes(type);
                const count = nodeCountsByType?.[type] || 0;

                return (
                  <button
                    key={type}
                    onClick={() => toggleType(type)}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-all ${
                      isSelected
                        ? `${colors.bg} ${colors.text} border ${colors.border}`
                        : 'bg-gray-50 text-gray-500 hover:bg-gray-100 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          isSelected ? '' : 'bg-gray-300'
                        }`}
                        style={{
                          backgroundColor: isSelected ? colors.color : undefined,
                        }}
                      />
                      <span>{type}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">{count}</span>
                      {isSelected && <X className="w-3 h-3" />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Year Range */}
          {onYearRangeChange && yearRange && (
            <div>
              <span className="text-sm font-medium text-gray-700 block mb-2">
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
                  className="w-20 px-2 py-1 border rounded text-sm"
                />
                <span className="text-gray-500">—</span>
                <input
                  type="number"
                  min={yearRange[0]}
                  max={maxYear}
                  value={yearRange[1]}
                  onChange={(e) =>
                    onYearRangeChange([yearRange[0], parseInt(e.target.value)])
                  }
                  className="w-20 px-2 py-1 border rounded text-sm"
                />
              </div>
            </div>
          )}

          {/* Active Filters Summary */}
          {hasActiveFilters && (
            <div className="pt-3 border-t">
              <div className="flex items-center justify-between">
                <p className="text-xs text-gray-500">
                  Showing {selectedTypes.length} of {entityTypes.length} types
                </p>
                {onReset && (
                  <button
                    onClick={onReset}
                    className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 transition-colors"
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
