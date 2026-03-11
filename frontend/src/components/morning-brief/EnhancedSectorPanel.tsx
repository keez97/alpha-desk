import { useState, useEffect, useMemo } from 'react';
import type { EnhancedSectorData } from '../../lib/api';
import { useEnhancedSectors } from '../../hooks/useEnhancedSectors';
import { DeltaBadge } from '../shared/DeltaBadge';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { formatCurrency, classNames } from '../../lib/utils';

const QUADRANT_COLORS: Record<string, string> = {
  Strengthening: 'bg-green-900/50 text-green-400',
  Weakening: 'bg-amber-900/50 text-amber-400',
  Recovering: 'bg-blue-900/50 text-blue-400',
  Deteriorating: 'bg-red-900/50 text-red-400',
  Unknown: 'bg-neutral-800 text-neutral-400',
};

const QUADRANT_TOOLTIPS: Record<string, string> = {
  Strengthening: 'RS-Ratio > 100 & rising momentum \u2014 leading the market',
  Weakening: 'RS-Ratio > 100 but falling momentum \u2014 losing relative strength',
  Recovering: 'RS-Ratio < 100 but rising momentum \u2014 starting to improve',
  Deteriorating: 'RS-Ratio < 100 & falling momentum \u2014 lagging the market',
};

const ROW_TINTS: Record<string, string> = {
  Strengthening: 'bg-green-950/20',
  Weakening: 'bg-amber-950/10',
  Recovering: 'bg-blue-950/10',
  Deteriorating: 'bg-red-950/10',
};

