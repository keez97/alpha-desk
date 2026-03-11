import { useSentimentVelocity } from '../../hooks/useSentimentVelocity';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';

function SentimentGauge({ score }: { score: number }) {
  // Map sentiment score (-1 to +1) to arc color
  const angle = ((score + 1) / 2) * 180; // 0° = bearish, 180° = bullish
  const color =
    score > 0.3
      ? 'from-green-500 to-green-400'
      : score < -0.3
        ? 'from-red-500 to-red-400'
        : 'from-amber-500 to-amber-400';

  const label =
    score > 0.5
      ? 'Bullish'
      : score > 0.2
        ? 'Mildly Bullish'
        : score < -0.5
          ? 'Bearish'
          : score < -0.2
            ? 'Mildly Bearish'
            : 'Neutral';

  return (
    <div className="flex flex-col items-center space-y-2">
      <div className="relative h-20 w-40">
        {/* Gauge background arc */}
        <svg className="absolute inset-0" viewBox="0 0 200 120">
          {/* Bearish side (red) */}
          <path
            d="M 30 110 A 80 80 0 0 1 70 20"
            stroke="rgb(71 85 105 / 0.3)"
            strokeWidth="12"
            fill="none"
            strokeLinecap="round"
          />
          {/* Neutral zone (amber) */}
          <path
            d="M 70 20 A 80 80 0 0 1 130 20"
            stroke="rgb(120 113 108 / 0.3)"
            strokeWidth="12"
            fill="none"
            strokeLinecap="round"
          />
          {/* Bullish side (green) */}
          <path
            d="M 130 20 A 80 80 0 0 1 170 110"
            stroke="rgb(34 197 94 / 0.3)"
            strokeWidth="12"
            fill="none"
            strokeLinecap="round"
          />

          {/* Needle indicator */}
          <g transform={`translate(100, 110) rotate(${angle - 90})`}>
            <circle cx="0" cy="0" r="4" fill="rgb(229 231 235)" />
            <line x1="0" y1="0" x2="0" y2="-70" stroke="rgb(229 231 235)" strokeWidth="2" strokeLinecap="round" />
          </g>
        </svg>
      </div>

      <div className="text-center">
        <span className="text-xs font-medium text-neutral-500">Market Sentiment</span>
        <div className="text-sm font-bold text-neutral-200">{label}</div>
        <div className="text-xs text-neutral-400">{score.toFixed(2)}</div>
      </div>
    </div>
  );
}

