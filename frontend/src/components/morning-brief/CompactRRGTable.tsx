import { useState, useMemo } from 'react';
import type { EnhancedSectorData } from '../../lib/api';
import { useEnhancedSectors } from '../../hooks/useEnhancedSectors';
import { DeltaBadge } from '../shared/DeltaBadge';
import { formatCurrency, classNames } from '../../lib/utils';

/* ── Shared Constants ── */

const QUADRANT_COLORS: Record<string, string> = {
  Strengthening: 'bg-green-900/50 text-green-400',
  Weakening: 'bg-amber-900/50 text-amber-400',
  Recovering: 'bg-blue-900/50 text-blue-400',
  Deteriorating: 'bg-red-900/50 text-red-400',
  Unknown: 'bg-neutral-800 text-neutral-400',
};

const QUADRANT_ABBR: Record<string, string> = {
  Strengthening: 'Strong',
  Weakening: 'Weak',
  Recovering: 'Recov',
  Deteriorating: 'Deter',
};

const ROW_TINTS: Record<string, string> = {
  Strengthening: 'bg-green-950/20',
  Weakening: 'bg-amber-950/10',
  Recovering: 'bg-blue-950/10',
  Deteriorating: 'bg-red-950/10',
};

function getMomentumColor(value: number): string {
  if (value > 0) return 'text-green-400';
  if (value < 0) return 'text-red-400';
  return 'text-neutral-400';
}

/* ── Column Definitions ── */

type ColumnKey = 'ticker' | 'price' | 'changePercent' | 'quadrant' | 'rsRatio' | 'rsMomentum' | 'trend' | 'tailLength' | 'quadrantAge';

interface ColumnDef {
  key: ColumnKey;
  label: string;
  shortLabel: string;
  sortable: boolean;
  defaultVisible: boolean;
}

const ALL_COLUMNS: ColumnDef[] = [
  { key: 'ticker', label: 'Ticker', shortLabel: 'Ticker', sortable: true, defaultVisible: true },
  { key: 'price', label: 'Price', shortLabel: 'Price', sortable: true, defaultVisible: true },
  { key: 'changePercent', label: 'Chg%', shortLabel: 'Chg%', sortable: true, defaultVisible: true },
  { key: 'quadrant', label: 'Quadrant', shortLabel: 'Quad', sortable: true, defaultVisible: true },
  { key: 'rsRatio', label: 'RS-Ratio', shortLabel: 'RS-R', sortable: true, defaultVisible: true },
  { key: 'rsMomentum', label: 'RS-Mom', shortLabel: 'RS-M', sortable: true, defaultVisible: true },
  { key: 'trend', label: 'Trend', shortLabel: 'Trend', sortable: true, defaultVisible: true },
  { key: 'tailLength', label: 'Tail', shortLabel: 'Tail', sortable: true, defaultVisible: false },
  { key: 'quadrantAge', label: 'Age', shortLabel: 'Age', sortable: true, defaultVisible: false },
];

type SortKey = 'ticker' | 'price' | 'changePercent' | 'quadrant' | 'rsMomentum' | 'tailLength' | 'quadrantAge' | 'rsRatio' | 'trend';

/* ── Column Config Dropdown ── */

function ColumnConfig({
  visibleColumns,
  onToggle,
  onClose,
}: {
  visibleColumns: Set<ColumnKey>;
  onToggle: (key: ColumnKey) => void;
  onClose: () => void;
}) {
  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div className="absolute right-0 top-6 z-50 bg-neutral-900 border border-neutral-700 rounded shadow-xl py-1 min-w-[140px]">
        <div className="text-[8px] text-neutral-500 px-2 py-1 uppercase tracking-wider">Columns</div>
        {ALL_COLUMNS.map(col => (
          <label
            key={col.key}
            className="flex items-center gap-2 px-2 py-1 hover:bg-neutral-800/50 cursor-pointer text-[9px] text-neutral-300"
          >
            <input
              type="checkbox"
              checked={visibleColumns.has(col.key)}
              onChange={() => onToggle(col.key)}
              disabled={col.key === 'ticker'}
              className="rounded border-neutral-600 bg-neutral-800 text-blue-500 w-3 h-3"
            />
            {col.label}
          </label>
        ))}
      </div>
    </>
  );
}

