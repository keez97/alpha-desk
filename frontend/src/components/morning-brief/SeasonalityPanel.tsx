/**
 * Sector Seasonality — Monthly average return heatmap for 11 SPDR sector ETFs.
 * Uses historical monthly returns to show seasonal patterns.
 */
import { useQuery } from '@tanstack/react-query';
import api from '../../lib/api';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';

interface SectorSeasonality {
  ticker: string;
  name: string;
  monthly_returns: Record<string, number>; // "Jan" -> avg return %
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

async function fetchSeasonality(): Promise<SectorSeasonality[]> {
  const { data } = await api.get('/sector-seasonality');
  const raw = data.data || data.sectors || data;
  if (!Array.isArray(raw)) return [];
  return raw.map((s: any) => ({
    ticker: s.ticker || '',
    name: s.name || s.sector || s.ticker || '',
    monthly_returns: s.monthly_returns || s.returns || {},
  }));
}

function getHeatColor(value: number): string {
  // Green for positive, red for negative, intensity by magnitude
  if (value >= 3) return 'bg-green-600/80 text-green-100';
  if (value >= 2) return 'bg-green-700/60 text-green-200';
  if (value >= 1) return 'bg-green-800/40 text-green-300';
  if (value >= 0.3) return 'bg-green-900/30 text-green-400';
  if (value > -0.3) return 'bg-neutral-800/50 text-neutral-400';
  if (value > -1) return 'bg-red-900/30 text-red-400';
  if (value > -2) return 'bg-red-800/40 text-red-300';
  if (value > -3) return 'bg-red-700/60 text-red-200';
  return 'bg-red-600/80 text-red-100';
}

// Highlight current month
const CURRENT_MONTH_IDX = new Date().getMonth();

export function SeasonalityPanel() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['sector-seasonality'],
    queryFn: fetchSeasonality,
    staleTime: 60 * 60 * 1000, // 1 hour — seasonality doesn't change often
    retry: 2,
  });

  if (isLoading) return <LoadingState message="Loading seasonality data..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data || data.length === 0) {
    return (
      <div className="p-3">
        <div className="text-xs font-semibold text-neutral-200 mb-2">Sector Seasonality</div>
        <div className="text-xs text-neutral-500 text-center py-4">No data available</div>
      </div>
    );
  }

  return (
    <div className="p-3 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-neutral-200">Sector Seasonality</span>
        <span className="text-xs text-neutral-500">Avg Monthly Returns (%)</span>
      </div>

      <div className="overflow-x-auto flex-1">
        <table className="w-full text-xs border-collapse" role="table" aria-label="Sector seasonality heatmap">
          <thead>
            <tr>
              <th className="text-left text-neutral-500 font-normal px-1.5 py-1 sticky left-0 bg-neutral-900 z-10">Sector</th>
              {MONTHS.map((m, i) => (
                <th
                  key={m}
                  className={`text-center font-normal px-1 py-1 ${
                    i === CURRENT_MONTH_IDX
                      ? 'text-blue-400 font-medium'
                      : 'text-neutral-500'
                  }`}
                >
                  {m}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((sector) => (
              <tr key={sector.ticker} className="border-t border-neutral-800/30">
                <td className="text-neutral-300 font-medium px-1.5 py-1 whitespace-nowrap sticky left-0 bg-neutral-900 z-10">
                  {sector.ticker}
                </td>
                {MONTHS.map((m, i) => {
                  const val = sector.monthly_returns[m] ?? 0;
                  const colorClass = getHeatColor(val);
                  const isCurrentMonth = i === CURRENT_MONTH_IDX;
                  return (
                    <td
                      key={m}
                      className={`text-center font-mono px-1 py-1 ${colorClass} ${
                        isCurrentMonth ? 'ring-1 ring-blue-500/50' : ''
                      }`}
                      title={`${sector.name} ${m}: ${val >= 0 ? '+' : ''}${val.toFixed(1)}%`}
                    >
                      {val >= 0 ? '+' : ''}{val.toFixed(1)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-2 flex items-center justify-between text-xs text-neutral-500 shrink-0">
        <div className="flex items-center gap-2">
          <span className="inline-block w-3 h-3 bg-green-700/60 rounded-sm" /> Positive
          <span className="inline-block w-3 h-3 bg-red-700/60 rounded-sm" /> Negative
        </div>
        <span>Based on 10-year averages</span>
      </div>
    </div>
  );
}
