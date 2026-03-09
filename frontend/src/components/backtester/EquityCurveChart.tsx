import {
  LineChart,
  Line,
  ComposedChart,
  Area,
  AreaChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { BacktestResult } from '../../lib/api';

interface EquityCurveChartProps {
  results: BacktestResult;
}

export function EquityCurveChart({ results }: EquityCurveChartProps) {
  const data = results.equity_curve || [];

  if (!data || data.length === 0) {
    return (
      <div className="border border-neutral-800 rounded p-4 bg-black">
        <p className="text-xs text-neutral-500">No equity curve data available</p>
      </div>
    );
  }

  // Combine strategy and drawdown on same chart
  const chartData = data.map((d) => ({
    date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', year: '2-digit' }),
    strategy: Math.round(d.strategy * 10000) / 10000, // Scale to percentage
    benchmark: Math.round(d.benchmark * 10000) / 10000,
    drawdown: d.drawdown * 100, // Convert to percentage
  }));

  return (
    <div className="border border-neutral-800 rounded p-4 space-y-3 bg-black">
      <div>
        <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">Equity Curve</span>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 30 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
          <XAxis
            dataKey="date"
            stroke="#737373"
            style={{ fontSize: '10px' }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis
            yAxisId="left"
            stroke="#737373"
            style={{ fontSize: '10px' }}
            label={{ value: 'Return', angle: -90, position: 'insideLeft' }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="#737373"
            style={{ fontSize: '10px' }}
            label={{ value: 'Drawdown %', angle: 90, position: 'insideRight' }}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#0a0a0a', border: '1px solid #404040' }}
            labelStyle={{ color: '#d4d4d8' }}
            formatter={(value: number) => [value.toFixed(4), '']}
          />
          <Legend wrapperStyle={{ paddingTop: '20px' }} />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="strategy"
            stroke="#e5e7eb"
            dot={false}
            strokeWidth={1.5}
            name="Strategy"
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="benchmark"
            stroke="#737373"
            dot={false}
            strokeWidth={1}
            strokeDasharray="5 5"
            name="Benchmark"
          />
          <Area
            yAxisId="right"
            type="monotone"
            dataKey="drawdown"
            fill="#dc2626"
            stroke="none"
            fillOpacity={0.2}
            name="Drawdown %"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
