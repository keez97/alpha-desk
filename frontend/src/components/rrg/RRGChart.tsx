import Plotly from 'react-plotly.js';
import { motion } from 'framer-motion';
import type { RRGData } from '../../lib/api';
import { chartColors } from '../../styles/tokens';

interface RRGChartProps {
  data: RRGData;
}

export function RRGChart({ data }: RRGChartProps) {
  const getQuadrantColor = (rsRatio: number, rsMomentum: number): string => {
    if (rsRatio >= 100 && rsMomentum >= 100) return chartColors.leading;
    if (rsRatio >= 100 && rsMomentum < 100) return chartColors.weakening;
    if (rsRatio < 100 && rsMomentum < 100) return chartColors.lagging;
    return chartColors.improving;
  };

  const plotData = data.sectors.map((sector) => ({
    name: sector.name,
    x: [sector.rsRatio],
    y: [sector.rsMomentum],
    mode: 'markers+text' as const,
    marker: {
      size: Math.max(10, Math.min(30, Math.sqrt(sector.volume) / 100)),
      color: getQuadrantColor(sector.rsRatio, sector.rsMomentum),
      opacity: 0.7,
      line: { color: 'white', width: 1 },
    },
    text: [sector.ticker],
    textposition: 'middle center' as const,
    textfont: { color: 'white', size: 10 },
    hovertemplate: `${sector.name}<br>RS-Ratio: %{x:.2f}<br>RS-Momentum: %{y:.2f}<br>Volume: ${(sector.volume / 1e6).toFixed(1)}M<extra></extra>`,
  }));

  const shapes = [
    // Center lines
    {
      type: 'line' as const,
      x0: 100,
      x1: 100,
      y0: 50,
      y1: 150,
      line: { color: '#9ca3af', width: 1, dash: 'dash' as const },
    },
    {
      type: 'line' as const,
      x0: 50,
      x1: 150,
      y0: 100,
      y1: 100,
      line: { color: '#9ca3af', width: 1, dash: 'dash' as const },
    },
  ];

  const annotations = [
    {
      text: 'Leading',
      x: 120,
      y: 120,
      showarrow: false,
      font: { color: chartColors.leading, size: 14 },
      opacity: 0.5,
    },
    {
      text: 'Weakening',
      x: 120,
      y: 80,
      showarrow: false,
      font: { color: chartColors.weakening, size: 14 },
      opacity: 0.5,
    },
    {
      text: 'Lagging',
      x: 80,
      y: 80,
      showarrow: false,
      font: { color: chartColors.lagging, size: 14 },
      opacity: 0.5,
    },
    {
      text: 'Improving',
      x: 80,
      y: 120,
      showarrow: false,
      font: { color: chartColors.improving, size: 14 },
      opacity: 0.5,
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="rounded-lg border border-gray-700 bg-gray-800/30 p-4"
    >
      <Plotly
        data={plotData as any}
        layout={{
          width: 800,
          height: 600,
          xaxis: {
            title: 'RS-Ratio',
            zeroline: false,
            range: [50, 150],
          },
          yaxis: {
            title: 'RS-Momentum',
            zeroline: false,
            range: [50, 150],
          },
          shapes,
          annotations,
          margin: { l: 60, r: 60, t: 40, b: 60 },
          paper_bgcolor: '#1a1d27',
          plot_bgcolor: '#252836',
          font: { color: '#e5e7eb' },
          showlegend: false,
          hovermode: 'closest',
        } as any}
        config={{ responsive: true }}
      />
    </motion.div>
  );
}
