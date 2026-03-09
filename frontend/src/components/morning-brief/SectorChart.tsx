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

  // Use real chart_data from the API if available
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
    <div className="rounded-lg border border-gray-700 bg-gray-800/30 p-4">
      <h3 className="mb-4 font-semibold text-white">1-Month Sector Performance (Normalized)</h3>
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="day" stroke="#9ca3af" style={{ fontSize: '11px' }} />
            <YAxis stroke="#9ca3af" style={{ fontSize: '11px' }} domain={['auto', 'auto']} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1a1d27', border: '1px solid #2d3148', borderRadius: '8px' }}
              labelStyle={{ color: '#e5e7eb' }}
              formatter={(value: number) => [`${value.toFixed(2)}%`, '']}
            />
            <Legend wrapperStyle={{ paddingTop: '12px' }} />
            {displaySectors.map((sector: any) => (
              <Line
                key={sector.ticker}
                type="monotone"
                dataKey={sector.ticker}
                stroke={sectorColors[sector.ticker] || '#9ca3af'}
                dot={false}
                strokeWidth={2}
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
