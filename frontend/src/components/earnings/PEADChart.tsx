import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { PEADData } from '../../lib/api';

interface PEADChartProps {
  data: PEADData[];
  isLoading?: boolean;
}

export function PEADChart({ data, isLoading }: PEADChartProps) {
  if (isLoading) {
    return (
      <div className="w-full h-64 flex items-center justify-center bg-[#0a0a0a] rounded border border-neutral-800">
        <div className="text-xs text-neutral-500">Loading chart...</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="w-full h-64 flex items-center justify-center bg-[#0a0a0a] rounded border border-neutral-800">
        <div className="text-xs text-neutral-500">No PEAD data available</div>
      </div>
    );
  }

  // Aggregate PEAD data by surprise direction
  const positiveQuarters = data.filter((q) => q.surprise_direction === 'positive');
  const negativeQuarters = data.filter((q) => q.surprise_direction === 'negative');

  // Calculate average returns by post-earnings window
  const avgPositive = {
    day: '1D Post-Earnings',
    positive: positiveQuarters.length > 0
      ? positiveQuarters.reduce((sum, q) => sum + q.car_1d, 0) / positiveQuarters.length
      : 0,
    negative: negativeQuarters.length > 0
      ? negativeQuarters.reduce((sum, q) => sum + q.car_1d, 0) / negativeQuarters.length
      : 0,
  };

  const avg5d = {
    day: '5D Post-Earnings',
    positive: positiveQuarters.length > 0
      ? positiveQuarters.reduce((sum, q) => sum + q.car_5d, 0) / positiveQuarters.length
      : 0,
    negative: negativeQuarters.length > 0
      ? negativeQuarters.reduce((sum, q) => sum + q.car_5d, 0) / negativeQuarters.length
      : 0,
  };

  const avg21d = {
    day: '21D Post-Earnings',
    positive: positiveQuarters.length > 0
      ? positiveQuarters.reduce((sum, q) => sum + q.car_21d, 0) / positiveQuarters.length
      : 0,
    negative: negativeQuarters.length > 0
      ? negativeQuarters.reduce((sum, q) => sum + q.car_21d, 0) / negativeQuarters.length
      : 0,
  };

  const avg60d = {
    day: '60D Post-Earnings',
    positive: positiveQuarters.length > 0
      ? positiveQuarters.reduce((sum, q) => sum + q.car_60d, 0) / positiveQuarters.length
      : 0,
    negative: negativeQuarters.length > 0
      ? negativeQuarters.reduce((sum, q) => sum + q.car_60d, 0) / negativeQuarters.length
      : 0,
  };

  const chartData = [avgPositive, avg5d, avg21d, avg60d];

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 30 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
          <XAxis
            dataKey="day"
            tick={{ fill: '#737373', fontSize: 10 }}
            axisLine={{ stroke: '#404040' }}
          />
          <YAxis tick={{ fill: '#737373', fontSize: 10 }} axisLine={{ stroke: '#404040' }} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0a0a0a',
              border: '1px solid #262626',
              borderRadius: '4px',
            }}
            labelStyle={{ color: '#e5e5e5' }}
            formatter={(value) => (typeof value === 'number' ? `${value.toFixed(2)}%` : value)}
          />
          <Legend
            wrapperStyle={{ paddingTop: '12px', fontSize: '11px' }}
            iconType="line"
          />
          <Line
            type="monotone"
            dataKey="positive"
            stroke="#22c55e"
            strokeWidth={2}
            name="Positive Surprises"
            dot={{ fill: '#22c55e', r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="negative"
            stroke="#ef4444"
            strokeWidth={2}
            name="Negative Surprises"
            dot={{ fill: '#ef4444', r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
