import axios, { AxiosError } from 'axios';
import type { AxiosInstance } from 'axios';

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
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

export interface Grade {
  overall: string;
  metrics: { name: string; grade: string; value: number }[];
  summary: string;
  risks: string[];
  catalysts: string[];
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

// ── Stock Grade ────────────────────────────────────────────
function scoreToGrade(score: number | undefined): string {
  if (!score) return 'N/A';
  if (score >= 8) return 'STRONG BUY';
  if (score >= 6) return 'BUY';
  if (score >= 4) return 'HOLD';
  if (score >= 2) return 'SELL';
  return 'STRONG SELL';
}

export async function gradeStock(ticker: string): Promise<Grade> {
  const { data: raw } = await api.post(`/stock/${ticker}/grade`);
  const g = raw.grade || raw;
  return {
    overall: g.overall || g.overall_grade || g.grade || 'N/A',
    metrics: Array.isArray(g.metrics) && g.metrics.length > 0
      ? g.metrics.map((m: any) => ({
          name: m.name || m.metric,
          grade: m.grade,
          value: m.value ?? 0,
        }))
      : [
          { name: 'Valuation', grade: scoreToGrade(g.valuation_score), value: g.valuation_score ?? 0 },
          { name: 'Growth', grade: scoreToGrade(g.growth_score), value: g.growth_score ?? 0 },
          { name: 'Quality', grade: scoreToGrade(g.quality_score), value: g.quality_score ?? 0 },
          { name: 'Momentum', grade: scoreToGrade(g.momentum_score), value: g.momentum_score ?? 0 },
        ].filter((m) => m.value > 0),
    summary: g.summary || g.thesis || '',
    risks: g.risks || g.key_risks || [],
    catalysts: g.catalysts || [],
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
  // Backend uses ticker as the path param for delete
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
  // Build sections from the report JSON
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
export async function fetchRRG(benchmark: string = 'SPY', weeks: number = 52): Promise<RRGData> {
  const { data: raw } = await api.get('/rrg', { params: { benchmark, weeks } });
  const rrg = raw.data || raw;
  return {
    benchmark: rrg.benchmark || benchmark,
    weeks: rrg.weeks || weeks,
    sectors: (rrg.sectors || []).map((s: any) => ({
      ticker: s.ticker,
      name: s.sector || s.name || s.ticker,
      rsRatio: s.rs_ratio ?? s.rsRatio ?? 100,
      rsMomentum: s.rs_momentum ?? s.rsMomentum ?? 100,
      volume: s.volume ?? 0,
      quadrant: s.quadrant || 'Unknown',
      history: (s.trail || s.history || []).map((h: any) => ({
        date: h.date,
        rsRatio: h.rs_ratio ?? h.rsRatio ?? 100,
        rsMomentum: h.rs_momentum ?? h.rsMomentum ?? 100,
      })),
    })),
  };
}

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
