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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Sector Performance</h2>
        <div className="flex space-x-1">
          {(['1D', '5D', '1M', '3M'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                period === p
                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                  : 'text-gray-400 hover:text-gray-300 border border-gray-700'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-gray-800/30 rounded-lg border border-gray-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700 bg-gray-800/50">
              <th className="px-4 py-3 text-left text-gray-300 font-semibold">Ticker</th>
              <th className="px-4 py-3 text-left text-gray-300 font-semibold">Name</th>
              <th className="px-4 py-3 text-right text-gray-300 font-semibold">Price</th>
              <th className="px-4 py-3 text-right text-gray-300 font-semibold">Change</th>
            </tr>
          </thead>
          <tbody>
            {data.map((sector: any) => (
              <tr key={sector.ticker} className="border-b border-gray-800 hover:bg-gray-800/30">
                <td className="px-4 py-3 font-mono text-white">{sector.ticker}</td>
                <td className="px-4 py-3 text-gray-300">{sector.name}</td>
                <td className="px-4 py-3 text-right font-mono text-white">{formatCurrency(sector.price)}</td>
                <td className="px-4 py-3 text-right">
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
