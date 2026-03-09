import { Timestamp } from '../shared/Timestamp';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { useDrivers, useRefreshDrivers } from '../../hooks/useDrivers';

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
        {data.drivers.map((driver: any, idx: number) => {
          const headline = driver.headline || 'Untitled';
          const sources: string[] = driver.sources || [];
          const sentiment = driver.sentiment;

          return (
            <div key={idx} className="border border-neutral-800 rounded p-3">
              <div className="flex items-start justify-between mb-1.5">
                <span className="text-xs font-medium text-neutral-200">{headline}</span>
                {sentiment && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ml-2 flex-shrink-0 ${
                    sentiment === 'bullish' ? 'text-emerald-400' :
                    sentiment === 'bearish' ? 'text-red-400' :
                    'text-neutral-500'
                  }`}>
                    {sentiment}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-neutral-500 mb-2 leading-relaxed">{driver.explanation}</p>
              <div className="flex items-center justify-between">
                {sources.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {sources.map((source: string, i: number) => (
                      <a key={i} href={source} target="_blank" rel="noopener noreferrer"
                        className="text-[10px] text-neutral-500 hover:text-neutral-300 underline">
                        {driver.sourceName || `Source ${i + 1}`}
                      </a>
                    ))}
                  </div>
                )}
                {driver.impactScore && (
                  <span className="text-[10px] text-neutral-600">Impact: {driver.impactScore}/10</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
