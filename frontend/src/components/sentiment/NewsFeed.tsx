import type { NewsArticle } from '../../lib/api';
import { SentimentScore } from './SentimentScore';
import { classNames } from '../../lib/utils';

interface NewsFeedProps {
  articles: NewsArticle[];
  isLoading?: boolean;
  error?: Error | null;
}

function timeAgo(date: string): string {
  const now = new Date();
  const published = new Date(date);
  const seconds = Math.floor((now.getTime() - published.getTime()) / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function NewsFeed({ articles, isLoading, error }: NewsFeedProps) {
  if (error) {
    return (
      <div className="p-3 rounded border border-red-900 bg-red-950 text-red-400 text-xs">
        Error loading news: {error.message}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-4 text-neutral-500 text-xs">
        Loading articles...
      </div>
    );
  }

  if (!articles || articles.length === 0) {
    return (
      <div className="flex items-center justify-center p-4 text-neutral-500 text-xs">
        No articles found
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {articles.map((article) => (
        <div
          key={article.id}
          className="p-2 rounded border border-neutral-800 bg-[#0a0a0a] hover:border-neutral-700 transition-colors"
        >
          {/* Headline */}
          <a
            href={article.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-semibold text-neutral-100 hover:text-emerald-400 transition-colors block mb-1 line-clamp-2"
          >
            {article.headline}
          </a>

          {/* Meta */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-[10px] text-neutral-500">
              <span>{article.source}</span>
              <span>•</span>
              <span>{timeAgo(article.published_at)}</span>
            </div>
            <div className="flex-shrink-0">
              <SentimentScore score={article.sentiment_score} showLabel={false} size="sm" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
