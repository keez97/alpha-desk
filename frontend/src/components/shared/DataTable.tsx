import { useState } from 'react';
import { classNames, formatCurrency, formatPercent, formatLargeNumber } from '../../lib/utils';

export interface ColumnDef<T> {
  accessor: keyof T;
  header: string;
  align?: 'left' | 'right' | 'center';
  format?: 'currency' | 'percent' | 'number' | 'delta';
  width?: string;
}

interface DataTableProps<T extends Record<string, any>> {
  columns: ColumnDef<T>[];
  data: T[];
  sortable?: boolean;
}

type SortDirection = 'asc' | 'desc' | null;

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  sortable = true,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<keyof T | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  const handleSort = (key: keyof T) => {
    if (!sortable) return;

    if (sortKey === key) {
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else {
        setSortKey(null);
        setSortDirection(null);
      }
    } else {
      setSortKey(key);
      setSortDirection('asc');
    }
  };

  const sortedData = sortKey && sortDirection ? [...data].sort((a, b) => {
    const aVal = a[sortKey];
    const bVal = b[sortKey];

    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  }) : data;

  const formatValue = (value: any, format?: string): string => {
    if (value === null || value === undefined) return '-';

    switch (format) {
      case 'currency':
        return formatCurrency(value);
      case 'percent':
        return formatPercent(value);
      case 'number':
        return formatLargeNumber(value);
      case 'delta':
        return formatPercent(value);
      default:
        return String(value);
    }
  };

  const getValueColor = (value: any, format?: string): string => {
    if (format === 'delta' || format === 'percent') {
      if (value > 0) return 'text-green-400';
      if (value < 0) return 'text-red-400';
      return 'text-gray-400';
    }
    return 'text-gray-300';
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700 bg-gray-800/50">
            {columns.map((col) => (
              <th
                key={String(col.accessor)}
                onClick={() => handleSort(col.accessor)}
                className={classNames(
                  'px-4 py-3 font-semibold text-gray-300',
                  col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left',
                  sortable && col.header ? 'cursor-pointer hover:bg-gray-700/50' : ''
                )}
                style={{ width: col.width }}
              >
                <div className="flex items-center space-x-2">
                  <span>{col.header}</span>
                  {sortable && sortKey === col.accessor && (
                    <span className="text-blue-400">{sortDirection === 'asc' ? '▲' : '▼'}</span>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row, idx) => (
            <tr key={idx} className="border-b border-gray-800 hover:bg-gray-800/30 transition-colors">
              {columns.map((col) => {
                const value = row[col.accessor];
                const formatted = formatValue(value, col.format);
                const color = getValueColor(value, col.format);

                return (
                  <td
                    key={String(col.accessor)}
                    className={classNames(
                      'px-4 py-3 font-mono text-gray-300',
                      col.accessor === 'ticker' ? '' : 'font-mono',
                      color,
                      col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'
                    )}
                  >
                    {formatted}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
