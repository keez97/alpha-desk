import { useState } from 'react';
import { DataTable } from '../shared/DataTable';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { useSectors } from '../../hooks/useSectors';

type Period = '1D' | '5D' | '1M' | '3M';

export function SectorPanel() {
  const [period, setPeriod] = useState<Period>('1D');
  const { data, isLoading, error, refetch } = useSectors(period);

  const columns = [
    { accessor: 'ticker' as const, header: 'Ticker', width: '80px' },
    { accessor: 'name' as const, header: 'Name', width: '200px' },
    { accessor: 'price' as const, header: 'Price', align: 'right' as const, format: 'currency' as const, width: '100px' },
    { accessor: 'changePercent' as const, header: 'Change', align: 'right' as const, format: 'delta' as const, width: '80px' },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Sector Performance</h2>
        <div className="flex space-x-2">
          {(['1D', '5D', '1M', '3M'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                period === p
                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                  : 'bg-gray-700/30 text-gray-400 hover:bg-gray-700/50'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <LoadingState message="Loading sectors..." />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : data ? (
        <div className="bg-gray-800/30 rounded-lg border border-gray-700 overflow-hidden">
          <DataTable columns={columns} data={data} sortable={true} />
        </div>
      ) : null}
    </div>
  );
}
