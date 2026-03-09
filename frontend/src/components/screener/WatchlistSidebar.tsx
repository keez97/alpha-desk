import { DeltaBadge } from '../shared/DeltaBadge';
import { GradeBadge } from '../shared/GradeBadge';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { useWatchlistQuery, useRemoveFromWatchlist } from '../../hooks/useWatchlist';
import { formatCurrency } from '../../lib/utils';

interface WatchlistSidebarProps {
  selectedTicker?: string;
  onSelect: (ticker: string) => void;
}

export function WatchlistSidebar({ selectedTicker, onSelect }: WatchlistSidebarProps) {
  const { data, isLoading, error, refetch } = useWatchlistQuery();
  const { mutate: remove } = useRemoveFromWatchlist();

  if (isLoading) return <LoadingState message="Loading..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  return (
    <div className="h-full flex flex-col border border-neutral-800 rounded">
      <div className="border-b border-neutral-800 px-3 py-2 flex items-center justify-between">
        <span className="text-xs font-medium text-neutral-300">Watchlist</span>
        <span className="text-[10px] text-neutral-600">{data.length}</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {data.length === 0 ? (
          <div className="flex items-center justify-center h-24 text-neutral-600">
            <p className="text-xs">Empty</p>
          </div>
        ) : (
          <div className="divide-y divide-neutral-900">
            {data.map((item: any) => (
              <button
                key={item.id}
                onClick={() => onSelect(item.ticker)}
                className={`w-full px-3 py-2 text-left hover:bg-neutral-900/50 transition-colors border-l-2 ${
                  selectedTicker === item.ticker
                    ? 'border-neutral-400 bg-neutral-900/30'
                    : 'border-transparent'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-mono text-xs font-medium text-neutral-200">{item.ticker}</p>
                    <p className="text-[10px] text-neutral-500 mt-0.5">{formatCurrency(item.price)}</p>
                  </div>
                  <div className="flex flex-col items-end gap-0.5">
                    <DeltaBadge value={item.changePercent} format="pct" />
                    {(item as any).grade && <GradeBadge grade={(item as any).grade} size="sm" />}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {selectedTicker && (
        <div className="border-t border-neutral-800 px-3 py-2">
          <button
            onClick={() => {
              const item = data.find((i) => i.ticker === selectedTicker);
              if (item) remove(item.id);
            }}
            className="w-full rounded px-2 py-1 text-[10px] font-medium text-red-400/70 hover:text-red-400 transition-colors"
          >
            Remove
          </button>
        </div>
      )}
    </div>
  );
}