function VelocityIndicator({ velocity, signal }: { velocity: number; signal: string }) {
  const isAccelerating = signal === 'accelerating';
  const isDecelerating = signal === 'decelerating';

  return (
    <div className="space-y-2">
      <span className="text-xs font-medium text-neutral-500">Velocity</span>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {isAccelerating ? (
            <div className="text-lg">📈</div>
          ) : isDecelerating ? (
            <div className="text-lg">📉</div>
          ) : (
            <div className="text-lg">➡️</div>
          )}
          <div>
            <div
              className={`text-sm font-mono font-bold ${
                isAccelerating ? 'text-green-400' : isDecelerating ? 'text-red-400' : 'text-amber-400'
              }`}
            >
              {velocity > 0 ? '+' : ''}{velocity.toFixed(2)}
            </div>
            <div className="text-xs capitalize text-neutral-500">{signal}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ContrarianAlert({ flag }: { flag: string | null }) {
  if (!flag) return null;

  const isBull = flag === 'oversold';
  const message = isBull
    ? 'Extreme bearish sentiment with positive price action'
    : 'Extreme bullish sentiment with negative price action';

  return (
    <div
      className={`rounded border p-2 text-xs ${
        isBull
          ? 'border-green-600/50 bg-green-900/20 text-green-400'
          : 'border-red-600/50 bg-red-900/20 text-red-400'
      }`}
    >
      <span className="font-bold">⚠️ Contrarian Signal:</span> {message}
    </div>
  );
}

function AttentionBadge({ level, density }: { level: string; density: number }) {
  const colors =
    level === 'extreme'
      ? 'bg-red-900/40 text-red-400'
      : level === 'elevated'
        ? 'bg-amber-900/40 text-amber-400'
        : 'bg-neutral-800/40 text-neutral-400';

  const label = level === 'extreme' ? 'Extreme Activity' : level === 'elevated' ? 'Elevated Activity' : 'Normal';

  return (
    <div className={`rounded px-2 py-1 text-xs font-medium ${colors}`}>
      {label} ({density} articles)
    </div>
  );
}

function HeadlinesList({ headlines }: { headlines: any[] }) {
  if (headlines.length === 0) {
    return <div className="text-xs text-neutral-500 italic">No recent headlines</div>;
  }

  return (
    <div className="max-h-64 space-y-2 overflow-y-auto">
      {headlines.map((h, i) => {
        const isBullish = h.sentiment > 0.3;
        const isBearish = h.sentiment < -0.3;

        return (
          <div key={i} className="space-y-0.5 border-l border-neutral-700 pl-2">
            <div className="flex items-start justify-between gap-2">
              <p className="flex-1 text-xs leading-snug text-neutral-300">{h.headline}</p>
              <span
                className={`whitespace-nowrap text-xs font-mono font-bold ${
                  isBullish ? 'text-green-400' : isBearish ? 'text-red-400' : 'text-neutral-400'
                }`}
              >
                {h.sentiment > 0 ? '+' : ''}{h.sentiment.toFixed(2)}
              </span>
            </div>
            <div className="text-[10px] text-neutral-600">
              {h.source || h.ticker} • {new Date(h.published_at).toLocaleTimeString()}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SentimentChart({ history }: { history: any[] }) {
  if (history.length === 0) return null;

  const min = Math.min(...history.map((h) => h.sentiment)) - 0.1;
  const max = Math.max(...history.map((h) => h.sentiment)) + 0.1;
  const range = max - min;

  return (
    <div className="space-y-1">
      <span className="text-xs font-medium text-neutral-500">5-Day Trend</span>
      <svg className="h-12 w-full" viewBox="0 0 200 40">
        {/* Y-axis reference lines */}
        <line x1="0" y1="20" x2="200" y2="20" stroke="rgb(82 82 91 / 0.3)" strokeWidth="0.5" />

        {/* Sentiment line chart */}
        {history.length > 1 && (
          <polyline
            points={history
              .map((h, i) => {
                const x = (i / (history.length - 1)) * 200;
                const y = 40 - ((h.sentiment - min) / range) * 40;
                return `${x},${y}`;
              })
              .join(' ')}
            fill="none"
            stroke="rgb(34 197 94)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}

        {/* Data points */}
        {history.map((h, i) => {
          const x = (i / (history.length - 1)) * 200;
          const y = 40 - ((h.sentiment - min) / range) * 40;
          return <circle key={i} cx={x} cy={y} r="1.5" fill="rgb(34 197 94)" />;
        })}
      </svg>
    </div>
  );
}

export function SentimentVelocityPanel() {
  const { data, isLoading, error, refetch } = useSentimentVelocity('SPY,QQQ');

  if (isLoading) return <LoadingState message="Loading sentiment velocity..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  // Empty state: no articles available
  if (data.news_density === 0 && data.aggregate_score === 0 && data.top_headlines.length === 0) {
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-3">
        <div className="text-xs font-bold text-neutral-400 mb-2">NEWS SENTIMENT</div>
        <div className="flex flex-col items-center justify-center py-6">
          <div className="text-2xl mb-2 opacity-50">📡</div>
          <div className="text-xs text-neutral-500 text-center">No news articles available</div>
          <div className="text-[10px] text-neutral-600 mt-1">RSS feeds not returning data</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded border border-neutral-800 bg-neutral-900/50 p-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium uppercase text-neutral-400">News Sentiment Velocity</span>
          {data.scoring_model && data.scoring_model.includes('finbert') && (
            <span className="rounded bg-indigo-900/40 px-1.5 py-0.5 text-[10px] font-medium text-indigo-400">FinBERT</span>
          )}
        </div>
        <span className="text-[10px] text-neutral-600">
          {new Date(data.timestamp).toLocaleTimeString()}
        </span>
      </div>

      {/* Sentiment distribution bar */}
      {data.sentiment_distribution && (
        <div className="space-y-1">
          <div className="flex h-2 w-full overflow-hidden rounded-full">
            {(() => {
              const d = data.sentiment_distribution;
              const total = (d.positive || 0) + (d.negative || 0) + (d.neutral || 0);
              if (total === 0) return null;
              return (
                <>
                  <div className="bg-green-500" style={{ width: `${(d.positive / total) * 100}%` }} />
                  <div className="bg-neutral-500" style={{ width: `${(d.neutral / total) * 100}%` }} />
                  <div className="bg-red-500" style={{ width: `${(d.negative / total) * 100}%` }} />
                </>
              );
            })()}
          </div>
          <div className="flex justify-between text-[10px] text-neutral-500">
            <span className="text-green-400">{data.sentiment_distribution.positive} positive</span>
            <span>{data.sentiment_distribution.neutral} neutral</span>
            <span className="text-red-400">{data.sentiment_distribution.negative} negative</span>
          </div>
        </div>
      )}

      {/* Main metrics grid */}
      <div className="grid grid-cols-2 gap-3">
        {/* Sentiment gauge */}
        <div>
          <SentimentGauge score={data.aggregate_score} />
        </div>

        {/* Velocity and attention */}
        <div className="space-y-3">
          <VelocityIndicator velocity={data.velocity} signal={data.velocity_signal} />
          <AttentionBadge level={data.attention_level} density={data.news_density} />
        </div>
      </div>

      {/* Contrarian alert if present */}
      {data.contrarian_flag && <ContrarianAlert flag={data.contrarian_flag} />}

      {/* Sentiment trend chart */}
      <SentimentChart history={data.history_5d} />

      {/* Top headlines */}
      <div className="space-y-2">
        <span className="text-xs font-medium text-neutral-500">Top Headlines</span>
        <HeadlinesList headlines={data.top_headlines} />
      </div>
    </div>
  );
}
