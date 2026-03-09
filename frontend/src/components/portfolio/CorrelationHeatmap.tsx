import Plotly from 'react-plotly.js';
import type { PortfolioAnalysis } from '../../lib/api';

interface CorrelationHeatmapProps {
  analysis: PortfolioAnalysis;
}

export function CorrelationHeatmap({ analysis }: CorrelationHeatmapProps) {
  const tickers = Object.keys(analysis.maxSharpe.weights);

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/30 p-4">
      <h3 className="mb-4 font-semibold text-white">Correlation Matrix</h3>
      <Plotly
        data={[
          {
            z: analysis.correlation,
            x: tickers,
            y: tickers,
            type: 'heatmap' as const,
            colorscale: [
              [0, '#3b82f6'],
              [0.5, '#ffffff'],
              [1, '#ef4444'],
            ],
            colorbar: { tickvals: [-1, 0, 1], ticktext: ['-1', '0', '1'] },
          } as any,
        ]}
        layout={{
          width: 600,
          height: 600,
          margin: { l: 100, r: 100, t: 50, b: 100 },
          paper_bgcolor: '#1a1d27',
          plot_bgcolor: '#252836',
          font: { color: '#e5e7eb' },
          xaxis: { side: 'bottom' },
        } as any}
        config={{ responsive: true }}
      />
    </div>
  );
}
