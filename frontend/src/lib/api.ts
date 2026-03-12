// AlphaDesk API client - v4 aggregate-first
import axios, { AxiosError } from 'axios';
import type { AxiosInstance } from 'axios';

// In dev: '/api' proxied by Vite. In prod: full Railway URL from env.
const API_BASE = import.meta.env.VITE_API_URL || '/api';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 120000, // 2 min for LLM calls and slow cold starts
});

// ── Response pre-cache ────────────────────────────────────
// The aggregate endpoint fetches all data in a single request.
// Individual fetchXxx() functions call api.get(path) — this cache
// intercepts those calls and returns pre-fetched data, eliminating
// the need for additional HTTP requests.
const _preCache = new Map<string, any>();

/** Seed the response cache from the /morning-brief/all aggregate. */
export function seedApiCache(allData: any) {
  const mapping: Record<string, any> = {
    '/morning-brief/macro': allData.macro,
    '/morning-brief/breadth': allData.breadth,
    '/vix-term-structure': allData.vix_term_structure,
    '/morning-brief/sectors': allData.sectors,
    '/enhanced-sectors?period=1D': allData.enhanced_sectors,
    '/sector-transitions': allData.sector_transitions,
    '/sentiment-velocity': allData.sentiment_velocity,
    '/options-flow': allData.options_flow,
    '/earnings-brief': allData.earnings_brief,
    '/cot-positioning': allData.cot_positioning,
    '/scenario-risk': allData.scenario_risk,
    '/momentum-spillover': allData.momentum_spillover,
    '/overnight-returns': allData.overnight_returns,
  };
  // Endpoints whose arrays must be non-empty to be worth caching
  const requireNonEmpty: Record<string, string> = {
    '/enhanced-sectors?period=1D': 'sectors',
    '/sector-transitions': 'transitions',
    '/momentum-spillover': 'signals',
  };
  // Custom validators for endpoints that need deeper checks
  const customValidators: Record<string, (d: any) => boolean> = {
    '/morning-brief/macro': (d) => {
      // Must have regime with layers (6 layers expected)
      const layers = d?.regime?.layers;
      return layers && typeof layers === 'object' && Object.keys(layers).length >= 4;
    },
    '/morning-brief/breadth': (d) => {
      // Must have actual breadth data with total > 0
      const bd = d?.data;
      return bd && typeof bd === 'object' && (bd.total ?? 0) > 0;
    },
  };
  for (const [path, data] of Object.entries(mapping)) {
    if (!data) continue;
    const arrayKey = requireNonEmpty[path];
    if (arrayKey && (!Array.isArray(data[arrayKey]) || data[arrayKey].length === 0)) {
      console.log(`[api] Skipped pre-cache for ${path} — empty ${arrayKey}`);
      continue;
    }
    const validator = customValidators[path];
    if (validator && !validator(data)) {
      console.log(`[api] Skipped pre-cache for ${path} — failed validation`);
      continue;
    }
    _preCache.set(path, data);
  }
  console.log(`[api] Seeded pre-cache with ${_preCache.size} endpoints`);
}

// Override api.get to check pre-cache first, then fall back to HTTP.
// IMPORTANT: NOT async — returning _originalGet's Promise directly avoids
// double-wrapping that can break Axios response handling.
const _originalGet = api.get.bind(api);
(api as any).get = function (url: string, config?: any) {
  // Build full cache key including query params so parameterized endpoints
  // (e.g. /enhanced-sectors?period=1D vs ?period=3M) don't collide.
  let cacheKey = url.split('?')[0];
  if (config?.params) {
    const qs = new URLSearchParams(config.params).toString();
    if (qs) cacheKey += '?' + qs;
  } else if (url.includes('?')) {
    cacheKey = url;  // URL already has query string
  }
  // Try exact key first, then path-only fallback for endpoints without params
  const cached = _preCache.get(cacheKey) ?? _preCache.get(url.split('?')[0]);
  if (cached) {
    console.log(`[api] pre-cache HIT: ${cacheKey}`);
    return Promise.resolve({ data: cached, status: 200, statusText: 'OK', headers: {}, config: config || {} });
  }
  console.log(`[api] pre-cache MISS: ${cacheKey} — falling through to HTTP`);
  return _originalGet(url, config);
};

api.interceptors.response.use(
  (response: any) => response,
  (error: AxiosError) => {
    console.error('API Error:', error.config?.url, error.message);
    return Promise.reject(error);
  }
);

export default api;

// ── Types ──────────────────────────────────────────────────
export interface RegimeSignal {
  name: string;
  value: string;
  reading: string;
  bias: 'bull' | 'bear' | 'neutral';
}

export interface RegimeData {
  regime: 'bull' | 'bear' | 'neutral';
  confidence: number;
  bullScore: number;
  bearScore: number;
  signals: RegimeSignal[];
}

export interface MacroData {
  timestamp: string;
  indicators: { name: string; value: number; change: number }[];
  regime?: RegimeData;
}

export interface SectorData {
  ticker: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  chartData?: number[];
  chartDates?: string[];
}

export interface DriverMetric {
  label: string;
  value: string;
  direction: 'up' | 'down' | 'flat';
}

export interface NewsArticleForDriver {
  title: string;
  url: string;
  publisher: string;
  publishedAt: string | null;
  ticker?: string;
}

export interface Driver {
  headline: string;
  explanation: string;
  keyData: string;
  marketImplications: string;
  sources: string[];
  sentiment?: string;
  impactScore?: number;
  contrarianSignal?: string | null;
  affectedAssets: string[];
  newsArticles: NewsArticleForDriver[];
  metrics: DriverMetric[];
}

export interface DriverResponse {
  drivers: Driver[];
  timestamp: string;
}

export interface Quote {
  ticker: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  marketCap: number;
}

// ── Grade Types (V2 — 8-dimension institutional) ──────────
export interface GradeDimension {
  name: string;
  score: number;
  weight: number;
  assessment: string;
  data_points: string[];
}

export interface ScenarioCase {
  target_pct: number;
  probability: number;
  drivers: string[];
}

export interface CatalystEvent {
  event: string;
  expected_date: string;
  impact: 'positive' | 'negative' | 'uncertain';
  probability: number;
}

export interface Grade {
  overall: string;
  compositeScore: number;
  sector: string;
  regime: string;
  dimensions: GradeDimension[];
  summary: string;
  risks: string[];
  catalysts: string[];        // Legacy: simple string list
  catalystEvents: CatalystEvent[];  // V2: structured catalysts
  scenarios: {
    bull: ScenarioCase;
    base: ScenarioCase;
    bear: ScenarioCase;
  } | null;
  contrarianSignal: string | null;
  dataGaps: string[];
  // Legacy compat
  metrics: { name: string; grade: string; value: number }[];
}

export interface WatchlistItem {
  id: string;
  ticker: string;
  price: number;
  change: number;
  changePercent: number;
  addedAt: string;
  grade?: string;
}

export interface ScreenerResult {
  ticker: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  pe: number;
  pbv: number;
  score: number;
  momentum: number;
}

export interface ScreenerResponse {
  timestamp: string;
  valueOpportunities: ScreenerResult[];
  momentumLeaders: ScreenerResult[];
}

export interface Report {
  id: string;
  date: string;
  title: string;
  sections: ReportSection[];
}

export interface ReportSection {
  title: string;
  content: string;
  tables?: unknown[];
}

export interface Portfolio {
  id: string;
  name: string;
  capital: number;
  holdings: { ticker: string; shares: number; weight?: number }[];
  createdAt: string;
}

