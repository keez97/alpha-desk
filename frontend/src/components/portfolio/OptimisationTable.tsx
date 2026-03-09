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
    <div className="space-y-4">
      <div className="rounded-lg border border-gray-700 bg-gray-800/30 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-700 bg-gray-800/50">
          <h3 className="font-semibold text-white">Maximum Sharpe Ratio Portfolio</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 bg-gray-800/50">
                <th className="px-4 py-2 text-left text-gray-300 font-semibold">Ticker</th>
                <th className="px-4 py-2 text-right text-gray-300 font-semibold">Weight</th>
              </tr>
            </thead>
            <tbody>
              {tickers.map((ticker) => (
                <tr key={ticker} className="border-b border-gray-800 hover:bg-gray-800/30">
                  <td className="px-4 py-2 font-mono text-gray-300">{ticker}</td>
                  <td className="px-4 py-2 text-right font-mono text-gray-300">
                    {formatPercent(maxSharpe.weights[ticker] * 100)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="border-t border-gray-700 px-4 py-3 grid grid-cols-3 gap-4 bg-gray-800/20">
          <div>
            <p className="text-xs text-gray-500">Expected Return</p>
            <p className="text-lg font-semibold text-green-400">{formatPercent(maxSharpe.return)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Volatility</p>
            <p className="text-lg font-semibold text-gray-300">{formatPercent(maxSharpe.volatility)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Sharpe Ratio</p>
            <p className="text-lg font-semibold text-blue-400">{maxSharpe.sharpeRatio.toFixed(2)}</p>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-gray-700 bg-gray-800/30 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-700 bg-gray-800/50">
          <h3 className="font-semibold text-white">Minimum Variance Portfolio</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 bg-gray-800/50">
                <th className="px-4 py-2 text-left text-gray-300 font-semibold">Ticker</th>
                <th className="px-4 py-2 text-right text-gray-300 font-semibold">Weight</th>
              </tr>
            </thead>
            <tbody>
              {tickers.map((ticker) => (
                <tr key={ticker} className="border-b border-gray-800 hover:bg-gray-800/30">
                  <td className="px-4 py-2 font-mono text-gray-300">{ticker}</td>
                  <td className="px-4 py-2 text-right font-mono text-gray-300">
                    {formatPercent(maxVariance.weights[ticker] * 100)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="border-t border-gray-700 px-4 py-3 grid grid-cols-3 gap-4 bg-gray-800/20">
          <div>
            <p className="text-xs text-gray-500">Expected Return</p>
            <p className="text-lg font-semibold text-green-400">{formatPercent(maxVariance.return)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Volatility</p>
            <p className="text-lg font-semibold text-gray-300">{formatPercent(maxVariance.volatility)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Sharpe Ratio</p>
            <p className="text-lg font-semibold text-blue-400">{maxVariance.sharpeRatio.toFixed(2)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
