import axios, { AxiosError } from 'axios';
import type { AxiosInstance } from 'axios';

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 60000, // Increased for LLM calls
});

api.interceptors.response.use(
  (response: any) => response,
  (error: AxiosError) => {
    console.error('API Error:', error.message);
    return Promise.reject(error);
  }
);

// ── Types ──────────────────────────────────────────────────
export interface MacroData {
  timestamp: string;
  indicators: { name: string; value: number; change: number }[];
}

export interface SectorData {
  ticker: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  chartData?: number[];
}

export interface Driver {
  headline: string;
  explanation: string;
  sources: string[];
  sentiment?: string;
  impactScore?: number;
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
};

export async function fetchMacro(): Promise<MacroData> {
  const { data: raw } = await api.get('/morning-brief/macro');
  const indicators = Object.entries(raw.data || {}).map(([ticker, info]: [string, any]) => ({
    name: MACRO_NAMES[ticker] || ticker,
    value: info.price ?? 0,
    change: info.pct_change ?? 0,
  }));
  return { timestamp: raw.timestamp, indicators };
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
  }));
}

// ── Drivers ────────────────────────────────────────────────
export async function fetchDrivers(): Promise<DriverResponse> {
  const { data: raw } = await api.get('/morning-brief/drivers');
  const driversData = raw.data || raw;
  const drivers = Array.isArray(driversData) ? driversData : (driversData.drivers || []);
  return {
    drivers: drivers.map((d: any) => ({
      headline: d.headline || d.title || 'Untitled',
      explanation: d.explanation || '',
      sources: d.sources || (d.url ? [d.url] : []),
      sentiment: d.sentiment,
      impactScore: d.impact_score,
      sourceName: d.source,
    })),
    timestamp: raw.timestamp,
  };
}

export async function refreshDrivers(): Promise<DriverResponse> {
  const { data: raw } = await api.post('/morning-brief/drivers/refresh');
  const driversData = raw.data || raw;
  const drivers = Array.isArray(driversData) ? driversData : (driversData.drivers || []);
  return {
    drivers: drivers.map((d: any) => ({
      headline: d.headline || d.title || 'Untitled',
      explanation: d.explanation || '',
      sources: d.sources || (d.url ? [d.url] : []),
      sentiment: d.sentiment,
      impactScore: d.impact_score,
    })),
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
  api.get('/backtests').then((r) => r.data);

export const deleteBacktest = (id: number) =>
  api.delete(`/backtests/${id}`).then((r) => r.data);

export const getFactors = () =>
  api.get('/factors').then((r) => r.data);

export const createFactor = (data: any) =>
  api.post('/factors', data).then((r) => r.data);

export const getFactorScores = (id: number) =>
  api.get(`/factors/${id}/scores`).then((r) => r.data);

export default api;

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
