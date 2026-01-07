'use client';

import { useState } from 'react';
import { Filter, ChevronDown, ChevronUp, X } from 'lucide-react';

interface FilterPanelProps {
  entityTypes: string[];
  selectedTypes: string[];
  onTypeChange: (types: string[]) => void;
  yearRange?: [number, number];
  onYearRangeChange?: (range: [number, number]) => void;
  minYear?: number;
  maxYear?: number;
}

const entityTypeColors: Record<string, { bg: string; text: string }> = {
  Paper: { bg: 'bg-blue-100', text: 'text-blue-700' },
  Author: { bg: 'bg-green-100', text: 'text-green-700' },
  Concept: { bg: 'bg-purple-100', text: 'text-purple-700' },
  Method: { bg: 'bg-amber-100', text: 'text-amber-700' },
  Finding: { bg: 'bg-red-100', text: 'text-red-700' },
};

export function FilterPanel({
  entityTypes,
  selectedTypes,
  onTypeChange,
  yearRange,
  onYearRangeChange,
  minYear = 2015,
  maxYear = 2025,
}: FilterPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const toggleType = (type: string) => {
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

  return (
    <div className="absolute top-4 right-4 bg-white rounded-lg shadow-lg border w-64 z-10">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <span className="font-medium text-gray-900">Filters</span>
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
                };
                const isSelected = selectedTypes.includes(type);

                return (
                  <button
                    key={type}
                    onClick={() => toggleType(type)}
                    className={`w-full flex items-center justify-between px-2 py-1.5 rounded text-sm transition-colors ${
                      isSelected
                        ? `${colors.bg} ${colors.text}`
                        : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
                    }`}
                  >
                    <span>{type}</span>
                    {isSelected && <X className="w-3 h-3" />}
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
          {selectedTypes.length > 0 && selectedTypes.length < entityTypes.length && (
            <div className="pt-2 border-t">
              <p className="text-xs text-gray-500">
                Showing {selectedTypes.length} of {entityTypes.length} types
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
