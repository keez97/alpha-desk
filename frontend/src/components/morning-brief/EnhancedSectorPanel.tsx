import { useState, useEffect } from 'react';
import type { EnhancedSectorData } from '../../lib/api';
import { useEnhancedSectors } from '../../hooks/useEnhancedSectors';
import { DeltaBadge } from '../shared/DeltaBadge';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { formatCurrency, classNames } from '../../lib/utils';

const QUADRANT_COLORS = {
  Strengthening: 'bg-green-900/50 text-green-400',
  Weakening: 'bg-amber-900/50 text-amber-400',
  Recovering: 'bg-blue-900/50 text-blue-400',
  Deteriorating: 'bg-red-900/50 text-red-400',
  Unknown: 'bg-neutral-800 text-neutral-400',
};

function QuadrantBadge({ quadrant }: { quadrant: string }) {
  const colors = QUADRANT_COLORS[quadrant as keyof typeof QUADRANT_COLORS] || QUADRANT_COLORS.Unknown;

  return (
    <span
      className={classNames(
        'inline-block px-2 py-0.5 rounded-full text-[10px] font-medium whitespace-nowrap',
        colors
      )}
    >
      {quadrant}
    </span>
  );
}

function getMomentumColor(value: number): string {
  if (value > 0) return 'text-green-400';
  if (value < 0) return 'text-red-400';
  return 'text-neutral-400';
}

export function EnhancedSectorPanel() {
  const [period, setPeriod] = useState<'1D' | '5D' | '1M' | '3M'>('1D');
  const [timedOut, setTimedOut] = useState(false);
  const { data, isLoading, error, refetch } = useEnhancedSectors(period);

  // Timeout after 8 seconds
  useEffect(() => {
    if (!isLoading) {
      setTimedOut(false);
      return;
    }

    const timer = setTimeout(() => {
      setTimedOut(true);
    }, 8000);

    return () => clearTimeout(timer);
  }, [isLoading]);

  if (timedOut) {
    return (
      <div className="flex items-center gap-3 py-4 px-4 bg-amber-950/30 rounded border border-amber-900/50">
        <span className="text-xs text-amber-400">⏱️ Request timed out</span>
        <button
          onClick={() => {
            setTimedOut(false);
            refetch();
          }}
          className="ml-auto rounded px-3 py-1 text-xs font-medium text-neutral-400 border border-neutral-800 hover:text-neutral-200 hover:border-neutral-700 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (isLoading) return <LoadingState message="Loading sectors..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data || data.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-neutral-300">Sector Performance with RRG</span>
        <div className="flex gap-0.5">
          {(['1D', '5D', '1M', '3M'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
                period === p
                  ? 'bg-neutral-800 text-neutral-200'
                  : 'text-neutral-500 hover:text-neutral-300'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="border border-neutral-800 rounded overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-neutral-800">
              <th className="px-3 py-2 text-left text-[10px] text-neutral-500 font-medium uppercase tracking-wider">
                Ticker
              </th>
              <th className="px-3 py-2 text-left text-[10px] text-neutral-500 font-medium uppercase tracking-wider">
                Name
              </th>
              <th className="px-3 py-2 text-right text-[10px] text-neutral-500 font-medium uppercase tracking-wider">
                Price
              </th>
              <th className="px-3 py-2 text-right text-[10px] text-neutral-500 font-medium uppercase tracking-wider">
                Change
              </th>
              <th className="px-3 py-2 text-center text-[10px] text-neutral-500 font-medium uppercase tracking-wider">
                Quadrant
              </th>
              <th className="px-3 py-2 text-right text-[10px] text-neutral-500 font-medium uppercase tracking-wider">
                RS-Mom
              </th>
            </tr>
          </thead>
          <tbody>
            {data.map((sector: EnhancedSectorData) => (
              <tr key={sector.ticker} className="border-b border-neutral-900 hover:bg-neutral-900/50">
                <td className="px-3 py-2 font-mono text-neutral-200">{sector.ticker}</td>
                <td className="px-3 py-2 text-neutral-400">{sector.name}</td>
                <td className="px-3 py-2 text-right font-mono text-neutral-200">
                  {formatCurrency(sector.price)}
                </td>
                <td className="px-3 py-2 text-right">
                  <DeltaBadge value={sector.changePercent} format="pct" />
                </td>
                <td className="px-3 py-2 text-center">
                  <QuadrantBadge quadrant={sector.quadrant} />
                </td>
                <td className={classNames('px-3 py-2 text-right font-mono text-[10px]', getMomentumColor(sector.rsMomentum))}>
                  {sector.rsMomentum.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
