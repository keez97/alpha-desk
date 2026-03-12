import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchUpgradedRegime, fetchVixTermStructure, fetchOvernightReturns, fetchBreadth } from '../../lib/api';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import type { UpgradedRegimeData, VixTermStructureData, OvernightReturnsData, BreadthData, RegimeSignal, AlphaInsight, RegimeLayerData } from '../../lib/api';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const REGIME_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  bull:    { bg: 'bg-green-500/10', text: 'text-green-400', label: 'BULL' },
  bear:    { bg: 'bg-red-500/10', text: 'text-red-400', label: 'BEAR' },
  neutral: { bg: 'bg-neutral-500/10', text: 'text-neutral-400', label: 'NEUTRAL' },
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
// Signal Tooltips — explains what each metric does and how it's measured
// ═══════════════════════════════════════════════════════════════
const SIGNAL_TOOLTIPS: Record<string, string> = {
  // Trend layer
  'SMA Crossover': 'Compares 50-day vs 200-day simple moving average. Golden Cross (50 > 200) is bullish, Death Cross is bearish. Ratio measures distance between the two.',
  'Price vs 200 SMA': 'Measures how far the current price is from the 200-day moving average. Being above signals uptrend, below signals downtrend. Percentage distance gauges conviction.',
  'Momentum': 'Fast momentum uses 1-month return, slow momentum uses 6-month return. Divergence between fast and slow can signal turning points (Goulding, Harvey & Mazzoleni).',

  // Volatility layer
  'VIX': 'The CBOE Volatility Index measures 30-day expected S&P 500 volatility. Below 15 = calm, 15–25 = normal, 25–35 = elevated, above 35 = panic. Percentile rank gives historical context.',
  'VVIX': 'Volatility of VIX — measures uncertainty about future volatility itself. High VVIX means options traders disagree on direction. Calm VVIX with elevated VIX = persistent fear.',

  // Yield/Credit layer
  'Yield Curve': 'The 10Y–3M Treasury spread. Positive = normal (growth expected), inverted (negative) = recession warning. Estrella-Mishkin probit model converts this into a recession probability.',
  'HY Credit Spread': 'High yield (junk) bond OAS spread over Treasuries. Measures corporate credit stress. Below 3% = tight (risk-on), 3–5% = normal, above 5% = stress, above 8% = crisis.',

  // Sentiment layer
  'Fear & Greed': 'CNN\'s composite of 7 market indicators (momentum, strength, breadth, put/call, junk bond demand, volatility, safe haven). 0–25 = Extreme Fear, 75–100 = Extreme Greed. Used as contrarian signal.',

  // Macro layer
  'WTI Oil': 'West Texas Intermediate crude oil price. Spikes above $90 are inflationary headwinds. Large moves signal supply disruptions or demand shifts that affect corporate margins.',
  'USD Index': 'Trade-weighted dollar index (DXY). Strong dollar hurts multinational earnings and emerging markets. Rapid moves signal capital flow shifts.',
  'Yield Curve Momentum': 'Rate of change in the yield curve slope. Steepening = improving growth outlook, flattening = tightening conditions or slowdown expectations.',

  // Systemic layer
  'Turbulence Index': 'Mahalanobis distance measuring how unusual multi-asset returns are vs history. Uses SPY, TLT, GLD, HYG returns over 60 days. High values = cross-asset stress.',
  'Absorption Ratio': 'PCA-based: fraction of total variance explained by first eigenvector across SPY, TLT, GLD, HYG. High absorption = tightly coupled markets = fragile. Above 80th %ile = systemic risk.',
  'Windham Fragility': 'Windham Capital 2×2 classification: Turbulence %ile (calm vs turbulent) × Absorption %ile (resilient vs fragile). Fragile-calm = Hidden Risk; fragile-turbulent = Crisis Mode.',
};

// ═══════════════════════════════════════════════════════════════
// Sub-components
// ═══════════════════════════════════════════════════════════════

function SignalTooltip({ text }: { text: string }) {
  return (
    <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-56 px-2.5 py-2 bg-neutral-900 border border-neutral-700 rounded-lg shadow-xl pointer-events-none">
      <div className="text-[9px] text-neutral-300 leading-snug">{text}</div>
      <div className="absolute top-full left-1/2 -translate-x-1/2 w-2 h-2 bg-neutral-900 border-r border-b border-neutral-700 rotate-45 -mt-1" />
    </div>
  );
}

