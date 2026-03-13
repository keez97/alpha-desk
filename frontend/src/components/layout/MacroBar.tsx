import { useState } from 'react';
import { DeltaBadge } from '../shared/DeltaBadge';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { useMacro } from '../../hooks/useMacro';

const REGIME_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  bull: { bg: 'bg-green-900/50 border-green-700/50', text: 'text-green-400', label: 'BULL' },
  bear: { bg: 'bg-red-900/50 border-red-700/50', text: 'text-red-400', label: 'BEAR' },
  neutral: { bg: 'bg-yellow-900/50 border-yellow-700/50', text: 'text-yellow-400', label: 'NEUTRAL' },
};

function RegimeBadge({ regime }: { regime: any }) {
  const [showTooltip, setShowTooltip] = useState(false);
  if (!regime || !regime.regime) return null;

  const style = REGIME_STYLES[regime.regime] || REGIME_STYLES.neutral;
  const signals = regime.signals || [];

  return (
    <div className="relative flex-shrink-0">
      <button
        className={`px-3 py-2 bg-black border-r border-neutral-800 h-full flex flex-col items-center justify-center`}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <span className="text-xs text-neutral-500 uppercase tracking-wider">Regime</span>
        <span className={`text-xs font-bold mt-0.5 px-2 py-0.5 rounded border ${style.bg} ${style.text}`}>
          {style.label}
        </span>
        <span className="text-xs text-neutral-500 mt-0.5">{regime.confidence}%</span>
      </button>

      {showTooltip && signals.length > 0 && (
        <div className="absolute top-full left-0 mt-1 z-50 bg-neutral-900 border border-neutral-700 rounded p-2 shadow-lg min-w-48">
          <span className="text-xs text-neutral-400 font-medium block mb-1">Contributing Signals</span>
          {signals.map((s: any, i: number) => (
            <div key={i} className="flex items-center justify-between gap-3 py-0.5">
              <span className="text-xs text-neutral-400">{s.name}</span>
              <span className="text-xs font-mono text-neutral-300">{s.value}</span>
              <span className={`text-xs ${
                s.bias === 'bull' ? 'text-green-400' : s.bias === 'bear' ? 'text-red-400' : 'text-neutral-500'
              }`}>
                {s.reading}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function MacroBar() {
  const { data, isLoading, error, refetch } = useMacro();

  if (isLoading) return <LoadingState message="Loading macro data..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  return (
    <div className="flex gap-px overflow-x-auto bg-neutral-900 border-b border-neutral-800" aria-label="Market data ticker bar">
      {data.regime && <RegimeBadge regime={data.regime} />}
      {data.indicators.map((indicator: any) => (
        <div key={indicator.name} className="flex-shrink-0 px-4 py-2 bg-black">
          <div className="text-xs text-neutral-500 uppercase tracking-wider">{indicator.name}</div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="font-mono text-sm font-medium text-neutral-200">{indicator.value.toFixed(2)}</span>
            {indicator.change == null ? (
              <span className="inline-block text-xs font-mono text-neutral-500">N/A</span>
            ) : (
              <DeltaBadge value={indicator.change} format="pct" />
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
