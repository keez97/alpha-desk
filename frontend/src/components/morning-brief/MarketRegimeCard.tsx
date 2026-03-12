import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchUpgradedRegime, fetchVixTermStructure, fetchOvernightReturns, fetchBreadth, fetchRegimeInsight } from '../../lib/api';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { CompactRRGTable } from './CompactRRGTable';
import type { UpgradedRegimeData, VixTermStructureData, OvernightReturnsData, BreadthData, RegimeSignal, AlphaInsight, RegimeLayerData, RegimeInsight } from '../../lib/api';

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
  'Turbulence Index': 'Mahalanobis distance measuring how unusual cross-asset returns are vs 60-day rolling history. Core 10-asset universe: SPY, QQQ, IWM, EFA, EEM, TLT, IEF, LQD, HYG, GLD. Tier 3 expansion: XME, COPX, UNG, DBA, BITO, VIXY (when available). Ledoit-Wolf shrinkage for robust covariance. Chi-squared p-value flags statistically significant stress episodes.',
  'Absorption Ratio': 'PCA-based: variance explained by top eigenvectors across 11 SPDR sector ETFs (XLK, XLV, XLF, XLY, XLP, XLE, XLRE, XLI, XLU, XLC, XLB). 52-week rolling window of weekly returns, Ledoit-Wolf covariance. Tracks week-over-week AR delta as a leading indicator. Above 80th %ile = systemic fragility.',
  'Windham Fragility': 'Windham 2×2 framework: Turbulence %ile × Absorption %ile. Smooth sigmoid transitions (no binary jumps). Hysteresis: entry at 75th/80th, exit at 65th/70th to prevent oscillation. State persistence tracks duration in current regime. Fragile-calm = Hidden Risk; fragile-turbulent = Crisis Mode.',
  'AR Delta': 'Week-over-week change in Absorption Ratio, z-scored against historical deltas. Rising AR delta (z > 1.0) = systemic coupling increasing rapidly — a leading indicator of fragility. Falling AR delta (z < -1.0) = coupling easing, potential stabilization.',
};

// ═══════════════════════════════════════════════════════════════
// Sub-components
// ═══════════════════════════════════════════════════════════════

function SignalTooltip({ text, x, y }: { text: string; x: number; y: number }) {
  return (
    <div
      className="fixed z-[9999] w-56 px-2.5 py-2 bg-neutral-900 border border-neutral-700 rounded-lg shadow-xl pointer-events-none"
      style={{ left: x + 12, top: y - 8 }}
    >
      <div className="text-[9px] text-neutral-300 leading-snug">{text}</div>
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
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
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
                  className="flex items-center gap-1.5 text-[9px]"
                >
                  <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${BIAS_DOT[sig.bias] || BIAS_DOT.neutral}`} />
                  <span
                    className={`text-neutral-400 truncate flex-1 ${tooltip ? 'cursor-help border-b border-dotted border-neutral-700' : ''}`}
                    onMouseEnter={() => tooltip ? setHoveredSignal(sig.name) : undefined}
                    onMouseMove={(e) => tooltip ? setMousePos({ x: e.clientX, y: e.clientY }) : undefined}
                    onMouseLeave={() => setHoveredSignal(null)}
                  >
                    {sig.name}
                  </span>
                  <span className={`font-mono ${sig.bias === 'bull' ? 'text-green-400' : sig.bias === 'bear' ? 'text-red-400' : 'text-neutral-500'}`}>
                    {sig.value}
                  </span>
                  {sig.name === 'AR Delta' && sig.bias === 'bear' && (
                    <span className="ml-0.5 w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" title="AR coupling rising rapidly" />
                  )}
                  {hoveredSignal === sig.name && tooltip && <SignalTooltip text={tooltip} x={mousePos.x} y={mousePos.y} />}
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

// ═══════════════════════════════════════════════════════════════
// AI Market Insight — Claude-powered narrative assessment
// ═══════════════════════════════════════════════════════════════

function InsightFactorDot({ bias }: { bias: string }) {
  const color = bias === 'bull' ? 'bg-green-400' : bias === 'bear' ? 'bg-red-400' : 'bg-neutral-500';
  return <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${color}`} />;
}

