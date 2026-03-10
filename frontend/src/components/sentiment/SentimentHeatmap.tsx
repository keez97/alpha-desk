import type { SentimentHeatmapSector } from '../../lib/api';
import { SentimentScore } from './SentimentScore';
import { classNames } from '../../lib/utils';

interface SentimentHeatmapProps {
  data: SentimentHeatmapSector[];
  isLoading?: boolean;
  error?: Error | null;
  onSectorClick?: (sector: string) => void;
}

export function SentimentHeatmap({
  data,
  isLoading,
  error,
  onSectorClick,
}: SentimentHeatmapProps) {
  if (error) {
    return (
      <div className="p-4 rounded border border-red-900 bg-red-950 text-red-400 text-xs">
        Error loading heatmap: {error.message}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8 text-neutral-500 text-xs">
        Loading sector data...
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center p-8 text-neutral-500 text-xs">
        No sector data available
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {data.map((sector) => (
        <div
          key={sector.sector}
          onClick={() => onSectorClick?.(sector.sector)}
          className={classNames(
            'p-3 rounded border transition-all cursor-pointer hover:border-neutral-600',
            'border-neutral-800 bg-[#0a0a0a] hover:bg-neutral-900'
          )}
        >
          <div className="space-y-2">
            {/* Sector Name */}
            <div className="text-sm font-semibold text-neutral-100">
              {sector.sector}
            </div>

            {/* Score Bar */}
            <SentimentScore score={sector.avg_sentiment} showLabel={true} size="sm" />

            {/* Meta */}
            <div className="text-[10px] text-neutral-500">
              {sector.article_count} articles
            </div>

            {/* Top Movers */}
            {sector.top_movers.length > 0 && (
              <div className="text-[10px] space-y-1 pt-2 border-t border-neutral-800">
                <div className="text-neutral-500 font-semibold">Top Movers:</div>
                {sector.top_movers.slice(0, 3).map((mover) => (
                  <div key={mover.ticker} className="flex items-center justify-between">
                    <span className="text-neutral-400">{mover.ticker}</span>
                    <span
                      className={
                        mover.score > 0
                          ? 'text-emerald-400'
                          : mover.score < 0
                          ? 'text-red-400'
                          : 'text-neutral-400'
                      }
                    >
                      {mover.score > 0 ? '+' : ''}{mover.score.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
