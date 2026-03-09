import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { PortfolioAnalysis } from '../../lib/api';

interface MonteCarloChartProps {
  analysis: PortfolioAnalysis;
}

export function MonteCarloChart({ analysis }: MonteCarloChartProps) {
  const { paths, stats } = analysis.monteCarlo;

  // Create data for percentile bands
  const maxPath = Math.max(...paths.map(p => p.length));
  const data = Array.from({ length: maxPath }, (_, i) => {
    const values = paths
      .map(path => path[i] || path[path.length - 1])
      .filter(v => v !== undefined);

    values.sort((a, b) => a - b);

    const p5Idx = Math.floor(values.length * 0.05);
    const p25Idx = Math.floor(values.length * 0.25);
    const p50Idx = Math.floor(values.length * 0.5);
    const p75Idx = Math.floor(values.length * 0.75);
    const p95Idx = Math.floor(values.length * 0.95);

    return {
      day: i,
      p5: values[p5Idx] || values[0],
      p25: values[p25Idx] || values[0],
      p50: values[p50Idx] || values[0],
      p75: values[p75Idx] || values[0],
      p95: values[p95Idx] || values[0],
    };
  });

  return (
    <div className="space-y-4">
      <div className="h-96 w-full rounded-lg border border-gray-700 bg-gray-800/30 p-4">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="day" stroke="#9ca3af" style={{ fontSize: '12px' }} />
            <YAxis stroke="#9ca3af" style={{ fontSize: '12px' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1a1d27',
                border: '1px solid #2d3148',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#e5e7eb' }}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="p5"
              fill="#ef4444"
              stroke="#ef4444"
              fillOpacity={0.1}
              name="5th Percentile"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="p25"
              fill="#f59e0b"
              stroke="#f59e0b"
              fillOpacity={0.2}
              name="25th Percentile"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="p50"
              fill="#3b82f6"
              stroke="#3b82f6"
              fillOpacity={0.3}
              name="Median"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="p75"
              fill="#10b981"
              stroke="#10b981"
              fillOpacity={0.2}
              name="75th Percentile"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="p95"
              fill="#10b981"
              stroke="#10b981"
              fillOpacity={0.1}
              name="95th Percentile"
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-gray-700 bg-gray-800/30 p-4">
          <p className="text-xs text-gray-500 mb-2">Mean Final Value</p>
          <p className="text-2xl font-semibold text-green-400 font-mono">${stats.mean.toFixed(0)}</p>
        </div>
        <div className="rounded-lg border border-gray-700 bg-gray-800/30 p-4">
          <p className="text-xs text-gray-500 mb-2">Median Final Value</p>
          <p className="text-2xl font-semibold text-blue-400 font-mono">${stats.median.toFixed(0)}</p>
        </div>
        <div className="rounded-lg border border-gray-700 bg-gray-800/30 p-4">
          <p className="text-xs text-gray-500 mb-2">Standard Deviation</p>
          <p className="text-2xl font-semibold text-yellow-400 font-mono">${stats.std.toFixed(0)}</p>
        </div>
      </div>
    </div>
  );
}
