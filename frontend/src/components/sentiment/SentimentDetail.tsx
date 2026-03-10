import { useSentimentHistory, useSentimentNews } from '../../hooks/useSentiment';
import { useSentimentAlerts } from '../../hooks/useSentiment';
import { SentimentData, SentimentAlert } from '../../lib/api';
import { SentimentScore } from './SentimentScore';
import { SentimentChart } from './SentimentChart';
import { SentimentAlertBadge } from './SentimentAlertBadge';
import { NewsFeed } from './NewsFeed';

interface SentimentDetailProps {
  ticker: string | null;
  sentiment: SentimentData | null;
  isLoading: boolean;
}

export function SentimentDetail({
  ticker,
  sentiment,
  isLoading,
}: SentimentDetailProps) {
  const { data: history, isLoading: historyLoading } = useSentimentHistory(ticker);
  const { data: news, isLoading: newsLoading } = useSentimentNews(ticker);
  const { data: allAlerts } = useSentimentAlerts();

  // Filter alerts for this ticker
  const tickerAlerts = (allAlerts || []).filter((a: SentimentAlert) => a.ticker === ticker);

  if (!ticker) {
    return (
      <div className="h-full flex items-center justify-center border border-neutral-800 rounded bg-[#0a0a0a]">
        <div className="text-xs text-neutral-500">Select a ticker to view details</div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center border border-neutral-800 rounded bg-[#0a0a0a]">
        <div className="text-xs text-neutral-500">Loading details...</div>
      </div>
    );
  }

  if (!sentiment) {
    return (
      <div className="h-full flex items-center justify-center border border-neutral-800 rounded bg-[#0a0a0a]">
        <div className="text-xs text-neutral-500">No sentiment data available</div>
      </div>
    );
  }

  // Get current scores by window
  const scores24h = sentiment.scores.find(s => s.window === '24h');
  const scores7d = sentiment.scores.find(s => s.window === '7d');
  const scores30d = sentiment.scores.find(s => s.window === '30d');

  return (
    <div className="h-full flex flex-col border border-neutral-800 rounded bg-[#0a0a0a]">
      {/* Header */}
      <div className="p-3 border-b border-neutral-800">
        <h2 className="text-sm font-semibold text-neutral-100">{ticker}</h2>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-4">
        {/* Current Scores */}
        <div className="space-y-3">
          <div className="text-xs font-semibold text-neutral-400 uppercase">Sentiment Scores</div>

          {scores24h && (
            <div>
              <div className="text-[10px] text-neutral-500 mb-1">24h</div>
              <SentimentScore score={scores24h.score} showLabel={true} size="sm" />
              <div className="text-[10px] text-neutral-500 mt-1">
                {scores24h.article_count} articles • Velocity: {scores24h.velocity.toFixed(3)}
              </div>
            </div>
          )}

          {scores7d && (
            <div>
              <div className="text-[10px] text-neutral-500 mb-1">7d</div>
              <SentimentScore score={scores7d.score} showLabel={true} size="sm" />
              <div className="text-[10px] text-neutral-500 mt-1">
                {scores7d.article_count} articles • Velocity: {scores7d.velocity.toFixed(3)}
              </div>
            </div>
          )}

          {scores30d && (
            <div>
              <div className="text-[10px] text-neutral-500 mb-1">30d</div>
              <SentimentScore score={scores30d.score} showLabel={true} size="sm" />
              <div className="text-[10px] text-neutral-500 mt-1">
                {scores30d.article_count} articles • Velocity: {scores30d.velocity.toFixed(3)}
              </div>
            </div>
          )}
        </div>

        {/* Active Alerts */}
        {tickerAlerts.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-semibold text-neutral-400 uppercase">Active Alerts</div>
            <div className="flex flex-col gap-2">
              {tickerAlerts.map(alert => (
                <div key={alert.id} className="space-y-1">
                  <SentimentAlertBadge alert={alert} />
                  <div className="text-[10px] text-neutral-500">
                    <div>Divergence: {(alert.divergence_magnitude * 100).toFixed(1)}%</div>
                    <div>Price Return: {(alert.price_return * 100).toFixed(2)}%</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Chart */}
        <div className="space-y-2">
          <div className="text-xs font-semibold text-neutral-400 uppercase">Sentiment Trend</div>
          <SentimentChart data={history || []} isLoading={historyLoading} />
        </div>

        {/* News Feed */}
        <div className="space-y-2">
          <div className="text-xs font-semibold text-neutral-400 uppercase">Recent News</div>
          <NewsFeed articles={news || []} isLoading={newsLoading} />
        </div>
      </div>
    </div>
  );
}
