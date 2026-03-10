import { useMemo } from 'react';
import { EarningsSignal, EarningsHistory, PEADData } from '../../lib/api';
import { EarningsSignalBadge } from './EarningsSignalBadge';
import { DivergenceIndicator } from './DivergenceIndicator';
import { SmartEstimateChart } from './SmartEstimateChart';
import { PEADChart } from './PEADChart';

interface EarningsDetailProps {
  signal: EarningsSignal | null;
  history: EarningsHistory[] | null;
  pead: PEADData[] | null;
  isLoading?: boolean;
  isHistoryLoading?: boolean;
  isPEADLoading?: boolean;
}

export function EarningsDetail({
  signal,
  history,
  pead,
  isLoading,
  isHistoryLoading,
  isPEADLoading,
}: EarningsDetailProps) {
  const stats = useMemo(() => {
    if (!history || history.length === 0) {
      return { avgSurprise: 0, smartEstimateAccuracy: 0, beatCount: 0 };
    }

    const avgSurprise = history.reduce((sum, h) => sum + h.surprise_pct, 0) / history.length;
    const beatCount = history.filter((h) => h.surprise_pct > 0).length;
    const smartEstimateDiffs = history.map((h) =>
      Math.abs(h.smart_estimate_eps - h.actual_eps)
    );
    const consensusDiffs = history.map((h) =>
      Math.abs(h.consensus_eps - h.actual_eps)
    );
    const smartEstimateAccuracy =
      100 -
      ((smartEstimateDiffs.reduce((a, b) => a + b, 0) / history.length) /
        (consensusDiffs.reduce((a, b) => a + b, 0) / history.length || 1)) *
        100;

    return {
      avgSurprise,
      smartEstimateAccuracy: Math.max(0, smartEstimateAccuracy),
      beatCount,
    };
  }, [history]);

  if (isLoading) {
    return (
      <div className="p-4 rounded border border-neutral-800 bg-[#0a0a0a] h-full flex items-center justify-center">
        <div className="text-xs text-neutral-500">Select a ticker to view details</div>
      </div>
    );
  }

  if (!signal) {
    return (
      <div className="p-4 rounded border border-neutral-800 bg-[#0a0a0a] h-full flex items-center justify-center">
        <div className="text-xs text-neutral-500">No data available</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 h-full overflow-y-auto">
      {/* Header with Ticker */}
      <div className="border-b border-neutral-800 pb-3">
        <h2 className="text-sm font-bold text-neutral-100 mb-3">{signal.ticker}</h2>

        {/* Signal Badge */}
        <div className="mb-4">
          <EarningsSignalBadge
            signal={signal.signal as 'buy' | 'sell' | 'hold'}
            confidence={signal.confidence}
            size="lg"
          />
        </div>

        {/* Divergence */}
        <DivergenceIndicator
          divergence={signal.divergence_pct}
          signal={signal.signal as 'buy' | 'sell' | 'hold'}
        />
      </div>

      {/* Smart Estimate vs Consensus */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-neutral-300">Estimate Comparison</h3>
        <div className="space-y-2 text-xs">
          <div className="flex justify-between items-center p-2 rounded bg-neutral-900">
            <span className="text-neutral-500">SmartEstimate EPS</span>
            <span className="font-semibold text-neutral-200">${signal.smart_eps.toFixed(2)}</span>
          </div>
          <div className="flex justify-between items-center p-2 rounded bg-neutral-900">
            <span className="text-neutral-500">Consensus EPS</span>
            <span className="font-semibold text-neutral-200">${signal.consensus_eps.toFixed(2)}</span>
          </div>
          <div className="flex justify-between items-center p-2 rounded bg-neutral-900">
            <span className="text-neutral-500">Days to Earnings</span>
            <span className="font-semibold text-neutral-200">{signal.days_to_earnings}d</span>
          </div>
        </div>
      </div>

      {/* Historical Stats */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-neutral-300">Historical Performance</h3>
        <div className="space-y-2 text-xs">
          <div className="flex justify-between items-center p-2 rounded bg-neutral-900">
            <span className="text-neutral-500">Avg Surprise (8Q)</span>
            <span
              className={classNames(
                'font-semibold',
                stats.avgSurprise > 0 ? 'text-emerald-400' : 'text-red-400'
              )}
            >
              {stats.avgSurprise > 0 ? '+' : ''}{stats.avgSurprise.toFixed(2)}%
            </span>
          </div>
          <div className="flex justify-between items-center p-2 rounded bg-neutral-900">
            <span className="text-neutral-500">Beat Rate (8Q)</span>
            <span className="font-semibold text-neutral-200">
              {((stats.beatCount / (history?.length || 1)) * 100).toFixed(0)}%
            </span>
          </div>
          <div className="flex justify-between items-center p-2 rounded bg-neutral-900">
            <span className="text-neutral-500">SmartEst Accuracy</span>
            <span className="font-semibold text-emerald-400">
              {stats.smartEstimateAccuracy.toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {/* Smart Estimate Chart */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-neutral-300">Estimate Accuracy (8Q)</h3>
        <SmartEstimateChart data={history || []} isLoading={isHistoryLoading} />
      </div>

      {/* PEAD Chart */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-neutral-300">Post-Earnings Drift</h3>
        <PEADChart data={pead || []} isLoading={isPEADLoading} />
      </div>
    </div>
  );
}

// Helper function for classNames
function classNames(...classes: any[]) {
  return classes.filter(Boolean).join(' ');
}