export interface PortfolioAnalysis {
  correlation: number[][];
  maxSharpe: {
    weights: Record<string, number>;
    return: number;
    volatility: number;
    sharpeRatio: number;
  };
  maxVariance: {
    weights: Record<string, number>;
    return: number;
    volatility: number;
    sharpeRatio: number;
  };
  monteCarlo: {
    paths: number[][];
    percentiles: Record<string, number[]>;
    stats: { mean: number; median: number; std: number };
  };
}

export interface RRGData {
  benchmark: string;
  weeks: number;
  sectors: {
    ticker: string;
    name: string;
    rsRatio: number;
    rsMomentum: number;
    volume: number;
    quadrant: string;
    history: { date: string; rsRatio: number; rsMomentum: number }[];
  }[];
}

export interface MorningReportSection {
  title: string;
  content: string;
}

// ── Macro ──────────────────────────────────────────────────
const MACRO_NAMES: Record<string, string> = {
  '^TNX': '10Y Yield', '^IRX': '3M Yield', '^VIX': 'VIX',
  'DX-Y.NYB': 'Dollar', 'GC=F': 'Gold', 'CL=F': 'Crude Oil',
  'BTC-USD': 'Bitcoin', 'SPY': 'S&P 500', 'QQQ': 'Nasdaq', 'IWM': 'Russell 2000',
  'XLF': 'Financials', 'XLK': 'Technology', 'XLE': 'Energy', 'XLV': 'Healthcare',
};

export async function fetchMacro(): Promise<MacroData> {
  const { data: raw } = await api.get('/morning-brief/macro');
  const indicators = Object.entries(raw.data || {}).map(([ticker, info]: [string, any]) => ({
    name: MACRO_NAMES[ticker] || ticker,
    value: info.price ?? 0,
    change: info.pct_change,
  }));
  const regime = raw.regime ? {
    regime: raw.regime.regime || 'neutral',
    confidence: raw.regime.confidence ?? 50,
    bullScore: raw.regime.bull_score ?? 0,
    bearScore: raw.regime.bear_score ?? 0,
    signals: (raw.regime.signals || []).map((s: any) => ({
      name: s.name || '',
      value: s.value || '',
      reading: s.reading || '',
      bias: s.bias || 'neutral',
    })),
  } : undefined;
  return { timestamp: raw.timestamp, indicators, regime };
}

// ── Sectors ────────────────────────────────────────────────
export async function fetchSectors(period: '1D' | '5D' | '1M' | '3M' = '1D'): Promise<SectorData[]> {
  const { data: raw } = await api.get('/morning-brief/sectors', { params: { period } });
  return (raw.sectors || []).map((s: any) => ({
    ticker: s.ticker,
    name: s.sector || s.name || s.ticker,
    price: s.price ?? 0,
    change: s.daily_change ?? s.change ?? 0,
    changePercent: s.daily_pct_change ?? s.changePercent ?? 0,
    chartData: s.chart_data || [],
    chartDates: s.chart_dates || [],
  }));
}

// ── Drivers ────────────────────────────────────────────────
function _mapDriver(d: any): Driver {
  // Map news_articles from backend (existing format)
  let newsArticles: NewsArticleForDriver[] = (d.news_articles || []).map((a: any) => ({
    title: a.title || '',
    url: a.url || '',
    publisher: a.publisher || 'Unknown',
    publishedAt: a.published_at || null,
    ticker: a.ticker || '',
  }));

  // Also map news_sources from Claude's response (string array: "headline — Source")
  if (d.news_sources && Array.isArray(d.news_sources) && newsArticles.length === 0) {
    newsArticles = d.news_sources.map((src: string) => {
      const parts = src.split(' — ');
      return {
        title: parts[0] || src,
        url: '',
        publisher: parts[1] || 'News',
        publishedAt: null,
        ticker: '',
      };
    });
  }

  return {
    headline: d.headline || d.title || 'Untitled',
    explanation: d.explanation || d.market_implications || '',
    keyData: d.key_data || '',
    marketImplications: d.market_implications || '',
    sources: d.sources || (d.url ? [d.url] : []),
    sentiment: d.sentiment || d.impact,
    impactScore: d.impact_score,
    contrarianSignal: d.contrarian_signal || null,
    affectedAssets: d.affected_assets || [],
    newsArticles,
    metrics: (d.metrics || []).map((m: any) => ({
      label: m.label || '',
      value: m.value || '',
      direction: m.direction || 'flat',
    })),
  };
}

export async function fetchDrivers(): Promise<DriverResponse> {
  const { data: raw } = await api.get('/morning-brief/drivers');
  const driversData = raw.data || raw;
  const drivers = Array.isArray(driversData) ? driversData : (driversData.drivers || []);
  return {
    drivers: drivers.map(_mapDriver),
    timestamp: raw.timestamp,
  };
}

export async function refreshDrivers(): Promise<DriverResponse> {
  const { data: raw } = await api.post('/morning-brief/drivers/refresh');
  const driversData = raw.data || raw;
  const drivers = Array.isArray(driversData) ? driversData : (driversData.drivers || []);
  return {
    drivers: drivers.map(_mapDriver),
    timestamp: raw.timestamp,
  };
}

// ── Morning Report ─────────────────────────────────────────
export async function fetchMorningReport(): Promise<Record<string, MorningReportSection>> {
  const { data: raw } = await api.get('/morning-brief/report');
  const reportData = raw.data || raw;
  // Normalize — extract only sections that have title+content
  const result: Record<string, MorningReportSection> = {};
  for (const [key, value] of Object.entries(reportData)) {
    if (value && typeof value === 'object' && 'title' in (value as any) && 'content' in (value as any)) {
      const v = value as any;
      result[key] = { title: v.title, content: v.content };
    }
  }
  return result;
}

// ── Market Breadth ────────────────────────────────────────
export interface BreadthData {
  advances: number;
  declines: number;
  unchanged: number;
  total: number;
  adRatio: number;
  pctAdvancing: number;
  pctDeclining: number;
  breadthThrust: boolean;
  mcclellan: number;
  netAdvances: number;
  signal: string;
  sampleSize: number;
}

export async function fetchBreadth(): Promise<BreadthData> {
  const { data: raw } = await api.get('/morning-brief/breadth');
  const d = raw.data || raw;
  return {
    advances: d.advances ?? 0,
    declines: d.declines ?? 0,
    unchanged: d.unchanged ?? 0,
    total: d.total ?? 0,
    adRatio: d.ad_ratio ?? 1,
    pctAdvancing: d.pct_advancing ?? 50,
    pctDeclining: d.pct_declining ?? 50,
    breadthThrust: d.breadth_thrust ?? false,
    mcclellan: d.mcclellan ?? 0,
    netAdvances: d.net_advances ?? 0,
    signal: d.signal || 'neutral',
    sampleSize: d.sample_size ?? 0,
  };
}

// ── VIX Term Structure ─────────────────────────────────────
export interface VixTermStructureHistoryItem {
  date?: string;
  ratio: number;
  vix: number;
}

export interface VixTermStructureData {
  vixSpot: number;
  vix3m: number;
  ratio: number;
  state: 'contango' | 'backwardation';
  magnitude: number;
  percentile: number;
  rollYield: number;
  signal: 'bullish' | 'bearish' | 'neutral';
  history: VixTermStructureHistoryItem[];
}

export async function fetchVixTermStructure(): Promise<VixTermStructureData> {
  const { data: raw } = await api.get('/vix-term-structure');
  const d = raw.data || raw;
  return {
    vixSpot: d.vix_spot ?? 0,
    vix3m: d.vix3m ?? 0,
    ratio: d.ratio ?? 1,
    state: d.state || 'contango',
    magnitude: d.magnitude ?? 0,
    percentile: d.percentile ?? 50,
    rollYield: d.roll_yield ?? 0,
    signal: d.signal || 'neutral',
    history: (d.history || []).map((h: any) => ({
      date: h.date,
      ratio: h.ratio ?? 1,
      vix: h.vix ?? 0,
    })),
  };
}

