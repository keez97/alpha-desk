import { useOvernightReturns } from '../../hooks/useOvernightReturns';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { DeltaBadge } from '../shared/DeltaBadge';

export function OvernightPanel() {
  const { data, isLoading, error, refetch } = useOvernightReturns();

  if (isLoading) {
    return <LoadingState message="Loading overnight gaps..." />;
  }

  if (error) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  if (!data) {
    return <div className="text-xs text-neutral-500 p-4">No data available</div>;
  }

  const { indices, summary } = data;

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-neutral-200">Overnight Gaps</h3>
          <span className="text-xs text-neutral-500">({summary.total_tracked} tracked)</span>
        </div>
        <div className={`text-xs font-mono px-2 py-1 rounded ${
          summary.net_direction === 'up' ? 'bg-emerald-900/30 text-emerald-400' :
          summary.net_direction === 'down' ? 'bg-red-900/30 text-red-400' :
          'bg-neutral-800 text-neutral-400'
        }`}>
          {summary.gaps_up} up / {summary.gaps_down} down
        </div>
      </div>

      {/* Major Indices (4 items) */}
      <div className="space-y-2 border-b border-neutral-800 pb-3">
        <div className="text-xs text-neutral-500 font-semibold">Major Indices</div>
        {indices.slice(0, 4).map((item) => (
          <div key={item.ticker} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 flex-1">
              <span className="font-mono font-semibold w-12">{item.ticker}</span>
              <span className="text-neutral-500 flex-1 truncate">{item.name}</span>
              {item.is_outlier && (
                <span className="text-amber-400 text-xs" title={`Z-score: ${item.z_score}`}>⚠</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <DeltaBadge value={item.overnight_return_pct} />
              <span className={item.direction === 'up' ? 'text-emerald-400' : 'text-red-400'}>
                {item.direction === 'up' ? '▲' : '▼'}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Sector ETFs (remaining items) */}
      {indices.length > 4 && (
        <div className="space-y-2">
          <div className="text-xs text-neutral-500 font-semibold">Sectors</div>
          <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">
            {indices.slice(4).map((item) => (
              <div key={item.ticker} className="flex items-center justify-between text-xs bg-neutral-800/30 rounded p-2">
                <div className="flex items-center gap-1 flex-1 min-w-0">
                  <span className="font-mono font-semibold w-10">{item.ticker}</span>
                  {item.is_outlier && (
                    <span className="text-amber-400 text-xs flex-shrink-0">⚠</span>
                  )}
                </div>
                <DeltaBadge value={item.overnight_return_pct} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Notable Gaps (outliers) */}
      {summary.notable_gaps.length > 0 && (
        <div className="border-t border-neutral-800 pt-3 space-y-2">
          <div className="text-xs text-amber-400 font-semibold flex items-center gap-1">
            <span>⚠</span>
            Notable Outliers
          </div>
          <div className="space-y-1">
            {summary.notable_gaps.slice(0, 3).map((gap) => (
              <div key={gap.ticker} className="flex items-center justify-between text-xs bg-amber-900/20 rounded px-2 py-1">
                <span className="font-mono font-semibold">{gap.ticker}</span>
                <div className="flex items-center gap-2">
                  <DeltaBadge value={gap.overnight_return_pct} />
                  <span className="text-amber-400 text-[10px]">Z: {gap.z_score}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
