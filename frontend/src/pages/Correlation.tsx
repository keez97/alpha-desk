import { useState } from 'react';
import { useCorrelationMatrix } from '../hooks/useCorrelation';
import { CorrelationMatrix } from '../components/correlation/CorrelationMatrix';
import { PairsPanel } from '../components/correlation/PairsPanel';
import { LoadingState } from '../components/shared/LoadingState';
import { ErrorState } from '../components/shared/ErrorState';

export function Correlation() {
  const [lookback, setLookback] = useState(90);
  const [selectedPair, setSelectedPair] = useState<{
    ticker1: string;
    ticker2: string;
  } | null>(null);

  const { data, isLoading, error, refetch } = useCorrelationMatrix(lookback);

  const lookbackOptions = [
    { label: '30D', value: 30 },
    { label: '60D', value: 60 },
    { label: '90D', value: 90 },
    { label: '180D', value: 180 },
  ];

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-neutral-100">
          Sector Correlation Analysis
        </h1>
        <p className="text-sm text-neutral-400">
          Identify pairs trades and hedging opportunities from cross-sector correlations
        </p>
      </div>

      {/* Lookback Period Selector */}
      <div className="flex items-center gap-2 bg-neutral-900 border border-neutral-800 rounded p-3">
        <span className="text-xs font-medium text-neutral-400 uppercase tracking-wider">
          Lookback Period:
        </span>
        <div className="flex gap-2">
          {lookbackOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => setLookback(option.value)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                lookback === option.value
                  ? 'bg-neutral-700 text-neutral-100'
                  : 'text-neutral-400 hover:text-neutral-300 hover:bg-neutral-800'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <LoadingState message="Loading correlation data..." />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : data?.error || !data?.matrix || data.matrix.length === 0 ? (
        <div className="text-center p-8 border border-neutral-800 rounded bg-neutral-900">
          <p className="text-amber-400 font-bold text-lg">Correlation data temporarily unavailable</p>
          <p className="text-sm text-neutral-400 mt-2">Data sources are rate-limited. Try again in a few minutes.</p>
          <button
            onClick={() => refetch()}
            className="mt-4 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded text-sm font-medium transition-colors"
          >
            Retry
          </button>
        </div>
      ) : data ? (
        <div className="grid gap-4 lg:grid-cols-10">
          {/* Correlation Matrix (70% width) */}
          <div className="lg:col-span-7 border border-neutral-800 rounded p-4 bg-neutral-900">
            <CorrelationMatrix
              data={data}
              onPairSelect={(ticker1, ticker2) =>
                setSelectedPair({ ticker1, ticker2 })
              }
            />
          </div>

          {/* Pairs Panel (30% width) */}
          <div className="lg:col-span-3 border border-neutral-800 rounded p-4 bg-neutral-900">
            <PairsPanel
              pairsTrades={data.pairs_trades || []}
              hedgingPairs={data.hedging_pairs || []}
              onPairSelect={(ticker1, ticker2) =>
                setSelectedPair({ ticker1, ticker2 })
              }
            />
          </div>
        </div>
      ) : null}

      {/* Selected Pair Info (optional detail view) */}
      {selectedPair && (
        <div className="border border-neutral-700 rounded p-4 bg-neutral-900">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-neutral-100">
              Pair Analysis: {selectedPair.ticker1} / {selectedPair.ticker2}
            </h3>
            <button
              onClick={() => setSelectedPair(null)}
              className="text-xs text-neutral-400 hover:text-neutral-200"
            >
              ✕ Close
            </button>
          </div>
          <p className="text-xs text-neutral-400">
            Detailed spread and z-score analysis coming soon
          </p>
        </div>
      )}
    </div>
  );
}