// ── Upgraded Regime Data (Institutional-grade) ─────────────
export interface RegimeLayerData {
  score: number;
  weight: number;
  weighted_contribution: number;
  signals: RegimeSignal[];
  details: Record<string, any>;
}

export interface WindhamState {
  state: string;
  label: string;
  risk_level: string;
  description: string;
}

export interface AlphaInsight {
  category: string;
  signal: string;
  action: string;
  conviction: string;
}

export interface UpgradedRegimeData extends RegimeData {
  recessionProbability: number | null;
  correlationRegime: string;
  macroSurpriseScore: number;
  compositeScore: number;
  windham: WindhamState;
  layers: Record<string, RegimeLayerData>;
  alphaInsights: AlphaInsight[];
  systemicRisk: {
    turbulenceIndex: number | null;
    turbulencePercentile: number | null;
    absorptionRatio: number | null;
    absorptionPercentile: number | null;
  };
}

export async function fetchUpgradedRegime(): Promise<UpgradedRegimeData> {
  const { data: raw } = await api.get('/morning-brief/macro');
  const regime = raw.regime || {};
  return {
    regime: regime.regime || 'neutral',
    confidence: regime.confidence ?? 50,
    bullScore: regime.bull_score ?? 0,
    bearScore: regime.bear_score ?? 0,
    signals: regime.signals || [],
    recessionProbability: regime.recession_probability ?? null,
    correlationRegime: regime.correlation_regime || 'normal',
    macroSurpriseScore: regime.macro_surprise_score ?? 0,
    compositeScore: regime.composite_score ?? 0,
    windham: regime.windham || { state: 'resilient-calm', label: 'Normal Markets', risk_level: 'low', description: '' },
    layers: regime.layers || {},
    alphaInsights: regime.alpha_insights || [],
    systemicRisk: {
      turbulenceIndex: regime.systemic_risk?.turbulence_index ?? null,
      turbulencePercentile: regime.systemic_risk?.turbulence_percentile ?? null,
      absorptionRatio: regime.systemic_risk?.absorption_ratio ?? null,
      absorptionPercentile: regime.systemic_risk?.absorption_percentile ?? null,
    },
  };
}

// ── Regime Insight (Claude-powered) ──────────────────────
export interface RegimeInsightFactor {
  label: string;
  assessment: string;
  bias: 'bull' | 'bear' | 'neutral';
}

export interface RegimeInsightDivergence {
  title: string;
  explanation: string;
  resolution: string;
}

export interface RegimeInsightWatchSignal {
  metric: string;
  trigger: string;
  timeframe: string;
}

export interface RegimeInsight {
  narrative: string;
  divergences: RegimeInsightDivergence[];
  watch_signal: RegimeInsightWatchSignal | null;
  factors: RegimeInsightFactor[];
  stance: string;
  conviction: 'high' | 'medium' | 'low';
}

export async function fetchRegimeInsight(): Promise<RegimeInsight> {
  const { data: raw } = await api.get('/morning-brief/regime-insight');
  const d = raw.data || raw;
  return {
    narrative: d.narrative || '',
    divergences: (d.divergences || []).map((div: any) => ({
      title: div.title || '',
      explanation: div.explanation || '',
      resolution: div.resolution || '',
    })),
    watch_signal: d.watch_signal ? {
      metric: d.watch_signal.metric || '',
      trigger: d.watch_signal.trigger || '',
      timeframe: d.watch_signal.timeframe || '',
    } : null,
    factors: (d.factors || []).map((f: any) => ({
      label: f.label || '',
      assessment: f.assessment || '',
      bias: f.bias || 'neutral',
    })),
    stance: d.stance || 'Unknown',
    conviction: d.conviction || 'low',
  };
}

// ── Custom Report ─────────────────────────────────────────
export async function fetchCustomReport(topics: string[]): Promise<Record<string, MorningReportSection>> {
  const { data: raw } = await api.post('/morning-brief/report/custom', { topics });
  const reportData = raw.data || raw;
  const result: Record<string, MorningReportSection> = {};
  for (const [key, value] of Object.entries(reportData)) {
    if (value && typeof value === 'object' && 'title' in (value as any) && 'content' in (value as any)) {
      const v = value as any;
      result[key] = { title: v.title, content: v.content };
    }
  }
  return result;
}

// ── Stock Search & Quote ───────────────────────────────────
export async function searchTicker(query: string): Promise<{ ticker: string; name: string; sector: string }[]> {
  const { data: raw } = await api.get('/search', { params: { q: query } });
  return raw.results || raw || [];
}

export async function fetchQuote(ticker: string): Promise<Quote> {
  const { data: raw } = await api.get(`/stock/${ticker}/quote`);
  const q = raw.quote || raw;
  return {
    ticker: q.ticker || ticker,
    price: q.price ?? q.regularMarketPrice ?? 0,
    change: q.change ?? q.regularMarketChange ?? 0,
    changePercent: q.pct_change ?? q.changePercent ?? q.regularMarketChangePercent ?? 0,
    volume: q.volume ?? q.regularMarketVolume ?? 0,
    marketCap: q.market_cap ?? q.marketCap ?? 0,
  };
}

// ── Stock Grade (V2 — institutional) ───────────────────────
function scoreToGrade(score: number | undefined): string {
  if (!score) return 'N/A';
  if (score >= 8.5) return 'STRONG BUY';
  if (score >= 7) return 'BUY';
  if (score >= 5) return 'HOLD';
  if (score >= 3) return 'SELL';
  return 'STRONG SELL';
}

export async function gradeStock(ticker: string): Promise<Grade> {
  const { data: raw } = await api.post(`/stock/${ticker}/grade`);
  const g = raw.grade || raw;

  // Parse V2 dimensions
  const dimensions: GradeDimension[] = Array.isArray(g.dimensions)
    ? g.dimensions.map((d: any) => ({
        name: d.name || '',
        score: d.score ?? 5,
        weight: d.weight ?? 0.125,
        assessment: d.assessment || '',
        data_points: d.data_points || [],
      }))
    : [];

  // Parse scenarios
  let scenarios = null;
  if (g.scenarios && typeof g.scenarios === 'object') {
    const defaultCase = { target_pct: 0, probability: 0, drivers: [] };
    scenarios = {
      bull: { ...defaultCase, ...g.scenarios.bull },
      base: { ...defaultCase, ...g.scenarios.base },
      bear: { ...defaultCase, ...g.scenarios.bear },
    };
  }

  // Parse structured catalysts
  const catalystEvents: CatalystEvent[] = Array.isArray(g.catalysts)
    ? g.catalysts
        .filter((c: any) => typeof c === 'object' && c.event)
        .map((c: any) => ({
          event: c.event,
          expected_date: c.expected_date || '',
          impact: c.impact || 'uncertain',
          probability: c.probability ?? 0.5,
        }))
    : [];

  // Legacy simple catalysts (string list)
  const simpleCatalysts: string[] = Array.isArray(g.catalysts)
    ? g.catalysts.filter((c: any) => typeof c === 'string')
    : [];

  // Build legacy metrics from dimensions for backward compat
  const metrics = dimensions.map(d => ({
    name: d.name,
    grade: scoreToGrade(d.score),
    value: d.score,
  }));

  return {
    overall: g.grade || g.overall || g.overall_grade || 'N/A',
    compositeScore: g.composite_score ?? 0,
    sector: g.sector || '',
    regime: g.regime || 'neutral',
    dimensions,
    summary: g.thesis || g.summary || '',
    risks: g.key_risks || g.risks || [],
    catalysts: simpleCatalysts,
    catalystEvents,
    scenarios,
    contrarianSignal: g.contrarian_signal || null,
    dataGaps: g.data_gaps || [],
    metrics,
  };
}

