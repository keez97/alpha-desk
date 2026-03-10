import { useState } from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { SentimentHistoryPoint } from '../../lib/api';
import { classNames } from '../../lib/utils';

interface SentimentChartProps {
  data: SentimentHistoryPoint[];
  isLoading?: boolean;
}

type Period = '7d' | '30d' | '90d';

export function SentimentChart({ data, isLoading }: SentimentChartProps) {
  const [period, setPeriod] = useState<Period>('30d');

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
        <div className="text-xs text-neutral-500">No sentiment history available</div>
      </div>
    );
  }

  // Filter data by period
  const periodDays: Record<Period, number> = {
    '7d': 7,
    '30d': 30,
    '90d': 90,
  };

  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - periodDays[period]);

  const filteredData = data.filter(d => new Date(d.date) >= cutoffDate);

  // Identify divergence periods (price and sentiment moving opposite directions)
  const divergencePeriods: Array<{ start: number; end: number }> = [];
  if (filteredData.length > 1) {
    for (let i = 1; i < filteredData.length; i++) {
      const prev = filteredData[i - 1];
      const curr = filteredData[i];

      const priceChange = (curr.price || 0) - (prev.price || 0);
      const sentimentChange = curr.score - prev.score;

      // Divergence: opposite directions and both significant
      if (
        priceChange * sentimentChange < 0 &&
        Math.abs(priceChange) > 0.01 &&
        Math.abs(sentimentChange) > 0.05
      ) {
        if (divergencePeriods.length === 0 || divergencePeriods[divergencePeriods.length - 1].end !== i - 1) {
          divergencePeriods.push({ start: i - 1, end: i });
        } else {
          divergencePeriods[divergencePeriods.length - 1].end = i;
        }
      }
    }
  }

  // Normalize price to -1 to 1 range for comparison
  const priceMin = Math.min(...filteredData.map(d => d.price || 0));
  const priceMax = Math.max(...filteredData.map(d => d.price || 0));
  const priceRange = priceMax - priceMin || 1;

  const normalizedData = filteredData.map(d => ({
    ...d,
    normalizedPrice: ((d.price || 0) - priceMin) / priceRange * 2 - 1,
  }));

  return (
    <div className="w-full space-y-3">
      {/* Period Selector */}
      <div className="flex gap-2">
        {(['7d', '30d', '90d'] as Period[]).map(p => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={classNames(
              'px-3 py-1 rounded text-xs font-medium transition-colors',
              period === p
                ? 'bg-neutral-700 text-white'
                : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700'
            )}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={normalizedData} margin={{ top: 10, right: 20, left: 0, bottom: 30 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#737373', fontSize: 10 }}
            axisLine={{ stroke: '#404040' }}
            tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          />
          <YAxis
            yAxisId="left"
            tick={{ fill: '#737373', fontSize: 10 }}
            axisLine={{ stroke: '#404040' }}
            label={{ value: 'Price (normalized)', angle: -90, position: 'insideLeft' }}
            domain={[-1, 1]}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fill: '#737373', fontSize: 10 }}
            axisLine={{ stroke: '#404040' }}
            label={{ value: 'Sentiment Score', angle: 90, position: 'insideRight' }}
            domain={[-1, 1]}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0a0a0a',
              border: '1px solid #262626',
              borderRadius: '4px',
            }}
            labelStyle={{ color: '#e5e5e5' }}
            formatter={(value) => {
              if (typeof value === 'number') return value.toFixed(2);
              return value;
            }}
          />
          <Legend wrapperStyle={{ paddingTop: '12px', fontSize: '11px' }} />

          {/* Divergence Background Shading */}
          {divergencePeriods.map((period, idx) => (
            <rect
              key={`divergence-${idx}`}
              x="0"
              y="0"
              width="100%"
              height="100%"
              opacity={0.05}
              fill="#f59e0b"
            />
          ))}

          <Line
            yAxisId="left"
            type="monotone"
            dataKey="normalizedPrice"
            stroke="#6366f1"
            strokeWidth={2}
            name="Price (normalized)"
            dot={false}
          />
          <Area
            yAxisId="right"
            type="monotone"
            dataKey="score"
            fill="#22c55e"
            stroke="#22c55e"
            strokeWidth={2}
            name="Sentiment Score"
            fillOpacity={0.1}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
