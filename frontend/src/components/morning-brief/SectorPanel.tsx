import { useState } from 'react';
import { DeltaBadge } from '../shared/DeltaBadge';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { useSectors } from '../../hooks/useSectors';
import { formatCurrency } from '../../lib/utils';

export function SectorPanel() {
  const [period, setPeriod] = useState<'1D' | '5D' | '1M' | '3M'>('1D');
  const { data, isLoading, error, refetch } = useSectors(period);

  if (isLoading) return <LoadingState message="Loading sectors..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data || data.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-neutral-300">Sector Performance</span>
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
              <th className="px-3 py-2 text-left text-[10px] text-neutral-500 font-medium uppercase tracking-wider">Ticker</th>
              <th className="px-3 py-2 text-left text-[10px] text-neutral-500 font-medium uppercase tracking-wider">Name</th>
              <th className="px-3 py-2 text-right text-[10px] text-neutral-500 font-medium uppercase tracking-wider">Price</th>
              <th className="px-3 py-2 text-right text-[10px] text-neutral-500 font-medium uppercase tracking-wider">Change</th>
            </tr>
          </thead>
          <tbody>
            {data.map((sector: any) => (
              <tr key={sector.ticker} className="border-b border-neutral-900 hover:bg-neutral-900/50">
                <td className="px-3 py-2 font-mono text-neutral-200">{sector.ticker}</td>
                <td className="px-3 py-2 text-neutral-400">{sector.name}</td>
                <td className="px-3 py-2 text-right font-mono text-neutral-200">{formatCurrency(sector.price)}</td>
                <td className="px-3 py-2 text-right">
                  <DeltaBadge value={sector.changePercent} format="pct" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
