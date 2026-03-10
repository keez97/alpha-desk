import { useState } from 'react';
import { BenchmarkSelector } from '../components/rrg/BenchmarkSelector';
import { RRGChart } from '../components/rrg/RRGChart';
import { TradeIdeaPanel } from '../components/rrg/TradeIdeaPanel';
import { RotationAlerts } from '../components/rrg/RotationAlerts';
import { AlertBadge } from '../components/rrg/AlertBadge';
import { IntradayMomentum } from '../components/rrg/IntradayMomentum';
import { useRRG } from '../hooks/useRRG';
import { LoadingState } from '../components/shared/LoadingState';
import { ErrorState } from '../components/shared/ErrorState';

export function RRG() {
  const [benchmark, setBenchmark] = useState('SPY');
  const [weeks, setWeeks] = useState(52);
  const { data, isLoading, error, refetch } = useRRG(benchmark, weeks);

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium text-neutral-300">Relative Rotation Graph</span>
        <AlertBadge />
      </div>
      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-1 space-y-3">
          <div className="border border-neutral-800 rounded p-3">
            <BenchmarkSelector value={benchmark} onChange={setBenchmark} />

            <div className="mt-4">
              <span className="block text-[10px] text-neutral-500 uppercase tracking-wider mb-2">Period</span>
              <div className="space-y-1">
                {[
                  { label: '3M', value: 13 },
                  { label: '6M', value: 26 },
                  { label: '1Y', value: 52 },
                  { label: '2Y', value: 104 },
                ].map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setWeeks(option.value)}
                    className={`w-full rounded px-2 py-1 text-xs font-medium transition-colors ${
                      weeks === option.value
                        ? 'bg-neutral-800 text-neutral-200'
                        : 'text-neutral-500 hover:text-neutral-300'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <TradeIdeaPanel benchmark={benchmark} weeks={weeks} />
        </div>

        <div className="lg:col-span-4">
          {isLoading ? (
            <LoadingState message="Loading RRG data..." />
          ) : error ? (
            <ErrorState error={error} onRetry={() => refetch()} />
          ) : data ? (
            <RRGChart data={data} />
          ) : null}
        </div>
      </div>

      <RotationAlerts />
      <IntradayMomentum />
    </div>
  );
}