function QuadrantBadge({ quadrant }: { quadrant: string }) {
  const colors = QUADRANT_COLORS[quadrant] || QUADRANT_COLORS.Unknown;
  const tooltip = QUADRANT_TOOLTIPS[quadrant] || '';
  return (
    <span
      className={classNames('inline-block px-2 py-0.5 rounded-full text-[10px] font-medium whitespace-nowrap', colors)}
      title={tooltip}
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

type SortKey = 'ticker' | 'price' | 'changePercent' | 'quadrant' | 'rsMomentum' | 'tailLength' | 'quadrantAge' | 'rsRatio';

function SortHeader({ label, sortKey, currentKey, direction, onClick }: {
  label: string;
  sortKey: SortKey;
  currentKey: SortKey;
  direction: 'asc' | 'desc';
  onClick: (key: SortKey) => void;
}) {
  const isActive = currentKey === sortKey;
  return (
    <th
      className="px-2 py-2 text-[10px] text-neutral-500 font-medium uppercase tracking-wider cursor-pointer hover:text-neutral-300 select-none transition-colors"
      onClick={() => onClick(sortKey)}
    >
      <span className="inline-flex items-center gap-0.5">
        {label}
        {isActive && (
          <span className="text-neutral-400">{direction === 'asc' ? '\u25b2' : '\u25bc'}</span>
        )}
      </span>
    </th>
  );
}

export function EnhancedSectorPanel() {
  const [period, setPeriod] = useState<'1D' | '5D' | '1M' | '3M'>('1D');
  const [timedOut, setTimedOut] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>('changePercent');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const { data, isLoading, error, refetch } = useEnhancedSectors(period);

  useEffect(() => {
    if (!isLoading) { setTimedOut(false); return; }
    const timer = setTimeout(() => setTimedOut(true), 8000);
    return () => clearTimeout(timer);
  }, [isLoading]);

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sortedData = useMemo(() => {
    if (!data) return [];
    const arr = [...data];
    arr.sort((a, b) => {
      let aVal: any = (a as any)[sortKey];
      let bVal: any = (b as any)[sortKey];
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return arr;
  }, [data, sortKey, sortDir]);

  if (timedOut) {
    return (
      <div className="flex items-center gap-3 py-4 px-4 bg-amber-950/30 rounded border border-amber-900/50">
        <span className="text-xs text-amber-400">Request timed out</span>
        <button
          onClick={() => { setTimedOut(false); refetch(); }}
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
                period === p ? 'bg-neutral-800 text-neutral-200' : 'text-neutral-500 hover:text-neutral-300'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="border border-neutral-800 rounded overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-neutral-800">
              <SortHeader label="Ticker" sortKey="ticker" currentKey={sortKey} direction={sortDir} onClick={handleSort} />
              <th className="px-2 py-2 text-left text-[10px] text-neutral-500 font-medium uppercase tracking-wider">Name</th>
              <SortHeader label="Price" sortKey="price" currentKey={sortKey} direction={sortDir} onClick={handleSort} />
              <SortHeader label="Chg%" sortKey="changePercent" currentKey={sortKey} direction={sortDir} onClick={handleSort} />
              <SortHeader label="Quadrant" sortKey="quadrant" currentKey={sortKey} direction={sortDir} onClick={handleSort} />
              <SortHeader label="RS-Ratio" sortKey="rsRatio" currentKey={sortKey} direction={sortDir} onClick={handleSort} />
              <SortHeader label="RS-Mom" sortKey="rsMomentum" currentKey={sortKey} direction={sortDir} onClick={handleSort} />
              <SortHeader label="Tail" sortKey="tailLength" currentKey={sortKey} direction={sortDir} onClick={handleSort} />
              <SortHeader label="Age" sortKey="quadrantAge" currentKey={sortKey} direction={sortDir} onClick={handleSort} />
              <th className="px-2 py-2 text-center text-[10px] text-neutral-500 font-medium uppercase tracking-wider">Trend</th>
            </tr>
          </thead>
          <tbody>
            {sortedData.map((sector: EnhancedSectorData) => {
              const rowTint = ROW_TINTS[sector.quadrant] || '';
              return (
                <tr key={sector.ticker} className={`border-b border-neutral-900 hover:bg-neutral-900/50 ${rowTint}`}>
                  <td className="px-2 py-2 font-mono text-neutral-200">{sector.ticker}</td>
                  <td className="px-2 py-2 text-neutral-400 whitespace-nowrap">{sector.name}</td>
                  <td className="px-2 py-2 text-right font-mono text-neutral-200">{formatCurrency(sector.price)}</td>
                  <td className="px-2 py-2 text-right"><DeltaBadge value={sector.changePercent} format="pct" /></td>
                  <td className="px-2 py-2 text-center"><QuadrantBadge quadrant={sector.quadrant} /></td>
                  <td className={classNames('px-2 py-2 text-right font-mono text-[10px]', sector.rsRatio > 100 ? 'text-green-400' : 'text-red-400')}>
                    {sector.rsRatio.toFixed(1)}
                  </td>
                  <td className={classNames('px-2 py-2 text-right font-mono text-[10px]', getMomentumColor(sector.rsMomentum))}>
                    {sector.rsMomentum.toFixed(2)}
                  </td>
                  <td className="px-2 py-2 text-right" title="Euclidean distance traveled on RRG plane (last 4 weeks)">
                    <div className="flex items-center justify-end gap-1">
                      <div className="w-10 h-1.5 bg-neutral-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-neutral-500 rounded-full"
                          style={{ width: `${Math.min(100, sector.tailLength * 10)}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-neutral-500 font-mono w-6 text-right">{sector.tailLength.toFixed(1)}</span>
                    </div>
                  </td>
                  <td className="px-2 py-2 text-center" title={`${sector.quadrantAge} weeks in ${sector.quadrant}`}>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-400 font-mono">
                      {sector.quadrantAge}w
                    </span>
                  </td>
                  <td className="px-2 py-2 text-center">
                    <span className={classNames(
                      'text-[10px] font-medium',
                      sector.rsTrend === 'up' ? 'text-green-400' : 'text-red-400'
                    )} title={`RS-Ratio trending ${sector.rsTrend}, rotating ${sector.rotationDirection}`}>
                      {sector.rsTrend === 'up' ? '\u2191' : '\u2193'}{' '}
                      <span className="text-neutral-600 text-[9px]">
                        {sector.rotationDirection === 'clockwise' ? '\u21bb' : '\u21ba'}
                      </span>
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
