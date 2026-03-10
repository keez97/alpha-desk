import { useState } from 'react';
import { EarningsCalendarItem } from '../../lib/api';
import { EarningsSignalBadge } from './EarningsSignalBadge';
import { classNames } from '../../lib/utils';

interface EarningsCalendarProps {
  items: EarningsCalendarItem[];
  selectedTicker?: string;
  onSelectTicker: (ticker: string) => void;
  isLoading?: boolean;
  error?: Error | null;
}

type SortField = 'ticker' | 'earnings_date' | 'days_to_earnings' | 'divergence_pct' | 'signal';
type SortOrder = 'asc' | 'desc';

export function EarningsCalendar({
  items,
  selectedTicker,
  onSelectTicker,
  isLoading,
  error,
}: EarningsCalendarProps) {
  const [sortField, setSortField] = useState<SortField>('days_to_earnings');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const sortedItems = [...items].sort((a, b) => {
    let aVal: any = a[sortField];
    let bVal: any = b[sortField];

    if (sortField === 'days_to_earnings' || sortField === 'divergence_pct') {
      aVal = parseFloat(aVal);
      bVal = parseFloat(bVal);
    }

    if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  const SortHeader = ({ field, label }: { field: SortField; label: string }) => (
    <button
      onClick={() => handleSort(field)}
      className="flex items-center gap-1 hover:text-neutral-300 transition-colors font-medium"
    >
      <span>{label}</span>
      <span className="text-[10px]">
        {sortField === field ? (sortOrder === 'asc' ? '↑' : '↓') : '⇅'}
      </span>
    </button>
  );

  if (error) {
    return (
      <div className="p-4 rounded border border-red-900 bg-red-950 text-red-400 text-xs">
        Error loading earnings calendar: {error.message}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 h-full">
      {/* Header */}
      <div className="text-xs text-neutral-500 font-medium">
        {sortedItems.length} upcoming earnings
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full border-collapse text-xs">
          <thead className="sticky top-0 bg-black">
            <tr className="border-b border-neutral-800">
              <th className="text-left px-3 py-2">
                <SortHeader field="ticker" label="Ticker" />
              </th>
              <th className="text-left px-3 py-2">
                <SortHeader field="earnings_date" label="Date" />
              </th>
              <th className="text-right px-3 py-2">
                <SortHeader field="days_to_earnings" label="Days" />
              </th>
              <th className="text-right px-3 py-2">Consensus EPS</th>
              <th className="text-right px-3 py-2">SmartEst EPS</th>
              <th className="text-right px-3 py-2">
                <SortHeader field="divergence_pct" label="Divergence" />
              </th>
              <th className="text-center px-3 py-2">
                <SortHeader field="signal" label="Signal" />
              </th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={7} className="px-3 py-4 text-center text-neutral-500">
                  Loading...
                </td>
              </tr>
            ) : sortedItems.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-4 text-center text-neutral-500">
                  No earnings data available
                </td>
              </tr>
            ) : (
              sortedItems.map((item) => (
                <tr
                  key={item.ticker}
                  onClick={() => onSelectTicker(item.ticker)}
                  className={classNames(
                    'border-b border-neutral-800 cursor-pointer transition-colors hover:bg-neutral-900',
                    selectedTicker === item.ticker ? 'bg-neutral-900 border-l-2 border-l-neutral-600' : ''
                  )}
                >
                  <td className="px-3 py-2 font-semibold text-neutral-100">
                    {item.ticker}
                  </td>
                  <td className="px-3 py-2 text-neutral-400">
                    {new Date(item.earnings_date).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </td>
                  <td className="px-3 py-2 text-right text-neutral-400">
                    {item.days_to_earnings}d
                  </td>
                  <td className="px-3 py-2 text-right text-neutral-400">
                    ${item.consensus_eps.toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-right text-neutral-400">
                    ${item.smart_estimate_eps.toFixed(2)}
                  </td>
                  <td
                    className={classNames(
                      'px-3 py-2 text-right font-semibold',
                      item.divergence_pct > 0 ? 'text-emerald-400' : 'text-red-400'
                    )}
                  >
                    {item.divergence_pct > 0 ? '+' : ''}{item.divergence_pct.toFixed(2)}%
                  </td>
                  <td className="px-3 py-2 text-center">
                    <EarningsSignalBadge
                      signal={item.signal}
                      confidence={item.confidence}
                      showConfidence={false}
                      size="sm"
                    />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
