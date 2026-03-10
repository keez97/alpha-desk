import type { PairsTrade, HedgingPair } from '../../hooks/useCorrelation';

interface PairsPanelProps {
  pairsTrades: PairsTrade[];
  hedgingPairs: HedgingPair[];
  onPairSelect?: (ticker1: string, ticker2: string) => void;
}

/**
 * Get color badge for RRG quadrant
 */
function getQuadrantBadge(quadrant: string): {
  bg: string;
  text: string;
  label: string;
} {
  switch (quadrant) {
    case 'Strengthening':
      return { bg: 'bg-green-900', text: 'text-green-100', label: '↗ Strengthening' };
    case 'Weakening':
      return { bg: 'bg-yellow-900', text: 'text-yellow-100', label: '↘ Weakening' };
    case 'Recovering':
      return { bg: 'bg-blue-900', text: 'text-blue-100', label: '↙ Recovering' };
    case 'Deteriorating':
      return { bg: 'bg-red-900', text: 'text-red-100', label: '↖ Deteriorating' };
    default:
      return { bg: 'bg-neutral-800', text: 'text-neutral-300', label: quadrant };
  }
}

/**
 * Get color for conviction level
 */
function getConvictionColor(conviction: number): string {
  if (conviction >= 0.8) return 'text-green-400';
  if (conviction >= 0.6) return 'text-lime-400';
  if (conviction >= 0.4) return 'text-yellow-400';
  return 'text-neutral-400';
}

export function PairsPanel({
  pairsTrades,
  hedgingPairs,
  onPairSelect,
}: PairsPanelProps) {
  return (
    <div className="space-y-4">
      {/* Pairs Trades Section */}
      <div className="space-y-2">
        <div>
          <h3 className="text-sm font-semibold text-neutral-100">
            Pairs Trades
          </h3>
          <p className="text-xs text-neutral-400">
            Mean-reversion opportunities from correlated divergence
          </p>
        </div>

        {pairsTrades && pairsTrades.length > 0 ? (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {pairsTrades.slice(0, 10).map((pair, idx) => {
              const quad1 = getQuadrantBadge(pair.quadrant1);
              const quad2 = getQuadrantBadge(pair.quadrant2);

              return (
                <div
                  key={idx}
                  className="border border-neutral-700 rounded p-3 bg-neutral-900 hover:bg-neutral-800 transition-colors cursor-pointer"
                  onClick={() => {
                    if (onPairSelect) {
                      onPairSelect(pair.ticker1, pair.ticker2);
                    }
                  }}
                >
                  {/* Pair Tickers */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="font-semibold text-neutral-100">
                        <span className="text-green-400">{pair.ticker1}</span>
                        {' / '}
                        <span className="text-red-400">{pair.ticker2}</span>
                      </div>
                    </div>
                    <div className={`text-sm font-semibold ${getConvictionColor(pair.conviction)}`}>
                      {(pair.conviction * 100).toFixed(0)}%
                    </div>
                  </div>

                  {/* Sector Names */}
                  <p className="text-xs text-neutral-400 mb-2">
                    {pair.sector1} → {pair.sector2}
                  </p>

                  {/* Correlation */}
                  <p className="text-xs text-neutral-300 mb-2">
                    Correlation: <span className="font-semibold">{pair.correlation.toFixed(2)}</span>
                  </p>

                  {/* RRG Quadrants */}
                  <div className="flex gap-2 mb-2 flex-wrap">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${quad1.bg} ${quad1.text}`}>
                      {pair.ticker1}: {quad1.label}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${quad2.bg} ${quad2.text}`}>
                      {pair.ticker2}: {quad2.label}
                    </span>
                  </div>

                  {/* Trade Suggestion */}
                  <p className="text-xs text-neutral-300 italic">
                    <span className="text-green-400">Long {pair.ticker1}</span>
                    {' / '}
                    <span className="text-red-400">Short {pair.ticker2}</span>
                  </p>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="border border-neutral-700 rounded p-3 bg-neutral-900 text-center">
            <p className="text-xs text-neutral-500">
              No pairs trades identified with current correlation thresholds
            </p>
          </div>
        )}
      </div>

      {/* Hedging Pairs Section */}
      <div className="space-y-2">
        <div>
          <h3 className="text-sm font-semibold text-neutral-100">
            Hedging Pairs
          </h3>
          <p className="text-xs text-neutral-400">
            Low/negative correlation for diversification
          </p>
        </div>

        {hedgingPairs && hedgingPairs.length > 0 ? (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {hedgingPairs.slice(0, 10).map((pair, idx) => {
              const isNegative = pair.correlation < -0.3;

              return (
                <div
                  key={idx}
                  className="border border-neutral-700 rounded p-3 bg-neutral-900 hover:bg-neutral-800 transition-colors cursor-pointer"
                  onClick={() => {
                    if (onPairSelect) {
                      onPairSelect(pair.ticker1, pair.ticker2);
                    }
                  }}
                >
                  {/* Pair Tickers */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="font-semibold text-neutral-100">
                      <span>{pair.ticker1}</span>
                      {' / '}
                      <span>{pair.ticker2}</span>
                    </div>
                    <div className={`text-xs font-semibold px-2 py-1 rounded ${
                      isNegative
                        ? 'bg-red-900 text-red-300'
                        : 'bg-blue-900 text-blue-300'
                    }`}>
                      {pair.hedge_type}
                    </div>
                  </div>

                  {/* Sector Names */}
                  <p className="text-xs text-neutral-400 mb-2">
                    {pair.sector1} ↔ {pair.sector2}
                  </p>

                  {/* Correlation */}
                  <p className="text-xs text-neutral-300">
                    Correlation: <span className="font-semibold">{pair.correlation.toFixed(2)}</span>
                    {isNegative && (
                      <span className="text-red-400 ml-2">(Inverse relationship)</span>
                    )}
                  </p>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="border border-neutral-700 rounded p-3 bg-neutral-900 text-center">
            <p className="text-xs text-neutral-500">
              No hedging pairs found with current thresholds
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