function AIMarketInsight() {
  const insight = useQuery({
    queryKey: ['regime-insight'],
    queryFn: fetchRegimeInsight,
    staleTime: 10 * 60_000, // 10 min — backend caches 15 min
    retry: 1,
    refetchOnWindowFocus: false,
  });

  if (insight.isLoading) {
    return (
      <div className="flex items-center gap-2 py-1">
        <div className="w-3 h-3 border border-blue-400/50 border-t-blue-400 rounded-full animate-spin" />
        <span className="text-[9px] text-neutral-500 italic">Generating AI market assessment...</span>
      </div>
    );
  }

  if (insight.error || !insight.data) {
    return (
      <div className="text-[9px] text-neutral-600 italic py-1">
        AI insight unavailable — see factor signals above
      </div>
    );
  }

  const d = insight.data;
  const stanceColor = d.conviction === 'high'
    ? 'text-yellow-400 border-yellow-800/40 bg-yellow-900/20'
    : d.conviction === 'medium'
    ? 'text-blue-400 border-blue-800/40 bg-blue-900/20'
    : 'text-neutral-400 border-neutral-700/40 bg-neutral-800/40';

  return (
    <div className="space-y-2">
      {/* Row 1: Stance badge + factor dots */}
      <div className="flex items-center gap-2">
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded border shrink-0 ${stanceColor}`}>
          {d.stance}
        </span>
        {d.factors.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            {d.factors.map(f => (
              <div key={f.label} className="flex items-center gap-0.5">
                <InsightFactorDot bias={f.bias} />
                <span className="text-[8px] text-neutral-500">{f.label}</span>
                <span className={`text-[8px] font-mono ${
                  f.bias === 'bull' ? 'text-green-400' : f.bias === 'bear' ? 'text-red-400' : 'text-neutral-400'
                }`}>
                  {f.assessment}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Row 2: Narrative */}
      <div className="text-[10px] text-neutral-300 leading-relaxed">
        {d.narrative}
      </div>

      {/* Row 3: Signal Divergences */}
      {d.divergences && d.divergences.length > 0 && (
        <div className="space-y-1">
          {d.divergences.map((div, i) => (
            <div key={i} className="rounded border border-amber-800/30 bg-amber-900/10 px-2 py-1.5">
              <div className="flex items-center gap-1.5 mb-0.5">
                <span className="text-amber-400 text-[9px]">⚡</span>
                <span className="text-[9px] font-bold text-amber-300">{div.title}</span>
              </div>
              <div className="text-[9px] text-neutral-400 leading-relaxed">{div.explanation}</div>
              <div className="text-[9px] text-neutral-500 mt-0.5 italic">
                Resolution: {div.resolution}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Row 4: Watch Signal */}
      {d.watch_signal && d.watch_signal.metric && (
        <div className="flex items-start gap-2 rounded border border-blue-800/30 bg-blue-900/10 px-2 py-1.5">
          <span className="text-blue-400 text-[9px] mt-0.5 shrink-0">👁</span>
          <div className="min-w-0">
            <div className="text-[9px] text-blue-300 font-mono font-bold">{d.watch_signal.metric}</div>
            <div className="text-[9px] text-neutral-400">{d.watch_signal.trigger}</div>
            <div className="text-[8px] text-neutral-500 mt-0.5">{d.watch_signal.timeframe}</div>
          </div>
        </div>
      )}
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

        {/* ─── Col 2: VIX Structure — Gauge + Term Curve + Signal (2 cols) ─── */}
        <div className="col-span-2 p-2.5 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[9px] text-neutral-500 font-medium">VIX Structure</span>
          </div>

          {v && (() => {
            // VIX zone classification
            const spot = v.vixSpot;
            const zone = spot < 15 ? 'calm' : spot < 20 ? 'normal' : spot < 25 ? 'elevated' : spot < 35 ? 'high' : 'panic';
            const zoneConfig: Record<string, { color: string; label: string; textColor: string }> = {
              calm:     { color: 'bg-green-500', label: 'Calm', textColor: 'text-green-400' },
              normal:   { color: 'bg-blue-500', label: 'Normal', textColor: 'text-blue-400' },
              elevated: { color: 'bg-yellow-500', label: 'Elevated', textColor: 'text-yellow-400' },
              high:     { color: 'bg-orange-500', label: 'High', textColor: 'text-orange-400' },
              panic:    { color: 'bg-red-500', label: 'Panic', textColor: 'text-red-400' },
            };
            const z = zoneConfig[zone];

            // Gauge position: VIX 10–50 mapped to 0–100%
            const gaugePos = Math.min(100, Math.max(0, ((spot - 10) / 40) * 100));

            // Signal interpretation
            const isBackwardation = v.state !== 'contango';
            let signalText = '';
            if (spot >= 35) {
              signalText = 'Panic-level vol — historically marks capitulation zones';
            } else if (spot >= 25 && isBackwardation) {
              signalText = 'Elevated VIX in backwardation — active hedging demand, near-term stress';
            } else if (spot >= 25) {
              signalText = 'Elevated fear but contango intact — stress is priced, not acute';
            } else if (spot >= 20 && isBackwardation) {
              signalText = 'Moderate vol + backwardation — unusual, watch for escalation';
            } else if (spot >= 20) {
              signalText = 'Slightly elevated vol — mild caution, no structural stress';
            } else if (spot < 15 && v.percentile < 10) {
              signalText = 'Extreme complacency — low vol environments precede sharp moves';
            } else if (spot < 15) {
              signalText = 'Low vol regime — risk-on environment, carry trades favored';
            } else {
              signalText = 'Normal vol range — no directional signal from volatility';
            }

            return (
              <>
                {/* VIX Gauge */}
                <div className="space-y-0.5">
                  <div className="flex items-baseline justify-between">
                    <span className={`text-lg font-mono font-bold ${z.textColor}`}>{spot.toFixed(1)}</span>
                    <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded-full ${z.color}/20 ${z.textColor}`}>{z.label}</span>
                  </div>
                  {/* Zone bar gauge */}
                  <div className="relative h-2 rounded-full overflow-hidden bg-neutral-800">
                    {/* Zone gradient: green → blue → yellow → orange → red */}
                    <div className="absolute inset-0 flex">
                      <div className="bg-green-500/40 h-full" style={{ width: '12.5%' }} />
                      <div className="bg-blue-500/40 h-full" style={{ width: '12.5%' }} />
                      <div className="bg-yellow-500/40 h-full" style={{ width: '12.5%' }} />
                      <div className="bg-orange-500/40 h-full" style={{ width: '25%' }} />
                      <div className="bg-red-500/40 h-full" style={{ width: '37.5%' }} />
                    </div>
                    {/* Needle */}
                    <div
                      className="absolute top-0 w-1 h-full bg-white rounded-full shadow-lg shadow-white/30 transition-all"
                      style={{ left: `calc(${gaugePos}% - 2px)` }}
                    />
                  </div>
                  <div className="flex justify-between text-[6px] text-neutral-600">
                    <span>10</span><span>20</span><span>30</span><span>50</span>
                  </div>
                </div>

                {/* Term Structure Mini Curve */}
                <div className="bg-neutral-900/40 rounded p-1.5">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[7px] text-neutral-500">Term Structure</span>
                    <span className={`text-[8px] font-bold ${v.state === 'contango' ? 'text-green-400' : 'text-red-400'}`}>
                      {v.state === 'contango' ? 'Contango' : 'Backwrdtn'} {v.magnitude.toFixed(1)}%
                    </span>
                  </div>
                  {/* Visual: Spot vs 3M comparison */}
                  <div className="flex items-end gap-2 h-8">
                    <div className="flex-1 flex flex-col items-center">
                      <div className="text-[7px] text-neutral-500 mb-0.5">Spot</div>
                      <div
                        className={`w-full rounded-t-sm ${v.state === 'contango' ? 'bg-blue-500/50' : 'bg-red-500/50'}`}
                        style={{ height: `${Math.max(20, (spot / Math.max(spot, v.vix3m)) * 100)}%` }}
                      />
                      <div className="text-[8px] font-mono font-bold text-neutral-200 mt-0.5">{spot.toFixed(1)}</div>
                    </div>
                    <div className="flex-1 flex flex-col items-center">
                      <div className="text-[7px] text-neutral-500 mb-0.5">3M</div>
                      <div
                        className={`w-full rounded-t-sm ${v.state === 'contango' ? 'bg-blue-500/30' : 'bg-red-500/30'}`}
                        style={{ height: `${Math.max(20, (v.vix3m / Math.max(spot, v.vix3m)) * 100)}%` }}
                      />
                      <div className="text-[8px] font-mono font-bold text-neutral-300 mt-0.5">{v.vix3m.toFixed(1)}</div>
                    </div>
                  </div>
                </div>

                {/* Percentile */}
                <div className="flex items-center gap-1.5">
                  <span className="text-[7px] text-neutral-500 shrink-0">1Y %ile</span>
                  <div className="flex-1 h-1 rounded-full bg-neutral-800 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${v.percentile > 75 ? 'bg-red-500' : v.percentile < 25 ? 'bg-green-500' : 'bg-yellow-500'}`}
                      style={{ width: `${v.percentile}%` }}
                    />
                  </div>
                  <span className={`text-[7px] font-mono ${v.percentile > 75 ? 'text-red-400' : v.percentile < 25 ? 'text-green-400' : 'text-yellow-400'}`}>
                    {v.percentile}th
                  </span>
                </div>

                {/* One-line Signal Interpretation */}
                <div className="bg-neutral-900/60 rounded px-1.5 py-1 border-l-2 border-blue-500/50">
                  <div className="text-[8px] text-neutral-300 leading-snug italic">{signalText}</div>
                </div>
              </>
            );
          })()}

          {!v && <div className="text-[9px] text-neutral-600 py-4 text-center">Loading...</div>}
        </div>

        {/* ─── Col 3: Overnight Gaps — Vertical Bar Chart (3 cols) ─── */}
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

          {g && (() => {
            // Sort by absolute overnight return (biggest movers first)
            const sorted = [...g.indices].sort(
              (a, b) => Math.abs(b.overnight_return_pct) - Math.abs(a.overnight_return_pct)
            );
            const maxAbs = Math.max(...sorted.map(s => Math.abs(s.overnight_return_pct)), 0.01);
            const notableSet = new Set(g.summary.notable_gaps.map(n => n.ticker));

            // Show top ~14 items to fit in the column
            const items = sorted.slice(0, 14);

            return (
              <div className="flex items-end gap-px" style={{ height: 130 }}>
                {items.map(item => {
                  const pct = item.overnight_return_pct;
                  const absPct = Math.abs(pct);
                  // Bar height: proportional to move magnitude (min 12% for label visibility)
                  const heightPct = Math.max(12, (absPct / maxAbs) * 100);
                  // Color intensity: 0.15 (tiny) to 0.7 (max)
                  const intensity = 0.15 + (absPct / maxAbs) * 0.55;
                  const bgColor = pct >= 0
                    ? `rgba(16, 185, 129, ${intensity})`
                    : `rgba(239, 68, 68, ${intensity})`;
                  const isNotable = notableSet.has(item.ticker);

                  return (
                    <div
                      key={item.ticker}
                      className="flex-1 flex flex-col items-center justify-end min-w-0"
                      style={{ height: '100%' }}
                    >
                      {/* Percentage label above bar */}
                      <div className={`text-[7px] font-mono font-bold mb-0.5 leading-none ${
                        pct >= 0 ? 'text-emerald-400' : 'text-red-400'
                      }`}>
                        {pct > 0 ? '+' : ''}{pct.toFixed(1)}
                      </div>
                      {/* Vertical bar */}
                      <div
                        className={`w-full rounded-t-sm transition-all ${
                          isNotable ? 'ring-1 ring-amber-500/50' : ''
                        }`}
                        style={{
                          backgroundColor: bgColor,
                          height: `${heightPct}%`,
                          minHeight: 16,
                        }}
                        title={`${item.ticker} (${item.name}): ${pct > 0 ? '+' : ''}${pct.toFixed(2)}% overnight${
                          item.z_score ? ` | z=${item.z_score.toFixed(1)}` : ''
                        }${item.last_price > 0 ? ` | $${item.last_price.toFixed(0)}` : ''}`}
                      />
                      {/* Ticker label below bar */}
                      <div className="text-[6px] font-mono text-neutral-400 mt-0.5 leading-none truncate w-full text-center">
                        {item.ticker}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })()}

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

      {/* ═══ Compact RRG Table Row ═══ */}
      <div className="border-t border-neutral-800/50 px-3 py-2">
        <CompactRRGTable />
      </div>

      {/* ═══ AI Market Insight Footer ═══ */}
      <div className="border-t border-neutral-800/50 px-3 py-2">
        <AIMarketInsight />
      </div>
    </div>
  );
}