// ── Watchlist ──────────────────────────────────────────────
export async function fetchWatchlist(): Promise<WatchlistItem[]> {
  const { data: raw } = await api.get('/watchlist');
  return (raw.items || raw || []).map((item: any) => ({
    id: item.id?.toString() || item.ticker,
    ticker: item.ticker,
    price: item.price ?? 0,
    change: item.change ?? 0,
    changePercent: item.pct_change ?? item.changePercent ?? 0,
    addedAt: item.added_at || item.addedAt || '',
    grade: item.last_grade || item.grade,
  }));
}

export async function addToWatchlist(ticker: string): Promise<WatchlistItem> {
  const { data: raw } = await api.post('/watchlist', { ticker });
  return {
    id: raw.id?.toString() || raw.ticker || ticker,
    ticker: raw.ticker || ticker,
    price: raw.price ?? 0,
    change: raw.change ?? 0,
    changePercent: raw.pct_change ?? raw.changePercent ?? 0,
    addedAt: raw.added_at || raw.addedAt || new Date().toISOString(),
  };
}

export async function removeFromWatchlist(id: string): Promise<void> {
  await api.delete(`/watchlist/${id}`);
}

// ── Screener ───────────────────────────────────────────────
export async function runScreener(): Promise<ScreenerResponse> {
  const { data: raw } = await api.post('/screener/run');
  const results = raw.results || {};
  return {
    timestamp: raw.timestamp || new Date().toISOString(),
    valueOpportunities: results.value_opportunities || results.valueOpportunities || [],
    momentumLeaders: results.momentum_leaders || results.momentumLeaders || [],
  };
}

export async function fetchLatestScreener(): Promise<ScreenerResponse> {
  const { data: raw } = await api.get('/screener/latest');
  const results = raw.results || {};
  if (!results || typeof results !== 'object') {
    return { timestamp: raw.timestamp, valueOpportunities: [], momentumLeaders: [] };
  }
  return {
    timestamp: raw.timestamp || new Date().toISOString(),
    valueOpportunities: results.value_opportunities || results.valueOpportunities || [],
    momentumLeaders: results.momentum_leaders || results.momentumLeaders || [],
  };
}

// ── Weekly Report ──────────────────────────────────────────
export function generateWeeklyReportSSE(): string {
  return '/api/weekly-report/generate';
}

export async function fetchReportList(): Promise<{ id: string; date: string; title: string }[]> {
  const { data: raw } = await api.get('/weekly-report/list');
  return (raw.reports || []).map((r: any) => ({
    id: r.id?.toString() || '',
    date: r.generated_at || r.data_as_of || r.date || '',
    title: r.summary || r.title || `Report ${r.id}`,
  }));
}

export async function fetchReport(id: string): Promise<Report> {
  const { data: raw } = await api.get(`/weekly-report/${id}`);
  const reportData = raw.report || {};
  const sections: ReportSection[] = [];
  if (typeof reportData === 'object') {
    for (const [key, value] of Object.entries(reportData)) {
      if (typeof value === 'object' && value !== null) {
        const v = value as any;
        sections.push({
          title: v.title || key.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
          content: v.summary || v.content || v.analysis || JSON.stringify(v, null, 2),
          tables: v.tables || v.data || undefined,
        });
      } else if (typeof value === 'string') {
        sections.push({ title: key.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()), content: value });
      }
    }
  }
  return {
    id: raw.id?.toString() || id,
    date: raw.data_as_of || raw.generated_at || raw.date || '',
    title: raw.summary || raw.title || `Weekly Report`,
    sections: sections.length > 0 ? sections : [{ title: 'Report', content: typeof reportData === 'string' ? reportData : JSON.stringify(reportData, null, 2) }],
  };
}

export async function deleteReport(id: string): Promise<void> {
  await api.delete(`/weekly-report/${id}`);
}

// ── Portfolio ──────────────────────────────────────────────
export async function fetchPortfolios(): Promise<Portfolio[]> {
  const { data: raw } = await api.get('/portfolio');
  return (raw.portfolios || []).map((p: any) => ({
    id: p.id?.toString() || '',
    name: p.name,
    capital: p.capital ?? 100000,
    holdings: (p.holdings || []).map((h: any) => ({
      ticker: h.ticker,
      shares: h.shares ?? h.weight ?? 0,
      weight: h.weight,
    })),
    createdAt: p.created_at || p.createdAt || '',
  }));
}

export async function createPortfolio(data: {
  name: string;
  capital: number;
  holdings: { ticker: string; shares: number }[];
}): Promise<Portfolio> {
  const { data: raw } = await api.post('/portfolio', {
    name: data.name,
    capital: data.capital,
    holdings: data.holdings.map(h => ({ ticker: h.ticker, weight: h.shares })),
  });
  return {
    id: raw.id?.toString() || '',
    name: raw.name,
    capital: raw.capital ?? data.capital,
    holdings: (raw.holdings || []).map((h: any) => ({
      ticker: h.ticker,
      shares: h.shares ?? h.weight ?? 0,
      weight: h.weight,
    })),
    createdAt: raw.created_at || raw.createdAt || new Date().toISOString(),
  };
}

export async function fetchPortfolio(id: string): Promise<Portfolio> {
  const { data: raw } = await api.get(`/portfolio/${id}`);
  return {
    id: raw.id?.toString() || id,
    name: raw.name,
    capital: raw.capital ?? 100000,
    holdings: (raw.holdings || []).map((h: any) => ({
      ticker: h.ticker,
      shares: h.shares ?? h.weight ?? 0,
      weight: h.weight,
    })),
    createdAt: raw.created_at || raw.createdAt || '',
  };
}

export async function updatePortfolio(
  id: string,
  data: Partial<{ name: string; capital: number; holdings: { ticker: string; shares: number }[] }>
): Promise<Portfolio> {
  const { data: raw } = await api.put(`/portfolio/${id}`, data);
  return {
    id: raw.id?.toString() || id,
    name: raw.name,
    capital: raw.capital,
    holdings: (raw.holdings || []).map((h: any) => ({
      ticker: h.ticker,
      shares: h.shares ?? h.weight ?? 0,
      weight: h.weight,
    })),
    createdAt: raw.created_at || raw.createdAt || '',
  };
}

export async function deletePortfolio(id: string): Promise<void> {
  await api.delete(`/portfolio/${id}`);
}

export async function analyzePortfolio(id: string): Promise<PortfolioAnalysis> {
  const { data: raw } = await api.post(`/portfolio/${id}/analysis`);
  const corr = raw.correlation_matrix || raw.correlation || [];
  const sharpe = raw.max_sharpe_optimization || raw.maxSharpe || {};
  const variance = raw.max_variance_optimization || raw.maxVariance || {};
  const mc = raw.monte_carlo_simulation || raw.monteCarlo || {};
  return {
    correlation: corr.matrix || corr || [],
    maxSharpe: {
      weights: sharpe.weights || {},
      return: sharpe.expected_return ?? sharpe.return ?? 0,
      volatility: sharpe.volatility ?? 0,
      sharpeRatio: sharpe.sharpe_ratio ?? sharpe.sharpeRatio ?? 0,
    },
    maxVariance: {
      weights: variance.weights || {},
      return: variance.expected_return ?? variance.return ?? 0,
      volatility: variance.volatility ?? 0,
      sharpeRatio: variance.sharpe_ratio ?? variance.sharpeRatio ?? 0,
    },
    monteCarlo: {
      paths: mc.paths || [],
      percentiles: mc.percentiles || {},
      stats: {
        mean: mc.stats?.mean ?? mc.mean ?? 0,
        median: mc.stats?.median ?? mc.median ?? 0,
        std: mc.stats?.std ?? mc.std ?? 0,
      },
    },
  };
}

