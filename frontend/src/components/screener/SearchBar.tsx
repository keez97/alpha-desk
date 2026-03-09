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
          placeholder="Search ticker..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          className="w-full rounded-lg border border-gray-700 bg-gray-800/50 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        {isLoading && (
          <div className="absolute right-3 top-2.5 h-5 w-5 animate-spin rounded-full border-2 border-gray-700 border-t-blue-500"></div>
        )}
      </div>

      {isOpen && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 z-50 mt-2 rounded-lg border border-gray-700 bg-gray-800 shadow-lg">
          <div className="max-h-64 overflow-y-auto">
            {results.map((result, idx) => (
              <button
                key={idx}
                onClick={() => handleSelect(result.ticker)}
                className="w-full px-4 py-3 text-left hover:bg-gray-700/50 border-b border-gray-700/30 last:border-b-0 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <span className="inline-block rounded bg-blue-500/20 px-2 py-1 font-mono font-semibold text-blue-400 text-sm">
                    {result.ticker}
                  </span>
                  <div>
                    <div className="font-medium text-white">{result.name}</div>
                    <div className="text-xs text-gray-400">{result.sector}</div>
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
