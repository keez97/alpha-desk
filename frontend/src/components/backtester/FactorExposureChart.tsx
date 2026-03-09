import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { BacktestResult } from '../../lib/api';

interface FactorExposureChartProps {
  results: BacktestResult;
}

const factorColors: Record<string, string> = {
  'MKT-RF': '#d4d4d8',
  'SMB': '#a1a1a1',
  'HML': '#737373',
  'RMW': '#525252',
  'CMA': '#404040',
};

export function FactorExposureChart({ results }: FactorExposureChartProps) {
  const data = results.factor_exposures || [];

  if (!data || data.length === 0) {
    return (
      <div className="border border-neutral-800 rounded p-4 bg-black">
        <p className="text-xs text-neutral-500">No factor exposure data available</p>
      </div>
    );
  }

  // Format data for chart
  const chartData = data.map((d: any) => ({
    date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', year: '2-digit' }),
    ...Object.entries(d)
      .filter(([key]) => key !== 'date')
      .reduce((acc, [key, value]) => ({ ...acc, [key]: Number(value) }), {}),
  }));

  // Get factor names (exclude 'date')
  const factors = Object.keys(chartData[0] || {}).filter((k) => k !== 'date' && k !== 'undefined');

  return (
    <div className="border border-neutral-800 rounded p-4 space-y-3 bg-black">
      <div>
        <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">Factor Exposures</span>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 30 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
          <XAxis
            dataKey="date"
            stroke="#737373"
            style={{ fontSize: '10px' }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis stroke="#737373" style={{ fontSize: '10px' }} label={{ value: 'Beta', angle: -90, position: 'insideLeft' }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#0a0a0a', border: '1px solid #404040' }}
            labelStyle={{ color: '#d4d4d8' }}
            formatter={(value: number) => [value.toFixed(3), '']}
          />
          <Legend wrapperStyle={{ paddingTop: '20px' }} />
          {factors.map((factor) => (
            <Area
              key={factor}
              type="monotone"
              dataKey={factor}
              stackId="1"
              stroke={factorColors[factor] || '#d4d4d8'}
              fill={factorColors[factor] || '#d4d4d8'}
              fillOpacity={0.4}
              name={factor}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
