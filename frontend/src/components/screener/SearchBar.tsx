import { useState, useEffect, useRef } from 'react';
import { searchTicker } from '../../lib/api';

interface SearchBarProps {
  onSelect: (ticker: string) => void;
}

export function SearchBar({ onSelect }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);

    if (query.length < 1) {
      setResults([]);
      return;
    }

    setIsLoading(true);
    timeoutRef.current = setTimeout(async () => {
      try {
        const data = await searchTicker(query);
        setResults(data);
        setIsOpen(true);
      } catch (err) {
        console.error('Search failed:', err);
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 300);
  }, [query]);

  const handleSelect = (ticker: string) => {
    onSelect(ticker);
    setQuery('');
    setResults([]);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <div className="relative">
        <input
          type="text"
          placeholder="Search ticker or company..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          className="w-full rounded border border-neutral-800 bg-neutral-950 px-3 py-1.5 text-sm text-neutral-200 placeholder-neutral-600 focus:border-neutral-600 focus:outline-none"
        />
        {isLoading && (
          <div className="absolute right-3 top-2 h-4 w-4 animate-spin rounded-full border-2 border-neutral-700 border-t-neutral-400"></div>
        )}
      </div>

      {isOpen && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 z-50 mt-1 rounded border border-neutral-800 bg-neutral-950 shadow-lg">
          <div className="max-h-64 overflow-y-auto">
            {results.map((result, idx) => (
              <button
                key={idx}
                onClick={() => handleSelect(result.ticker)}
                className="w-full px-3 py-2 text-left hover:bg-neutral-900 border-b border-neutral-900 last:border-b-0 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono font-medium text-neutral-200 text-xs">
                    {result.ticker}
                  </span>
                  <div>
                    <div className="text-xs text-neutral-400">{result.name}</div>
                    <div className="text-[10px] text-neutral-600">{result.sector}</div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
