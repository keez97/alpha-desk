import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { PortfolioAnalysis } from '../../lib/api';

interface MonteCarloChartProps {
  analysis: PortfolioAnalysis;
}

export function MonteCarloChart({ analysis }: MonteCarloChartProps) {
  const { paths, stats } = analysis.monteCarlo;

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
    <div className="space-y-2">
      <div className="h-80 w-full border border-neutral-800 rounded p-3">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f1f1f" />
            <XAxis dataKey="day" stroke="#404040" style={{ fontSize: '10px' }} />
            <YAxis stroke="#404040" style={{ fontSize: '10px' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0a0a0a',
                border: '1px solid #262626',
                borderRadius: '4px',
                fontSize: '11px',
              }}
              labelStyle={{ color: '#a3a3a3' }}
            />
            <Legend
              wrapperStyle={{ fontSize: '10px', color: '#525252' }}
            />
            <Area
              type="monotone"
              dataKey="p5"
              fill="#ef4444"
              stroke="#ef4444"
              fillOpacity={0.05}
              strokeWidth={1}
              name="5th"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="p25"
              fill="#a3a3a3"
              stroke="#a3a3a3"
              fillOpacity={0.08}
              strokeWidth={1}
              name="25th"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="p50"
              fill="#d4d4d4"
              stroke="#d4d4d4"
              fillOpacity={0.1}
              strokeWidth={1.5}
              name="Median"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="p75"
              fill="#a3a3a3"
              stroke="#a3a3a3"
              fillOpacity={0.08}
              strokeWidth={1}
              name="75th"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="p95"
              fill="#22c55e"
              stroke="#22c55e"
              fillOpacity={0.05}
              strokeWidth={1}
              name="95th"
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid gap-2 grid-cols-3">
        <div className="border border-neutral-800 rounded px-3 py-2">
          <p className="text-[10px] text-neutral-600 uppercase tracking-wider">Mean</p>
          <p className="text-sm font-mono text-emerald-400">${stats.mean.toFixed(0)}</p>
        </div>
        <div className="border border-neutral-800 rounded px-3 py-2">
          <p className="text-[10px] text-neutral-600 uppercase tracking-wider">Median</p>
          <p className="text-sm font-mono text-neutral-200">${stats.median.toFixed(0)}</p>
        </div>
        <div className="border border-neutral-800 rounded px-3 py-2">
          <p className="text-[10px] text-neutral-600 uppercase tracking-wider">Std Dev</p>
          <p className="text-sm font-mono text-neutral-400">${stats.std.toFixed(0)}</p>
        </div>
      </div>
    </div>
  );
}
