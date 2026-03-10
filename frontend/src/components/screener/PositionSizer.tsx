import { usePositionSizing, type PositionSizing } from '../../hooks/usePositionSizing';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { classNames } from '../../lib/utils';

interface PositionSizerProps {
  ticker: string | null;
  portfolioValue?: number;
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'from-green-600 to-emerald-600';
  if (score >= 60) return 'from-blue-600 to-cyan-600';
  if (score >= 40) return 'from-amber-600 to-yellow-600';
  if (score >= 20) return 'from-orange-600 to-red-500';
  return 'from-red-700 to-red-800';
}

function getCategoryColor(category: string): string {
  switch (category) {
    case 'Full Size':
      return 'bg-green-950/40 text-green-400 border-green-900/50';
    case 'Three-Quarter':
      return 'bg-blue-950/40 text-blue-400 border-blue-900/50';
    case 'Half Size':
      return 'bg-amber-950/40 text-amber-400 border-amber-900/50';
    case 'Quarter Size':
      return 'bg-orange-950/40 text-orange-400 border-orange-900/50';
    case 'Avoid':
      return 'bg-red-950/40 text-red-400 border-red-900/50';
    default:
      return 'bg-neutral-900/40 text-neutral-400 border-neutral-800/50';
  }
}

function CircularGauge({ score, size = 120 }: { score: number; size?: number }) {
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (score / 100) * circumference;
  const angle = (score / 100) * 360;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
        style={{ filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.4))' }}
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={45}
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth={4}
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={45}
          fill="none"
          stroke="url(#scoreGradient)"
          strokeWidth={4}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.3s ease' }}
        />
        <defs>
          <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            {score >= 80 && (
              <>
                <stop offset="0%" stopColor="#16a34a" />
                <stop offset="100%" stopColor="#059669" />
              </>
            )}
            {score >= 60 && score < 80 && (
              <>
                <stop offset="0%" stopColor="#2563eb" />
                <stop offset="100%" stopColor="#0891b2" />
              </>
            )}
            {score >= 40 && score < 60 && (
              <>
                <stop offset="0%" stopColor="#d97706" />
                <stop offset="100%" stopColor="#eab308" />
              </>
            )}
            {score >= 20 && score < 40 && (
              <>
                <stop offset="0%" stopColor="#ea580c" />
                <stop offset="100%" stopColor="#dc2626" />
              </>
            )}
            {score < 20 && (
              <>
                <stop offset="0%" stopColor="#b91c1c" />
                <stop offset="100%" stopColor="#7f1d1d" />
              </>
            )}
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <div className="text-2xl font-bold text-neutral-100">{score.toFixed(0)}</div>
          <div className="text-xs text-neutral-500">Score</div>
        </div>
      </div>
    </div>
  );
}

function FactorBreakdownBars({ data }: { data: PositionSizing }) {
  return (
    <div className="space-y-2">
      {data.factorBreakdown.map((factor) => (
        <div key={factor.name} className="space-y-0.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-neutral-400">{factor.name}</span>
            <span className="text-xs font-mono text-neutral-500">
              {factor.percentile.toFixed(0)}%
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-neutral-800/50 rounded h-1 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-600 to-cyan-600"
                style={{ width: `${factor.percentile}%` }}
              />
            </div>
            <span className="text-xs text-neutral-600 w-10 text-right">
              {(factor.contribution).toFixed(1)}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

function RiskNotes({ notes }: { notes: string[] }) {
  return (
    <div className="space-y-1">
      {notes.map((note, i) => (
        <div key={i} className="flex items-start gap-2 text-xs text-neutral-400">
          <div className="w-1 h-1 rounded-full bg-neutral-600 mt-1.5 flex-shrink-0" />
          <span>{note}</span>
        </div>
      ))}
    </div>
  );
}

export function PositionSizer({
  ticker,
  portfolioValue = 100000,
}: PositionSizerProps) {
  const { data, isLoading, error, refetch } = usePositionSizing(ticker, portfolioValue);

  if (!ticker) return null;
  if (isLoading) return <LoadingState message="Computing position sizing..." />;
  if (error)
    return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  const categoryColor = getCategoryColor(data.sizeCategory);
  const portfolioValueFormatted = (portfolioValue / 1000).toFixed(0);

  return (
    <div className="space-y-6 rounded-lg border border-neutral-800/50 bg-[#0a0a0a] p-4">
      {/* Header */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-neutral-100">Position Sizing</h3>

        {/* Score Gauge */}
        <div className="flex justify-center">
          <CircularGauge score={data.compositeScore} size={140} />
        </div>

        {/* Size Category Badge */}
        <div className="flex justify-center">
          <div
            className={classNames(
              'px-3 py-1.5 rounded border text-sm font-medium transition-colors',
              categoryColor
            )}
          >
            {data.sizeCategory}
          </div>
        </div>

        {/* Allocation Info */}
        <div className="bg-neutral-900/40 rounded p-3 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-neutral-400">Suggested Allocation</span>
            <span className="text-sm font-mono font-semibold text-neutral-200">
              {data.sizePct.toFixed(2)}%
            </span>
          </div>
          <div className="w-full bg-neutral-800/50 rounded h-1.5 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-600 to-cyan-600"
              style={{ width: `${Math.min(100, data.sizePct * 10)}%` }}
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-neutral-500">Position Value</span>
            <span className="text-xs font-mono text-green-400">
              ${(data.positionValue / 1000).toFixed(2)}K of ${portfolioValueFormatted}K portfolio
            </span>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="h-px bg-neutral-800/30" />

      {/* Factor Breakdown */}
      <div className="space-y-3">
        <h4 className="text-xs font-semibold text-neutral-300 uppercase tracking-wide">
          Factor Breakdown
        </h4>
        <FactorBreakdownBars data={data} />
      </div>

      {/* Risk Notes */}
      {data.riskNotes.length > 0 && (
        <>
          <div className="h-px bg-neutral-800/30" />
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-neutral-300 uppercase tracking-wide">
              Risk Notes
            </h4>
            <RiskNotes notes={data.riskNotes} />
          </div>
        </>
      )}

      {/* Kelly & Stop Loss */}
      <div className="h-px bg-neutral-800/30" />
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-neutral-900/30 rounded p-2.5 space-y-1">
          <div className="text-xs text-neutral-500">Kelly Fraction</div>
          <div className="text-sm font-mono font-semibold text-amber-400">
            {(data.kellyFraction * 100).toFixed(1)}%
          </div>
        </div>
        <div className="bg-neutral-900/30 rounded p-2.5 space-y-1">
          <div className="text-xs text-neutral-500">Suggested Stop</div>
          <div className="text-sm font-mono font-semibold text-red-400">
            -{data.stopLoss.toFixed(2)}%
          </div>
        </div>
      </div>
    </div>
  );
}