// ── RRG ────────────────────────────────────────────────────
export async function fetchRRG(benchmark: string = 'SPY', weeks: number = 20): Promise<RRGData> {
  const { data: raw } = await api.get('/rrg', { params: { benchmark, weeks } });
  const rrg = raw.data || raw;
  return {
    benchmark: rrg.benchmark || benchmark,
    weeks: rrg.weeks || weeks,
    sectors: (rrg.sectors || []).map((s: any) => ({
      ticker: s.ticker,
      name: s.sector || s.name || s.ticker,
      rsRatio: s.rs_ratio ?? s.rsRatio ?? 100,
      rsMomentum: s.rs_momentum ?? s.rsMomentum ?? 0,
      volume: s.volume ?? 0,
      quadrant: s.quadrant || 'Unknown',
      history: (s.trail || s.history || []).map((h: any) => ({
        date: h.date,
        rsRatio: h.rs_ratio ?? h.rsRatio ?? 100,
        rsMomentum: h.rs_momentum ?? h.rsMomentum ?? 0,
      })),
    })),
  };
}

// ── Backtester ────────────────────────────────────────────
export interface Factor {
  id: number;
  name: string;
  description: string;
  category: string;
  customizable: boolean;
}

export interface CreateBacktestRequest {
  name: string;
  start_date: string;
  end_date: string;
  rebalance_frequency: 'Monthly' | 'Quarterly' | 'Annual';
  transaction_costs: {
    commission_bps: number;
    slippage_bps: number;
  };
  universe_selection: string;
  factor_allocations: Record<string, number>;
}

export interface BacktestStatus {
  id: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress_percent: number;
  current_rebalance_date?: string;
  error_message?: string;
}

export interface BacktestResult {
  statistics: {
    total_return: number;
    annualized_return: number;
    annualized_volatility: number;
    sharpe_ratio: number;
    sortino_ratio: number;
    calmar_ratio: number;
    max_drawdown: number;
    information_ratio: number;
    hit_rate: number;
    best_day: number;
    worst_day: number;
    avg_turnover: number;
  };
  equity_curve: Array<{ date: string; strategy: number; benchmark: number; drawdown: number }>;
  factor_exposures: Array<{ date: string; [key: string]: number | string }>;
  correlation_matrix: number[][];
  alpha_decay: {
    pre_publication_return: number;
    post_publication_return: number;
    decay_percent: number;
  };
}

export interface Backtest {
  id: number;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  results?: BacktestResult;
}

export const createBacktest = (data: CreateBacktestRequest) =>
  api.post('/backtests', data).then((r) => r.data);

export const runBacktest = (id: number) =>
  api.post(`/backtests/${id}/run`).then((r) => r.data);

export const getBacktestStatus = (id: number) =>
  api.get(`/backtests/${id}/status`).then((r) => r.data);

export const getBacktestResults = (id: number) =>
  api.get(`/backtests/${id}/results`).then((r) => r.data);

export const exportBacktest = (id: number) =>
  api.get(`/backtests/${id}/export`).then((r) => r.data);

export const listBacktests = () =>
  api.get('/backtests').then((r) => r.data?.backtests || []);

export const deleteBacktest = (id: number) =>
  api.delete(`/backtests/${id}`).then((r) => r.data);

export const getFactors = () =>
  api.get('/factors').then((r) => r.data);

export const createFactor = (data: any) =>
  api.post('/factors', data).then((r) => r.data);

export const getFactorScores = (id: number) =>
  api.get(`/factors/${id}/scores`).then((r) => r.data);

// ── Model Settings ─────────────────────────────────────────
export interface ModelInfo {
  key: string;
  openrouterId: string;
}

export interface ModelsResponse {
  current: string;
  currentId: string;
  available: ModelInfo[];
}

export async function fetchModels(): Promise<ModelsResponse> {
  const { data } = await api.get('/settings/models');
  return {
    current: data.current,
    currentId: data.current_id,
    available: (data.available || []).map((m: any) => ({
      key: m.key,
      openrouterId: m.openrouter_id,
    })),
  };
}

export async function switchModel(modelKey: string): Promise<ModelsResponse> {
  const { data } = await api.post('/settings/models', { model: modelKey });
  return {
    current: data.current,
    currentId: data.current_id,
    available: [],
  };
}

// ── Event Scanner ──────────────────────────────────────────
export interface EventItem {
  id: number;
  ticker: string;
  event_type: string;
  severity_score: number;
  headline: string;
  event_date: string;
  detected_at: string;
  source: string;
}

export interface AlphaDecayWindow {
  window_type: string;
  abnormal_return: number;
  benchmark_return: number;
  confidence: number;
}

export interface EventDetail extends EventItem {
  description: string;
  metadata: any;
  alpha_decay_windows: AlphaDecayWindow[];
}

export interface PollingStatus {
  last_run: string | null;
  events_found: number;
  status: string;
}

export interface EventsListResponse {
  items: EventItem[];
  total: number;
  page: number;
  page_size: number;
}

export const listEvents = (params?: any) =>
  api.get('/events', { params }).then((r) => r.data as EventsListResponse);

export const getEvent = (id: number) =>
  api.get(`/events/${id}`).then((r) => r.data as EventDetail);

export const getAlphaDecay = (id: number) =>
  api.get(`/events/${id}/alpha-decay`).then((r) => r.data as AlphaDecayWindow[]);

export const triggerScan = () =>
  api.post('/events/scan').then((r) => r.data);

export const getPollingStatus = () =>
  api.get('/events/polling-status').then((r) => r.data as PollingStatus);

export const getEventTimeline = (params?: any) =>
  api.get('/events/timeline', { params }).then((r) => r.data as EventItem[]);

export const getScreenerBadges = (tickers: string[]) =>
  api.get('/events/screener-badges', { params: { tickers: tickers.join(',') } }).then((r) => r.data);

export const deleteEvent = (id: number) =>
  api.delete(`/events/${id}`).then((r) => r.data);

// ── Earnings ────────────────────────────────────────────────
export interface EarningsCalendarItem {
  ticker: string;
  earnings_date: string;
  days_to_earnings: number;
  consensus_eps: number;
  smart_estimate_eps: number;
  divergence_pct: number;
  signal: 'buy' | 'sell' | 'hold';
  confidence: number;
}

export interface EarningsHistory {
  fiscal_quarter: string;
  actual_eps: number;
  consensus_eps: number;
  smart_estimate_eps: number;
  surprise_pct: number;
  report_date: string;
}

export interface PEADData {
  fiscal_quarter: string;
  surprise_direction: string;
  car_1d: number;
  car_5d: number;
  car_21d: number;
  car_60d: number;
}

export interface EarningsSignal {
  ticker: string;
  signal: string;
  confidence: number;
  smart_eps: number;
  consensus_eps: number;
  divergence_pct: number;
  days_to_earnings: number;
}

export interface EarningsCalendarResponse {
  items: EarningsCalendarItem[];
  total: number;
}

export interface EarningsHistoryResponse {
  quarters: EarningsHistory[];
}

export interface EarningsPEADResponse {
  quarters: PEADData[];
}

export interface ScreenerEarningsSignalsResponse {
  signals: Array<{ ticker: string; signal: string; divergence_pct: number; days_to_earnings: number }>;
}

export const getEarningsCalendar = (params?: any) =>
  api.get('/earnings/calendar', { params }).then((r) => r.data as EarningsCalendarResponse);

export const getEarningsHistory = (ticker: string) =>
  api.get(`/earnings/${ticker}/history`).then((r) => r.data as EarningsHistoryResponse);

