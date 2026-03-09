import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useSectors } from '../../hooks/useSectors';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { chartColors } from '../../styles/tokens';

const sectorOrder = [
  { ticker: 'XLK', color: chartColors.leading },
  { ticker: 'XLV', color: '#8b5cf6' },
  { ticker: 'XLF', color: '#06b6d4' },
  { ticker: 'XLI', color: '#ec4899' },
  { ticker: 'XLY', color: '#14b8a6' },
];

export function SectorChart() {
  const { data, isLoading, error, refetch } = useSectors('1M');

  if (isLoading) return <LoadingState message="Loading chart data..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  // Mock normalized data - in production this would come from the API
  const mockData = Array.from({ length: 20 }, (_, i) => {
    const obj: any = { date: `Day ${i + 1}` };
    sectorOrder.forEach((sector) => {
      obj[sector.ticker] = 100 + Math.random() * 5;
    });
    return obj;
  });

  return (
    <div className="h-96 w-full rounded-lg border border-gray-700 bg-gray-800/30 p-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={mockData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="date" stroke="#9ca3af" style={{ fontSize: '12px' }} />
          <YAxis stroke="#9ca3af" style={{ fontSize: '12px' }} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1a1d27',
              border: '1px solid #2d3148',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#e5e7eb' }}
          />
          <Legend wrapperStyle={{ paddingTop: '20px' }} />
          {sectorOrder.map((sector) => (
            <Line
              key={sector.ticker}
              type="monotone"
              dataKey={sector.ticker}
              stroke={sector.color}
              dot={false}
              strokeWidth={2}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
