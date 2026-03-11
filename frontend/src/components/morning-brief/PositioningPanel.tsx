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
  // Commercial bar - left side (0% at center, negative = left)
  const commColor = commercialPct > 50 ? 'bg-blue-500/70' : 'bg-blue-400/50';
  const commWidth = Math.abs(commercialPct - 50);

  // Speculative bar - right side (0% at center, positive = right)
  const specColor = speculativePct > 50 ? 'bg-purple-500/70' : 'bg-purple-400/50';
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
      <div className="flex h-5 items-center gap-1 rounded bg-neutral-800">
        {/* Commercial (left side) */}
        {commercialPct > 50 && (
          <div className="flex-shrink-0 bg-blue-600/70" style={{ width: `${(commercialPct - 50) * 2}%` }} />
        )}

        {/* Center divider */}
        <div className="mx-auto flex-shrink-0 w-0.5 h-4 bg-neutral-700" />

        {/* Speculative (right side) */}
        {speculativePct > 50 && (
          <div className="flex-shrink-0 bg-purple-600/70" style={{ width: `${(speculativePct - 50) * 2}%` }} />
        )}
      </div>

      {/* Percentile labels */}
      <div className="flex justify-between text-[9px] text-neutral-600">
        <span>C: {commercialPct}%</span>
        <span>S: {speculativePct}%</span>
      </div>
    </div>
  );
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

  return (
    <div className={`rounded border p-2 text-xs space-y-1 ${colors}`}>
      <div className="flex items-start gap-2">
        <span className="text-sm">{biasIcon}</span>
        <div className="flex-1 leading-snug">{message}</div>
      </div>
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

      {/* Legend */}
      <div className="flex gap-3 text-xs text-neutral-500">
        <div className="flex items-center gap-1">
          <div className="h-2 w-2 rounded-full bg-blue-500" />
          <span>Commercial</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="h-2 w-2 rounded-full bg-purple-500" />
          <span>Speculative</span>
        </div>
      </div>

      {/* Markets positioning bars */}
      <div className="space-y-3">
        {data.markets.map((market) => (
          <PositioningBar
            key={market.ticker}
            label={market.name}
            commercialPct={market.commercial_percentile}
            speculativePct={market.speculative_percentile}
            extremeFlag={market.extreme_flag}
          />
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
        Percentiles vs 1-year range • Extremes (90th/10th) show reversal risk
      </div>
    </div>
  );
}
