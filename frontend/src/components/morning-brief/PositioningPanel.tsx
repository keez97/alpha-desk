import { usePositioning } from '../../hooks/usePositioning';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';

function PositioningBar({
  label,
  commercialPct,
  speculativePct,
  extremeFlag,
}: {
  label: string;
  commercialPct: number;
  speculativePct: number;
  extremeFlag: string | null;
}) {
  // Commercial bar - left side (0% at center, negative = left) - Green (emerald)
  const commColor = commercialPct > 50 ? 'bg-emerald-600/70' : 'bg-emerald-400/50';
  const commWidth = Math.abs(commercialPct - 50);

  // Speculative bar - right side (0% at center, positive = right) - Amber/Orange
  const specColor = speculativePct > 50 ? 'bg-amber-500/70' : 'bg-amber-400/50';
  const specWidth = Math.abs(speculativePct - 50);

  // Extreme flag styling
  let extremeIndicator = null;
  let extremeColor = '';

  if (extremeFlag) {
    if (extremeFlag.includes('extreme_long')) {
      extremeColor = 'text-green-400';
      extremeIndicator = '↗️';
    } else if (extremeFlag.includes('extreme_short')) {
      extremeColor = 'text-red-400';
      extremeIndicator = '↘️';
    }
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-neutral-300">{label}</span>
        {extremeIndicator && <span className={`text-sm ${extremeColor}`}>{extremeIndicator}</span>}
      </div>

      {/* Positioning bar */}
      <div className="flex h-5 items-center gap-1 rounded bg-neutral-800" title="Commercial (Hedgers) on left, Speculative (Large Traders) on right">
        {/* Commercial (left side) */}
        {commercialPct > 50 && (
          <div className="flex-shrink-0 bg-emerald-600/70" style={{ width: `${(commercialPct - 50) * 2}%` }} />
        )}

        {/* Center divider */}
        <div className="mx-auto flex-shrink-0 w-0.5 h-4 bg-neutral-700" />

        {/* Speculative (right side) */}
        {speculativePct > 50 && (
          <div className="flex-shrink-0 bg-amber-500/70" style={{ width: `${(speculativePct - 50) * 2}%` }} />
        )}
      </div>

      {/* Percentile labels */}
      <div className="flex justify-between text-[9px] text-neutral-600">
        <span>Hedgers: {commercialPct}th pctl</span>
        <span>Specs: {speculativePct}th pctl</span>
      </div>
    </div>
  );
}

function getPlainEnglish(message: string, bias: 'bullish' | 'bearish' | 'neutral'): string {
  if (message.includes('reversal')) {
    if (bias === 'bearish') {
      return 'Smart money is positioning for a downturn. Consider reducing risk.';
    } else if (bias === 'bullish') {
      return 'Smart money is turning bullish. A price recovery may be ahead.';
    }
  }

  if (message.includes('divergence')) {
    if (bias === 'bearish') {
      return 'Price is rising but institutional positioning disagrees. Caution warranted.';
    } else if (bias === 'bullish') {
      return 'Price is falling but institutions are accumulating. Could be a buying opportunity.';
    }
  }

  if (message.includes('extreme')) {
    if (bias === 'bearish') {
      return 'Positioning is at extreme bearish levels. Historically, this often precedes a reversal upward.';
    } else if (bias === 'bullish') {
      return 'Positioning is at extreme bullish levels. Historically, this often precedes a pullback.';
    }
  }

  return 'Monitor this market closely for potential shifts.';
}

function AlertBadge({
  severity,
  message,
  bias,
}: {
  severity: 'high' | 'medium';
  message: string;
  bias: 'bullish' | 'bearish' | 'neutral';
}) {
  const colors =
    severity === 'high'
      ? 'border-red-600/50 bg-red-900/20 text-red-400'
      : 'border-amber-600/50 bg-amber-900/20 text-amber-400';

  const biasIcon = bias === 'bullish' ? '📈' : bias === 'bearish' ? '📉' : '➡️';
  const plainEnglish = getPlainEnglish(message, bias);

  return (
    <div className={`rounded border p-2 text-xs space-y-1 ${colors}`}>
      <div className="flex items-start gap-2">
        <span className="text-sm">{biasIcon}</span>
        <div className="flex-1 leading-snug">{message}</div>
      </div>
      <div className="text-neutral-300 italic pl-6">{plainEnglish}</div>
    </div>
  );
}

export function PositioningPanel() {
  const { data, isLoading, error, refetch } = usePositioning();

  if (isLoading) return <LoadingState message="Loading positioning data..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data || data.markets.length === 0) return null;

  return (
    <div className="space-y-3 rounded border border-neutral-800 bg-neutral-900/50 p-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase text-neutral-400">COT Positioning & Alerts</span>
        <span className="text-[10px] text-neutral-600">
          {new Date(data.timestamp).toLocaleTimeString()}
        </span>
      </div>

      {/* Summary */}
      {data.summary && (
        <div className="rounded bg-neutral-800/50 px-3 py-2 text-[11px] text-neutral-300 leading-relaxed">
          {data.summary}
        </div>
      )}

      {/* Legend */}
      <div className="flex gap-3 text-xs text-neutral-500">
        <div className="flex items-center gap-1">
          <div className="h-2 w-2 rounded-full bg-emerald-500" />
          <span>Hedgers (Commercial)</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="h-2 w-2 rounded-full bg-amber-500" />
          <span>Speculators (Large Traders)</span>
        </div>
      </div>

      {/* Markets positioning bars with insights */}
      <div className="space-y-3">
        {data.markets.map((market) => (
          <div key={market.ticker}>
            <PositioningBar
              label={market.name}
              commercialPct={market.commercial_percentile}
              speculativePct={market.speculative_percentile}
              extremeFlag={market.extreme_flag}
            />
            {market.insight && (
              <p className={`text-[10px] mt-0.5 leading-snug ${
                market.bias === 'bullish' ? 'text-emerald-400/70' :
                market.bias === 'bearish' ? 'text-red-400/70' :
                'text-neutral-500'
              }`}>
                {market.insight}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Alerts section */}
      {data.alerts.length > 0 && (
        <div className="space-y-2 border-t border-neutral-800 pt-3">
          <span className="text-xs font-medium text-neutral-500">Reversal & Divergence Alerts</span>
          <div className="space-y-2">
            {data.alerts.map((alert, i) => (
              <AlertBadge
                key={i}
                severity={alert.severity}
                message={alert.message}
                bias={alert.bias}
              />
            ))}
          </div>
        </div>
      )}

      {/* Info footer */}
      <div className="border-t border-neutral-800 pt-2 text-[9px] text-neutral-600">
        Percentiles vs 52-week range • Extreme positioning (above 90th or below 10th percentile) often signals mean-reversion risk
      </div>
    </div>
  );
}
