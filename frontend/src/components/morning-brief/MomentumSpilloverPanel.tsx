import { useMomentumSpillover } from '../../hooks/useMomentumSpillover';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';

const SIGNAL_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  bullish: { bg: 'bg-green-900/20', text: 'text-green-400', label: 'Bullish' },
  bearish: { bg: 'bg-red-900/20', text: 'text-red-400', label: 'Bearish' },
  warning: { bg: 'bg-amber-900/20', text: 'text-amber-400', label: 'Warning' },
};

function MomentumState({ state }: { state: 'positive' | 'negative' | 'neutral' }) {
  if (state === 'positive') {
    return <span className="inline-block w-2 h-2 rounded-full bg-green-500 mr-1" />;
  } else if (state === 'negative') {
    return <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" />;
  }
  return <span className="inline-block w-2 h-2 rounded-full bg-neutral-600 mr-1" />;
}

function AssetRow({
  ticker,
  name,
  momentum_1m,
  momentum_3m,
  state,
}: {
  ticker: string;
  name: string;
  momentum_1m: number;
  momentum_3m: number;
  state: 'positive' | 'negative' | 'neutral';
}) {
  const color1m = momentum_1m > 0 ? 'text-green-300' : momentum_1m < 0 ? 'text-red-300' : 'text-neutral-400';
  const color3m = momentum_3m > 0 ? 'text-green-300' : momentum_3m < 0 ? 'text-red-300' : 'text-neutral-400';

  return (
    <div className="flex items-center justify-between py-1.5 px-2 hover:bg-neutral-800/30 rounded text-xs">
      <div className="flex items-center gap-1.5 flex-1 min-w-0">
        <MomentumState state={state} />
        <span className="text-neutral-300 font-medium min-w-fit">{ticker}</span>
        <span className="text-neutral-500 truncate">{name}</span>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0 ml-2">
        <span className={`font-mono ${color1m} min-w-[45px] text-right`}>
          {momentum_1m > 0 ? '+' : ''}{(momentum_1m * 100).toFixed(1)}%
        </span>
        <span className={`font-mono ${color3m} min-w-[45px] text-right`}>
          {momentum_3m > 0 ? '+' : ''}{(momentum_3m * 100).toFixed(1)}%
        </span>
      </div>
    </div>
  );
}

function SignalBadge({ signal }: { signal: { description: string; type: string; confidence: number } }) {
  const typeColor = signal.type === 'bullish' ? 'bg-green-900/40 text-green-300' : signal.type === 'bearish' ? 'bg-red-900/40 text-red-300' : 'bg-amber-900/40 text-amber-300';

  return (
    <div className={`p-2 rounded text-xs ${typeColor}`}>
      <div className="flex justify-between items-start gap-2">
        <div className="flex-1">{signal.description}</div>
        <span className="font-mono flex-shrink-0">
          {(signal.confidence * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  );
}

export function MomentumSpilloverPanel() {
  const { data, isLoading, error, refetch } = useMomentumSpillover();

  if (isLoading) return <LoadingState message="Loading momentum spillover..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  const hasSignals = data.signals && data.signals.length > 0;

  return (
    <div className="border border-neutral-800 rounded p-3 bg-neutral-900/30">
      <div className="mb-2.5">
        <span className="text-xs font-semibold text-neutral-200 block">Factor Decomposition</span>
        <span className="text-xs text-neutral-500">Cross-Asset Momentum Analysis</span>
      </div>

      {/* Momentum Matrix - Asset Rows */}
      <div className="mb-3 bg-neutral-900/40 rounded border border-neutral-800/50">
        <div className="px-2 py-1 border-b border-neutral-800/50 grid grid-cols-12 gap-2 text-xs text-neutral-500">
          <span className="col-span-6">Asset</span>
          <span className="col-span-3 text-right">1M</span>
          <span className="col-span-3 text-right">3M</span>
        </div>

        {data.assets.map((asset) => (
          <AssetRow
            key={asset.ticker}
            ticker={asset.ticker}
            name={asset.name}
            momentum_1m={asset.momentum_1m}
            momentum_3m={asset.momentum_3m}
            state={asset.state}
          />
        ))}
      </div>

      {/* Momentum Summary */}
      <div className="grid grid-cols-3 gap-2 mb-3 text-center text-xs">
        <div className="bg-green-900/20 rounded p-1.5">
          <span className="text-neutral-500 block">Positive</span>
          <span className="text-green-300 font-mono font-bold">{data.matrix.positive_count}</span>
        </div>
        <div className="bg-neutral-800/20 rounded p-1.5">
          <span className="text-neutral-500 block">Neutral</span>
          <span className="text-neutral-400 font-mono font-bold">{data.matrix.neutral_count}</span>
        </div>
        <div className="bg-red-900/20 rounded p-1.5">
          <span className="text-neutral-500 block">Negative</span>
          <span className="text-red-300 font-mono font-bold">{data.matrix.negative_count}</span>
        </div>
      </div>

      {/* Signals */}
      {hasSignals && (
        <div className="space-y-1.5 pt-2 border-t border-neutral-800">
          <span className="text-xs text-neutral-500 block font-medium">Spillover Signals</span>
          <div className="space-y-1">
            {data.signals.map((signal, idx) => (
              <SignalBadge key={idx} signal={signal} />
            ))}
          </div>
        </div>
      )}

      {/* No Signals Message */}
      {!hasSignals && (
        <div className="text-xs text-neutral-500 text-center py-2">
          No significant spillover signals detected
        </div>
      )}
    </div>
  );
}
