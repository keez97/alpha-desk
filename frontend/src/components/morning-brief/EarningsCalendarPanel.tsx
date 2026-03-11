import { useEarningsBrief } from '../../hooks/useEarningsBrief';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { DeltaBadge } from '../shared/DeltaBadge';

export function EarningsCalendarPanel() {
  const { data, isLoading, error, refetch } = useEarningsBrief();

  if (isLoading) {
    return <LoadingState message="Loading earnings calendar..." />;
  }

  if (error) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  if (!data || data.upcoming.length === 0) {
    return <div className="text-xs text-neutral-500 p-4">No earnings scheduled in next 2 weeks</div>;
  }

  const { upcoming, clusters, alerts } = data;

  // Group upcoming by date
  const grouped = upcoming.reduce((acc, item) => {
    const date = item.earnings_date;
    if (!acc[date]) acc[date] = [];
    acc[date].push(item);
    return acc;
  }, {} as Record<string, typeof upcoming>);

  const sortedDates = Object.keys(grouped).sort();

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-200">Upcoming Earnings</h3>
        {alerts.length > 0 && (
          <span className="text-xs bg-amber-900/30 text-amber-400 px-2 py-1 rounded">
            {alerts.length} drift signals
          </span>
        )}
      </div>

      {/* Timeline by Date */}
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {sortedDates.slice(0, 7).map((date) => {
          const items = grouped[date];
          const dateObj = new Date(date);
          const formattedDate = dateObj.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            weekday: 'short',
          });

          return (
            <div key={date} className="border-l-2 border-neutral-700 pl-3 space-y-2">
              <div className="text-xs font-semibold text-neutral-400">{formattedDate}</div>

              <div className="space-y-1">
                {items.map((item) => {
                  const hasDriftSignal = item.pre_drift_signal;
                  const isDriftUp = item.pre_drift_pct > 0;

                  return (
                    <div
                      key={item.ticker}
                      className={`flex items-center justify-between text-xs rounded px-2 py-1.5 ${
                        hasDriftSignal
                          ? isDriftUp
                            ? 'bg-emerald-900/20 border border-emerald-800/50'
                            : 'bg-red-900/20 border border-red-800/50'
                          : 'bg-neutral-800/30'
                      }`}
                    >
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <span className="font-mono font-semibold w-12">{item.ticker}</span>
                        <span className="text-neutral-500 text-[10px] truncate">{item.sector}</span>
                        {hasDriftSignal && (
                          <div className="flex items-center gap-1">
                            {isDriftUp ? (
                              <span className="text-emerald-400 text-xs font-bold">↗</span>
                            ) : (
                              <span className="text-red-400 text-xs font-bold">↘</span>
                            )}
                          </div>
                        )}
                      </div>
                      <DeltaBadge value={item.pre_drift_pct} />
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Clustering Badge */}
      {clusters.length > 0 && (
        <div className="border-t border-neutral-800 pt-3 space-y-2">
          <div className="text-xs text-neutral-500 font-semibold">Sector Clusters</div>
          <div className="flex flex-wrap gap-2">
            {clusters.map((cluster, idx) => (
              <div
                key={idx}
                className="flex items-center gap-1 text-xs bg-neutral-800/50 border border-neutral-700 rounded px-2 py-1"
              >
                <span>{cluster.sector}</span>
                <span className="text-neutral-400 font-mono">{cluster.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Drift Alerts */}
      {alerts.length > 0 && (
        <div className="border-t border-neutral-800 pt-3 space-y-2">
          <div className="text-xs text-amber-400 font-semibold flex items-center gap-1">
            <span>⚠</span>
            Drift Signals
          </div>
          <div className="space-y-1">
            {alerts.slice(0, 3).map((alert) => {
              const isSurge = alert.alert_type === 'pre_earnings_surge';
              return (
                <div
                  key={alert.ticker}
                  className={`flex items-center justify-between text-xs rounded px-2 py-1 ${
                    isSurge
                      ? 'bg-emerald-900/20 text-emerald-400'
                      : 'bg-red-900/20 text-red-400'
                  }`}
                >
                  <span className="font-mono font-semibold">{alert.ticker}</span>
                  <DeltaBadge value={alert.pre_drift_pct} />
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
