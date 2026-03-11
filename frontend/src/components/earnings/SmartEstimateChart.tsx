import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { EarningsHistory } from '../../lib/api';

interface SmartEstimateChartProps {
  data: EarningsHistory[];
  isLoading?: boolean;
}

export function SmartEstimateChart({ data, isLoading }: SmartEstimateChartProps) {
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
        <div className="text-xs text-neutral-500">No historical data available</div>
      </div>
    );
  }

  // Format data for chart
  const chartData = data.map((item) => ({
    quarter: item.fiscal_quarter,
    consensus: item.consensus_eps,
    smart_estimate: item.smart_estimate_eps,
    actual: item.actual_eps,
    surprised: item.surprise_pct > 0,
  }));

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 30 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
          <XAxis
            dataKey="quarter"
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
            formatter={(value) => (typeof value === 'number' ? `$${value.toFixed(2)}` : value)}
          />
          <Legend
            wrapperStyle={{ paddingTop: '12px', fontSize: '11px' }}
            iconType="square"
          />
          <Bar dataKey="consensus" fill="#525252" name="Consensus" />
          <Bar dataKey="smart_estimate" fill="#d4d4d4" name="SmartEstimate" />
          <Bar dataKey="actual" fill="#22c55e" name="Actual" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
