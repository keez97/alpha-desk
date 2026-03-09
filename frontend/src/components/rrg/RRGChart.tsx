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

  // Calculate dynamic axis ranges from data
  const allX = data.sectors.map((s) => s.rsRatio);
  const allY = data.sectors.map((s) => s.rsMomentum);
  const padX = Math.max(5, (Math.max(...allX) - Math.min(...allX)) * 0.15);
  const padY = Math.max(5, (Math.max(...allY) - Math.min(...allY)) * 0.15);
  const xMin = Math.min(Math.min(...allX) - padX, 95);
  const xMax = Math.max(Math.max(...allX) + padX, 105);
  const yMin = Math.min(Math.min(...allY) - padY, 95);
  const yMax = Math.max(Math.max(...allY) + padY, 105);

  const plotData = data.sectors.map((sector) => ({
    name: sector.name,
    x: [sector.rsRatio],
    y: [sector.rsMomentum],
    mode: 'markers+text' as const,
    marker: {
      size: 14,
      color: getQuadrantColor(sector.rsRatio, sector.rsMomentum),
      opacity: 0.85,
      line: { color: 'white', width: 1 },
    },
    text: [sector.ticker],
    textposition: 'top center' as const,
    textfont: { color: 'white', size: 10 },
    hovertemplate: `${sector.name}<br>RS-Ratio: %{x:.2f}<br>RS-Momentum: %{y:.2f}<extra></extra>`,
  }));

  // Add trail lines for each sector
  const trailTraces = data.sectors.map((sector) => ({
    x: sector.history.slice(-10).map((h) => h.rsRatio),
    y: sector.history.slice(-10).map((h) => h.rsMomentum),
    mode: 'lines' as const,
    line: {
      color: getQuadrantColor(sector.rsRatio, sector.rsMomentum),
      width: 1.5,
      dash: 'dot' as const,
    },
    showlegend: false,
    hoverinfo: 'skip' as const,
  }));

  const shapes = [
    {
      type: 'line' as const,
      x0: 100, x1: 100, y0: yMin, y1: yMax,
      line: { color: '#9ca3af', width: 1, dash: 'dash' as const },
    },
    {
      type: 'line' as const,
      x0: xMin, x1: xMax, y0: 100, y1: 100,
      line: { color: '#9ca3af', width: 1, dash: 'dash' as const },
    },
  ];

  // Place labels in the center of each visible quadrant
  const midXRight = (100 + xMax) / 2;
  const midXLeft = (xMin + 100) / 2;
  const midYTop = (100 + yMax) / 2;
  const midYBot = (yMin + 100) / 2;

  const annotations = [
    { text: 'Leading', x: midXRight, y: midYTop, showarrow: false, font: { color: chartColors.leading, size: 14 }, opacity: 0.4 },
    { text: 'Weakening', x: midXRight, y: midYBot, showarrow: false, font: { color: chartColors.weakening, size: 14 }, opacity: 0.4 },
    { text: 'Lagging', x: midXLeft, y: midYBot, showarrow: false, font: { color: chartColors.lagging, size: 14 }, opacity: 0.4 },
    { text: 'Improving', x: midXLeft, y: midYTop, showarrow: false, font: { color: chartColors.improving, size: 14 }, opacity: 0.4 },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="rounded-lg border border-gray-700 bg-gray-800/30 p-4"
    >
      <Plotly
        data={[...plotData, ...trailTraces] as any}
        layout={{
          autosize: true,
          height: 600,
          xaxis: {
            title: 'RS-Ratio',
            zeroline: false,
            range: [xMin, xMax],
          },
          yaxis: {
            title: 'RS-Momentum',
            zeroline: false,
            range: [yMin, yMax],
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
        style={{ width: '100%' }}
      />
    </motion.div>
  );
}
