'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Search, X, Loader2, FileText, User, Lightbulb, Beaker, Trophy } from 'lucide-react';
import { debounce } from '@/lib/utils';
import type { SearchResult, EntityType } from '@/types';

interface SearchBarProps {
  onSearch: (query: string) => Promise<SearchResult[]>;
  onSelectResult: (result: SearchResult) => void;
  placeholder?: string;
}

const entityTypeConfig: Record<EntityType, { color: string; bg: string; icon: React.ReactNode }> = {
  Paper: { color: 'text-blue-600', bg: 'bg-blue-50', icon: <FileText className="w-3 h-3" /> },
  Author: { color: 'text-green-600', bg: 'bg-green-50', icon: <User className="w-3 h-3" /> },
  Concept: { color: 'text-purple-600', bg: 'bg-purple-50', icon: <Lightbulb className="w-3 h-3" /> },
  Method: { color: 'text-amber-600', bg: 'bg-amber-50', icon: <Beaker className="w-3 h-3" /> },
  Finding: { color: 'text-red-600', bg: 'bg-red-50', icon: <Trophy className="w-3 h-3" /> },
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
    }
  };

  return (
    <div ref={containerRef} className="relative w-80">
      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleChange}
          onFocus={() => query && setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full pl-10 pr-10 py-2 border rounded-lg bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
        />
        {query && (
          <button
            onClick={handleClear}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 hover:bg-gray-100 rounded"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
            ) : (
              <X className="w-4 h-4 text-gray-400" />
            )}
          </button>
        )}
      </div>

      {/* Results Dropdown */}
      {isOpen && (query || results.length > 0) && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border rounded-lg shadow-lg max-h-80 overflow-y-auto z-50">
          {results.length === 0 && !isLoading && query && (
            <div className="p-3 text-sm text-gray-500 text-center">
              No results found for "{query}"
            </div>
          )}

          {results.length > 0 && (
            <ul className="py-1">
              {results.map((result) => {
                const config = entityTypeConfig[result.entity_type] || {
                  color: 'text-gray-600',
                  bg: 'bg-gray-100',
                  icon: null,
                };
                return (
                  <li key={result.id}>
                    <button
                      onClick={() => handleSelect(result)}
                      className="w-full px-3 py-2 text-left hover:bg-gray-50 flex items-start gap-3 transition-colors"
                    >
                      <span
                        className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded ${config.color} ${config.bg}`}
                      >
                        {config.icon}
                        {result.entity_type}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-900 truncate">
                          {result.name}
                        </p>
                        {(() => {
                          const props = result.properties as Record<string, unknown> | undefined;
                          const year = props?.year;
                          return year ? (
                            <p className="text-xs text-gray-500">{String(year)}</p>
                          ) : null;
                        })()}
                        {result.score !== undefined && (
                          <p className="text-xs text-gray-400">
                            Relevance: {Math.round(result.score * 100)}%
                          </p>
                        )}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}

          {isLoading && (
            <div className="p-3 text-sm text-gray-500 text-center flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Searching...
            </div>
          )}
        </div>
      )}
    </div>
  );
}
