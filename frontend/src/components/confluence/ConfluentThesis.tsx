import { SignalCard } from './SignalCard';
import type { ConfluenceResponse } from '../../hooks/useConfluence';

interface ConfluentThesisProps {
  data: ConfluenceResponse;
  isLoading: boolean;
}

export function ConfluentThesis({ data, isLoading }: ConfluentThesisProps) {
  if (isLoading) {
    return (
      <div className="border border-neutral-800 rounded-lg p-6 bg-neutral-900/50">
        <div className="flex items-center justify-center h-48">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-neutral-700 border-t-neutral-400 rounded-full animate-spin mx-auto mb-2" />
            <p className="text-sm text-neutral-500">Loading confluence signals...</p>
          </div>
        </div>
      </div>
    );
  }

  const signals = data.signals || [];
  const highConviction = signals.filter(s => s.conviction === 'HIGH');
  const mediumConviction = signals.filter(s => s.conviction === 'MEDIUM');
  const lowConviction = signals.filter(s => s.conviction === 'LOW');

  const regime = data.macro_regime || {};

  return (
    <div className="space-y-6">
      {/* Macro Regime Summary */}
      <div className="border border-neutral-800 rounded-lg p-4 bg-neutral-900/50">
        <h3 className="text-sm font-semibold text-neutral-200 mb-3">Market Regime</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div>
            <p className="text-neutral-500 mb-1">Overall</p>
            <p className="text-neutral-200 font-medium capitalize">
              {regime.regime || 'Neutral'}
            </p>
          </div>
          <div>
            <p className="text-neutral-500 mb-1">VIX Signal</p>
            <p className={`font-medium ${
              regime.vix_signal === 'bullish' ? 'text-green-400' :
              regime.vix_signal === 'bearish' ? 'text-red-400' :
              'text-gray-400'
            }`}>
              {regime.vix_signal ? regime.vix_signal.charAt(0).toUpperCase() + regime.vix_signal.slice(1) : 'Neutral'}
            </p>
          </div>
          <div>
            <p className="text-neutral-500 mb-1">Yields</p>
            <p className={`font-medium ${regime.yield_rising ? 'text-red-400' : 'text-green-400'}`}>
              {regime.yield_rising ? 'Rising' : 'Falling'}
            </p>
          </div>
          <div>
            <p className="text-neutral-500 mb-1">Dollar</p>
            <p className={`font-medium ${regime.dollar_weakening ? 'text-green-400' : 'text-red-400'}`}>
              {regime.dollar_weakening ? 'Weakening' : 'Strengthening'}
            </p>
          </div>
        </div>
      </div>

      {/* High Conviction Signals */}
      {highConviction.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
            <span className="w-1 h-1 bg-amber-400 rounded-full" />
            High Conviction Signals ({highConviction.length})
          </h3>
          <div className="grid gap-3">
            {highConviction.map((signal, idx) => (
              <SignalCard key={idx} signal={signal} />
            ))}
          </div>
        </div>
      )}

      {/* Medium Conviction Signals */}
      {mediumConviction.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-yellow-400 mb-3 flex items-center gap-2">
            <span className="w-1 h-1 bg-yellow-400 rounded-full" />
            Medium Conviction Signals ({mediumConviction.length})
          </h3>
          <div className="grid gap-3">
            {mediumConviction.map((signal, idx) => (
              <SignalCard key={idx} signal={signal} />
            ))}
          </div>
        </div>
      )}

      {/* Low Conviction Signals */}
      {lowConviction.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
            <span className="w-1 h-1 bg-gray-400 rounded-full" />
            Low Conviction Signals ({lowConviction.length})
          </h3>
          <div className="grid gap-3">
            {lowConviction.map((signal, idx) => (
              <SignalCard key={idx} signal={signal} />
            ))}
          </div>
        </div>
      )}

      {/* No Signals State */}
      {signals.length === 0 && (
        <div className="border border-neutral-800 rounded-lg p-8 bg-neutral-900/50 text-center">
          <p className="text-sm text-neutral-500">
            No confluence signals detected. Waiting for multiple signal sources to align.
          </p>
        </div>
      )}
    </div>
  );
}
