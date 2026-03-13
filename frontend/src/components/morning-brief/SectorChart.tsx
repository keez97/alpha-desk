import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useSectors } from '../../hooks/useSectors';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';

const sectorColors: Record<string, string> = {
  XLK: '#10b981', XLV: '#8b5cf6', XLF: '#06b6d4',
  XLI: '#ec4899', XLY: '#14b8a6', XLP: '#f59e0b',
  XLE: '#ef4444', XLRE: '#3b82f6', XLU: '#84cc16',
  XLC: '#f97316',
};

const periods = ['1D', '5D', '1M', '3M'] as const;
type Period = typeof periods[number];

interface ChartPoint {
  date: string;
  [ticker: string]: number | string;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function calculatePctChangeFromStart(currentPrice: number, priceAtStart: number): number {
  if (priceAtStart === 0) return 0;
  return ((currentPrice - priceAtStart) / priceAtStart) * 100;
}

export function SectorChart() {
  const [period, setPeriod] = useState<Period>('1M');
  const [hiddenSectors, setHiddenSectors] = useState<Set<string>>(new Set());
  const { data: sectors, isLoading, error, refetch } = useSectors(period);

  if (isLoading) return <LoadingState message="Loading chart data..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!sectors || sectors.length === 0) return null;

  const sectorsWithData = sectors.filter((s: any) => s.chartData && s.chartData.length > 0);
  if (sectorsWithData.length === 0) return null;

  // Build chart data with actual prices and real dates
  const maxLen = Math.max(...sectorsWithData.map((s: any) => s.chartData.length));
  const chartData: ChartPoint[] = Array.from({ length: maxLen }, (_, i) => {
    const point: ChartPoint = { date: '' };
    sectorsWithData.forEach((s: any) => {
      if (s.chartData[i] !== undefined) {
        point[s.ticker] = s.chartData[i];
      }
      // Set date from first sector that has it
      if (!point.date && s.chartDates && s.chartDates[i]) {
        point.date = s.chartDates[i];
      }
    });
    return point;
  });

  const toggleSector = (ticker: string) => {
    setHiddenSectors(prev => {
      const next = new Set(prev);
      if (next.has(ticker)) {
        next.delete(ticker);
      } else {
        next.add(ticker);
      }
      return next;
    });
  };

  const customTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload) return null;

    const dataPoint = chartData.find(d => d.date === label?.date);
    if (!dataPoint) return null;

    return (
      <div className="bg-neutral-900 border border-neutral-700 rounded p-2 shadow-lg">
        <p className="text-xs text-neutral-300 mb-1 font-medium">
          {formatDate(label?.date || '')}
        </p>
        {payload.map((entry: any, idx: number) => {
          const sector = sectorsWithData.find(s => s.ticker === entry.dataKey);
          const currentPrice = entry.value;
          const startPrice = sector?.chartData?.[0];
          const pctFromStart = startPrice ? calculatePctChangeFromStart(currentPrice, startPrice) : 0;

          return (
            <p key={idx} style={{ color: entry.color }} className="text-xs">
              <span className="font-medium">{entry.dataKey}</span>: ${currentPrice?.toFixed(2)} ({pctFromStart >= 0 ? '+' : ''}{pctFromStart.toFixed(2)}%)
            </p>
          );
        })}
      </div>
    );
  };

  return (
    <div className="border border-neutral-800 rounded p-3">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-neutral-300">{period} Sector Performance</span>
        <div className="flex gap-1">
          {periods.map(p => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                period === p
                  ? 'bg-neutral-700 text-white'
                  : 'text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Clickable sector legend for toggling visibility */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {sectorsWithData.map((s: any) => {
          const isHidden = hiddenSectors.has(s.ticker);
          const color = sectorColors[s.ticker] || '#525252';
          return (
            <button
              key={s.ticker}
              onClick={() => toggleSector(s.ticker)}
              className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-xs transition-all border ${
                isHidden
                  ? 'border-neutral-800 text-neutral-500 opacity-50'
                  : 'border-neutral-700 text-neutral-300'
              }`}
              title={`Click to ${isHidden ? 'show' : 'hide'} ${s.name}`}
            >
              <span
                className="w-2 h-2 rounded-full inline-block"
                style={{ backgroundColor: isHidden ? '#404040' : color }}
              />
              {s.ticker}
            </button>
          );
        })}
      </div>

      <div className="h-80 w-full" role="img" aria-label="Sector performance chart showing multiple sector price movements">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f1f1f" />
            <XAxis
              dataKey="date"
              stroke="#525252"
              style={{ fontSize: '10px' }}
              tickFormatter={(date: string) => formatDate(date)}
              interval={Math.floor(chartData.length / 6)}
            />
            <YAxis
              stroke="#525252"
              style={{ fontSize: '10px' }}
              domain={['auto', 'auto']}
              tickFormatter={(value: number) => `$${value.toFixed(0)}`}
            />
            <Tooltip content={customTooltip} />
            {sectorsWithData
              .filter((s: any) => !hiddenSectors.has(s.ticker))
              .map((sector: any) => (
                <Line
                  key={sector.ticker}
                  type="monotone"
                  dataKey={sector.ticker}
                  stroke={sectorColors[sector.ticker] || '#525252'}
                  dot={false}
                  strokeWidth={1.5}
                  isAnimationActive={false}
                  name={sector.name}
                />
              ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
