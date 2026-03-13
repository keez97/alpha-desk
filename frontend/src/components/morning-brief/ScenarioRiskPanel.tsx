import { useState, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useScenarioRisk } from '../../hooks/useScenarioRisk';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import api from '../../lib/api';

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
  const queryClient = useQueryClient();
  const [expandedScenario, setExpandedScenario] = useState<string | null>(null);
  const [drilldownData, setDrilldownData] = useState<Record<string, any>>({});
  const [loadingDrilldown, setLoadingDrilldown] = useState<string | null>(null);
  const claudeFetched = useRef(false);

  // Background: fetch Claude-generated scenarios after initial load
  useEffect(() => {
    if (!data || claudeFetched.current) return;
    claudeFetched.current = true;
    api.get('/morning-brief/scenarios').then(res => {
      const scenarios = res.data?.data?.scenarios;
      if (scenarios && scenarios.length > 0 && res.data?.data?.source === 'claude') {
        // Update cached scenario risk data with Claude scenarios
        queryClient.setQueryData(['scenarioRisk'], (old: any) =>
          old ? { ...old, scenarios } : old
        );
      }
    }).catch(() => { /* silent — fallback scenarios still shown */ });
  }, [data, queryClient]);

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

  const handleScenarioClick = async (scenarioName: string) => {
    if (expandedScenario === scenarioName) {
      setExpandedScenario(null);
      return;
    }

    // Check if we already have this drilldown cached
    if (drilldownData[scenarioName]) {
      setExpandedScenario(scenarioName);
      return;
    }

    // Fetch drill-down data
    setLoadingDrilldown(scenarioName);
    try {
      const response = await api.get('/morning-brief/scenario-drilldown', {
        params: { scenario_name: scenarioName }
      });
      setDrilldownData(prev => ({
        ...prev,
        [scenarioName]: response.data.data
      }));
      setExpandedScenario(scenarioName);
    } catch (err) {
      console.error('Failed to fetch scenario drilldown:', err);
      setDrilldownData(prev => ({
        ...prev,
        [scenarioName]: { error: 'Failed to load drill-down data' }
      }));
      setExpandedScenario(scenarioName);
    } finally {
      setLoadingDrilldown(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* VaR Comparison */}
      <div className="border border-neutral-800 rounded p-3 bg-neutral-900/50">
        <h3 className="text-xs font-semibold text-neutral-300 mb-3 tracking-wider">
          Value-at-Risk (95% Confidence)
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="text-xs text-neutral-500 uppercase mb-1">Historical VaR</div>
            <div className={`text-lg font-mono font-bold ${getVaRColor(var_95_historical)}`}>
              {var_95_historical > 0 ? '▼ ' : ''}−{var_95_historical.toFixed(2)}%
            </div>
          </div>
          <div>
            <div className="text-xs text-neutral-500 uppercase mb-1">
              Regime-Adjusted ({current_regime})
            </div>
            <div className={`text-lg font-mono font-bold ${getVaRColor(var_95_regime_adjusted)}`}>
              {var_95_regime_adjusted > 0 ? '▼ ' : ''}−{var_95_regime_adjusted.toFixed(2)}%
            </div>
          </div>
        </div>
      </div>

      {/* Scenario Cards */}
      <div className="border border-neutral-800 rounded overflow-hidden">
        <div className="bg-neutral-900/50 px-3 py-2 border-b border-neutral-800">
          <h3 className="text-xs font-semibold text-neutral-300 tracking-wider">
            Stress Scenarios
          </h3>
        </div>
        <div className="divide-y divide-neutral-800">
          {scenarios.map((scenario) => {
            const isExpanded = expandedScenario === scenario.name;
            const drilldown = drilldownData[scenario.name];
            const isLoading = loadingDrilldown === scenario.name;

            return (
              <div key={scenario.name}>
                <div
                  onClick={() => handleScenarioClick(scenario.name)}
                  className={`px-3 py-2 ${getRiskBg(scenario.severity)} hover:opacity-80 transition-opacity cursor-pointer`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="font-semibold text-sm text-neutral-200">{scenario.name}</div>
                    <div className={`text-sm font-mono font-bold ${getRiskColor(scenario.severity)}`}>
                      {scenario.estimated_impact_pct < 0 ? '▼ ' : '▲ '}{scenario.estimated_impact_pct > 0 ? '+' : ''}{scenario.estimated_impact_pct.toFixed(1)}%
                    </div>
                  </div>
                  <div className="text-xs text-neutral-400 mb-2">{scenario.description}</div>

                  {/* Probability reasoning */}
                  {scenario.probability_reasoning && (
                    <div className="text-xs text-neutral-400 mb-2">
                      <span className="text-neutral-500">Why: </span>{scenario.probability_reasoning}
                    </div>
                  )}

                  {/* Affected sectors badges */}
                  {scenario.affected_sectors && scenario.affected_sectors.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {scenario.affected_sectors.slice(0, 4).map(sector => (
                        <span key={sector} className="bg-neutral-800 text-neutral-300 px-2 py-0.5 rounded text-xs">
                          {sector}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Historical analog */}
                  {scenario.historical_analog && (
                    <div className="text-xs text-neutral-400 mb-2">
                      <span className="text-neutral-500">Analog: </span>{scenario.historical_analog}
                    </div>
                  )}

                  {/* Key indicators */}
                  {scenario.key_indicators && scenario.key_indicators.length > 0 && (
                    <div className="text-xs text-neutral-400 mb-1">
                      <span className="text-neutral-500">Watch: </span>
                      {scenario.key_indicators.slice(0, 2).join(', ')}
                    </div>
                  )}

                  {/* Probability and severity */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="text-neutral-500">
                      Probability: <span className="text-neutral-300">{(scenario.probability * 100).toFixed(0)}%</span>
                    </div>
                    <div className="text-neutral-500">
                      <span className="text-neutral-300 capitalize">{scenario.severity}</span>
                    </div>
                  </div>
                </div>

                {/* Drill-down content */}
                {isExpanded && (
                  <div className="bg-neutral-900/30 px-3 py-3 border-t border-neutral-800 text-xs">
                    {isLoading ? (
                      <div className="text-neutral-500 text-center py-2">Loading analysis...</div>
                    ) : drilldown?.error ? (
                      <div className="text-red-400 text-center py-2">{drilldown.error}</div>
                    ) : drilldown ? (
                      <div className="space-y-3">
                        {/* Transmission Mechanism */}
                        {drilldown.transmission_mechanism && (
                          <div>
                            <div className="font-semibold text-neutral-300 mb-1">Transmission Mechanism</div>
                            <div className="text-neutral-400 text-xs">{drilldown.transmission_mechanism}</div>
                          </div>
                        )}

                        {/* Historical Precedent */}
                        {drilldown.historical_precedent && (
                          <div>
                            <div className="font-semibold text-neutral-300 mb-1">Historical Precedent</div>
                            <div className="text-neutral-400 text-xs">{drilldown.historical_precedent}</div>
                          </div>
                        )}

                        {/* Portfolio Positioning */}
                        {drilldown.portfolio_positioning && (
                          <div>
                            <div className="font-semibold text-neutral-300 mb-1">Positioning Ideas</div>
                            <ul className="text-neutral-400 text-xs list-disc list-inside space-y-0.5">
                              {(Array.isArray(drilldown.portfolio_positioning)
                                ? drilldown.portfolio_positioning
                                : [drilldown.portfolio_positioning]
                              ).map((item: string, idx: number) => (
                                <li key={idx}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Leading Indicators */}
                        {drilldown.leading_indicators && (
                          <div>
                            <div className="font-semibold text-neutral-300 mb-1">Leading Indicators to Watch</div>
                            <ul className="text-neutral-400 text-xs list-disc list-inside space-y-0.5">
                              {(Array.isArray(drilldown.leading_indicators)
                                ? drilldown.leading_indicators
                                : [drilldown.leading_indicators]
                              ).map((item: string, idx: number) => (
                                <li key={idx}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Counter Argument */}
                        {drilldown.counter_argument && (
                          <div>
                            <div className="font-semibold text-neutral-300 mb-1">Counter Argument</div>
                            <div className="text-neutral-400 text-xs italic">{drilldown.counter_argument}</div>
                          </div>
                        )}
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Historical Analogs */}
      {historical_analogs.length > 0 && (
        <div className="border border-neutral-800 rounded overflow-hidden">
          <div className="bg-neutral-900/50 px-3 py-2 border-b border-neutral-800">
            <h3 className="text-xs font-semibold text-neutral-300 tracking-wider">
              Historical Analogs
            </h3>
            <div className="text-xs text-neutral-500 mt-1">
              Similar past periods and subsequent returns
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-neutral-800 bg-neutral-900/50">
                  <th className="px-3 py-2 text-left text-xs text-neutral-500 font-medium uppercase">Period</th>
                  <th className="px-3 py-2 text-center text-xs text-neutral-500 font-medium uppercase">Similarity</th>
                  <th className="px-3 py-2 text-right text-xs text-neutral-500 font-medium uppercase">5D</th>
                  <th className="px-3 py-2 text-right text-xs text-neutral-500 font-medium uppercase">10D</th>
                  <th className="px-3 py-2 text-right text-xs text-neutral-500 font-medium uppercase">20D</th>
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
