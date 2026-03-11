import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchUpgradedRegime } from '../../lib/api';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import type { UpgradedRegimeData, RegimeSignal } from '../../lib/api';

const REGIME_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  bull: { bg: 'bg-green-900/40', text: 'text-green-400', label: 'BULL' },
  bear: { bg: 'bg-red-900/40', text: 'text-red-400', label: 'BEAR' },
  neutral: { bg: 'bg-neutral-800/50', text: 'text-neutral-400', label: 'NEUTRAL' },
};

function ConfidenceBar({ value }: { value: number }) {
  const barColor = value > 75 ? 'bg-green-500' : value > 50 ? 'bg-yellow-500' : 'bg-neutral-600';

  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-[10px]">
        <span className="text-neutral-500">Confidence</span>
        <span className="font-mono text-neutral-300">{value.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-neutral-800 overflow-hidden">
        <div className={`${barColor} h-full transition-all`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function SignalItem({ signal }: { signal: RegimeSignal }) {
  const biasColors: Record<string, string> = {
    bull: 'text-green-400',
    bear: 'text-red-400',
    neutral: 'text-neutral-400',
  };

  return (
    <div className="flex justify-between items-center text-xs py-1">
      <div>
        <div className="font-medium text-neutral-300">{signal.name}</div>
        <div className="text-[9px] text-neutral-600">{signal.reading}</div>
      </div>
      <div className="text-right">
        <div className={`font-mono font-bold ${biasColors[signal.bias]}`}>{signal.value}</div>
        <div className="text-[9px] text-neutral-600">{signal.bias}</div>
      </div>
    </div>
  );
}

function RecessionProbabilityMeter({ probability }: { probability: number }) {
  let color = 'text-green-400';
  let bgColor = 'bg-green-900/20';
  let label = 'Low Risk';

  if (probability > 70) {
    color = 'text-red-400';
    bgColor = 'bg-red-900/20';
    label = 'High Risk';
  } else if (probability > 40) {
    color = 'text-yellow-400';
    bgColor = 'bg-yellow-900/20';
    label = 'Moderate Risk';
  }

  return (
    <div className={`border border-neutral-800 rounded p-2 ${bgColor}`}>
      <div className="text-[9px] text-neutral-500 mb-1">Recession Probability (Estrella)</div>
      <div className={`text-lg font-mono font-bold ${color}`}>{probability.toFixed(1)}%</div>
      <div className="text-[9px] text-neutral-600">{label}</div>
    </div>
  );
}

function MetricBox({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value: number;
  unit: string;
  color?: string;
}) {
  return (
    <div className="text-center">
      <span className="text-[9px] text-neutral-500 block">{label}</span>
      <span className={`text-sm font-mono font-bold ${color || 'text-neutral-200'}`}>
        {value > 0 ? '+' : ''}{value.toFixed(2)}{unit}
      </span>
    </div>
  );
}

function CorrelationRegimeBadge({ regime }: { regime: string }) {
  const isShift = regime === 'regime_shift';
  const bgColor = isShift ? 'bg-yellow-900/30' : 'bg-green-900/20';
  const textColor = isShift ? 'text-yellow-400' : 'text-green-400';

  return (
    <div className={`border border-neutral-800 rounded p-2 text-center ${bgColor}`}>
      <div className="text-[9px] text-neutral-500 mb-1">Correlation Regime</div>
      <div className={`text-xs font-mono font-bold ${textColor}`}>
        {isShift ? 'SHIFT' : 'NORMAL'}
      </div>
    </div>
  );
}

export function RegimePanel() {
  const [showAllSignals, setShowAllSignals] = useState(false);
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['regime'],
    queryFn: fetchUpgradedRegime,
    staleTime: 5 * 60 * 1000,
    retry: 2,
    retryDelay: 2000,
  });

  if (isLoading) return <LoadingState message="Loading regime..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  const regimeColor = REGIME_COLORS[data.regime] || REGIME_COLORS.neutral;

  return (
    <div className={`border border-neutral-800 rounded p-3 ${regimeColor.bg}`}>
      {/* Header with regime label */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-neutral-300">Market Regime</span>
        <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${regimeColor.text} bg-neutral-900/50`}>
          {regimeColor.label}
        </span>
      </div>

      {/* Confidence bar */}
      <div className="mb-3">
        <ConfidenceBar value={data.confidence} />
      </div>

      {/* Key metrics grid */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <RecessionProbabilityMeter probability={data.recessionProbability} />
        <CorrelationRegimeBadge regime={data.correlationRegime} />
      </div>

      {/* Macro surprise score */}
      <div className="mb-3">
        <div className="grid grid-cols-1 gap-2">
          <MetricBox
            label="Macro Surprise"
            value={data.macroSurpriseScore}
            unit=""
            color={
              data.macroSurpriseScore > 0
                ? 'text-green-400'
                : data.macroSurpriseScore < 0
                  ? 'text-red-400'
                  : 'text-neutral-400'
            }
          />
        </div>
      </div>

      {/* Score breakdown */}
      <div className="border-t border-neutral-800 pt-2 mb-3">
        <div className="grid grid-cols-2 gap-2 text-center text-xs mb-2">
          <div>
            <span className="text-neutral-500 block text-[9px]">Bull Signals</span>
            <span className="font-mono font-bold text-green-400">{data.bullScore}</span>
          </div>
          <div>
            <span className="text-neutral-500 block text-[9px]">Bear Signals</span>
            <span className="font-mono font-bold text-red-400">{data.bearScore}</span>
          </div>
        </div>
      </div>

      {/* Contributing signals */}
      {data.signals && data.signals.length > 0 && (
        <div className="space-y-1 border-t border-neutral-800 pt-2">
          <div className="text-[9px] text-neutral-500 mb-1">Key Signals</div>
          {data.signals.slice(0, showAllSignals ? data.signals.length : 3).map((signal, i) => (
            <SignalItem key={i} signal={signal} />
          ))}
          {data.signals.length > 3 && (
            <button
              onClick={() => setShowAllSignals(!showAllSignals)}
              className="text-[9px] text-blue-400 hover:text-blue-300 text-center mt-1 w-full cursor-pointer transition-colors"
            >
              {showAllSignals ? 'Show fewer' : `+${data.signals.length - 3} more signals`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
