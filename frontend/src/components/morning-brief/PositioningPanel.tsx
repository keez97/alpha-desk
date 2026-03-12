import { useState, useRef, useEffect } from 'react';
import { usePositioning } from '../../hooks/usePositioning';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import type { MarketPositioning } from '../../lib/api';

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════
const CATEGORIES = ['All', 'Equities', 'Rates', 'Energy', 'Metals', 'Agriculture', 'FX'] as const;
const DEFAULT_MARKETS = ['ES', 'NQ', 'ZB', 'GC', 'CL', 'NG', '6E', 'DX'];
const STORAGE_KEY = 'cot_positioning_markets';

function getInitialMarkets(): Set<string> {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return new Set(JSON.parse(saved));
  } catch { /* ignore */ }
  return new Set(DEFAULT_MARKETS);
}

function saveMarkets(markets: Set<string>) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(markets))); } catch { /* ignore */ }
}

function formatContracts(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

// ═══════════════════════════════════════════════════════════════
// Sub-components
// ═══════════════════════════════════════════════════════════════

function Tooltip({ text, children }: { text: string; children: React.ReactNode }) {
  return (
    <span className="relative group/tip cursor-help">
      {children}
      <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-max max-w-[180px] rounded bg-neutral-800 border border-neutral-700 px-2 py-1.5 text-[9px] leading-snug text-neutral-300 opacity-0 group-hover/tip:opacity-100 transition-opacity z-50 shadow-lg">
        {text}
      </span>
    </span>
  );
}

function ColumnHeaders() {
  // Uses identical flex layout as PositioningBar: gap:8, same widths on direct flex children
  return (
    <div className="flex items-center h-4 mb-1 border-b border-neutral-800/50 pb-1" style={{ gap: 8 }}>
      {/* Label spacer — same as PositioningBar label (48px) */}
      <span style={{ width: 48, flexShrink: 0 }} />

      {/* Bar header — same as PositioningBar flex-1 bar container */}
      <div className="flex-1 text-center">
        <Tooltip text="Bar length shows the relative size of the net position. The larger group (hedger or spec) fills the full bar; the smaller scales proportionally. Green = net long, Red = net short.">
          <span className="text-[8px] font-medium text-neutral-500 uppercase tracking-wider">Positioning</span>
        </Tooltip>
      </div>

      {/* Net — wrapper div is the flex child with width, Tooltip inside */}
      <div style={{ width: 60, flexShrink: 0 }} className="text-right">
        <Tooltip text="Net contracts = long minus short contracts held by that trader group.">
          <span className="text-[8px] font-medium text-neutral-500 uppercase tracking-wider">Net</span>
        </Tooltip>
      </div>

      {/* Side */}
      <div style={{ width: 40, flexShrink: 0 }} className="text-center">
        <Tooltip text="Whether the group is net long (buying) or net short (selling) overall.">
          <span className="text-[8px] font-medium text-neutral-500 uppercase tracking-wider">Side</span>
        </Tooltip>
      </div>

      {/* %ile */}
      <div style={{ width: 28, flexShrink: 0 }} className="text-right">
        <Tooltip text="Percentile rank vs 52-week range. P90+ or P10- = extreme positioning (amber). P50 = middle of the range.">
          <span className="text-[8px] font-medium text-neutral-500 uppercase tracking-wider">%ile</span>
        </Tooltip>
      </div>

      {/* Wk */}
      <div style={{ width: 16, flexShrink: 0 }} className="text-center">
        <Tooltip text="Week-over-week change in net positioning. ↑ = added to position, ↓ = reduced position.">
          <span className="text-[8px] font-medium text-neutral-500 uppercase tracking-wider">Wk</span>
        </Tooltip>
      </div>
    </div>
  );
}

function PositioningBar({
  label,
  net,
  percentile,
  weeklyChange,
  isExtreme,
  maxNet,
}: {
  label: string;
  net: number;
  percentile: number;
  weeklyChange?: number;
  isExtreme?: boolean;
  maxNet: number;
}) {
  const isLong = net > 0;
  const barColor = isLong ? 'bg-emerald-500' : 'bg-red-500';
  const textColor = isLong ? 'text-emerald-400' : 'text-red-400';
  const direction = isLong ? 'LONG' : 'SHORT';
  // Bar width = magnitude of net position relative to the largest in this market
  // This makes hedger vs spec bars directly comparable within a market
  const fillWidth = maxNet > 0 ? Math.max(3, (Math.abs(net) / maxNet) * 100) : 3;

  return (
    <div className="flex items-center h-5" style={{ gap: 8 }}>
      {/* Label */}
      <span className="text-[9px] text-neutral-500" style={{ width: 48, flexShrink: 0 }}>{label}</span>

      {/* Bar container */}
      <div className="flex-1 h-3.5 rounded-sm bg-neutral-800 overflow-hidden relative">
        <div
          className={`h-full rounded-sm ${barColor} transition-all duration-300`}
          style={{ width: `${fillWidth}%`, opacity: isExtreme ? 1 : 0.65 }}
        />
        {isExtreme && (
          <div className="absolute inset-0 rounded-sm border border-amber-400/40" />
        )}
      </div>

      {/* Net position */}
      <span className={`text-[9px] font-mono font-bold text-right ${textColor}`} style={{ width: 60, flexShrink: 0 }}>
        {isLong ? '+' : ''}{formatContracts(net)}
      </span>

      {/* Direction badge */}
      <span className={`text-[7px] font-bold text-center ${textColor}`} style={{ width: 40, flexShrink: 0 }}>
        {direction}
      </span>

      {/* Percentile */}
      <span className={`text-[8px] font-mono text-right ${
        isExtreme ? 'text-amber-400 font-bold' : 'text-neutral-500'
      }`} style={{ width: 28, flexShrink: 0 }}>
        P{percentile}
      </span>

      {/* Weekly change */}
      <span className="text-[8px] text-center" style={{ width: 16, flexShrink: 0 }}>
        {weeklyChange != null && weeklyChange !== 0 ? (
          <span className={weeklyChange > 0 ? 'text-emerald-400' : 'text-red-400'}>
            {weeklyChange > 0 ? '↑' : '↓'}
          </span>
        ) : ''}
      </span>
    </div>
  );
}

function MarketCard({ market }: { market: MarketPositioning }) {
  const commExtreme = market.extreme_flag?.startsWith('commercial_extreme');
  const specExtreme = market.extreme_flag?.startsWith('speculative_extreme');
  // Extract speculative weekly change if available (rough estimate from weekly_change)
  const specWeeklyChange = market.weekly_change != null ? -market.weekly_change : undefined;
  // Normalize bar widths: the larger position fills 100%, the smaller scales proportionally
  const maxNet = Math.max(Math.abs(market.commercial_net), Math.abs(market.speculative_net));

  return (
    <div className="py-1.5 border-b border-neutral-800/30 last:border-0">
      {/* Market header */}
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[10px] font-bold text-neutral-200">{market.name}</span>
        <span className="text-[8px] font-mono text-neutral-500">({market.ticker})</span>
        {market.divergence && (
          <Tooltip text="Hedgers and speculators are positioned on opposite sides with a wide gap — watch for reversal.">
            <span className="text-[7px] px-1.5 py-0.5 rounded-full bg-amber-900/30 text-amber-400 font-medium">DIV</span>
          </Tooltip>
        )}
      </div>

      {/* Hedgers bar */}
      <PositioningBar
        label="Hedgers"
        net={market.commercial_net}
        percentile={market.commercial_percentile}
        weeklyChange={market.weekly_change ?? undefined}
        isExtreme={commExtreme}
        maxNet={maxNet}
      />

      {/* Specs bar */}
      <PositioningBar
        label="Specs"
        net={market.speculative_net}
        percentile={market.speculative_percentile}
        weeklyChange={specWeeklyChange ?? undefined}
        isExtreme={specExtreme}
        maxNet={maxNet}
      />
    </div>
  );
}

function AlertBadge({
  severity,
  message,
  bias,
}: {
  severity: 'high' | 'medium';
  message: string;
  bias: 'bullish' | 'bearish' | 'neutral';
}) {
  const colors =
    severity === 'high'
      ? 'border-red-600/50 bg-red-900/20 text-red-400'
      : 'border-amber-600/50 bg-amber-900/20 text-amber-400';

  const biasIcon = bias === 'bullish' ? '📈' : bias === 'bearish' ? '📉' : '➡️';

  return (
    <div className={`rounded border p-1.5 text-[10px] ${colors}`}>
      <div className="flex items-start gap-1.5">
        <span className="text-xs">{biasIcon}</span>
        <div className="flex-1 leading-snug">{message}</div>
      </div>
    </div>
  );
}

function SettingsDropdown({
  allMarkets,
  visibleMarkets,
  onToggle,
  onReset,
  onClose,
}: {
  allMarkets: MarketPositioning[];
  visibleMarkets: Set<string>;
  onToggle: (ticker: string) => void;
  onReset: () => void;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  // Group markets by category
  const grouped: Record<string, MarketPositioning[]> = {};
  for (const m of allMarkets) {
    if (!grouped[m.category]) grouped[m.category] = [];
    grouped[m.category].push(m);
  }

  return (
    <div ref={ref} className="absolute right-0 top-6 z-50 w-64 bg-neutral-900 border border-neutral-700 rounded-lg shadow-xl p-3 space-y-2">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] font-bold text-neutral-300">Customize Markets</span>
        <button onClick={onReset} className="text-[9px] text-blue-400 hover:text-blue-300 cursor-pointer">
          Reset defaults
        </button>
      </div>
      {Object.entries(grouped).map(([cat, markets]) => (
        <div key={cat}>
          <div className="text-[8px] font-bold text-neutral-500 uppercase mb-0.5">{cat}</div>
          <div className="space-y-0.5">
            {markets.sort((a, b) => a.sort_order - b.sort_order).map(m => (
              <label key={m.ticker} className="flex items-center gap-2 cursor-pointer py-0.5 hover:bg-neutral-800/50 rounded px-1">
                <input
                  type="checkbox"
                  checked={visibleMarkets.has(m.ticker)}
                  onChange={() => onToggle(m.ticker)}
                  className="w-3 h-3 rounded border-neutral-600 accent-blue-500"
                />
                <span className="text-[9px] text-neutral-300">{m.name}</span>
                <span className="text-[8px] text-neutral-600 font-mono ml-auto">{m.ticker}</span>
              </label>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// Main Component
// ═══════════════════════════════════════════════════════════════
export function PositioningPanel() {
  const { data, isLoading, error, refetch } = usePositioning();
  const [activeTab, setActiveTab] = useState<string>('All');
  const [visibleMarkets, setVisibleMarkets] = useState<Set<string>>(getInitialMarkets);
  const [showSettings, setShowSettings] = useState(false);

  if (isLoading) return <LoadingState message="Loading positioning data..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data || data.markets.length === 0) return null;

  const toggleMarket = (ticker: string) => {
    setVisibleMarkets(prev => {
      const next = new Set(prev);
      if (next.has(ticker)) next.delete(ticker);
      else next.add(ticker);
      saveMarkets(next);
      return next;
    });
  };

  const resetToDefaults = () => {
    const defaults = new Set(DEFAULT_MARKETS);
    setVisibleMarkets(defaults);
    saveMarkets(defaults);
  };

  // Filter markets based on active tab
  const filteredMarkets = data.markets
    .filter(m => {
      if (activeTab === 'All') return visibleMarkets.has(m.ticker);
      return m.category === activeTab;
    })
    .sort((a, b) => {
      if (a.category !== b.category) return a.category.localeCompare(b.category);
      return a.sort_order - b.sort_order;
    });

  // Only show alerts relevant to visible markets when on "All" tab
  const filteredAlerts = activeTab === 'All'
    ? data.alerts.filter(a => visibleMarkets.has(a.ticker))
    : data.alerts.filter(a => {
        const m = data.markets.find(m => m.ticker === a.ticker);
        return m?.category === activeTab;
      });

  return (
    <div className="space-y-2 rounded border border-neutral-800 bg-neutral-900/50 p-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase text-neutral-400">COT Positioning</span>
        <div className="flex items-center gap-2 relative">
          <button
            onClick={() => setShowSettings(s => !s)}
            className="text-neutral-500 hover:text-neutral-300 cursor-pointer"
            title="Customize markets"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </button>
          <span className="text-[10px] text-neutral-600">
            {new Date(data.timestamp).toLocaleTimeString()}
          </span>
          {showSettings && (
            <SettingsDropdown
              allMarkets={data.markets}
              visibleMarkets={visibleMarkets}
              onToggle={toggleMarket}
              onReset={resetToDefaults}
              onClose={() => setShowSettings(false)}
            />
          )}
        </div>
      </div>

      {/* Category tabs */}
      <div className="flex gap-1 flex-wrap">
        {CATEGORIES.map(cat => {
          const isActive = activeTab === cat;
          const label = cat === 'Agriculture' ? 'Ag' : cat;
          return (
            <button
              key={cat}
              onClick={() => setActiveTab(cat)}
              className={`text-[9px] px-2 py-0.5 rounded-full cursor-pointer transition-colors ${
                isActive
                  ? 'bg-blue-500/20 text-blue-400 font-bold'
                  : 'bg-neutral-800/50 text-neutral-500 hover:text-neutral-300'
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex gap-4 text-[9px] text-neutral-600">
        <div className="flex items-center gap-1">
          <div className="h-1.5 w-3 rounded-sm bg-emerald-500/70" />
          <span>Net Long</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="h-1.5 w-3 rounded-sm bg-red-500/70" />
          <span>Net Short</span>
        </div>
        <Tooltip text="Positioning in the top 10% or bottom 10% of the 52-week range. Historically marks turning points.">
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-3 rounded-sm border border-amber-400/40" />
            <span>Extreme</span>
          </div>
        </Tooltip>
        <Tooltip text="Divergence: hedgers and speculators are on opposite sides with a wide percentile gap (>30pts). Smart money vs crowd.">
          <div className="flex items-center gap-1">
            <span className="text-[7px] px-1 rounded-full bg-amber-900/30 text-amber-400 font-medium">DIV</span>
            <span>Divergence</span>
          </div>
        </Tooltip>
      </div>

      {/* Column headers */}
      <ColumnHeaders />

      {/* Markets list */}
      <div className="space-y-0">
        {filteredMarkets.length === 0 && (
          <div className="text-[10px] text-neutral-600 py-4 text-center">
            No markets selected. Click ⚙ to customize.
          </div>
        )}
        {filteredMarkets.map(market => (
          <MarketCard key={market.ticker} market={market} />
        ))}
      </div>

      {/* Alerts section */}
      {filteredAlerts.length > 0 && (
        <div className="space-y-1.5 border-t border-neutral-800 pt-2">
          <span className="text-[9px] font-medium text-neutral-500">Reversal & Divergence Alerts</span>
          <div className="space-y-1">
            {filteredAlerts.map((alert, i) => (
              <AlertBadge
                key={i}
                severity={alert.severity}
                message={alert.message}
                bias={alert.bias}
              />
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="border-t border-neutral-800 pt-1.5 text-[8px] text-neutral-600">
        Percentiles vs 52-week range · CFTC COT report (weekly, Fri release) · {data.markets.length} markets tracked
      </div>
    </div>
  );
}