export const getEarningsSignal = (ticker: string) =>
  api.get(`/earnings/${ticker}/signal`).then((r) => r.data as EarningsSignal);

export const getEarningsPEAD = (ticker: string) =>
  api.get(`/earnings/${ticker}/pead`).then((r) => r.data as EarningsPEADResponse);

export const refreshEarnings = () =>
  api.post('/earnings/refresh').then((r) => r.data);

export const getScreenerEarningsSignals = (tickers: string[]) =>
  api.get('/earnings/screener-signals', { params: { tickers: tickers.join(',') } }).then((r) => r.data as ScreenerEarningsSignalsResponse);

// ── Sentiment ────────────────────────────────────────────────
export interface SentimentData {
  ticker: string;
  scores: { window: string; score: number; velocity: number; article_count: number }[];
  lm_categories: Record<string, number>;
}

export interface SentimentHistoryPoint {
  date: string;
  score: number;
  velocity: number;
  article_count: number;
  price?: number;
}

export interface SentimentAlert {
  id: number;
  ticker: string;
  alert_type: string;
  sentiment_score: number;
  price_return: number;
  divergence_magnitude: number;
  alert_date: string;
  resolved_at: string | null;
}

export interface SentimentMover {
  ticker: string;
  sentiment_score: number;
  velocity: number;
  velocity_change: number;
  article_count: number;
}

export interface NewsArticle {
  id: number;
  headline: string;
  source: string;
  published_at: string;
  sentiment_score: number;
  source_url: string;
}

export interface SentimentHeatmapSector {
  sector: string;
  avg_sentiment: number;
  article_count: number;
  top_movers: { ticker: string; score: number }[];
}

export const getSentiment = (ticker: string) =>
  api.get(`/sentiment/${ticker}`).then(r => r.data as SentimentData);

export const getSentimentHistory = (ticker: string, days: number = 30) =>
  api.get(`/sentiment/${ticker}/history`, { params: { days } }).then(r => r.data as SentimentHistoryPoint[]);

export const getSentimentAlerts = () =>
  api.get('/sentiment/alerts').then(r => {
    const d = r.data;
    return Array.isArray(d) ? d as SentimentAlert[] : [];
  });

export const getSentimentMovers = (limit: number = 20) =>
  api.get('/sentiment/movers', { params: { limit } }).then(r => {
    const d = r.data;
    return Array.isArray(d) ? d as SentimentMover[] : [];
  });

export const getSentimentNews = (ticker: string, limit: number = 20) =>
  api.get(`/sentiment/news/${ticker}`, { params: { limit } }).then(r => r.data as NewsArticle[]);

export const getSentimentHeatmap = () =>
  api.get('/sentiment/heatmap').then(r => r.data as SentimentHeatmapSector[]);

export const refreshSentiment = () =>
  api.post('/sentiment/refresh').then(r => r.data);

// ── Quantitative Screener ──────────────────────────
export interface QuantScreenResult {
  ticker: string;
  name: string;
  price: number;
  change_1d: number;
  change_1d_pct: number;
  rs_ratio: number;
  rs_momentum: number;
  quadrant: string;
}

export interface QuantScreenResponse {
  timestamp: string;
  data: {
    results: QuantScreenResult[];
    total: number;
    filters_applied: Record<string, any>;
  };
}

export interface ScreenPreset {
  id: string;
  name: string;
  description: string;
  filters: Record<string, any>;
}

export interface ScreenPresetsResponse {
  timestamp: string;
  presets: ScreenPreset[];
}

export interface QuantFilter {
  rrg_quadrant?: string[];
  rrg_momentum_min?: number;
  rrg_momentum_max?: number;
  rrg_ratio_min?: number;
  rrg_ratio_max?: number;
  change_1d_min?: number;
  change_1d_max?: number;
  sector?: string;
  sort_by?: string;
  sort_desc?: boolean;
}

export async function runQuantScreen(filters: QuantFilter): Promise<QuantScreenResponse> {
  const params: Record<string, any> = {};
  if (filters.rrg_quadrant) params.rrg_quadrant = filters.rrg_quadrant;
  if (filters.rrg_momentum_min !== undefined) params.rrg_momentum_min = filters.rrg_momentum_min;
  if (filters.rrg_momentum_max !== undefined) params.rrg_momentum_max = filters.rrg_momentum_max;
  if (filters.rrg_ratio_min !== undefined) params.rrg_ratio_min = filters.rrg_ratio_min;
  if (filters.rrg_ratio_max !== undefined) params.rrg_ratio_max = filters.rrg_ratio_max;
  if (filters.change_1d_min !== undefined) params.change_1d_min = filters.change_1d_min;
  if (filters.change_1d_max !== undefined) params.change_1d_max = filters.change_1d_max;
  if (filters.sector) params.sector = filters.sector;
  if (filters.sort_by) params.sort_by = filters.sort_by;
  if (filters.sort_desc !== undefined) params.sort_desc = filters.sort_desc;

  const { data } = await api.get('/quant-screener/screen', { params });
  return data;
}

export async function getScreenPresets(): Promise<ScreenPresetsResponse> {
  const { data } = await api.get('/quant-screener/presets');
  return data;
}

// ── Overnight Returns ──────────────────────────────────────
export interface OvernightGapIndex {
  ticker: string;
  name: string;
  overnight_return_pct: number;
  avg_overnight: number;
  std_overnight: number;
  z_score: number;
  is_outlier: boolean;
  direction: 'up' | 'down';
  last_price: number;
}

export interface OvernightReturnsSummary {
  total_tracked: number;
  gaps_up: number;
  gaps_down: number;
  net_direction: 'up' | 'down' | 'neutral';
  notable_gaps: Array<{
    ticker: string;
    overnight_return_pct: number;
    z_score: number;
    direction: 'up' | 'down';
  }>;
}

export interface OvernightReturnsData {
  timestamp: string;
  indices: OvernightGapIndex[];
  summary: OvernightReturnsSummary;
}

export async function fetchOvernightReturns(): Promise<OvernightReturnsData> {
  const { data: raw } = await api.get('/overnight-returns');
  const d = raw.data || {};
  return {
    timestamp: raw.timestamp || d.timestamp || new Date().toISOString(),
    indices: (d.indices || []).map((i: any) => ({
      ticker: i.ticker,
      name: i.name || i.ticker,
      overnight_return_pct: i.overnight_return_pct ?? 0,
      avg_overnight: i.avg_overnight ?? 0,
      std_overnight: i.std_overnight ?? 0,
      z_score: i.z_score ?? 0,
      is_outlier: i.is_outlier ?? false,
      direction: i.direction || 'up',
      last_price: i.last_price ?? 0,
    })),
    summary: {
      total_tracked: d.summary?.total_tracked ?? 0,
      gaps_up: d.summary?.gaps_up ?? 0,
      gaps_down: d.summary?.gaps_down ?? 0,
      net_direction: d.summary?.net_direction || 'neutral',
      notable_gaps: (d.summary?.notable_gaps || []).map((g: any) => ({
        ticker: g.ticker,
        overnight_return_pct: g.overnight_return_pct ?? 0,
        z_score: g.z_score ?? 0,
        direction: g.direction || 'up',
      })),
    },
  };
}

// ── Earnings Brief ─────────────────────────────────────────
export interface EarningsBriefItem {
  ticker: string;
  name: string;
  earnings_date: string;
  days_until: number;
  pre_drift_pct: number;
  pre_drift_signal: boolean;
  sector: string;
}

export interface EarningsCluster {
  week: string;
  sector: string;
  count: number;
  tickers: string[];
}

export interface EarningsBriefAlert {
  ticker: string;
  alert_type: 'pre_earnings_surge' | 'pre_earnings_decline';
  pre_drift_pct: number;
  earnings_date: string;
}

