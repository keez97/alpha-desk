import { useState } from 'react';
import { Timestamp } from '../shared/Timestamp';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { useDrivers, useRefreshDrivers } from '../../hooks/useDrivers';
import type { Driver, NewsArticleForDriver, DriverMetric } from '../../lib/api';

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function ImpactBadge({ score }: { score?: number }) {
  if (score === undefined || score === null) return null;
  const color = score >= 70 ? 'text-red-400 border-red-400/30 bg-red-400/10'
    : score >= 40 ? 'text-amber-400 border-amber-400/30 bg-amber-400/10'
    : 'text-emerald-400 border-emerald-400/30 bg-emerald-400/10';
  return (
    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full border ${color}`}>
      {score}
    </span>
  );
}

function SentimentBadge({ sentiment }: { sentiment?: string }) {
  if (!sentiment) return null;
  const colors: Record<string, string> = {
    bullish: 'text-emerald-400 bg-emerald-400/10',
    positive: 'text-emerald-400 bg-emerald-400/10',
    bearish: 'text-red-400 bg-red-400/10',
    negative: 'text-red-400 bg-red-400/10',
    neutral: 'text-neutral-400 bg-neutral-400/10',
  };
  const cls = colors[sentiment] || colors.neutral;
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${cls}`}>
      {sentiment}
    </span>
  );
}

function ContrarianBadge({ signal }: { signal?: string | null }) {
  if (!signal) return null;
  return (
    <div className="flex items-center gap-1 px-2 py-1 rounded bg-amber-400/10 border border-amber-400/20 mt-1.5">
      <span className="text-amber-400 text-[10px]">⚠</span>
      <span className="text-[10px] text-amber-300 font-medium">{signal}</span>
    </div>
  );
}

function MetricChip({ metric }: { metric: DriverMetric }) {
  const arrow = metric.direction === 'up' ? '\u2191' : metric.direction === 'down' ? '\u2193' : '\u2192';
  const color = metric.direction === 'up' ? 'text-emerald-400' : metric.direction === 'down' ? 'text-red-400' : 'text-neutral-400';
  return (
    <span className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-800/50 text-neutral-300 font-mono">
      {metric.label}: <span className="font-medium">{metric.value}</span>{' '}
      <span className={color}>{arrow}</span>
    </span>
  );
}

function NewsItem({ article }: { article: NewsArticleForDriver }) {
  return (
    <a
      href={article.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-2 py-1.5 px-2 rounded hover:bg-neutral-800/40 transition-colors group"
    >
      <span className="text-[10px] text-neutral-600 mt-0.5 flex-shrink-0 w-10 text-right">
        {timeAgo(article.publishedAt)}
      </span>
      <div className="min-w-0">
        <span className="text-[11px] text-neutral-300 group-hover:text-white transition-colors line-clamp-2 leading-snug">
          {article.title}
        </span>
        <span className="text-[9px] text-neutral-600 block mt-0.5">
          {article.publisher} {article.ticker && `\u00b7 ${article.ticker}`}
        </span>
      </div>
    </a>
  );
}

function DriverCard({ driver }: { driver: Driver }) {
  const [expanded, setExpanded] = useState(false);
  const [newsPage, setNewsPage] = useState(1);
  const articlesPerPage = 3;
  const visibleArticles = driver.newsArticles.slice(0, newsPage * articlesPerPage);
  const hasMore = driver.newsArticles.length > newsPage * articlesPerPage;
  const showLess = newsPage > 1;
  const hasDetails = driver.keyData || driver.newsArticles.length > 0 || driver.marketImplications;

  return (
    <div className="border border-neutral-800 rounded overflow-hidden">
      {/* Header */}
      <button
        onClick={() => hasDetails && setExpanded(!expanded)}
        className={`w-full text-left p-3 ${hasDetails ? 'cursor-pointer hover:bg-neutral-800/30' : 'cursor-default'} transition-colors`}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <ImpactBadge score={driver.impactScore} />
              <span className="text-xs font-medium text-neutral-200 leading-snug block">
                {driver.headline}
              </span>
            </div>
            {driver.metrics.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1.5">
                {driver.metrics.map((m, i) => (
                  <MetricChip key={i} metric={m} />
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <SentimentBadge sentiment={driver.sentiment} />
            {hasDetails && (
              <svg
                className={`w-3 h-3 text-neutral-600 transition-transform ${expanded ? 'rotate-180' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            )}
          </div>
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-neutral-800/50 px-3 pb-3 space-y-2.5">
          {driver.keyData && (
            <>
              <p className="text-[11px] text-neutral-400 leading-relaxed mt-2">
                {driver.keyData}
              </p>
              <ContrarianBadge signal={driver.contrarianSignal} />
            </>
          )}

          {driver.marketImplications && (
            <div className="bg-neutral-900/50 rounded p-2">
              <span className="text-[10px] text-neutral-500 font-medium block mb-1">Market Implications</span>
              <p className="text-[11px] text-neutral-300 leading-relaxed">
                {driver.marketImplications}
              </p>
            </div>
          )}

          {driver.affectedAssets.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {driver.affectedAssets.map((t, i) => (
                <span key={i} className="text-[9px] px-1 py-0.5 rounded bg-neutral-800 text-neutral-500 font-mono">
                  {t}
                </span>
              ))}
            </div>
          )}

          {driver.newsArticles.length > 0 && (
            <div>
              <span className="text-[10px] text-neutral-500 font-medium block mb-1">Related News</span>
              <div className="space-y-0.5">
                {visibleArticles.map((article, i) => (
                  <NewsItem key={i} article={article} />
                ))}
              </div>
              {(hasMore || showLess) && (
                <div className="flex gap-2 mt-1">
                  {hasMore && (
                    <button onClick={() => setNewsPage(p => p + 1)} className="text-[10px] text-blue-400 hover:text-blue-300">
                      Show more →
                    </button>
                  )}
                  {showLess && (
                    <button onClick={() => setNewsPage(1)} className="text-[10px] text-neutral-500 hover:text-neutral-300">
                      ← Show less
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function DriversPanel() {
  const { data, isLoading, error, refetch } = useDrivers();
  const { mutate: refresh, isPending } = useRefreshDrivers();

  if (isLoading) return <LoadingState message="Loading market drivers..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data || !data.drivers || data.drivers.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-neutral-300">Market Drivers</span>
        <button
          onClick={() => refresh()}
          disabled={isPending}
          className="px-2 py-1 rounded text-[11px] text-neutral-500 hover:text-neutral-300 border border-neutral-800 hover:border-neutral-700 disabled:opacity-50 transition-colors"
        >
          {isPending ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
      <Timestamp date={data.timestamp} label="Generated" />
      <div className="space-y-2">
        {data.drivers.map((driver: Driver, idx: number) => (
          <DriverCard key={idx} driver={driver} />
        ))}
      </div>
    </div>
  );
}
