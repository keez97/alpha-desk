import { useState } from 'react';
import type {
  ConvictionStats,
  DirectionStats,
  ConfluenceBacktestResult,
} from '../../hooks/useConfluenceBacktest';
import { useConfluenceBacktest, useRunConfluenceBacktest } from '../../hooks/useConfluenceBacktest';

interface ConfluenceBacktestProps {
  autoRun?: boolean;
}

const getConvictionColor = (conviction: string): string => {
  switch (conviction) {
    case 'HIGH':
      return 'bg-green-500/10 border-l-4 border-green-500';
    case 'MEDIUM':
      return 'bg-amber-500/10 border-l-4 border-amber-500';
    case 'LOW':
      return 'bg-gray-500/10 border-l-4 border-gray-500';
    default:
      return 'bg-neutral-500/10 border-l-4 border-neutral-500';
  }
};

const getConvictionBadgeColor = (conviction: string): string => {
  switch (conviction) {
    case 'HIGH':
      return 'bg-green-500/20 text-green-400';
    case 'MEDIUM':
      return 'bg-amber-500/20 text-amber-400';
    case 'LOW':
      return 'bg-gray-500/20 text-gray-400';
    default:
      return 'bg-neutral-500/20 text-neutral-400';
  }
};

const getDirectionColor = (direction: string): string => {
  switch (direction) {
    case 'bullish':
      return 'text-green-400';
    case 'bearish':
      return 'text-red-400';
    default:
      return 'text-neutral-400';
  }
};

const SimpleEquityCurveChart = ({ data }: { data: Array<{ date: string; cumReturn: number }> }) => {
  if (!data || data.length === 0) {
    return (
      <div className="h-32 flex items-center justify-center text-neutral-500 text-sm">
        No equity curve data available
      </div>
    );
  }

  // Find min/max for scaling
  const returns = data.map((d) => d.cumReturn);
  const minReturn = Math.min(...returns, 0);
  const maxReturn = Math.max(...returns, 0);
  const range = maxReturn - minReturn;
  const scale = range === 0 ? 1 : range;

  // Create simple line chart using SVG
  const width = 400;
  const height = 150;
  const padding = 20;

  const points = data.map((d, i) => {
    const x = padding + (i / (data.length - 1)) * (width - 2 * padding);
    const y = height - padding - ((d.cumReturn - minReturn) / scale) * (height - 2 * padding);
    return { x, y, return: d.cumReturn };
  });

  const pathData = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

  return (
    <div className="flex flex-col items-center">
      <svg width={width} height={height} className="text-neutral-400">
        {/* Grid lines */}
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="currentColor" strokeOpacity="0.2" strokeWidth="1" />

        {/* Axes */}
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="currentColor" strokeOpacity="0.3" strokeWidth="1" />

        {/* Path */}
        <path d={pathData} stroke="#10b981" strokeWidth="2" fill="none" vectorEffect="non-scaling-stroke" />

        {/* Points */}
        {points.map((p, i) => (
          i % Math.max(1, Math.floor(data.length / 10)) === 0 && (
            <circle key={i} cx={p.x} cy={p.y} r="3" fill="#10b981" />
          )
        ))}
      </svg>
      <div className="text-xs text-neutral-500 mt-2">
        {data.length} signals | Final PnL: {data[data.length - 1]?.cumReturn.toFixed(2)}%
      </div>
    </div>
  );
};