export interface EarningsBriefData {
  timestamp: string;
  upcoming: EarningsBriefItem[];
  clusters: EarningsCluster[];
  alerts: EarningsBriefAlert[];
}

export async function fetchEarningsBrief(): Promise<EarningsBriefData> {
  const { data: raw } = await api.get('/earnings-brief');
  const d = raw.data || {};
  return {
    timestamp: raw.timestamp || d.timestamp || new Date().toISOString(),
    upcoming: (d.upcoming || []).map((u: any) => ({
      ticker: u.ticker,
      name: u.name || u.ticker,
      earnings_date: u.earnings_date,
      days_until: u.days_until ?? 0,
      pre_drift_pct: u.pre_drift_pct ?? 0,
      pre_drift_signal: u.pre_drift_signal ?? false,
      sector: u.sector || 'Unknown',
    })),
    clusters: (d.clusters || []).map((c: any) => ({
      week: c.week,
      sector: c.sector,
      count: c.count ?? 0,
      tickers: c.tickers || [],
    })),
    alerts: (d.alerts || []).map((a: any) => ({
      ticker: a.ticker,
      alert_type: a.alert_type || 'pre_earnings_surge',
      pre_drift_pct: a.pre_drift_pct ?? 0,
      earnings_date: a.earnings_date,
    })),
  };
}

// ── Enhanced Sectors ────────────────────────────────────────
export interface EnhancedSectorData extends SectorData {
  rsRatio: number;
  rsMomentum: number;
  quadrant: string;
  tailLength: number;
  quadrantAge: number;
  rsTrend: 'up' | 'down' | 'flat';
  rotationDirection: 'clockwise' | 'counter-clockwise';
}

export async function fetchEnhancedSectors(period: '1D' | '5D' | '1M' | '3M' = '1D'): Promise<EnhancedSectorData[]> {
  const mapSectors = (raw: any): EnhancedSectorData[] =>
    (raw?.sectors || []).map((s: any) => ({
      ticker: s.ticker,
      name: s.name || s.sector || s.ticker,
      price: s.price ?? 0,
      change: s.change ?? 0,
      changePercent: s.pct_change ?? 0,
      rsRatio: s.rs_ratio ?? 100,
      rsMomentum: s.rs_momentum ?? 0,
      quadrant: s.quadrant || 'Unknown',
      tailLength: s.tail_length ?? 0,
      quadrantAge: s.quadrant_age ?? 0,
      rsTrend: s.rs_trend || 'flat',
      rotationDirection: s.rotation_direction || 'clockwise',
      chartData: s.chart_data || [],
    }));

  try {
    const response = await api.get('/enhanced-sectors', { params: { period } });
    const raw = response.data;
    const mapped = mapSectors(raw);

    // If pre-cache returned empty sectors, evict the stale entry and retry via HTTP
    if (mapped.length === 0) {
      const cacheKey = `/enhanced-sectors?period=${period}`;
      if (_preCache.has(cacheKey)) {
        console.log(`[fetchEnhancedSectors] pre-cache returned 0 sectors for ${period} — evicting & retrying`);
        _preCache.delete(cacheKey);
        const retryResp = await api.get('/enhanced-sectors', { params: { period } });
        const retryMapped = mapSectors(retryResp.data);
        console.log(`[fetchEnhancedSectors] retry for ${period}: ${retryMapped.length} sectors`);
        return retryMapped;
      }
    }

    return mapped;
  } catch (err) {
    console.error(`[fetchEnhancedSectors] period=${period} ERROR:`, err);
    throw err;
  }
}

// ── Stock Factors ──────────────────────────────────────────
export interface StockFactorData {
  name: string;
  value: number;
  percentile: number;
  signal: 'strong' | 'neutral' | 'weak';
}

export async function fetchStockFactors(ticker: string): Promise<StockFactorData[]> {
  const { data: raw } = await api.get(`/stock/${ticker}/factors`);
  return (raw.factors || []).map((f: any) => ({
    name: f.name,
    value: f.value ?? 0,
    percentile: f.percentile ?? 50,
    signal: f.signal || 'neutral',
  }));
}

// ── Sector Transitions ──────────────────────────────────────────
export interface FactorDecomposition {
  ticker: string;
  name: string;
  beta_contribution: number;
  beta_label: string;
  size_contribution: number;
  size_label: string;
  value_contribution: number;
  value_label: string;
  momentum_contribution: number;
  momentum_label: string;
}

export interface Transition {
  ticker: string;
  name: string;
  from_quadrant: string;
  to_quadrant: string;
  transition_date: string;
  significance: number;
}

export interface CycleOverlay {
  current_phase: string;
  favorable_sectors: string[];
  unfavorable_sectors: string[];
  recession_probability: number | null;
}

export interface SectorTransitionsData {
  timestamp: string;
  transitions: Transition[];
  factor_decomposition: FactorDecomposition[];
  cycle_overlay: CycleOverlay;
}

export async function fetchSectorTransitions(): Promise<SectorTransitionsData> {
  const { data: raw } = await api.get('/sector-transitions');
  return {
    timestamp: raw.timestamp || new Date().toISOString(),
    transitions: (raw.transitions || []).map((t: any) => ({
      ticker: t.ticker,
      name: t.name,
      from_quadrant: t.from_quadrant,
      to_quadrant: t.to_quadrant,
      transition_date: t.transition_date,
      significance: t.significance ?? 0,
    })),
    factor_decomposition: (raw.factor_decomposition || []).map((f: any) => ({
      ticker: f.ticker,
      name: f.name,
      beta_contribution: f.beta_contribution ?? 0,
      beta_label: f.beta_label || '',
      size_contribution: f.size_contribution ?? 0,
      size_label: f.size_label || '',
      value_contribution: f.value_contribution ?? 0,
      value_label: f.value_label || '',
      momentum_contribution: f.momentum_contribution ?? 0,
      momentum_label: f.momentum_label || '',
    })),
    cycle_overlay: {
      current_phase: raw.cycle_overlay?.current_phase || 'unknown',
      favorable_sectors: raw.cycle_overlay?.favorable_sectors || [],
      unfavorable_sectors: raw.cycle_overlay?.unfavorable_sectors || [],
      recession_probability: raw.cycle_overlay?.recession_probability ?? null,
    },
  };
}

// ── Scenario Risk ──────────────────────────────────────────
export interface HistoricalAnalog {
  period: string;
  similarity_score: number;
  subsequent_5d_return: number;
  subsequent_10d_return: number;
  subsequent_20d_return: number;
}

export interface Scenario {
  name: string;
  description: string;
  estimated_impact_pct: number;
  probability: number;
  severity: string;
  probability_reasoning?: string;
  affected_sectors?: string[];
  historical_analog?: string;
  key_indicators?: string[];
}

export interface ScenarioRiskData {
  timestamp: string;
  var_95_historical: number;
  var_95_regime_adjusted: number;
  current_regime: string;
  historical_analogs: HistoricalAnalog[];
  scenarios: Scenario[];
}

export async function fetchScenarioRisk(): Promise<ScenarioRiskData> {
  const { data: raw } = await api.get('/scenario-risk');
  return {
    timestamp: raw.timestamp || new Date().toISOString(),
    var_95_historical: raw.var_95_historical ?? 0,
    var_95_regime_adjusted: raw.var_95_regime_adjusted ?? 0,
    current_regime: raw.current_regime || 'unknown',
    historical_analogs: (raw.historical_analogs || []).map((a: any) => ({
      period: a.period,
      similarity_score: a.similarity_score ?? 0,
      subsequent_5d_return: a.subsequent_5d_return ?? 0,
      subsequent_10d_return: a.subsequent_10d_return ?? 0,
      subsequent_20d_return: a.subsequent_20d_return ?? 0,
    })),
    scenarios: (raw.scenarios || []).map((s: any) => ({
      name: s.name,
      description: s.description,
      estimated_impact_pct: s.estimated_impact_pct ?? 0,
      probability: s.probability ?? 0,
      severity: s.severity || 'mild',
    })),
  };
}

