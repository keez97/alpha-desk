import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchUpgradedRegime, fetchVixTermStructure, fetchOvernightReturns } from '../../lib/api';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import type { UpgradedRegimeData, VixTermStructureData, OvernightReturnsData, RegimeSignal, AlphaInsight, RegimeLayerData } from '../../lib/api';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const REGIME_STYLES: Record<string, { bg: string; text: string; label: string; glow: string }> = {
  bull:    { bg: 'bg-green-500/10', text: 'text-green-400', label: 'BULL', glow: 'shadow-green-500/20' },
  bear:    { bg: 'bg-red-500/10', text: 'text-red-400', label: 'BEAR', glow: 'shadow-red-500/20' },
  neutral: { bg: 'bg-neutral-500/10', text: 'text-neutral-400', label: 'NEUTRAL', glow: 'shadow-neutral-500/10' },
};

const WINDHAM_STYLES: Record<string, { bg: string; text: string; icon: string }> = {
  'resilient-calm':      { bg: 'bg-green-900/30', text: 'text-green-400', icon: '✓' },
  'resilient-turbulent': { bg: 'bg-yellow-900/30', text: 'text-yellow-400', icon: '⚡' },
  'fragile-calm':        { bg: 'bg-orange-900/30', text: 'text-orange-400', icon: '⚠' },
  'fragile-turbulent':   { bg: 'bg-red-900/30', text: 'text-red-400', icon: '🔴' },
};

const LAYER_LABELS: Record<string, string> = {
  trend: 'Trend',
  volatility: 'Volatility',
  yield_credit: 'Yield/Credit',
  sentiment: 'Sentiment',
  macro: 'Macro',
  systemic: 'Systemic',
};

const LAYER_ORDER = ['trend', 'volatility', 'yield_credit', 'sentiment', 'macro', 'systemic'];

const BIAS_DOT: Record<string, string> = {
  bull: 'bg-green-400',
  bear: 'bg-red-400',
  neutral: 'bg-neutral-500',
};

