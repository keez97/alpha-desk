import { useState } from 'react';
import { BenchmarkSelector } from '../components/rrg/BenchmarkSelector';
import { RRGChart } from '../components/rrg/RRGChart';
import { useRRG } from '../hooks/useRRG';
import { LoadingState } from '../components/shared/LoadingState';
import { ErrorState } from '../components/shared/ErrorState';

export function RRG() {
  const [benchmark, setBenchmark] = useState('SPY');
  const [weeks, setWeeks] = useState(52);
  const { data, isLoading, error, refetch } = useRRG(benchmark, weeks);

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Relative Rotation Graph</h1>
        <p className="text-gray-400">Sector rotation analysis vs benchmark</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        <div className="lg:col-span-1 space-y-4">
          <div className="rounded-lg border border-gray-700 bg-gray-800/30 p-6">
            <BenchmarkSelector value={benchmark} onChange={setBenchmark} />

            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-300 mb-3">Time Period</label>
              <div className="space-y-2">
                {[
                  { label: '3 Months', value: 13 },
                  { label: '6 Months', value: 26 },
                  { label: '1 Year', value: 52 },
                  { label: '2 Years', value: 104 },
                ].map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setWeeks(option.value)}
                    className={`w-full rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      weeks === option.value
                        ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                        : 'bg-gray-700/30 text-gray-400 hover:bg-gray-700/50 border border-gray-700'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-3">
          {isLoading ? (
            <LoadingState message="Loading RRG data..." />
          ) : error ? (
            <ErrorState error={error} onRetry={() => refetch()} />
          ) : data ? (
            <div className="space-y-6">
              <RRGChart data={data} />

              <div className="rounded-lg border border-gray-700 bg-gray-800/30 p-6">
                <h3 className="mb-4 font-semibold text-white">Quadrant Legend</h3>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="flex space-x-3">
                    <div className="h-3 w-3 rounded-full bg-green-500 flex-shrink-0 mt-1"></div>
                    <div>
                      <p className="font-semibold text-white">Leading</p>
                      <p className="text-xs text-gray-400">Strong momentum and strength</p>
                    </div>
                  </div>
                  <div className="flex space-x-3">
                    <div className="h-3 w-3 rounded-full bg-yellow-500 flex-shrink-0 mt-1"></div>
                    <div>
                      <p className="font-semibold text-white">Weakening</p>
                      <p className="text-xs text-gray-400">Strong but losing momentum</p>
                    </div>
                  </div>
                  <div className="flex space-x-3">
                    <div className="h-3 w-3 rounded-full bg-red-500 flex-shrink-0 mt-1"></div>
                    <div>
                      <p className="font-semibold text-white">Lagging</p>
                      <p className="text-xs text-gray-400">Weak and losing momentum</p>
                    </div>
                  </div>
                  <div className="flex space-x-3">
                    <div className="h-3 w-3 rounded-full bg-blue-500 flex-shrink-0 mt-1"></div>
                    <div>
                      <p className="font-semibold text-white">Improving</p>
                      <p className="text-xs text-gray-400">Weak but gaining momentum</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
