import type { MatrixResponse } from '../../hooks/useConfluence';

interface SignalMatrixProps {
  data: MatrixResponse;
  isLoading: boolean;
}

const getQuadrantColor = (quadrant: string): string => {
  switch (quadrant) {
    case 'Strengthening':
      return 'bg-green-500/10 border-green-500/30 text-green-400';
    case 'Weakening':
      return 'bg-red-500/10 border-red-500/30 text-red-400';
    case 'Recovering':
      return 'bg-blue-500/10 border-blue-500/30 text-blue-400';
    case 'Deteriorating':
      return 'bg-orange-500/10 border-orange-500/30 text-orange-400';
    default:
      return 'bg-neutral-500/10 border-neutral-500/30 text-neutral-400';
  }
};

const getConfluenceColor = (confluence: string): string => {
  switch (confluence) {
    case 'bullish':
      return 'bg-green-500/20 text-green-400';
    case 'bearish':
      return 'bg-red-500/20 text-red-400';
    default:
      return 'bg-neutral-500/20 text-neutral-400';
  }
};

export function SignalMatrix({ data, isLoading }: SignalMatrixProps) {
  if (isLoading) {
    return (
      <div className="border border-neutral-800 rounded-lg p-6 bg-neutral-900/50">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-neutral-700 border-t-neutral-400 rounded-full animate-spin mx-auto mb-2" />
            <p className="text-sm text-neutral-500">Loading signal matrix...</p>
          </div>
        </div>
      </div>
    );
  }

  const matrix = data.matrix || [];

  if (matrix.length === 0) {
    return (
      <div className="border border-neutral-800 rounded-lg p-8 bg-neutral-900/50 text-center">
        <p className="text-sm text-neutral-500">No matrix data available</p>
      </div>
    );
  }

  return (
    <div className="border border-neutral-800 rounded-lg overflow-hidden bg-neutral-900/50">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-neutral-800 bg-neutral-900/80">
              <th className="px-4 py-3 text-left text-neutral-400 font-semibold">Sector</th>
              <th className="px-4 py-3 text-center text-neutral-400 font-semibold">RRG</th>
              <th className="px-4 py-3 text-center text-neutral-400 font-semibold">Momentum</th>
              <th className="px-4 py-3 text-center text-neutral-400 font-semibold">Macro</th>
              <th className="px-4 py-3 text-center text-neutral-400 font-semibold">1D %</th>
              <th className="px-4 py-3 text-center text-neutral-400 font-semibold">Confluence</th>
              <th className="px-4 py-3 text-center text-neutral-400 font-semibold">Signals</th>
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, idx) => (
              <tr
                key={idx}
                className="border-b border-neutral-800/50 hover:bg-neutral-800/30 transition-colors"
              >
                <td className="px-4 py-3 text-neutral-200 font-medium">
                  <div>
                    <div className="font-semibold">{row.ticker}</div>
                    <div className="text-neutral-500 text-xs mt-1">{row.name}</div>
                  </div>
                </td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={`inline-block px-2 py-1 rounded border text-xs font-medium ${getQuadrantColor(
                      row.rrg.quadrant
                    )}`}
                  >
                    {row.rrg.quadrant.split(' ')[0]}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={`font-semibold ${
                      row.rrg.momentum > 0 ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    {row.rrg.momentum.toFixed(1)}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <div className="text-neutral-400 text-xs max-w-[100px] mx-auto">
                    {row.macro.sectorImpact.split(' ')[0]}
                  </div>
                </td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={`font-semibold ${
                      row.performance.change1d > 0 ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    {row.performance.change1d > 0 ? '+' : ''}
                    {row.performance.change1d.toFixed(2)}%
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={`inline-block px-2 py-1 rounded text-xs font-medium capitalize ${getConfluenceColor(
                      row.confluence
                    )}`}
                  >
                    {row.confluence}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <div className="flex justify-center gap-1">
                    {Array.from({ length: Math.max(row.signalCount, 0) }).map((_, i) => (
                      <div
                        key={i}
                        className={`w-2 h-2 rounded-full ${
                          row.confluence === 'bullish'
                            ? 'bg-green-500'
                            : row.confluence === 'bearish'
                              ? 'bg-red-500'
                              : 'bg-neutral-600'
                        }`}
                      />
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="border-t border-neutral-800 px-4 py-3 bg-neutral-900/80">
        <p className="text-xs text-neutral-500 font-semibold mb-2">RRG Quadrants:</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500/20 border border-green-500/30 rounded" />
            <span className="text-neutral-400">Strengthening</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-red-500/20 border border-red-500/30 rounded" />
            <span className="text-neutral-400">Weakening</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-500/20 border border-blue-500/30 rounded" />
            <span className="text-neutral-400">Recovering</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-orange-500/20 border border-orange-500/30 rounded" />
            <span className="text-neutral-400">Deteriorating</span>
          </div>
        </div>
      </div>
    </div>
  );
}
