import { useState } from 'react';
import { DataTable, type ColumnDef } from '../shared/DataTable';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { Timestamp } from '../shared/Timestamp';
import { FilterBuilder } from './FilterBuilder';
import { useRunQuantScreen, useScreenPresets } from '../../hooks/useQuantScreener';
import type { QuantFilter, QuantScreenResult } from '../../lib/api';

export function QuantScreener() {
  const [filters, setFilters] = useState<QuantFilter>({
    sort_by: 'rs_momentum',
    sort_desc: true,
  });
  const [hasRun, setHasRun] = useState(false);

  const { data: presetsData } = useScreenPresets();
  const { mutate: runScreen, data, isPending, error } = useRunQuantScreen();

  const handleApplyFilters = (newFilters: QuantFilter) => {
    setFilters(newFilters);
    setHasRun(true);
    runScreen(newFilters);
  };

  const results = data?.data.results || [];
  const timestamp = data?.timestamp;

  const columns: ColumnDef<QuantScreenResult>[] = [
    { accessor: 'ticker' as const, header: 'Ticker', width: '70px' },
    { accessor: 'name' as const, header: 'Sector', width: '180px' },
    { accessor: 'price' as const, header: 'Price', align: 'right' as const, format: 'currency' as const, width: '90px' },
    { accessor: 'change_1d_pct' as const, header: '1D Change', align: 'right' as const, format: 'delta' as const, width: '90px' },
    { accessor: 'rs_ratio' as const, header: 'RS-Ratio', align: 'right' as const, format: 'number' as const, width: '80px' },
    { accessor: 'rs_momentum' as const, header: 'RS-Momentum', align: 'right' as const, format: 'number' as const, width: '100px' },
    { accessor: 'quadrant' as const, header: 'Quadrant', width: '120px' },
  ];

  const renderRow = (row: QuantScreenResult) => {
    const quadrantColors: Record<string, string> = {
      'Strengthening': 'bg-green-900/50 text-green-400',
      'Recovering': 'bg-blue-900/50 text-blue-400',
      'Weakening': 'bg-orange-900/50 text-orange-400',
      'Deteriorating': 'bg-red-900/50 text-red-400',
    };

    return (
      <tr key={row.ticker} className="border-b border-neutral-900 hover:bg-neutral-900/50 transition-colors">
        <td className="px-3 py-2 text-xs font-medium text-neutral-200">{row.ticker}</td>
        <td className="px-3 py-2 text-xs text-neutral-300">{row.name}</td>
        <td className="px-3 py-2 text-xs text-right font-mono text-neutral-300">
          ${row.price.toFixed(2)}
        </td>
        <td className={`px-3 py-2 text-xs text-right font-mono ${
          row.change_1d_pct > 0 ? 'text-emerald-400' : row.change_1d_pct < 0 ? 'text-red-400' : 'text-neutral-500'
        }`}>
          {row.change_1d_pct > 0 ? '+' : ''}{row.change_1d_pct.toFixed(2)}%
        </td>
        <td className="px-3 py-2 text-xs text-right font-mono text-neutral-300">
          {row.rs_ratio.toFixed(2)}
        </td>
        <td className={`px-3 py-2 text-xs text-right font-mono ${
          row.rs_momentum > 0 ? 'text-emerald-400' : row.rs_momentum < 0 ? 'text-red-400' : 'text-neutral-500'
        }`}>
          {row.rs_momentum > 0 ? '+' : ''}{row.rs_momentum.toFixed(2)}
        </td>
        <td className="px-3 py-2 text-xs">
          <span className={`px-2 py-1 rounded text-[10px] font-medium ${quadrantColors[row.quadrant] || 'bg-neutral-900 text-neutral-400'}`}>
            {row.quadrant}
          </span>
        </td>
      </tr>
    );
  };

  return (
    <div className="space-y-4">
      {/* Filter Builder */}
      <FilterBuilder
        presets={presetsData?.presets || []}
        onApplyFilters={handleApplyFilters}
        isLoading={isPending}
      />

      {/* Results */}
      {isPending && <LoadingState message="Running quantitative screen..." />}
      {error && <ErrorState error={error} onRetry={() => runScreen(filters)} />}

      {hasRun && !isPending && !error && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-xs font-medium text-neutral-300">
                Results: {results.length} sectors
              </span>
              {timestamp && <Timestamp date={timestamp} label="Generated" />}
            </div>
          </div>

          {results.length === 0 ? (
            <div className="border border-neutral-800 rounded p-8 text-center bg-neutral-950">
              <p className="text-xs text-neutral-500">
                No sectors match your filters. Try adjusting the criteria.
              </p>
            </div>
          ) : (
            <div className="border border-neutral-800 rounded overflow-hidden bg-neutral-950">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-neutral-800 bg-neutral-900/50">
                      {columns.map((col) => (
                        <th
                          key={String(col.accessor)}
                          className={`px-3 py-2 font-medium text-neutral-500 uppercase tracking-wider text-[10px] ${
                            col.align === 'right' ? 'text-right' : 'text-left'
                          }`}
                          style={{ width: col.width }}
                        >
                          {col.header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {results.map(renderRow)}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
