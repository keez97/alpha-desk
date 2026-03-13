import { useBreadth } from '../../hooks/useBreadth';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import type { BreadthData } from '../../lib/api';

const SIGNAL_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  strongly_bullish: { bg: 'bg-green-900/40', text: 'text-green-400', label: 'Strong Bull' },
  bullish: { bg: 'bg-green-900/20', text: 'text-green-400', label: 'Bullish' },
  neutral: { bg: 'bg-neutral-800/50', text: 'text-neutral-400', label: 'Neutral' },
  bearish: { bg: 'bg-red-900/20', text: 'text-red-400', label: 'Bearish' },
  strongly_bearish: { bg: 'bg-red-900/40', text: 'text-red-400', label: 'Strong Bear' },
};

function ADBar({ advances, declines, total }: { advances: number; declines: number; total: number }) {
  if (total === 0) return null;
  const advPct = (advances / total) * 100;
  const decPct = (declines / total) * 100;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-green-400">{advances} Advancing</span>
        <span className="text-red-400">{declines} Declining</span>
      </div>
      <div className="h-2 rounded-full overflow-hidden flex bg-neutral-800">
        <div className="bg-green-500/70 h-full transition-all" style={{ width: `${advPct}%` }} />
        <div className="bg-neutral-700 h-full transition-all" style={{ width: `${100 - advPct - decPct}%` }} />
        <div className="bg-red-500/70 h-full transition-all" style={{ width: `${decPct}%` }} />
      </div>
    </div>
  );
}

function MetricBox({ label, value, subtext, color }: { label: string; value: string; subtext?: string; color?: string }) {
  return (
    <div className="text-center">
      <span className="text-xs text-neutral-500 block">{label}</span>
      <span className={`text-sm font-mono font-medium ${color || 'text-neutral-200'}`}>{value}</span>
      {subtext && <span className="text-xs text-neutral-500 block">{subtext}</span>}
    </div>
  );
}

export function BreadthPanel() {
  const { data, isLoading, error, refetch } = useBreadth();

  if (isLoading) return <LoadingState message="Loading breadth data..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data || data.total === 0) return null;

  const signal = SIGNAL_COLORS[data.signal] || SIGNAL_COLORS.neutral;
  const adColor = data.adRatio > 1.5 ? 'text-green-400' : data.adRatio < 0.67 ? 'text-red-400' : 'text-neutral-300';
  const mcColor = data.mcclellan > 0 ? 'text-green-400' : data.mcclellan < 0 ? 'text-red-400' : 'text-neutral-400';

  return (
    <div className={`border border-neutral-800 rounded p-3 ${signal.bg}`}>
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-xs font-medium text-neutral-300">Market Breadth</span>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${signal.text} bg-neutral-900/50`}>
          {signal.label}
        </span>
      </div>

      <ADBar advances={data.advances} declines={data.declines} total={data.total} />

      <div className="grid grid-cols-4 gap-2 mt-3">
        <MetricBox
          label="A/D Ratio"
          value={data.adRatio.toFixed(2)}
          subtext={data.adRatio > 1 ? 'net advancing' : 'net declining'}
          color={adColor}
        />
        <MetricBox
          label="Net Advances"
          value={data.netAdvances > 0 ? `+${data.netAdvances}` : `${data.netAdvances}`}
          color={data.netAdvances > 0 ? 'text-green-400' : 'text-red-400'}
        />
        <MetricBox
          label="McClellan"
          value={data.mcclellan.toFixed(1)}
          subtext={data.mcclellan > 0 ? 'positive' : 'negative'}
          color={mcColor}
        />
        <MetricBox
          label="Breadth Thrust"
          value={data.breadthThrust ? 'YES' : 'No'}
          subtext={`${data.pctAdvancing.toFixed(0)}% adv.`}
          color={data.breadthThrust ? 'text-green-400' : 'text-neutral-500'}
        />
      </div>

      <div className="mt-2 text-xs text-neutral-500 text-right">
        Based on {data.sampleSize} S&P 500 components
      </div>
    </div>
  );
}
