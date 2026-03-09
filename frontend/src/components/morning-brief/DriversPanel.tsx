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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Market Drivers</h2>
        <button
          onClick={() => refresh()}
          disabled={isPending}
          className="px-3 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {isPending ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
      <Timestamp date={data.timestamp} label="Generated" />
      <div className="grid gap-4">
        {data.drivers.map((driver: any, idx: number) => {
          const headline = driver.headline || 'Untitled';
          const sources: string[] = driver.sources || [];
          const sentiment = driver.sentiment;

          return (
            <div key={idx} className="rounded-lg border border-gray-700 bg-gray-800/30 p-4">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-white">{headline}</h3>
                {sentiment && (
                  <span className={`text-xs px-2 py-1 rounded font-medium ml-2 flex-shrink-0 ${
                    sentiment === 'bullish' ? 'bg-green-500/20 text-green-400' :
                    sentiment === 'bearish' ? 'bg-red-500/20 text-red-400' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {sentiment}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-400 mb-3">{driver.explanation}</p>
              <div className="flex items-center justify-between">
                {sources.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {sources.map((source: string, i: number) => (
                      <a key={i} href={source} target="_blank" rel="noopener noreferrer"
                        className="text-xs text-blue-400 hover:text-blue-300 underline">
                        {driver.sourceName || `Source ${i + 1}`}
                      </a>
                    ))}
                  </div>
                )}
                {driver.impactScore && (
                  <span className="text-xs text-gray-500">Impact: {driver.impactScore}/10</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
