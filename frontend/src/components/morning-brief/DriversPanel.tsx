import { Timestamp } from '../shared/Timestamp';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { useDrivers, useRefreshDrivers } from '../../hooks/useDrivers';

export function DriversPanel() {
  const { data, isLoading, error, refetch } = useDrivers();
  const { mutate: refresh, isPending } = useRefreshDrivers();

  if (isLoading) return <LoadingState message="Loading market drivers..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

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
        {data.drivers.map((driver: any, idx: number) => (
          <div key={idx} className="rounded-lg border border-gray-700 bg-gray-800/30 p-4">
            <h3 className="font-semibold text-white mb-2">{driver.headline}</h3>
            <p className="text-sm text-gray-400 mb-3">{driver.explanation}</p>
            {driver.sources.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {driver.sources.map((source: string, i: number) => (
                  <a
                    key={i}
                    href={source}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-400 hover:text-blue-300 underline"
                  >
                    Source {i + 1}
                  </a>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
