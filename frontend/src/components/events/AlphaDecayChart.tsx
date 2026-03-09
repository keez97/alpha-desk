import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { AlphaDecayWindow } from '../../lib/api';

interface AlphaDecayChartProps {
  data: AlphaDecayWindow[];
}

const WINDOW_LABELS: Record<string, string> = {
  '+1d': '+1 Day',
  '+5d': '+5 Days',
  '+21d': '+21 Days',
  '+63d': '+63 Days',
  '1d': '+1 Day',
  '5d': '+5 Days',
  '21d': '+21 Days',
  '63d': '+63 Days',
};

export function AlphaDecayChart({ data }: AlphaDecayChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="border border-neutral-800 rounded p-4 text-center">
        <p className="text-xs text-neutral-500">No alpha decay data available</p>
      </div>
    );
  }

  const chartData = data.map((w) => ({
    name: WINDOW_LABELS[w.window_type] || w.window_type,
    abnormal_return: parseFloat((w.abnormal_return * 100).toFixed(2)),
    confidence: parseFloat((w.confidence * 100).toFixed(0)),
  }));

  const getBarColor = (value: number) => (value >= 0 ? '#22c55e' : '#ef4444');

  return (
    <div className="border border-neutral-800 rounded p-3">
      <h3 className="text-xs font-semibold text-neutral-300 mb-3">Alpha Decay Windows</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
          <XAxis dataKey="name" tick={{ fill: '#a3a3a3', fontSize: 10 }} />
          <YAxis tick={{ fill: '#a3a3a3', fontSize: 10 }} label={{ value: 'Return (%)', angle: -90, position: 'insideLeft' }} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0a0a0a',
              border: '1px solid #404040',
              borderRadius: '4px',
              padding: '8px',
            }}
            labelStyle={{ color: '#d4d4d4' }}
            formatter={(value: any, name: string) => {
              if (name === 'abnormal_return') {
                return [`${(value as number).toFixed(2)}%`, 'Abnormal Return'];
              }
              if (name === 'confidence') {
                return [`${(value as number).toFixed(0)}%`, 'Confidence'];
              }
              return [value, name];
            }}
          />
          <Bar dataKey="abnormal_return" name="abnormal_return">
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(entry.abnormal_return)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="grid grid-cols-2 gap-2 mt-3 text-[10px]">
        {chartData.map((item, idx) => (
          <div key={idx} className="flex justify-between border border-neutral-800 rounded p-1.5">
            <span className="text-neutral-400">{item.name}</span>
            <div className="flex gap-1">
              <span className={item.abnormal_return >= 0 ? 'text-green-500' : 'text-red-500'}>
                {item.abnormal_return >= 0 ? '+' : ''}{item.abnormal_return.toFixed(2)}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
