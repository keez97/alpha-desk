import { useSectorTransitions } from '../../hooks/useSectorTransitions';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';

function getRiskColor(significance: number): string {
  if (significance >= 80) return 'text-red-400';
  if (significance >= 60) return 'text-orange-400';
  if (significance >= 40) return 'text-yellow-400';
  return 'text-green-400';
}

function getRiskBg(significance: number): string {
  if (significance >= 80) return 'bg-red-950';
  if (significance >= 60) return 'bg-orange-950';
  if (significance >= 40) return 'bg-yellow-950';
  return 'bg-green-950';
}

function getFactorColor(value: number): string {
  if (value > 0.5) return 'text-green-400';
  if (value > 0) return 'text-emerald-400';
  if (value < -0.5) return 'text-red-400';
  return 'text-orange-400';
}

function getLabelBadgeColor(label: string): string {
  const positive = ['Strong Uptrend', 'Positive', 'Value Tilt', 'Small Cap Tilt', 'High Beta', 'Moderate'];
  const negative = ['Strong Downtrend', 'Negative', 'Growth Tilt', 'Large Cap Tilt', 'Very Defensive', 'Defensive'];
  if (positive.includes(label)) return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
  if (negative.includes(label)) return 'text-red-400 bg-red-400/10 border-red-400/20';
  return 'text-neutral-400 bg-neutral-400/10 border-neutral-400/20';
}

export function SectorTransitionsPanel() {
  const { data, isLoading, error, refetch } = useSectorTransitions();

  if (isLoading) return <LoadingState message="Loading sector transitions..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  const { transitions, factor_decomposition, cycle_overlay } = data;

  return (
    <div className="space-y-4">
      {/* Business Cycle Overlay */}
      <div className="border border-neutral-800 rounded p-3 bg-neutral-900/50">
        <h3 className="text-xs font-semibold text-neutral-300 mb-2 uppercase tracking-wider">
          Business Cycle: {cycle_overlay.current_phase.toUpperCase()}
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="text-xs text-neutral-500 uppercase mb-1">Favorable</div>
            <div className="flex flex-wrap gap-1">
              {cycle_overlay.favorable_sectors.map((sector) => (
                <span
                  key={sector}
                  className="px-2 py-1 text-xs font-medium bg-green-950 text-green-400 rounded"
                >
                  {sector}
                </span>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs text-neutral-500 uppercase mb-1">Unfavorable</div>
            <div className="flex flex-wrap gap-1">
              {cycle_overlay.unfavorable_sectors.map((sector) => (
                <span
                  key={sector}
                  className="px-2 py-1 text-xs font-medium bg-red-950 text-red-400 rounded"
                >
                  {sector}
                </span>
              ))}
            </div>
          </div>
        </div>
        <div className="text-xs text-neutral-500 mt-2">
          Recession Probability:{' '}
          <span className="text-neutral-300">
            {cycle_overlay.recession_probability !== null && cycle_overlay.recession_probability !== undefined
              ? `${cycle_overlay.recession_probability.toFixed(1)}%`
              : '—'}
          </span>
        </div>
      </div>

      {/* Quadrant Transitions */}
      {transitions.length > 0 && (
        <div className="border border-neutral-800 rounded overflow-hidden">
          <div className="bg-neutral-900/50 px-3 py-2 border-b border-neutral-800">
            <h3 className="text-xs font-semibold text-neutral-300 uppercase tracking-wider">
              Quadrant Transitions
            </h3>
          </div>
          <div className="divide-y divide-neutral-800">
            {transitions.map((t) => (
              <div key={t.ticker} className={`px-3 py-2 ${getRiskBg(t.significance)}`}>
                <div className="flex items-center justify-between mb-1">
                  <div className="font-mono text-sm font-bold text-neutral-200">{t.ticker}</div>
                  <div className={`text-xs font-semibold ${getRiskColor(t.significance)}`}>
                    {t.significance.toFixed(0)}
                  </div>
                </div>
                <div className="text-xs text-neutral-400">
                  {t.name}: {t.from_quadrant} → {t.to_quadrant}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Factor Decomposition */}
      <div className="border border-neutral-800 rounded overflow-hidden">
        <div className="bg-neutral-900/50 px-3 py-2 border-b border-neutral-800">
          <h3 className="text-xs font-semibold text-neutral-300 uppercase tracking-wider">
            Factor Decomposition
          </h3>
        </div>
        <div className="divide-y divide-neutral-800">
          {factor_decomposition.map((f) => {
            const factors = [
              { name: 'β', value: f.beta_contribution, label: f.beta_label },
              { name: 'Size', value: f.size_contribution, label: f.size_label },
              { name: 'Value', value: f.value_contribution, label: f.value_label },
              { name: 'Mom', value: f.momentum_contribution, label: f.momentum_label },
            ];

            return (
              <div key={f.ticker} className="px-3 py-2 hover:bg-neutral-900/50">
                <div className="font-mono text-sm font-semibold text-neutral-200 mb-1">{f.ticker}</div>
                <div className="grid grid-cols-4 gap-2">
                  {factors.map((fac) => (
                    <div key={fac.name} className="text-center">
                      <div className="text-xs text-neutral-500 mb-0.5">{fac.name}</div>
                      <div className={`text-xs font-mono font-semibold ${getFactorColor(fac.value)}`}>
                        {fac.value > 0 ? '+' : ''}{fac.value.toFixed(2)}
                      </div>
                      {fac.label && (
                        <span className={`inline-block mt-0.5 text-xs px-1 py-px rounded border font-medium ${getLabelBadgeColor(fac.label)}`}>
                          {fac.label}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* No Data State */}
      {transitions.length === 0 && factor_decomposition.length === 0 && (
        <div className="text-center py-6 text-neutral-500 text-xs">
          No significant transitions detected
        </div>
      )}
    </div>
  );
}
