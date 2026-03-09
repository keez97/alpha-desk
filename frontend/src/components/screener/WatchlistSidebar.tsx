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
    <div className="h-full flex flex-col rounded-lg border border-gray-700 bg-gray-800/30">
      <div className="border-b border-gray-700 px-4 py-3">
        <h3 className="font-semibold text-white">Watchlist</h3>
        <p className="text-xs text-gray-500 mt-1">{data.length} items</p>
      </div>

      <div className="flex-1 overflow-y-auto">
        {data.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-gray-500">
            <p className="text-sm">No items in watchlist</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-700">
            {data.map((item: any) => (
              <button
                key={item.id}
                onClick={() => onSelect(item.ticker)}
                className={`w-full px-4 py-3 text-left hover:bg-gray-700/30 transition-colors border-l-2 ${
                  selectedTicker === item.ticker
                    ? 'border-blue-500 bg-gray-700/20'
                    : 'border-transparent'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-mono font-semibold text-white">{item.ticker}</p>
                    <p className="text-xs text-gray-400 mt-1">{formatCurrency(item.price)}</p>
                  </div>
                  <div className="flex flex-col items-end space-y-1">
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
        <div className="border-t border-gray-700 px-4 py-3">
          <button
            onClick={() => {
              const item = data.find((i) => i.ticker === selectedTicker);
              if (item) remove(item.id);
            }}
            className="w-full rounded-lg bg-red-500/20 px-3 py-2 text-xs font-medium text-red-400 hover:bg-red-500/30 transition-colors"
          >
            Remove from Watchlist
          </button>
        </div>
      )}
    </div>
  );
}