/* ── Compact Sort Header ── */

function CompactSortHeader({
  label,
  sortKey,
  currentKey,
  direction,
  onClick,
}: {
  label: string;
  sortKey: SortKey;
  currentKey: SortKey;
  direction: 'asc' | 'desc';
  onClick: (key: SortKey) => void;
}) {
  const isActive = currentKey === sortKey;
  return (
    <th
      className="px-1.5 py-1 text-[8px] text-neutral-500 font-medium uppercase tracking-wider cursor-pointer hover:text-neutral-300 select-none transition-colors whitespace-nowrap"
      onClick={() => onClick(sortKey)}
    >
      <span className="inline-flex items-center gap-0.5">
        {label}
        {isActive && (
          <span className="text-neutral-400 text-[7px]">{direction === 'asc' ? '▲' : '▼'}</span>
        )}
      </span>
    </th>
  );
}

/* ── Main Component ── */

export function CompactRRGTable() {
  const [period, setPeriod] = useState<'1D' | '5D' | '1M' | '3M'>('1D');
  const [sortKey, setSortKey] = useState<SortKey>('changePercent');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [showConfig, setShowConfig] = useState(false);
  const [visibleColumns, setVisibleColumns] = useState<Set<ColumnKey>>(
    () => new Set(ALL_COLUMNS.filter(c => c.defaultVisible).map(c => c.key))
  );

  const { data, isLoading, error } = useEnhancedSectors(period);

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const toggleColumn = (key: ColumnKey) => {
    if (key === 'ticker') return; // always visible
    setVisibleColumns(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const sortedData = useMemo(() => {
    if (!data) return [];
    const arr = [...data];
    arr.sort((a, b) => {
      let aVal: any;
      let bVal: any;
      if (sortKey === 'trend') {
        // Sort by rsTrend (up/down) as primary, rotationDirection as secondary
        aVal = a.rsTrend === 'up' ? 1 : 0;
        bVal = b.rsTrend === 'up' ? 1 : 0;
      } else {
        aVal = (a as any)[sortKey];
        bVal = (b as any)[sortKey];
      }
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return arr;
  }, [data, sortKey, sortDir]);

  const activeCols = ALL_COLUMNS.filter(c => visibleColumns.has(c.key));

  /* ── Render ── */
  return (
    <div className="space-y-1">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[9px] text-neutral-500 font-medium">Sector RRG</span>
          <div className="flex gap-px">
            {(['1D', '5D', '1M', '3M'] as const).map(p => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={classNames(
                  'px-1.5 py-0.5 rounded text-[8px] font-medium transition-colors',
                  period === p
                    ? 'bg-neutral-700 text-neutral-200'
                    : 'text-neutral-600 hover:text-neutral-400'
                )}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-1 relative">
          {/* Column config toggle */}
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="text-neutral-600 hover:text-neutral-400 transition-colors p-0.5"
            title="Configure columns"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
          {/* Pop-out placeholder */}
          <button
            className="text-neutral-600 hover:text-neutral-400 transition-colors p-0.5"
            title="Expand (coming soon)"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            </svg>
          </button>
          {showConfig && (
            <ColumnConfig
              visibleColumns={visibleColumns}
              onToggle={toggleColumn}
              onClose={() => setShowConfig(false)}
            />
          )}
        </div>
      </div>

      {/* Loading / Error */}
      {isLoading && (
        <div className="flex items-center gap-2 py-2">
          <div className="w-2.5 h-2.5 border border-blue-400/50 border-t-blue-400 rounded-full animate-spin" />
          <span className="text-[8px] text-neutral-500 italic">Loading sectors...</span>
        </div>
      )}

      {error && !isLoading && (
        <div className="text-[8px] text-red-400/70 py-1">Failed to load sector data</div>
      )}

      {/* Table */}
      {!isLoading && !error && sortedData.length > 0 && (
        <div className="overflow-x-auto max-h-[180px] overflow-y-auto">
          <table className="w-full">
            <thead className="sticky top-0 bg-neutral-900/95 backdrop-blur-sm z-10">
              <tr className="border-b border-neutral-800/50">
                {activeCols.map(col =>
                  col.sortable ? (
                    <CompactSortHeader
                      key={col.key}
                      label={col.shortLabel}
                      sortKey={col.key as SortKey}
                      currentKey={sortKey}
                      direction={sortDir}
                      onClick={handleSort}
                    />
                  ) : (
                    <th
                      key={col.key}
                      className="px-1.5 py-1 text-[8px] text-neutral-500 font-medium uppercase tracking-wider text-center whitespace-nowrap"
                    >
                      {col.shortLabel}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {sortedData.map((sector: EnhancedSectorData) => {
                const rowTint = ROW_TINTS[sector.quadrant] || '';
                return (
                  <tr
                    key={sector.ticker}
                    className={classNames(
                      'border-b border-neutral-900/50 hover:bg-neutral-800/30 transition-colors',
                      rowTint
                    )}
                  >
                    {activeCols.map(col => (
                      <CellRenderer key={col.key} column={col.key} sector={sector} />
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ── Cell Renderer ── */

function CellRenderer({ column, sector }: { column: ColumnKey; sector: EnhancedSectorData }) {
  switch (column) {
    case 'ticker':
      return (
        <td className="px-1.5 py-1 font-mono text-[9px] font-bold text-neutral-200">
          {sector.ticker}
        </td>
      );
    case 'price':
      return (
        <td className="px-1.5 py-1 text-right font-mono text-[8px] text-neutral-300">
          {formatCurrency(sector.price)}
        </td>
      );
    case 'changePercent':
      return (
        <td className="px-1.5 py-1 text-right">
          <span className={classNames(
            'font-mono text-[8px] font-medium',
            sector.changePercent > 0 ? 'text-emerald-400' : sector.changePercent < 0 ? 'text-red-400' : 'text-neutral-400'
          )}>
            {sector.changePercent > 0 ? '+' : ''}{sector.changePercent.toFixed(2)}%
          </span>
        </td>
      );
    case 'quadrant': {
      const colors = QUADRANT_COLORS[sector.quadrant] || QUADRANT_COLORS.Unknown;
      const abbr = QUADRANT_ABBR[sector.quadrant] || sector.quadrant;
      return (
        <td className="px-1.5 py-1 text-center">
          <span className={classNames('inline-block px-1.5 py-px rounded-full text-[7px] font-medium whitespace-nowrap', colors)}>
            {abbr}
          </span>
        </td>
      );
    }
    case 'rsRatio':
      return (
        <td className={classNames(
          'px-1.5 py-1 text-right font-mono text-[8px]',
          sector.rsRatio > 100 ? 'text-green-400' : 'text-red-400'
        )}>
          {sector.rsRatio.toFixed(1)}
        </td>
      );
    case 'rsMomentum':
      return (
        <td className={classNames(
          'px-1.5 py-1 text-right font-mono text-[8px]',
          getMomentumColor(sector.rsMomentum)
        )}>
          {sector.rsMomentum > 0 ? '+' : ''}{sector.rsMomentum.toFixed(2)}
        </td>
      );
    case 'trend':
      return (
        <td className="px-1.5 py-1 text-center">
          <span className={classNames(
            'text-[9px] font-medium',
            sector.rsTrend === 'up' ? 'text-green-400' : 'text-red-400'
          )}>
            {sector.rsTrend === 'up' ? '↑' : '↓'}
          </span>
          <span className="text-neutral-600 text-[7px] ml-0.5">
            {sector.rotationDirection === 'clockwise' ? '↻' : '↺'}
          </span>
        </td>
      );
    case 'tailLength':
      return (
        <td className="px-1.5 py-1 text-right font-mono text-[8px] text-neutral-400">
          {sector.tailLength.toFixed(1)}
        </td>
      );
    case 'quadrantAge':
      return (
        <td className="px-1.5 py-1 text-center">
          <span className="text-[7px] px-1 py-px rounded bg-neutral-800/60 text-neutral-400 font-mono">
            {sector.quadrantAge}w
          </span>
        </td>
      );
    default:
      return <td />;
  }
}
