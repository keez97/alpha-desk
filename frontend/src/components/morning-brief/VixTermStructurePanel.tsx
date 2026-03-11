import { useVixTermStructure } from '../../hooks/useVixTermStructure';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import type { VixTermStructureData } from '../../lib/api';

const SIGNAL_COLORS: Record<string, { bg: string; text: string; icon: string }> = {
  bullish: { bg: 'bg-green-900/40', text: 'text-green-400', icon: '↗' },
  bearish: { bg: 'bg-red-900/40', text: 'text-red-400', icon: '↘' },
  neutral: { bg: 'bg-neutral-800/50', text: 'text-neutral-400', icon: '→' },
};

function MiniSparkline({ data, height = 20 }: { data: number[]; height?: number }) {
  if (!data || data.length === 0) return null;

  const minVal = Math.min(...data);
  const maxVal = Math.max(...data);
  const range = maxVal - minVal || 1;

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * 100;
    const y = ((maxVal - v) / range) * 100;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width="100%" height={height} viewBox="0 0 100 100" className="stroke-green-400">
      <polyline
        points={points}
        fill="none"
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

function StateBox({ state, magnitude }: { state: string; magnitude: number }) {
  const isContango = state === 'contango';
  const stateColor = isContango ? 'text-green-400' : 'text-red-400';
  const bgColor = isContango ? 'bg-green-900/20' : 'bg-red-900/20';

  return (
    <div className={`${bgColor} border border-neutral-800 rounded p-2 text-center`}>
      <div className="text-xs font-medium text-neutral-400 mb-1">Term Structure</div>
      <div className={`text-sm font-mono font-bold ${stateColor}`}>
        {isContango ? 'Contango' : 'Backwardation'}
      </div>
      <div className="text-[10px] text-neutral-500 mt-0.5">
        {magnitude.toFixed(2)}%
      </div>
    </div>
  );
}

function PercentileBar({ percentile }: { percentile: number }) {
  const barColor = percentile < 25 ? 'bg-green-500' : percentile < 75 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px]">
        <span className="text-neutral-400">VIX Percentile</span>
        <span className={`font-mono ${percentile < 25 ? 'text-green-400' : percentile < 75 ? 'text-yellow-400' : 'text-red-400'}`}>
          {percentile}th
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-neutral-800 overflow-hidden">
        <div className={`${barColor} h-full transition-all`} style={{ width: `${percentile}%` }} />
      </div>
    </div>
  );
}

function MetricRow({ label, value, unit, color }: { label: string; value: number; unit: string; color?: string }) {
  return (
    <div className="flex justify-between text-xs">
      <span className="text-neutral-500">{label}</span>
      <span className={`font-mono ${color || 'text-neutral-300'}`}>
        {value.toFixed(value < 0.01 ? 6 : 2)}{unit}
      </span>
    </div>
  );
}

export function VixTermStructurePanel() {
  const { data, isLoading, error, refetch } = useVixTermStructure();

  if (isLoading) return <LoadingState message="Loading VIX data..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  const signal = SIGNAL_COLORS[data.signal] || SIGNAL_COLORS.neutral;
  const sparklineData = data.history.map(h => h.ratio);

  return (
    <div className={`border border-neutral-800 rounded p-3 ${signal.bg}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-neutral-300">VIX Term Structure</span>
        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${signal.text} bg-neutral-900/50`}>
          {data.signal.charAt(0).toUpperCase() + data.signal.slice(1)} {signal.icon}
        </span>
      </div>

      {/* Main metrics grid */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        {/* VIX Spot & VIX3M */}
        <div className="space-y-1">
          <div className="text-[10px] text-neutral-500">VIX Spot</div>
          <div className="text-lg font-mono font-bold text-neutral-200">{data.vixSpot.toFixed(2)}</div>
        </div>
        <div className="space-y-1">
          <div className="text-[10px] text-neutral-500">VIX 3M</div>
          <div className="text-lg font-mono font-bold text-neutral-300">{data.vix3m.toFixed(2)}</div>
        </div>

        {/* State box takes up 2 cols */}
        <div className="col-span-2">
          <StateBox state={data.state} magnitude={data.magnitude} />
        </div>
      </div>

      {/* Percentile bar */}
      <div className="mb-3">
        <PercentileBar percentile={data.percentile} />
      </div>

      {/* Detail metrics */}
      <div className="space-y-1.5 mb-3 text-[11px]">
        <MetricRow label="VIX/VIX3M Ratio" value={data.ratio} unit="" />
        <MetricRow
          label="Roll Yield (Daily)"
          value={data.rollYield}
          unit=""
          color={data.rollYield > 0 ? 'text-green-400' : 'text-red-400'}
        />
      </div>

      {/* Sparkline of ratio history */}
      {sparklineData.length > 0 && (
        <div className="mb-2">
          <div className="text-[9px] text-neutral-600 mb-1">30-Day Ratio Trend</div>
          <div className="h-10 bg-neutral-900/50 rounded p-1">
            <MiniSparkline data={sparklineData} height={32} />
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="text-[9px] text-neutral-600 text-center">
        {data.state === 'contango' ? (
          <span>Normal backlog • Rolling into strength</span>
        ) : (
          <span>Steep curve • Potential reversal</span>
        )}
      </div>
    </div>
  );
}
