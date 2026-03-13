import { useOptionsFlow } from '../../hooks/useOptionsFlow';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';

const SIGNAL_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  bullish: { bg: 'bg-green-900/30', text: 'text-green-400', label: 'Bullish' },
  bearish: { bg: 'bg-red-900/30', text: 'text-red-400', label: 'Bearish' },
  neutral: { bg: 'bg-neutral-800/30', text: 'text-neutral-300', label: 'Neutral' },
};

const GEX_COLORS: Record<string, { bg: string; text: string }> = {
  positive: { bg: 'bg-green-900/40', text: 'text-green-300' },
  negative: { bg: 'bg-red-900/40', text: 'text-red-300' },
  neutral: { bg: 'bg-neutral-800/40', text: 'text-neutral-400' },
};

function MetricBox({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value: string | number;
  unit?: string;
  color?: string;
}) {
  return (
    <div className="text-center">
      <span className="text-xs text-neutral-500 block mb-0.5">{label}</span>
      <span className={`text-sm font-mono font-medium ${color || 'text-neutral-200'}`}>
        {value}
      </span>
      {unit && <span className="text-xs text-neutral-500 block">{unit}</span>}
    </div>
  );
}

function PutCallRatioBar({ ratio }: { ratio: number }) {
  // Ratio > 1 = more puts (red), < 1 = more calls (green)
  const isCallHeavy = ratio < 1;
  const displayRatio = isCallHeavy ? 1 / ratio : ratio;
  const label = isCallHeavy ? `${displayRatio.toFixed(2)}x Calls` : `${displayRatio.toFixed(2)}x Puts`;
  const color = isCallHeavy ? 'bg-green-500/60' : 'bg-red-500/60';

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-green-400">Calls</span>
        <span className="text-red-400">Puts</span>
      </div>
      <div className="h-2 rounded-full overflow-hidden flex bg-neutral-800">
        <div
          className={`${color} h-full transition-all`}
          style={{ width: isCallHeavy ? `${(1 / displayRatio) * 50}%` : `${Math.min((displayRatio / 2) * 50, 50)}%` }}
        />
        <div className="bg-neutral-700 h-full flex-1" />
      </div>
      <div className="text-center text-xs text-neutral-400">{label}</div>
    </div>
  );
}

function IVSkewIndicator({ skew }: { skew: number }) {
  // Positive = put skew (bearish), Negative = call skew (bullish)
  const isPutSkew = skew > 0.1;
  const isCallSkew = skew < -0.1;
  const color = isPutSkew ? 'text-red-300' : isCallSkew ? 'text-green-300' : 'text-neutral-400';
  const label = isPutSkew ? 'Put Skew' : isCallSkew ? 'Call Skew' : 'Balanced';

  return (
    <div className="space-y-1">
      <span className="text-xs text-neutral-500 block">IV Skew</span>
      <div className={`text-sm font-mono font-medium ${color}`}>{label}</div>
      <div className="text-xs text-neutral-500">{skew > 0 ? '+' : ''}{skew.toFixed(2)}</div>
    </div>
  );
}

export function OptionsFlowPanel() {
  const { data, isLoading, error, refetch } = useOptionsFlow();

  if (isLoading) return <LoadingState message="Loading options flow..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  const signal = SIGNAL_COLORS[data.signal] || SIGNAL_COLORS.neutral;
  const gexColor = GEX_COLORS[data.gex_signal] || GEX_COLORS.neutral;

  return (
    <div className={`border border-neutral-800 rounded p-3 ${signal.bg}`}>
      <div className="flex items-center justify-between mb-2.5">
        <div>
          <span className="text-xs font-semibold text-neutral-200 block">Options Flow</span>
          <span className="text-xs text-neutral-500">{data.ticker}</span>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${signal.text} bg-neutral-900/50`}>
          {signal.label}
        </span>
      </div>

      {/* Put/Call Ratio Bar */}
      <div className="mb-3">
        <PutCallRatioBar ratio={data.put_call_ratio} />
      </div>

      {/* Main Metrics Grid */}
      <div className="grid grid-cols-4 gap-2 mb-3">
        <MetricBox
          label="Spot"
          value={data.spot_price.toFixed(2)}
          color="text-neutral-200"
        />
        <IVSkewIndicator skew={data.iv_skew} />
        <MetricBox
          label="Vol Imbalance"
          value={data.volume_imbalance.toFixed(2)}
          unit={data.volume_imbalance > 1 ? 'Calls' : 'Puts'}
          color={data.volume_imbalance > 1 ? 'text-green-300' : 'text-red-300'}
        />
        <div className={`rounded p-1.5 text-center ${gexColor.bg}`}>
          <span className="text-xs text-neutral-500 block">GEX</span>
          <span className={`text-sm font-mono font-medium ${gexColor.text}`}>
            {data.gex_signal === 'positive' ? '+' : data.gex_signal === 'negative' ? '−' : '•'}
          </span>
          <span className="text-xs text-neutral-500 block">{Math.abs(data.gex_value) >= 1e6 ? `${(data.gex_value / 1e6).toFixed(1)}M` : data.gex_value.toFixed(0)}</span>
        </div>
      </div>

      {/* Volume Stats */}
      <div className="grid grid-cols-2 gap-2 mb-2 text-xs">
        <div className="text-center">
          <span className="text-neutral-500 block">Call Volume</span>
          <span className="text-green-300 font-mono">{(data.total_call_volume / 1e6).toFixed(1)}M</span>
        </div>
        <div className="text-center">
          <span className="text-neutral-500 block">Put Volume</span>
          <span className="text-red-300 font-mono">{(data.total_put_volume / 1e6).toFixed(1)}M</span>
        </div>
      </div>

      {/* Details */}
      {data.details && data.details.length > 0 && (
        <div className="mt-2 pt-2 border-t border-neutral-800 space-y-1">
          {data.details.map((detail, idx) => (
            <div key={idx} className="text-xs text-neutral-500">
              • {detail}
            </div>
          ))}
        </div>
      )}

      {/* Expiry */}
      <div className="mt-2 text-xs text-neutral-500 text-right">
        {data.expiry && `Expiry: ${data.expiry}`}
      </div>
    </div>
  );
}
