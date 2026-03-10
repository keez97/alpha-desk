import type { BacktestResult } from '../../lib/api';

interface CorrelationMatrixProps {
  results: BacktestResult;
}

const factors = ['MKT-RF', 'SMB', 'HML', 'RMW', 'CMA'];

export function CorrelationMatrix({ results }: CorrelationMatrixProps) {
  const matrix = results.correlation_matrix || [];

  if (!matrix || matrix.length === 0) {
    return (
      <div className="border border-neutral-800 rounded p-4 bg-black">
        <p className="text-xs text-neutral-500">No correlation data available</p>
      </div>
    );
  }

  const getColor = (value: number) => {
    // Value between -1 and 1
    if (value < -0.5) return 'bg-red-900/50';
    if (value < 0) return 'bg-red-800/30';
    if (value < 0.5) return 'bg-neutral-800/50';
    if (value < 1) return 'bg-green-900/30';
    return 'bg-green-900/50';
  };

  const getTextColor = (value: number) => {
    if (value < 0) return 'text-red-400';
    if (value > 0.5) return 'text-green-400';
    return 'text-neutral-400';
  };

  return (
    <div className="border border-neutral-800 rounded p-4 space-y-3 bg-black">
      <div>
        <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">Correlation Matrix</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-[10px]">
          <thead>
            <tr>
              <th className="border border-neutral-800 p-2 bg-neutral-900 text-left text-neutral-500 font-medium uppercase tracking-wider">
                Factor
              </th>
              {factors.map((f) => (
                <th
                  key={f}
                  className="border border-neutral-800 p-2 bg-neutral-900 text-center text-neutral-500 font-medium uppercase tracking-wider"
                >
                  {f}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, i) => (
              <tr key={i}>
                <td className="border border-neutral-800 p-2 bg-neutral-900/50 text-neutral-400 font-medium uppercase tracking-wider">
                  {factors[i]}
                </td>
                {row.map((value, j) => (
                  <td
                    key={j}
                    className={`border border-neutral-800 p-2 text-center font-mono ${getColor(value)} ${getTextColor(value)}`}
                  >
                    {value.toFixed(3)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
