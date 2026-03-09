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

export function SectorChart() {
  const { data: sectors, isLoading, error, refetch } = useSectors('1M');

  if (isLoading) return <LoadingState message="Loading chart data..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!sectors || sectors.length === 0) return null;

  const sectorsWithData = sectors.filter((s: any) => s.chartData && s.chartData.length > 0);
  if (sectorsWithData.length === 0) return null;

  const maxLen = Math.max(...sectorsWithData.map((s: any) => s.chartData.length));
  const chartData = Array.from({ length: maxLen }, (_, i) => {
    const point: Record<string, any> = { day: `Day ${i + 1}` };
    sectorsWithData.forEach((s: any) => {
      point[s.ticker] = s.chartData[i] ?? null;
    });
    return point;
  });

  const displaySectors = sectorsWithData.slice(0, 6);

  return (
    <div className="border border-neutral-800 rounded p-3">
      <span className="text-xs font-medium text-neutral-300 mb-3 block">1M Sector Performance</span>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f1f1f" />
            <XAxis dataKey="day" stroke="#525252" style={{ fontSize: '10px' }} />
            <YAxis stroke="#525252" style={{ fontSize: '10px' }} domain={['auto', 'auto']} />
            <Tooltip
              contentStyle={{ backgroundColor: '#0a0a0a', border: '1px solid #262626', borderRadius: '4px', fontSize: '11px' }}
              labelStyle={{ color: '#a3a3a3' }}
              formatter={(value: number) => [`${value.toFixed(2)}%`, '']}
            />
            <Legend wrapperStyle={{ paddingTop: '8px', fontSize: '10px' }} />
            {displaySectors.map((sector: any) => (
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
