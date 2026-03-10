import { useState, useMemo } from 'react';
import { SentimentMoverCard } from '../components/sentiment/SentimentMoverCard';
import { SentimentDetail } from '../components/sentiment/SentimentDetail';
import { useSentiment, useSentimentMovers, useSentimentAlerts, useRefreshSentiment } from '../hooks/useSentiment';

export function Sentiment() {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  // Queries
  const { data: moversData, isLoading: moversLoading, error: moversError } = useSentimentMovers(20);
  const { data: sentimentData, isLoading: sentimentLoading } = useSentiment(selectedTicker);
  const { data: alertsData, isLoading: alertsLoading } = useSentimentAlerts();
  const { mutate: refreshSentiment, isPending: isRefreshing } = useRefreshSentiment();

  const movers = useMemo(() => moversData || [], [moversData]);
  const alerts = useMemo(() => alertsData || [], [alertsData]);
  const activeAlerts = useMemo(() => alerts.filter(a => !a.resolved_at), [alerts]);

  const handleSelectTicker = (ticker: string) => {
    setSelectedTicker(ticker);
  };

  return (
    <div className="p-4 space-y-3 h-screen flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold text-neutral-100">News Sentiment Scoring</h1>
          {activeAlerts.length > 0 && (
            <div className="px-2 py-1 rounded bg-yellow-950 border border-yellow-800 text-yellow-400 text-xs font-semibold">
              {activeAlerts.length} Alert{activeAlerts.length !== 1 ? 's' : ''}
            </div>
          )}
        </div>
        <button
          onClick={() => refreshSentiment()}
          disabled={isRefreshing}
          className="px-3 py-1 rounded text-xs font-medium bg-neutral-800 hover:bg-neutral-700 disabled:opacity-50 transition-colors text-neutral-300"
        >
          {isRefreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-4 flex-1 min-h-0">
        {/* Left Panel: Movers Feed (60%) */}
        <div className="col-span-2 flex flex-col min-h-0 border border-neutral-800 rounded bg-[#0a0a0a]">
          <div className="p-3 border-b border-neutral-800">
            <h2 className="text-sm font-semibold text-neutral-100">Sentiment Movers</h2>
            <p className="text-xs text-neutral-500 mt-1">
              Top velocity changes in news sentiment
            </p>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto p-3">
            {moversError ? (
              <div className="p-4 rounded border border-red-900 bg-red-950 text-red-400 text-xs">
                Error loading movers: {moversError.message}
              </div>
            ) : moversLoading ? (
              <div className="flex items-center justify-center p-8 text-neutral-500 text-xs">
                Loading sentiment movers...
              </div>
            ) : movers.length === 0 ? (
              <div className="flex items-center justify-center p-8 text-neutral-500 text-xs">
                No sentiment movers available
              </div>
            ) : (
              <div className="space-y-2">
                {movers.map((mover) => (
                  <SentimentMoverCard
                    key={mover.ticker}
                    mover={mover}
                    isSelected={selectedTicker === mover.ticker}
                    onClick={handleSelectTicker}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Panel: Detail (40%) */}
        <div className="col-span-1 flex flex-col min-h-0">
          <SentimentDetail
            ticker={selectedTicker}
            sentiment={sentimentData || null}
            isLoading={sentimentLoading}
          />
        </div>
      </div>
    </div>
  );
}