export function ConfluenceBacktest({ autoRun = false }: ConfluenceBacktestProps) {
  const [lookbackMonths, setLookbackMonths] = useState(12);
  const [hasRunOnce, setHasRunOnce] = useState(false);

  const { data: backtestData, isLoading, error } = useConfluenceBacktest(lookbackMonths, hasRunOnce);
  const runBacktest = useRunConfluenceBacktest();

  const handleRunBacktest = () => {
    setHasRunOnce(true);
  };

  const handleLookbackChange = (value: number) => {
    setLookbackMonths(value);
    setHasRunOnce(false);
  };

  // Determine if we should show results
  const isRunning = isLoading || runBacktest.isPending;
  const hasResults = backtestData && !backtestData.error;

  // Extract key insights from HIGH conviction bullish signals
  const getKeyInsight = (): string => {
    if (!backtestData) return '';

    const highBullish = backtestData.summary.convictionStats.find(
      (s) => s.conviction === 'HIGH' && s.direction === 'bullish'
    );

    if (!highBullish) return '';

    const winRate = highBullish.winRate5D.toFixed(0);
    const avgReturn = highBullish.avgReturn5D.toFixed(2);
    const signals = highBullish.totalSignals;

    return `HIGH conviction bullish signals showed a ${winRate}% win rate at 5D horizon with +${avgReturn}% avg return over ${signals} historical signals.`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border border-neutral-800 rounded-lg p-6 bg-[#0a0a0a]">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h2 className="text-lg font-semibold text-neutral-100">Historical Signal Performance</h2>
            <p className="text-sm text-neutral-500 mt-1">
              Backtest confluence signals (3+ aligned signals) against historical returns
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
            <select
              value={lookbackMonths}
              onChange={(e) => handleLookbackChange(parseInt(e.target.value))}
              disabled={isRunning}
              className="px-3 py-2 rounded border border-neutral-800 bg-neutral-900 text-neutral-200 text-sm disabled:opacity-50"
            >
              <option value={1}>1 Month</option>
              <option value={3}>3 Months</option>
              <option value={6}>6 Months</option>
              <option value={12}>12 Months</option>
              <option value={24}>24 Months</option>
            </select>

            <button
              onClick={handleRunBacktest}
              disabled={isRunning}
              className="px-4 py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isRunning ? (
                <span className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-neutral-600 border-t-white rounded-full animate-spin" />
                  Running...
                </span>
              ) : (
                'Run Backtest'
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="border border-red-500/30 rounded-lg p-4 bg-red-500/10">
          <p className="text-red-400 text-sm">
            Error loading backtest: {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      )}

      {backtestData?.error && (
        <div className="border border-red-500/30 rounded-lg p-4 bg-red-500/10">
          <p className="text-red-400 text-sm">Backtest error: {backtestData.error}</p>
        </div>
      )}

      {/* Loading State */}
      {isRunning && !hasResults && (
        <div className="border border-neutral-800 rounded-lg p-8 bg-neutral-900/50 flex flex-col items-center justify-center">
          <div className="w-10 h-10 border-3 border-neutral-700 border-t-neutral-300 rounded-full animate-spin mb-3" />
          <p className="text-neutral-400 text-sm">Running backtest (this may take 30-60 seconds)...</p>
        </div>
      )}

      {/* Results */}
      {hasResults && (
        <>
          {/* Key Insight Box */}
          {getKeyInsight() && (
            <div className="border border-green-500/30 rounded-lg p-4 bg-green-500/10">
              <p className="text-green-400 text-sm font-medium">
                💡 {getKeyInsight()}
              </p>
            </div>
          )}

          {/* Conviction Stats Table */}
          <div className="border border-neutral-800 rounded-lg overflow-hidden bg-neutral-900/50">
            <div className="p-4 border-b border-neutral-800">
              <h3 className="text-sm font-semibold text-neutral-100">Conviction Level Statistics</h3>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-neutral-800 bg-neutral-900/80">
                    <th className="px-4 py-3 text-left text-neutral-400 font-semibold">Level</th>
                    <th className="px-4 py-3 text-center text-neutral-400 font-semibold">Dir</th>
                    <th className="px-4 py-3 text-center text-neutral-400 font-semibold">Signals</th>
                    <th className="px-4 py-3 text-center text-neutral-400 font-semibold">1D Win%</th>
                    <th className="px-4 py-3 text-center text-neutral-400 font-semibold">3D Win%</th>
                    <th className="px-4 py-3 text-center text-neutral-400 font-semibold">5D Win%</th>
                    <th className="px-4 py-3 text-center text-neutral-400 font-semibold">10D Win%</th>
                    <th className="px-4 py-3 text-center text-neutral-400 font-semibold">Avg 5D Ret</th>
                  </tr>
                </thead>
                <tbody>
                  {backtestData.summary.convictionStats.map((stat, idx) => (
                    <tr
                      key={idx}
                      className={`border-b border-neutral-800/50 ${getConvictionColor(stat.conviction)}`}
                    >
                      <td className="px-4 py-3 text-neutral-200 font-medium">
                        <span className={`px-2 py-1 rounded text-xs ${getConvictionBadgeColor(stat.conviction)}`}>
                          {stat.conviction}
                        </span>
                      </td>
                      <td className={`px-4 py-3 text-center font-medium ${getDirectionColor(stat.direction)}`}>
                        {stat.direction === 'bullish' ? '↑' : '↓'}
                      </td>
                      <td className="px-4 py-3 text-center text-neutral-300">{stat.totalSignals}</td>
                      <td className="px-4 py-3 text-center text-neutral-300">
                        {stat.winRate1D.toFixed(0)}%
                      </td>
                      <td className="px-4 py-3 text-center text-neutral-300">
                        {stat.winRate3D.toFixed(0)}%
                      </td>
                      <td className="px-4 py-3 text-center text-neutral-300">
                        {stat.winRate5D.toFixed(0)}%
                      </td>
                      <td className="px-4 py-3 text-center text-neutral-300">
                        {stat.winRate10D.toFixed(0)}%
                      </td>
                      <td className={`px-4 py-3 text-center font-medium ${stat.avgReturn5D > 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {stat.avgReturn5D > 0 ? '+' : ''}{stat.avgReturn5D.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {backtestData.summary.convictionStats.length === 0 && (
              <div className="p-8 text-center text-neutral-500 text-sm">
                No signal data available
              </div>
            )}
          </div>

          {/* Direction Stats */}
          {backtestData.summary.directionStats.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {backtestData.summary.directionStats.map((stat, idx) => (
                <div key={idx} className="border border-neutral-800 rounded-lg p-4 bg-neutral-900/50">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className={`text-sm font-semibold capitalize ${getDirectionColor(stat.direction)}`}>
                      {stat.direction === 'bullish' ? '📈 Bullish' : '📉 Bearish'}
                    </h4>
                    <span className="text-xs text-neutral-500">{stat.totalSignals} signals</span>
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-neutral-400">Win Rate</span>
                      <span className="text-sm font-medium text-neutral-200">
                        {stat.winRate.toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-neutral-400">Avg Return</span>
                      <span className={`text-sm font-medium ${stat.avgReturn > 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {stat.avgReturn > 0 ? '+' : ''}{stat.avgReturn.toFixed(2)}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Equity Curve */}
          {backtestData.equityCurve && backtestData.equityCurve.length > 0 && (
            <div className="border border-neutral-800 rounded-lg p-6 bg-neutral-900/50">
              <h3 className="text-sm font-semibold text-neutral-100 mb-4">
                Equity Curve (HIGH Conviction Bullish Signals)
              </h3>
              <SimpleEquityCurveChart data={backtestData.equityCurve} />
            </div>
          )}

          {/* Footer Info */}
          <div className="text-xs text-neutral-500 text-center">
            Backtest period: {backtestData.period} | Signals analyzed: {backtestData.signalsAnalyzed}
            <br />
            Last updated: {new Date(backtestData.timestamp).toLocaleString()}
          </div>
        </>
      )}

      {/* Empty State */}
      {!isRunning && !hasResults && !error && !backtestData?.error && (
        <div className="border border-neutral-800 rounded-lg p-8 bg-neutral-900/50 text-center">
          <p className="text-neutral-500 text-sm mb-4">
            Click "Run Backtest" to analyze how confluence signals performed historically
          </p>
        </div>
      )}
    </div>
  );
}
