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
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-4">Stock Screener</h1>
        <SearchBar onSelect={handleSelectTicker} />
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        <div className="lg:col-span-3">
          {!selectedTicker ? (
            <div>
              <ScreenerResults />
            </div>
          ) : quoteLoading || gradeLoading ? (
            <LoadingState message="Loading stock data..." />
          ) : gradeData && quote ? (
            <div className="space-y-4">
              <div className="rounded-lg border border-gray-700 bg-gray-800/30 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-bold text-white">{selectedTicker}</h2>
                    <p className="text-lg font-mono text-gray-400">${quote.price.toFixed(2)}</p>
                  </div>
                  <button
                    onClick={() => addToWatchlist(selectedTicker!)}
                    className="px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 transition-colors"
                  >
                    Add to Watchlist
                  </button>
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
