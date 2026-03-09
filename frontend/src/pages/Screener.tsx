import { useState } from 'react';
import { SearchBar } from '../components/screener/SearchBar';
import { StockGraderCard } from '../components/screener/StockGraderCard';
import { WatchlistSidebar } from '../components/screener/WatchlistSidebar';
import { ScreenerResults } from '../components/screener/ScreenerResults';
import { useStockQuote } from '../hooks/useStockQuote';
import { useStockGrade } from '../hooks/useStockGrade';
import { useAddToWatchlist } from '../hooks/useWatchlist';
import { LoadingState } from '../components/shared/LoadingState';

export function Screener() {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const { data: quote, isLoading: quoteLoading } = useStockQuote(selectedTicker);
  const { mutate: grade, data: gradeData, isPending: gradeLoading } = useStockGrade();
  const { mutate: addToWatchlist } = useAddToWatchlist();

  const handleSelectTicker = (ticker: string) => {
    setSelectedTicker(ticker);
    grade(ticker);
  };

  return (
    <div className="p-4 space-y-3">
      <SearchBar onSelect={handleSelectTicker} />

      <div className="grid gap-4 lg:grid-cols-4">
        <div className="lg:col-span-3">
          {!selectedTicker ? (
            <ScreenerResults />
          ) : quoteLoading || gradeLoading ? (
            <LoadingState message="Loading stock data..." />
          ) : gradeData && quote ? (
            <div className="space-y-3">
              <div className="border border-neutral-800 rounded p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-lg font-bold text-neutral-100">{selectedTicker}</span>
                    <span className="text-sm font-mono text-neutral-500 ml-3">${quote.price.toFixed(2)}</span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => addToWatchlist(selectedTicker!)}
                      className="px-3 py-1 rounded text-xs font-medium text-neutral-400 border border-neutral-800 hover:text-neutral-200 hover:border-neutral-700 transition-colors"
                    >
                      + Watchlist
                    </button>
                    <button
                      onClick={() => setSelectedTicker(null)}
                      className="px-3 py-1 rounded text-xs font-medium text-neutral-500 hover:text-neutral-300 transition-colors"
                    >
                      Back
                    </button>
                  </div>
                </div>
              </div>
              <StockGraderCard ticker={selectedTicker} grade={gradeData} />
            </div>
          ) : null}
        </div>

        <div className="lg:col-span-1">
          <WatchlistSidebar selectedTicker={selectedTicker ?? undefined} onSelect={handleSelectTicker} />
        </div>
      </div>
    </div>
  );
}