// ═══════════════════════════════════════════════════════════════
// Sub-components
// ═══════════════════════════════════════════════════════════════
function LayerBar({ name, layer, isExpanded, onToggle }: {
  name: string;
  layer: RegimeLayerData;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const score = layer.score;
  const pct = ((score + 1) / 2) * 100; // -1..+1 → 0..100%
  const barColor = score > 0.2 ? 'bg-green-500' : score < -0.2 ? 'bg-red-500' : 'bg-neutral-500';
  const weight = Math.round(layer.weight * 100);

  return (
    <div className="group">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-1.5 text-[10px] hover:bg-neutral-800/50 rounded px-1 py-0.5 transition-colors cursor-pointer"
      >
        <span className="text-neutral-500 w-[52px] text-left truncate">{LAYER_LABELS[name] || name}</span>
        <div className="flex-1 h-1.5 rounded-full bg-neutral-800 overflow-hidden relative">
          {/* Center marker */}
          <div className="absolute left-1/2 top-0 w-px h-full bg-neutral-600 z-10" />
          {/* Bar from center */}
          {score >= 0 ? (
            <div className={`${barColor} h-full absolute left-1/2 rounded-r-full transition-all`}
              style={{ width: `${(score / 1) * 50}%` }} />
          ) : (
            <div className={`${barColor} h-full absolute right-1/2 rounded-l-full transition-all`}
              style={{ width: `${(Math.abs(score) / 1) * 50}%` }} />
          )}
        </div>
        <span className={`font-mono w-8 text-right ${score > 0 ? 'text-green-400' : score < 0 ? 'text-red-400' : 'text-neutral-500'}`}>
          {score > 0 ? '+' : ''}{score.toFixed(1)}
        </span>
        <span className="text-neutral-600 w-4 text-right">{weight}%</span>
        <span className={`text-neutral-600 transition-transform ${isExpanded ? 'rotate-90' : ''}`}>›</span>
      </button>
      {/* Expanded detail */}
      {isExpanded && layer.signals && layer.signals.length > 0 && (
        <div className="ml-2 mt-0.5 mb-1 pl-2 border-l border-neutral-800 space-y-0.5">
          {layer.signals.map((sig, i) => (
            <div key={i} className="flex items-center gap-1.5 text-[9px]">
              <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${BIAS_DOT[sig.bias] || BIAS_DOT.neutral}`} />
              <span className="text-neutral-400 truncate flex-1">{sig.name}</span>
              <span className={`font-mono ${sig.bias === 'bull' ? 'text-green-400' : sig.bias === 'bear' ? 'text-red-400' : 'text-neutral-500'}`}>
                {sig.value}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CompositeGauge({ score, regime }: { score: number; regime: string }) {
  // Score goes -1 to +1, mapped to 0-100 for the gauge
  const pct = ((score + 1) / 2) * 100;
  const style = REGIME_STYLES[regime] || REGIME_STYLES.neutral;

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1">
        <div className="h-2 rounded-full bg-neutral-800 overflow-hidden relative">
          <div className="absolute left-0 top-0 h-full w-full bg-gradient-to-r from-red-500/30 via-neutral-700/30 to-green-500/30" />
          <div
            className="absolute top-0 w-1.5 h-full bg-white rounded-full shadow-lg transition-all"
            style={{ left: `calc(${pct}% - 3px)` }}
          />
        </div>
        <div className="flex justify-between text-[8px] text-neutral-600 mt-0.5">
          <span>Bear</span>
          <span>Neutral</span>
          <span>Bull</span>
        </div>
      </div>
      <span className={`font-mono text-sm font-bold ${style.text}`}>
        {score > 0 ? '+' : ''}{score.toFixed(2)}
      </span>
    </div>
  );
}

function WindhamBadge({ windham }: { windham: UpgradedRegimeData['windham'] }) {
  const ws = WINDHAM_STYLES[windham.state] || WINDHAM_STYLES['resilient-calm'];
  return (
    <div className={`${ws.bg} border border-neutral-800/50 rounded px-2 py-1 flex items-center gap-1.5`}>
      <span className="text-xs">{ws.icon}</span>
      <div className="min-w-0">
        <div className={`text-[10px] font-bold ${ws.text} leading-tight`}>{windham.label}</div>
        <div className="text-[8px] text-neutral-500 leading-tight truncate">{windham.state}</div>
      </div>
    </div>
  );
}

function MiniSparkline({ data }: { data: number[] }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * 100},${((max - v) / range) * 100}`).join(' ');
  const lastY = ((max - data[data.length - 1]) / range) * 100;
  const strokeColor = data[data.length - 1] >= data[0] ? '#4ade80' : '#f87171';

  return (
    <svg width="100%" height="24" viewBox="0 0 100 100" preserveAspectRatio="none" className="opacity-60">
      <polyline points={pts} fill="none" stroke={strokeColor} strokeWidth="2" vectorEffect="non-scaling-stroke" />
      <circle cx="100" cy={lastY} r="3" fill={strokeColor} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function InsightBar({ insight }: { insight: AlphaInsight }) {
  const convictionColor = insight.conviction === 'high' ? 'text-yellow-400' : insight.conviction === 'medium' ? 'text-blue-400' : 'text-neutral-500';
  const convictionBg = insight.conviction === 'high' ? 'bg-yellow-900/20' : insight.conviction === 'medium' ? 'bg-blue-900/20' : 'bg-neutral-800/50';

  return (
    <div className={`${convictionBg} border border-neutral-800/50 rounded px-2.5 py-1.5`}>
      <div className="flex items-center gap-1.5 mb-0.5">
        <span className={`text-[9px] font-bold uppercase ${convictionColor}`}>{insight.conviction}</span>
        <span className="text-[9px] text-neutral-600">·</span>
        <span className="text-[9px] text-neutral-500">{insight.category}</span>
      </div>
      <div className="text-[10px] text-neutral-300 leading-snug">{insight.action}</div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Main Component
// ═══════════════════════════════════════════════════════════════
export function MarketRegimeCard() {
  const [expandedLayer, setExpandedLayer] = useState<string | null>(null);
  const [showAllGaps, setShowAllGaps] = useState(false);
  const [activeTab, setActiveTab] = useState<'signals' | 'systemic'>('signals');

  // Fetch all three data sources in parallel
  const regime = useQuery({ queryKey: ['regime'], queryFn: fetchUpgradedRegime, staleTime: 5 * 60_000, retry: 2 });
  const vix = useQuery({ queryKey: ['vix-term-structure'], queryFn: fetchVixTermStructure, staleTime: 5 * 60_000, retry: 2 });
  const gaps = useQuery({ queryKey: ['overnight-returns'], queryFn: fetchOvernightReturns, staleTime: 30 * 60_000 });

  const isLoading = regime.isLoading && vix.isLoading && gaps.isLoading;
  const hasError = regime.error && vix.error;

  if (isLoading) return <LoadingState message="Loading market regime..." />;
  if (hasError) return <ErrorState error={regime.error || vix.error!} onRetry={() => { regime.refetch(); vix.refetch(); gaps.refetch(); }} />;

  const r = regime.data;
  const v = vix.data;
  const g = gaps.data;
  const style = r ? (REGIME_STYLES[r.regime] || REGIME_STYLES.neutral) : REGIME_STYLES.neutral;

  return (
    <div className={`border border-neutral-800 rounded-lg overflow-hidden ${style.bg}`}>
      {/* ═══ Header Row ═══ */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-neutral-800/50">
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-neutral-300">Market Regime</span>
          {r && (
            <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-bold ${style.text} bg-neutral-900/60`}>
              {style.label} {r.confidence}%
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {r?.windham && <WindhamBadge windham={r.windham} />}
        </div>
      </div>

      {/* ═══ Main 3-Column Layout ═══ */}
      <div className="grid grid-cols-12 divide-x divide-neutral-800/50">

        {/* ─── Left: Regime Layers (5 cols) ─── */}
        <div className="col-span-5 p-2.5 space-y-2">
          {/* Composite gauge */}
          {r && <CompositeGauge score={r.compositeScore} regime={r.regime} />}

          {/* Tab switcher */}
          <div className="flex gap-0.5 bg-neutral-900/50 rounded p-0.5">
            <button
              onClick={() => setActiveTab('signals')}
              className={`flex-1 text-[9px] py-0.5 rounded transition-colors cursor-pointer ${
                activeTab === 'signals' ? 'bg-neutral-700 text-neutral-200' : 'text-neutral-500 hover:text-neutral-400'
              }`}
            >
              6 Layers
            </button>
            <button
              onClick={() => setActiveTab('systemic')}
              className={`flex-1 text-[9px] py-0.5 rounded transition-colors cursor-pointer ${
                activeTab === 'systemic' ? 'bg-neutral-700 text-neutral-200' : 'text-neutral-500 hover:text-neutral-400'
              }`}
            >
              Systemic Risk
            </button>
          </div>

          {activeTab === 'signals' && r?.layers && (
            <div className="space-y-0">
              {LAYER_ORDER.map(name => {
                const layer = r.layers[name];
                if (!layer) return null;
                return (
                  <LayerBar
                    key={name}
                    name={name}
                    layer={layer}
                    isExpanded={expandedLayer === name}
                    onToggle={() => setExpandedLayer(expandedLayer === name ? null : name)}
                  />
                );
              })}
            </div>
          )}

          {activeTab === 'systemic' && r && (
            <div className="space-y-2">
              {/* Key metrics */}
              <div className="grid grid-cols-2 gap-1.5">
                <div className="bg-neutral-900/50 rounded p-1.5 text-center">
                  <div className="text-[8px] text-neutral-500">Turbulence</div>
                  <div className="text-xs font-mono font-bold text-neutral-200">
                    {r.systemicRisk.turbulenceIndex?.toFixed(3) ?? '—'}
                  </div>
                  <div className="text-[8px] text-neutral-500">
                    {r.systemicRisk.turbulencePercentile?.toFixed(0) ?? '—'}th %ile
                  </div>
                </div>
                <div className="bg-neutral-900/50 rounded p-1.5 text-center">
                  <div className="text-[8px] text-neutral-500">Absorption</div>
                  <div className="text-xs font-mono font-bold text-neutral-200">
                    {r.systemicRisk.absorptionRatio?.toFixed(3) ?? '—'}
                  </div>
                  <div className="text-[8px] text-neutral-500">
                    {r.systemicRisk.absorptionPercentile?.toFixed(0) ?? '—'}th %ile
                  </div>
                </div>
              </div>
              {/* Recession prob + Windham state */}
              <div className="grid grid-cols-2 gap-1.5">
                <div className="bg-neutral-900/50 rounded p-1.5 text-center">
                  <div className="text-[8px] text-neutral-500">Recession Prob</div>
                  <div className={`text-xs font-mono font-bold ${
                    r.recessionProbability < 25 ? 'text-green-400' : r.recessionProbability < 50 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {r.recessionProbability.toFixed(1)}%
                  </div>
                  <div className="text-[8px] text-neutral-500">Estrella</div>
                </div>
                <div className="bg-neutral-900/50 rounded p-1.5 text-center">
                  <div className="text-[8px] text-neutral-500">Windham State</div>
                  <div className={`text-[10px] font-bold ${WINDHAM_STYLES[r.windham.state]?.text || 'text-neutral-400'}`}>
                    {r.windham.label}
                  </div>
                  <div className="text-[8px] text-neutral-500">{r.windham.risk_level} risk</div>
                </div>
              </div>
              {/* Windham description */}
              {r.windham.description && (
                <div className="text-[9px] text-neutral-500 leading-snug bg-neutral-900/30 rounded p-1.5">
                  {r.windham.description}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ─── Middle: VIX Term Structure (3 cols) ─── */}
        <div className="col-span-3 p-2.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-neutral-500 font-medium">VIX Structure</span>
            {v && (
              <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium bg-neutral-900/50 ${
                v.signal === 'bullish' ? 'text-green-400' : v.signal === 'bearish' ? 'text-red-400' : 'text-neutral-400'
              }`}>
                {v.signal === 'bullish' ? '↗ Bullish' : v.signal === 'bearish' ? '↘ Bearish' : '→ Neutral'}
              </span>
            )}
          </div>

          {v && (
            <>
              {/* VIX numbers */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <div className="text-[8px] text-neutral-500">VIX Spot</div>
                  <div className="text-base font-mono font-bold text-neutral-200">{v.vixSpot.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-[8px] text-neutral-500">VIX 3M</div>
                  <div className="text-base font-mono font-bold text-neutral-300">{v.vix3m.toFixed(2)}</div>
                </div>
              </div>

              {/* Term structure state */}
              <div className={`rounded p-1.5 text-center ${v.state === 'contango' ? 'bg-green-900/20' : 'bg-red-900/20'}`}>
                <span className={`text-[10px] font-bold ${v.state === 'contango' ? 'text-green-400' : 'text-red-400'}`}>
                  {v.state === 'contango' ? 'Contango' : 'Backwardation'} {v.magnitude.toFixed(2)}%
                </span>
              </div>

              {/* Percentile bar */}
              <div>
                <div className="flex justify-between text-[8px] mb-0.5">
                  <span className="text-neutral-500">1Y Percentile</span>
                  <span className={`font-mono ${v.percentile > 75 ? 'text-red-400' : v.percentile < 25 ? 'text-green-400' : 'text-yellow-400'}`}>
                    {v.percentile}th
                  </span>
                </div>
                <div className="h-1 rounded-full bg-neutral-800 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${v.percentile > 75 ? 'bg-red-500' : v.percentile < 25 ? 'bg-green-500' : 'bg-yellow-500'}`}
                    style={{ width: `${v.percentile}%` }}
                  />
                </div>
              </div>

              {/* Ratio + Roll Yield */}
              <div className="grid grid-cols-2 gap-2 text-[9px]">
                <div className="flex justify-between">
                  <span className="text-neutral-500">Ratio</span>
                  <span className="font-mono text-neutral-300">{v.ratio.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-500">Roll Yield</span>
                  <span className={`font-mono ${v.rollYield > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {v.rollYield.toFixed(6)}
                  </span>
                </div>
              </div>

              {/* Sparkline */}
              {v.history.length > 0 && (
                <div className="bg-neutral-900/40 rounded p-1">
                  <MiniSparkline data={v.history.map(h => h.ratio)} />
                </div>
              )}
            </>
          )}

          {!v && <div className="text-[10px] text-neutral-600 py-4 text-center">VIX data loading...</div>}
        </div>

        {/* ─── Right: Overnight Gaps (4 cols) ─── */}
        <div className="col-span-4 p-2.5 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-neutral-500 font-medium">Overnight Gaps</span>
            {g && (
              <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded-full bg-neutral-900/50 ${
                g.summary.net_direction === 'up' ? 'text-emerald-400' : g.summary.net_direction === 'down' ? 'text-red-400' : 'text-neutral-400'
              }`}>
                {g.summary.gaps_up}↑ {g.summary.gaps_down}↓
              </span>
            )}
          </div>

          {g && (
            <>
              {/* Indices - compact */}
              <div className="space-y-0.5">
                {g.indices.slice(0, 4).map(item => (
                  <div key={item.ticker} className="flex items-center justify-between text-[10px]">
                    <div className="flex items-center gap-1">
                      <span className="font-mono font-bold text-neutral-300 w-8">{item.ticker}</span>
                      <span className="text-neutral-600 truncate text-[9px]">{item.name}</span>
                    </div>
                    <span className={`font-mono font-medium ${item.direction === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
                      {item.overnight_return_pct > 0 ? '+' : ''}{item.overnight_return_pct.toFixed(2)}%
                    </span>
                  </div>
                ))}
              </div>

              {/* Sectors - compact 2-col grid */}
              {g.indices.length > 4 && (
                <>
                  <div className="border-t border-neutral-800/50 pt-1">
                    <div className="text-[8px] text-neutral-600 mb-0.5">Sectors</div>
                    <div className="grid grid-cols-2 gap-x-2 gap-y-0">
                      {g.indices.slice(4, showAllGaps ? undefined : 12).map(item => (
                        <div key={item.ticker} className="flex items-center justify-between text-[9px] py-0.5">
                          <span className="font-mono text-neutral-400">{item.ticker}</span>
                          <span className={`font-mono ${item.direction === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
                            {item.overnight_return_pct > 0 ? '+' : ''}{item.overnight_return_pct.toFixed(2)}%
                          </span>
                        </div>
                      ))}
                    </div>
                    {g.indices.length > 12 && (
                      <button
                        onClick={() => setShowAllGaps(!showAllGaps)}
                        className="text-[8px] text-blue-400 hover:text-blue-300 mt-0.5 cursor-pointer"
                      >
                        {showAllGaps ? 'Show less' : `+${g.indices.length - 12} more`}
                      </button>
                    )}
                  </div>
                </>
              )}

              {/* Outlier alerts */}
              {g.summary.notable_gaps.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {g.summary.notable_gaps.slice(0, 2).map(gap => (
                    <span key={gap.ticker} className="text-[8px] bg-amber-900/20 text-amber-400 rounded px-1.5 py-0.5 font-mono">
                      ⚠ {gap.ticker} {gap.overnight_return_pct > 0 ? '+' : ''}{gap.overnight_return_pct.toFixed(2)}%
                    </span>
                  ))}
                </div>
              )}
            </>
          )}

          {!g && <div className="text-[10px] text-neutral-600 py-4 text-center">Gaps loading...</div>}
        </div>
      </div>

      {/* ═══ Alpha Insight Footer ═══ */}
      {r?.alphaInsights && r.alphaInsights.length > 0 && (
        <div className="border-t border-neutral-800/50 px-3 py-2">
          <InsightBar insight={r.alphaInsights[0]} />
        </div>
      )}
    </div>
  );
}