function LayerBar({ name, layer, isExpanded, onToggle }: {
  name: string;
  layer: RegimeLayerData;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const [hoveredSignal, setHoveredSignal] = useState<string | null>(null);
  const score = layer.score;
  const barColor = score > 0.2 ? 'bg-green-500' : score < -0.2 ? 'bg-red-500' : 'bg-neutral-500';
  const weight = Math.round(layer.weight * 100);

  return (
    <div className="group">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-1.5 text-[10px] hover:bg-neutral-800/50 rounded px-1 py-0.5 transition-colors cursor-pointer"
      >
        <span className="text-neutral-500 w-[62px] text-left truncate">{LAYER_LABELS[name] || name}</span>
        <div className="flex-1 h-1.5 rounded-full bg-neutral-800 overflow-hidden relative">
          <div className="absolute left-1/2 top-0 w-px h-full bg-neutral-600 z-10" />
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
      {isExpanded && (
        <div className="ml-2 mt-0.5 mb-1 pl-2 border-l border-neutral-800 space-y-0.5">
          {layer.signals && layer.signals.length > 0 ? (
            layer.signals.map((sig, i) => {
              const tooltip = SIGNAL_TOOLTIPS[sig.name];
              return (
                <div
                  key={i}
                  className="flex items-center gap-1.5 text-[9px] relative"
                  onMouseEnter={() => tooltip ? setHoveredSignal(sig.name) : undefined}
                  onMouseLeave={() => setHoveredSignal(null)}
                >
                  <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${BIAS_DOT[sig.bias] || BIAS_DOT.neutral}`} />
                  <span className={`text-neutral-400 truncate flex-1 ${tooltip ? 'cursor-help border-b border-dotted border-neutral-700' : ''}`}>
                    {sig.name}
                  </span>
                  <span className={`font-mono ${sig.bias === 'bull' ? 'text-green-400' : sig.bias === 'bear' ? 'text-red-400' : 'text-neutral-500'}`}>
                    {sig.value}
                  </span>
                  {hoveredSignal === sig.name && tooltip && <SignalTooltip text={tooltip} />}
                </div>
              );
            })
          ) : (
            <div className="text-[8px] text-neutral-600 italic py-0.5">No individual signals</div>
          )}
        </div>
      )}
    </div>
  );
}

function CompositeGauge({ score, regime }: { score: number; regime: string }) {
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

function ADBar({ advances, declines, total }: { advances: number; declines: number; total: number }) {
  if (total === 0) return null;
  const advPct = (advances / total) * 100;
  const decPct = (declines / total) * 100;
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-[9px]">
        <span className="text-green-400">{advances} Advancing</span>
        <span className="text-red-400">{declines} Declining</span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden flex bg-neutral-800">
        <div className="bg-green-500/70 h-full transition-all" style={{ width: `${advPct}%` }} />
        <div className="bg-neutral-700 h-full transition-all" style={{ width: `${100 - advPct - decPct}%` }} />
        <div className="bg-red-500/70 h-full transition-all" style={{ width: `${decPct}%` }} />
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Main Component
// ═══════════════════════════════════════════════════════════════
export function MarketRegimeCard() {
  const [expandedLayers, setExpandedLayers] = useState<Set<string>>(new Set());

  // Fetch all four data sources in parallel
  const regime = useQuery({ queryKey: ['regime'], queryFn: fetchUpgradedRegime, staleTime: 5 * 60_000, retry: 2 });
  const vix = useQuery({ queryKey: ['vix-term-structure'], queryFn: fetchVixTermStructure, staleTime: 5 * 60_000, retry: 2 });
  const gaps = useQuery({ queryKey: ['overnight-returns'], queryFn: fetchOvernightReturns, staleTime: 30 * 60_000 });
  const breadth = useQuery({ queryKey: ['breadth'], queryFn: fetchBreadth, staleTime: 10 * 60_000, retry: 2 });

  const isLoading = regime.isLoading && vix.isLoading && gaps.isLoading;
  const hasError = regime.error && vix.error;

  if (isLoading) return <LoadingState message="Loading market regime..." />;
  if (hasError) return <ErrorState error={regime.error || vix.error!} onRetry={() => { regime.refetch(); vix.refetch(); gaps.refetch(); breadth.refetch(); }} />;

  const r = regime.data;
  const v = vix.data;
  const g = gaps.data;
  const b = breadth.data;
  const style = r ? (REGIME_STYLES[r.regime] || REGIME_STYLES.neutral) : REGIME_STYLES.neutral;

  const toggleLayer = (name: string) => {
    setExpandedLayers(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const allExpanded = r?.layers ? LAYER_ORDER.every(n => expandedLayers.has(n)) : false;
  const toggleAll = () => {
    if (allExpanded) {
      setExpandedLayers(new Set());
    } else {
      setExpandedLayers(new Set(LAYER_ORDER));
    }
  };

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

      {/* ═══ Main 4-Column Layout ═══ */}
      <div className="grid grid-cols-12 divide-x divide-neutral-800/50">

        {/* ─── Col 1: Regime Layers (5 cols) ─── */}
        <div className="col-span-5 p-2.5 space-y-2">
          {r && <CompositeGauge score={r.compositeScore} regime={r.regime} />}

          {/* Expand all / Collapse all toggle */}
          <div className="flex items-center justify-between">
            <span className="text-[9px] text-neutral-500 font-medium">6 Layers</span>
            <button
              onClick={toggleAll}
              className="text-[8px] text-blue-400 hover:text-blue-300 cursor-pointer"
            >
              {allExpanded ? 'Collapse all' : 'Expand all'}
            </button>
          </div>

          {r?.layers && (
            <div className="space-y-0">
              {LAYER_ORDER.map(name => {
                const layer = r.layers[name];
                if (!layer) return null;
                return (
                  <LayerBar
                    key={name}
                    name={name}
                    layer={layer}
                    isExpanded={expandedLayers.has(name)}
                    onToggle={() => toggleLayer(name)}
                  />
                );
              })}
            </div>
          )}
        </div>

        {/* ─── Col 2: VIX Term Structure (2 cols) ─── */}
        <div className="col-span-2 p-2.5 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[9px] text-neutral-500 font-medium">VIX Structure</span>
            {v && (
              <span className={`text-[8px] px-1 py-0.5 rounded-full font-medium bg-neutral-900/50 ${
                v.signal === 'bullish' ? 'text-green-400' : v.signal === 'bearish' ? 'text-red-400' : 'text-neutral-400'
              }`}>
                {v.signal === 'bullish' ? '↗' : v.signal === 'bearish' ? '↘' : '→'}
              </span>
            )}
          </div>

          {v && (
            <>
              <div className="grid grid-cols-2 gap-1">
                <div>
                  <div className="text-[7px] text-neutral-500">Spot</div>
                  <div className="text-sm font-mono font-bold text-neutral-200">{v.vixSpot.toFixed(1)}</div>
                </div>
                <div>
                  <div className="text-[7px] text-neutral-500">3M</div>
                  <div className="text-sm font-mono font-bold text-neutral-300">{v.vix3m.toFixed(1)}</div>
                </div>
              </div>

              <div className={`rounded p-1 text-center ${v.state === 'contango' ? 'bg-green-900/20' : 'bg-red-900/20'}`}>
                <span className={`text-[9px] font-bold ${v.state === 'contango' ? 'text-green-400' : 'text-red-400'}`}>
                  {v.state === 'contango' ? 'Contango' : 'Backwrdtn'} {v.magnitude.toFixed(1)}%
                </span>
              </div>

              <div>
                <div className="flex justify-between text-[7px] mb-0.5">
                  <span className="text-neutral-500">1Y %ile</span>
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

              <div className="grid grid-cols-2 gap-1 text-[8px]">
                <div className="flex justify-between">
                  <span className="text-neutral-500">Ratio</span>
                  <span className="font-mono text-neutral-300">{v.ratio.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-500">Roll</span>
                  <span className={`font-mono ${v.rollYield > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {v.rollYield.toFixed(5)}
                  </span>
                </div>
              </div>

              {v.history.length > 0 && (
                <div className="bg-neutral-900/40 rounded p-0.5">
                  <MiniSparkline data={v.history.map(h => h.ratio)} />
                </div>
              )}
            </>
          )}

          {!v && <div className="text-[9px] text-neutral-600 py-4 text-center">Loading...</div>}
        </div>

        {/* ─── Col 3: Overnight Gaps (3 cols) ─── */}
        <div className="col-span-3 p-2.5 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[9px] text-neutral-500 font-medium">Overnight Gaps</span>
            {g && (
              <span className={`text-[8px] font-mono px-1 py-0.5 rounded-full bg-neutral-900/50 ${
                g.summary.net_direction === 'up' ? 'text-emerald-400' : g.summary.net_direction === 'down' ? 'text-red-400' : 'text-neutral-400'
              }`}>
                {g.summary.gaps_up}↑ {g.summary.gaps_down}↓
              </span>
            )}
          </div>

          {g && (
            <>
              {/* Major Indices */}
              <div className="space-y-0">
                {g.indices.slice(0, 4).map(item => (
                  <div key={item.ticker} className="flex items-center justify-between text-[9px] py-px">
                    <span className="font-mono font-bold text-neutral-300 w-7">{item.ticker}</span>
                    {item.last_price > 0 && (
                      <span className="font-mono text-neutral-500 text-[8px]">${item.last_price.toFixed(0)}</span>
                    )}
                    <span className={`font-mono font-medium ${item.direction === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
                      {item.overnight_return_pct > 0 ? '+' : ''}{item.overnight_return_pct.toFixed(2)}%
                    </span>
                  </div>
                ))}
              </div>

              {/* All Sectors — no show more/less */}
              {g.indices.length > 4 && (
                <div className="border-t border-neutral-800/50 pt-0.5">
                  <div className="text-[7px] text-neutral-600 mb-0.5">Sectors</div>
                  <div className="space-y-0">
                    {g.indices.slice(4).map(item => (
                      <div key={item.ticker} className="flex items-center justify-between text-[8px] py-px">
                        <span className="font-mono text-neutral-400 w-8 flex-shrink-0">{item.ticker}</span>
                        <div className="flex items-center gap-1">
                          {item.last_price > 0 && (
                            <span className="font-mono text-neutral-600 text-[7px]">${item.last_price.toFixed(0)}</span>
                          )}
                          <span className={`font-mono ${item.direction === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
                            {item.overnight_return_pct > 0 ? '+' : ''}{item.overnight_return_pct.toFixed(2)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Outlier alerts */}
              {g.summary.notable_gaps.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {g.summary.notable_gaps.slice(0, 2).map(gap => (
                    <span key={gap.ticker} className="text-[7px] bg-amber-900/20 text-amber-400 rounded px-1 py-0.5 font-mono">
                      ⚠ {gap.ticker} {gap.overnight_return_pct > 0 ? '+' : ''}{gap.overnight_return_pct.toFixed(2)}%
                    </span>
                  ))}
                </div>
              )}
            </>
          )}

          {!g && <div className="text-[9px] text-neutral-600 py-4 text-center">Loading...</div>}
        </div>

        {/* ─── Col 4: Market Breadth (2 cols) ─── */}
        <div className="col-span-2 p-2.5 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[9px] text-neutral-500 font-medium">Market Breadth</span>
            {b && (
              <span className={`text-[8px] px-1 py-0.5 rounded-full font-medium bg-neutral-900/50 ${
                b.signal.includes('bull') ? 'text-green-400' : b.signal.includes('bear') ? 'text-red-400' : 'text-neutral-400'
              }`}>
                {b.signal.includes('strongly') ? (b.signal.includes('bull') ? 'Strong Bull' : 'Strong Bear')
                  : b.signal.includes('bull') ? 'Bullish'
                  : b.signal.includes('bear') ? 'Bearish' : 'Neutral'}
              </span>
            )}
          </div>

          {b && b.total > 0 && (
            <>
              <ADBar advances={b.advances} declines={b.declines} total={b.total} />

              <div className="grid grid-cols-2 gap-1.5">
                <div className="bg-neutral-900/50 rounded p-1 text-center">
                  <div className="text-[7px] text-neutral-500">A/D Ratio</div>
                  <div className={`text-xs font-mono font-bold ${
                    b.adRatio > 1.5 ? 'text-green-400' : b.adRatio < 0.67 ? 'text-red-400' : 'text-neutral-300'
                  }`}>
                    {b.adRatio.toFixed(2)}
                  </div>
                  <div className="text-[7px] text-neutral-600">{b.adRatio > 1 ? 'net adv.' : 'net dec.'}</div>
                </div>
                <div className="bg-neutral-900/50 rounded p-1 text-center">
                  <div className="text-[7px] text-neutral-500">Net Adv</div>
                  <div className={`text-xs font-mono font-bold ${b.netAdvances > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {b.netAdvances > 0 ? '+' : ''}{b.netAdvances}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-1.5">
                <div className="bg-neutral-900/50 rounded p-1 text-center">
                  <div className="text-[7px] text-neutral-500">McClellan</div>
                  <div className={`text-xs font-mono font-bold ${b.mcclellan > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {b.mcclellan.toFixed(1)}
                  </div>
                  <div className="text-[7px] text-neutral-600">{b.mcclellan > 0 ? 'positive' : 'negative'}</div>
                </div>
                <div className="bg-neutral-900/50 rounded p-1 text-center">
                  <div className="text-[7px] text-neutral-500">Thrust</div>
                  <div className={`text-xs font-mono font-bold ${b.breadthThrust ? 'text-green-400' : 'text-neutral-500'}`}>
                    {b.breadthThrust ? 'YES' : 'No'}
                  </div>
                  <div className="text-[7px] text-neutral-600">{b.pctAdvancing.toFixed(0)}% adv.</div>
                </div>
              </div>

              <div className="text-[7px] text-neutral-600 text-right">
                Based on {b.sampleSize} S&P 500 components
              </div>
            </>
          )}

          {!b && <div className="text-[9px] text-neutral-600 py-4 text-center">Loading...</div>}
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