// ── Options Flow ──────────────────────────────────────────
export interface OptionsFlowData {
  timestamp: string;
  ticker: string;
  spot_price: number;
  iv_skew: number;
  put_call_ratio: number;
  volume_imbalance: number;
  gex_signal: 'positive' | 'negative' | 'neutral';
  gex_value: number;
  total_call_volume: number;
  total_put_volume: number;
  total_call_oi: number;
  total_put_oi: number;
  signal: 'bullish' | 'bearish' | 'neutral';
  details: string[];
  expiry: string;
}

export async function fetchOptionsFlow(): Promise<OptionsFlowData> {
  const { data: raw } = await api.get('/options-flow');
  return {
    timestamp: raw.timestamp || new Date().toISOString(),
    ticker: raw.ticker || 'SPX',
    spot_price: raw.spot_price ?? 0,
    iv_skew: raw.iv_skew ?? 0,
    put_call_ratio: raw.put_call_ratio ?? 1,
    volume_imbalance: raw.volume_imbalance ?? 1,
    gex_signal: raw.gex_signal || 'neutral',
    gex_value: raw.gex_value ?? 0,
    total_call_volume: raw.total_call_volume ?? 0,
    total_put_volume: raw.total_put_volume ?? 0,
    total_call_oi: raw.total_call_oi ?? 0,
    total_put_oi: raw.total_put_oi ?? 0,
    signal: raw.signal || 'neutral',
    details: raw.details || [],
    expiry: raw.expiry || '',
  };
}

// ── Momentum Spillover ──────────────────────────────────────
export interface AssetMomentum {
  ticker: string;
  name: string;
  asset_class: string;
  momentum_1m: number;
  momentum_3m: number;
  state: 'positive' | 'negative' | 'neutral';
}

export interface MomentumSignal {
  description: string;
  type: 'bullish' | 'bearish' | 'warning';
  confidence: number;
  based_on: string[];
}

export interface MomentumMatrix {
  positive_count: number;
  negative_count: number;
  neutral_count: number;
}

export interface MomentumSpilloverData {
  timestamp: string;
  assets: AssetMomentum[];
  signals: MomentumSignal[];
  matrix: MomentumMatrix;
}

export async function fetchMomentumSpillover(): Promise<MomentumSpilloverData> {
  const { data: raw } = await api.get('/momentum-spillover');
  return {
    timestamp: raw.timestamp || new Date().toISOString(),
    assets: (raw.assets || []).map((a: any) => ({
      ticker: a.ticker,
      name: a.name,
      asset_class: a.asset_class,
      momentum_1m: a.momentum_1m ?? 0,
      momentum_3m: a.momentum_3m ?? 0,
      state: a.state || 'neutral',
    })),
    signals: (raw.signals || []).map((s: any) => ({
      description: s.description,
      type: s.type || 'warning',
      confidence: s.confidence ?? 0,
      based_on: s.based_on || [],
    })),
    matrix: {
      positive_count: raw.matrix?.positive_count ?? 0,
      negative_count: raw.matrix?.negative_count ?? 0,
      neutral_count: raw.matrix?.neutral_count ?? 0,
    },
  };
}

// ── Sentiment Velocity ──────────────────────────────────────
export interface Headline {
  headline: string;
  ticker?: string;
  source?: string;
  link?: string;
  sentiment: number;
  label?: 'positive' | 'negative' | 'neutral';
  confidence?: number;
  published_at: string;
}

export interface SentimentDistribution {
  positive: number;
  negative: number;
  neutral: number;
}

export interface HistoryPoint {
  date: string;
  sentiment: number;
  news_count: number;
}

export interface SentimentVelocityData {
  timestamp: string;
  scoring_model?: string;
  aggregate_score: number;
  velocity: number;
  velocity_signal: 'accelerating' | 'decelerating' | 'stable';
  contrarian_flag: 'overbought' | 'oversold' | null;
  news_density: number;
  attention_level: 'normal' | 'elevated' | 'extreme';
  top_headlines: Headline[];
  history_5d: HistoryPoint[];
  sentiment_distribution?: SentimentDistribution;
}

export async function fetchSentimentVelocity(tickers?: string): Promise<SentimentVelocityData> {
  const url = tickers ? `/sentiment-velocity?tickers=${tickers}` : '/sentiment-velocity';
  const { data: raw } = await api.get(url);
  return {
    timestamp: raw.timestamp || new Date().toISOString(),
    scoring_model: raw.scoring_model || undefined,
    aggregate_score: raw.aggregate_score ?? 0,
    velocity: raw.velocity ?? 0,
    velocity_signal: raw.velocity_signal || 'stable',
    contrarian_flag: raw.contrarian_flag || null,
    news_density: raw.news_density ?? 0,
    attention_level: raw.attention_level || 'normal',
    top_headlines: (raw.top_headlines || []).map((h: any) => ({
      headline: h.headline,
      ticker: h.ticker,
      source: h.source,
      link: h.link,
      sentiment: h.sentiment ?? 0,
      label: h.label,
      confidence: h.confidence,
      published_at: h.published_at,
    })),
    history_5d: (raw.history_5d || []).map((p: any) => ({
      date: p.date,
      sentiment: p.sentiment ?? 0,
      news_count: p.news_count ?? 0,
    })),
    sentiment_distribution: raw.sentiment_distribution || undefined,
  };
}

// ── COT Positioning ──────────────────────────────────────────
export interface MarketPositioning {
  name: string;
  ticker: string;
  category: string;
  sort_order: number;
  commercial_net: number;
  speculative_net: number;
  commercial_percentile: number;
  speculative_percentile: number;
  insight?: string;
  bias?: 'bullish' | 'bearish' | 'neutral';
  extreme_flag:
    | 'commercial_extreme_long'
    | 'commercial_extreme_short'
    | 'speculative_extreme_long'
    | 'speculative_extreme_short'
    | null;
  divergence: boolean;
  weekly_change?: number;
}

export interface PositioningAlert {
  ticker: string;
  market_name: string;
  type: 'extreme_positioning' | 'divergence';
  severity: 'high' | 'medium';
  message: string;
  bias: 'bullish' | 'bearish' | 'neutral';
}

export interface PositioningData {
  timestamp: string;
  markets: MarketPositioning[];
  alerts: PositioningAlert[];
  summary?: string;
}

export async function fetchPositioning(): Promise<PositioningData> {
  const { data: raw } = await api.get('/cot-positioning');
  return {
    timestamp: raw.timestamp || new Date().toISOString(),
    summary: raw.summary,
    markets: (raw.markets || []).map((m: any) => ({
      name: m.name,
      ticker: m.ticker,
      category: m.category || 'Other',
      sort_order: m.sort_order ?? 99,
      commercial_net: m.commercial_net ?? 0,
      speculative_net: m.speculative_net ?? 0,
      commercial_percentile: m.commercial_percentile ?? 50,
      speculative_percentile: m.speculative_percentile ?? 50,
      extreme_flag: m.extreme_flag || null,
      divergence: m.divergence ?? false,
      insight: m.insight,
      bias: m.bias,
      weekly_change: m.weekly_change ?? null,
    })),
    alerts: (raw.alerts || []).map((a: any) => ({
      ticker: a.ticker,
      market_name: a.market_name,
      type: a.type || 'extreme_positioning',
      severity: a.severity || 'medium',
      message: a.message,
      bias: a.bias || 'neutral',
    })),
  };
}
