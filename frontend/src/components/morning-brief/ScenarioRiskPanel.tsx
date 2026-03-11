import { useScenarioRisk } from '../../hooks/useScenarioRisk';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';

function getRiskColor(severity: string): string {
  if (severity === 'high') return 'text-red-400';
  if (severity === 'moderate') return 'text-orange-400';
  if (severity === 'mild') return 'text-yellow-400';
  return 'text-green-400';
}

function getRiskBg(severity: string): string {
  if (severity === 'high') return 'bg-red-950';
  if (severity === 'moderate') return 'bg-orange-950';
  if (severity === 'mild') return 'bg-yellow-950';
  return 'bg-green-950';
}

function getVaRColor(value: number): string {
  if (Math.abs(value) > 3) return 'text-red-400';
  if (Math.abs(value) > 2) return 'text-orange-400';
  if (Math.abs(value) > 1) return 'text-yellow-400';
  return 'text-green-400';
}

export function ScenarioRiskPanel() {
  const { data, isLoading, error, refetch } = useScenarioRisk();

  if (isLoading) return <LoadingState message="Loading scenario risk..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  const {
    var_95_historical,
    var_95_regime_adjusted,
    current_regime,
    historical_analogs,
    scenarios,
  } = data;

  return (
    <div className="space-y-4">
      {/* VaR Comparison */}
      <div className="border border-neutral-800 rounded p-3 bg-neutral-900/50">
        <h3 className="text-xs font-semibold text-neutral-300 mb-3 uppercase tracking-wider">
          Value-at-Risk (95% Confidence)
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="text-[10px] text-neutral-500 uppercase mb-1">Historical VaR</div>
            <div className={`text-lg font-mono font-bold ${getVaRColor(var_95_historical)}`}>
              {var_95_historical.toFixed(2)}%
            </div>
          </div>
          <div>
            <div className="text-[10px] text-neutral-500 uppercase mb-1">
              Regime-Adjusted ({current_regime})
            </div>
            <div className={`text-lg font-mono font-bold ${getVaRColor(var_95_regime_adjusted)}`}>
              {var_95_regime_adjusted.toFixed(2)}%
            </div>
          </div>
        </div>
      </div>

      {/* Scenario Cards */}
      <div className="border border-neutral-800 rounded overflow-hidden">
        <div className="bg-neutral-900/50 px-3 py-2 border-b border-neutral-800">
          <h3 className="text-xs font-semibold text-neutral-300 uppercase tracking-wider">
            Stress Scenarios
          </h3>
        </div>
        <div className="divide-y divide-neutral-800">
          {scenarios.map((scenario) => (
            <div
              key={scenario.name}
              className={`px-3 py-2 ${getRiskBg(scenario.severity)} hover:opacity-80 transition-opacity`}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="font-semibold text-sm text-neutral-200">{scenario.name}</div>
                <div className={`text-sm font-mono font-bold ${getRiskColor(scenario.severity)}`}>
                  {scenario.estimated_impact_pct > 0 ? '+' : ''}{scenario.estimated_impact_pct.toFixed(1)}%
                </div>
              </div>
              <div className="text-xs text-neutral-400 mb-1">{scenario.description}</div>
              <div className="flex items-center justify-between text-[10px]">
                <div className="text-neutral-500">
                  Probability: <span className="text-neutral-300">{(scenario.probability * 100).toFixed(0)}%</span>
                </div>
                <div className="text-neutral-500">
                  <span className="text-neutral-300 capitalize">{scenario.severity}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Historical Analogs */}
      {historical_analogs.length > 0 && (
        <div className="border border-neutral-800 rounded overflow-hidden">
          <div className="bg-neutral-900/50 px-3 py-2 border-b border-neutral-800">
            <h3 className="text-xs font-semibold text-neutral-300 uppercase tracking-wider">
              Historical Analogs
            </h3>
            <div className="text-[10px] text-neutral-500 mt-1">
              Similar past periods and subsequent returns
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-neutral-800 bg-neutral-900/50">
                  <th className="px-3 py-2 text-left text-[10px] text-neutral-500 font-medium uppercase">Period</th>
                  <th className="px-3 py-2 text-center text-[10px] text-neutral-500 font-medium uppercase">Similarity</th>
                  <th className="px-3 py-2 text-right text-[10px] text-neutral-500 font-medium uppercase">5D</th>
                  <th className="px-3 py-2 text-right text-[10px] text-neutral-500 font-medium uppercase">10D</th>
                  <th className="px-3 py-2 text-right text-[10px] text-neutral-500 font-medium uppercase">20D</th>
                </tr>
              </thead>
              <tbody>
                {historical_analogs.map((analog) => (
                  <tr key={analog.period} className="border-b border-neutral-900 hover:bg-neutral-900/50">
                    <td className="px-3 py-2 font-mono text-neutral-400">{analog.period}</td>
                    <td className="px-3 py-2 text-center font-semibold text-neutral-300">
                      {analog.similarity_score.toFixed(0)}
                    </td>
                    <td
                      className={`px-3 py-2 text-right font-mono font-semibold ${
                        analog.subsequent_5d_return > 0 ? 'text-green-400' : 'text-red-400'
                      }`}
                    >
                      {analog.subsequent_5d_return > 0 ? '+' : ''}
                      {analog.subsequent_5d_return.toFixed(1)}%
                    </td>
                    <td
                      className={`px-3 py-2 text-right font-mono font-semibold ${
                        analog.subsequent_10d_return > 0 ? 'text-green-400' : 'text-red-400'
                      }`}
                    >
                      {analog.subsequent_10d_return > 0 ? '+' : ''}
                      {analog.subsequent_10d_return.toFixed(1)}%
                    </td>
                    <td
                      className={`px-3 py-2 text-right font-mono font-semibold ${
                        analog.subsequent_20d_return > 0 ? 'text-green-400' : 'text-red-400'
                      }`}
                    >
                      {analog.subsequent_20d_return > 0 ? '+' : ''}
                      {analog.subsequent_20d_return.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* No Data State */}
      {scenarios.length === 0 && historical_analogs.length === 0 && (
        <div className="text-center py-6 text-neutral-500 text-xs">
          No scenario data available
        </div>
      )}
    </div>
  );
}
