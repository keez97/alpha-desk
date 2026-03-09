import type { PortfolioAnalysis } from '../../lib/api';
import { formatPercent } from '../../lib/utils';

interface OptimisationTableProps {
  analysis: PortfolioAnalysis;
}

export function OptimisationTable({ analysis }: OptimisationTableProps) {
  const maxSharpe = analysis.maxSharpe;
  const maxVariance = analysis.maxVariance;

  const tickers = Object.keys(maxSharpe.weights).sort();

  return (
    <div className="space-y-2">
      {/* Max Sharpe */}
      <div className="border border-neutral-800 rounded overflow-hidden">
        <div className="px-3 py-2 border-b border-neutral-800">
          <span className="text-xs font-medium text-neutral-300">Max Sharpe Ratio</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-neutral-800">
                <th className="px-3 py-1.5 text-left text-[10px] text-neutral-500 uppercase tracking-wider font-medium">Ticker</th>
                <th className="px-3 py-1.5 text-right text-[10px] text-neutral-500 uppercase tracking-wider font-medium">Weight</th>
              </tr>
            </thead>
            <tbody>
              {tickers.map((ticker) => (
                <tr key={ticker} className="border-b border-neutral-900 hover:bg-neutral-900/50">
                  <td className="px-3 py-1.5 font-mono text-neutral-300">{ticker}</td>
                  <td className="px-3 py-1.5 text-right font-mono text-neutral-300">
                    {formatPercent(maxSharpe.weights[ticker] * 100)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="border-t border-neutral-800 px-3 py-2 grid grid-cols-3 gap-3">
          <div>
            <p className="text-[10px] text-neutral-600 uppercase tracking-wider">Return</p>
            <p className="text-sm font-mono text-emerald-400">{formatPercent(maxSharpe.return)}</p>
          </div>
          <div>
            <p className="text-[10px] text-neutral-600 uppercase tracking-wider">Vol</p>
            <p className="text-sm font-mono text-neutral-300">{formatPercent(maxSharpe.volatility)}</p>
          </div>
          <div>
            <p className="text-[10px] text-neutral-600 uppercase tracking-wider">Sharpe</p>
            <p className="text-sm font-mono text-neutral-200">{maxSharpe.sharpeRatio.toFixed(2)}</p>
          </div>
        </div>
      </div>

      {/* Min Variance */}
      <div className="border border-neutral-800 rounded overflow-hidden">
        <div className="px-3 py-2 border-b border-neutral-800">
          <span className="text-xs font-medium text-neutral-300">Min Variance</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-neutral-800">
                <th className="px-3 py-1.5 text-left text-[10px] text-neutral-500 uppercase tracking-wider font-medium">Ticker</th>
                <th className="px-3 py-1.5 text-right text-[10px] text-neutral-500 uppercase tracking-wider font-medium">Weight</th>
              </tr>
            </thead>
            <tbody>
              {tickers.map((ticker) => (
                <tr key={ticker} className="border-b border-neutral-900 hover:bg-neutral-900/50">
                  <td className="px-3 py-1.5 font-mono text-neutral-300">{ticker}</td>
                  <td className="px-3 py-1.5 text-right font-mono text-neutral-300">
                    {formatPercent(maxVariance.weights[ticker] * 100)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="border-t border-neutral-800 px-3 py-2 grid grid-cols-3 gap-3">
          <div>
            <p className="text-[10px] text-neutral-600 uppercase tracking-wider">Return</p>
            <p className="text-sm font-mono text-emerald-400">{formatPercent(maxVariance.return)}</p>
          </div>
          <div>
            <p className="text-[10px] text-neutral-600 uppercase tracking-wider">Vol</p>
            <p className="text-sm font-mono text-neutral-300">{formatPercent(maxVariance.volatility)}</p>
          </div>
          <div>
            <p className="text-[10px] text-neutral-600 uppercase tracking-wider">Sharpe</p>
            <p className="text-sm font-mono text-neutral-200">{maxVariance.sharpeRatio.toFixed(2)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
