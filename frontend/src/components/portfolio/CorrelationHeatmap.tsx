import Plotly from 'react-plotly.js';
import type { PortfolioAnalysis } from '../../lib/api';

interface CorrelationHeatmapProps {
  analysis: PortfolioAnalysis;
}

export function CorrelationHeatmap({ analysis }: CorrelationHeatmapProps) {
  const tickers = Object.keys(analysis.maxSharpe.weights);

  return (
    <div className="border border-neutral-800 rounded p-4">
      <span className="text-xs font-medium text-neutral-300 mb-3 block">Correlation Matrix</span>
      <Plotly
        data={[
          {
            z: analysis.correlation,
            x: tickers,
            y: tickers,
            type: 'heatmap' as const,
            colorscale: [
              [0, '#525252'],
              [0.5, '#0a0a0a'],
              [1, '#ef4444'],
            ],
            colorbar: { tickvals: [-1, 0, 1], ticktext: ['-1', '0', '1'], tickfont: { color: '#525252', size: 10 } },
          } as any,
        ]}
        layout={{
          width: 600,
          height: 600,
          margin: { l: 80, r: 80, t: 30, b: 80 },
          paper_bgcolor: '#000000',
          plot_bgcolor: '#0a0a0a',
          font: { color: '#a3a3a3', size: 11, family: 'Inter, system-ui, sans-serif' },
          xaxis: { side: 'bottom', gridcolor: '#1f1f1f' },
          yaxis: { gridcolor: '#1f1f1f' },
        } as any}
        config={{ responsive: true }}
      />
    </div>
  );
}
