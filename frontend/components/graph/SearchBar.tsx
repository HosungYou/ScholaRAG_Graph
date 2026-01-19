'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Search, X, Loader2, FileText, User, Lightbulb, Beaker, Trophy, Square, Hexagon, Diamond, Pentagon, Octagon } from 'lucide-react';
import { debounce } from '@/lib/utils';
import type { SearchResult, EntityType } from '@/types';

/* ============================================================
   SearchBar - VS Design Diverge Style
   Direction B (T-Score 0.4) "Editorial Research"

   Design Principles:
   - Line-based input (underline only, no border)
   - Monospace labels and metadata
   - Polygon icons matching PolygonNode
   - Sharp corners, no rounded-lg
   ============================================================ */

interface SearchBarProps {
  onSearch: (query: string) => Promise<SearchResult[]>;
  onSelectResult: (result: SearchResult) => void;
  placeholder?: string;
}

// VS Design Diverge palette - matching PolygonNode.tsx exactly
const entityTypeConfig: Record<EntityType, { color: string; icon: React.ReactNode }> = {
  Paper: {
    color: '#6366F1', // Indigo
    icon: <Square className="w-3 h-3" strokeWidth={2} />
  },
  Author: {
    color: '#A855F7', // Purple
    icon: <Hexagon className="w-3 h-3" strokeWidth={2} />
  },
  Concept: {
    color: '#8B5CF6', // Violet
    icon: <Lightbulb className="w-3 h-3" strokeWidth={2} />
  },
  Method: {
    color: '#F59E0B', // Amber
    icon: <Beaker className="w-3 h-3" strokeWidth={2} />
  },
  Finding: {
    color: '#10B981', // Emerald
    icon: <Trophy className="w-3 h-3" strokeWidth={2} />
  },
};

export function SearchBar({
  onSearch,
  onSelectResult,
  placeholder = 'Search nodes...',
}: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced search function
  const debouncedSearch = useCallback(
    debounce(async (searchQuery: string) => {
      if (!searchQuery.trim()) {
        setResults([]);
        setIsLoading(false);
        return;
      }

      try {
        const searchResults = await onSearch(searchQuery);
        setResults(searchResults);
      } catch (error) {
        console.error('Search failed:', error);
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 300),
    [onSearch]
  );

  // Handle input change
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    setIsLoading(true);
    setIsOpen(true);
    setActiveIndex(-1);
    debouncedSearch(value);
  };

  // Handle result selection
  const handleSelect = (result: SearchResult) => {
    onSelectResult(result);
    setQuery('');
    setResults([]);
    setIsOpen(false);
    inputRef.current?.blur();
  };

  // Handle clear
  const handleClear = () => {
    setQuery('');
    setResults([]);
    setIsOpen(false);
    setActiveIndex(-1);
    inputRef.current?.focus();
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
      inputRef.current?.blur();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex(prev => Math.min(prev + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex(prev => Math.max(prev - 1, -1));
    } else if (e.key === 'Enter' && activeIndex >= 0 && results[activeIndex]) {
      handleSelect(results[activeIndex]);
    }
  };

  return (
    <div ref={containerRef} className="relative w-80">
      {/* Search Input - VS Design Diverge Style */}
      <div className="relative group">
        {/* Floating label effect */}
        <div className="absolute -top-5 left-0 font-mono text-xs uppercase tracking-widest text-muted opacity-0 group-focus-within:opacity-100 transition-opacity">
          Search
        </div>

        <Search className="absolute left-0 top-1/2 -translate-y-1/2 w-4 h-4 text-muted group-focus-within:text-accent-teal transition-colors" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleChange}
          onFocus={() => query && setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full pl-7 pr-8 py-2 bg-transparent border-0 border-b-2 border-ink/20 dark:border-paper/20 focus:border-accent-teal focus:outline-none text-sm text-ink dark:text-paper font-mono placeholder:text-muted transition-colors"
        />
        {query && (
          <button
            onClick={handleClear}
            className="absolute right-0 top-1/2 -translate-y-1/2 p-1 text-muted hover:text-accent-red transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <X className="w-4 h-4" />
            )}
          </button>
        )}
      </div>

      {/* Results Dropdown - VS Design Diverge Style */}
      {isOpen && (query || results.length > 0) && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 shadow-lg max-h-80 overflow-y-auto z-50">
          {/* Result count header */}
          {results.length > 0 && (
            <div className="px-3 py-2 border-b border-ink/10 dark:border-paper/10">
              <span className="font-mono text-xs uppercase tracking-wider text-muted">
                {results.length} result{results.length !== 1 ? 's' : ''}
              </span>
            </div>
          )}

          {results.length === 0 && !isLoading && query && (
            <div className="p-4 text-center">
              <p className="font-mono text-xs text-muted uppercase tracking-wider mb-1">No Results</p>
              <p className="text-sm text-muted">No matches for "{query}"</p>
            </div>
          )}

          {results.length > 0 && (
            <ul className="divide-y divide-ink/5 dark:divide-paper/5">
              {results.map((result, index) => {
                const config = entityTypeConfig[result.entity_type] || {
                  color: '#6B7280',
                  icon: <Square className="w-3 h-3" />,
                };
                const isActive = index === activeIndex;

                return (
                  <li key={result.id}>
                    <button
                      onClick={() => handleSelect(result)}
                      onMouseEnter={() => setActiveIndex(index)}
                      className={`w-full px-3 py-3 text-left flex items-start gap-3 transition-all relative ${
                        isActive ? 'bg-surface/10' : 'hover:bg-surface/5'
                      }`}
                    >
                      {/* Left accent bar for active item */}
                      {isActive && (
                        <div
                          className="absolute left-0 top-0 bottom-0 w-0.5"
                          style={{ backgroundColor: config.color }}
                        />
                      )}

                      {/* Entity type badge */}
                      <span
                        className="inline-flex items-center gap-1.5 font-mono text-xs px-2 py-1 border flex-shrink-0"
                        style={{
                          color: config.color,
                          borderColor: `${config.color}40`,
                        }}
                      >
                        {config.icon}
                        {result.entity_type}
                      </span>

                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-ink dark:text-paper truncate font-medium">
                          {result.name}
                        </p>
                        {(() => {
                          const props = result.properties as Record<string, unknown> | undefined;
                          const year = props?.year;
                          return year ? (
                            <p className="font-mono text-xs text-muted mt-0.5">{String(year)}</p>
                          ) : null;
                        })()}
                        {result.score !== undefined && (
                          <div className="flex items-center gap-2 mt-1">
                            <div className="h-1 w-16 bg-ink/10 dark:bg-paper/10 overflow-hidden">
                              <div
                                className="h-full transition-all"
                                style={{
                                  width: `${result.score * 100}%`,
                                  backgroundColor: config.color,
                                }}
                              />
                            </div>
                            <span className="font-mono text-xs text-muted">
                              {Math.round(result.score * 100)}%
                            </span>
                          </div>
                        )}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}

          {isLoading && (
            <div className="p-4 flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 text-accent-teal animate-spin" />
              <span className="font-mono text-xs text-muted uppercase tracking-wider">
                Searching...
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
