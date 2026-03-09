import axios, { AxiosError } from 'axios';
import type { AxiosInstance } from 'axios';

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response: any) => response,
  (error: AxiosError) => {
    console.error('API Error:', error.message);
    return Promise.reject(error);
  }
);

// Types
export interface MacroData {
  timestamp: string;
  indicators: {
    name: string;
    value: number;
    change: number;
  }[];
}

export interface SectorData {
  ticker: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
}

export interface Driver {
  headline: string;
  explanation: string;
  sources: string[];
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
  metrics: {
    name: string;
    grade: string;
    value: number;
  }[];
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
  holdings: {
    ticker: string;
    shares: number;
    weight?: number;
  }[];
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
    stats: {
      mean: number;
      median: number;
      std: number;
    };
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
    history: {
      date: string;
      rsRatio: number;
      rsMomentum: number;
    }[];
  }[];
}

// Macro APIs
export async function fetchMacro(): Promise<MacroData> {
  const response = await api.get<MacroData>('/morning-brief/macro');
  return response.data;
}

// Sector APIs
export async function fetchSectors(period: '1D' | '5D' | '1M' | '3M' = '1D'): Promise<SectorData[]> {
  const response = await api.get<SectorData[]>('/morning-brief/sectors', {
    params: { period },
  });
  return response.data;
}

// Driver APIs
export async function fetchDrivers(): Promise<DriverResponse> {
  const response = await api.get<DriverResponse>('/morning-brief/drivers');
  return response.data;
}

export async function refreshDrivers(): Promise<DriverResponse> {
  const response = await api.post<DriverResponse>('/morning-brief/drivers/refresh');
  return response.data;
}

// Stock Quote APIs
export async function searchTicker(query: string): Promise<{ ticker: string; name: string; sector: string }[]> {
  const response = await api.get('/stock/search', {
    params: { q: query },
  });
  return response.data;
}

export async function fetchQuote(ticker: string): Promise<Quote> {
  const response = await api.get<Quote>(`/stock/${ticker}/quote`);
  return response.data;
}

// Stock Grade APIs
export async function gradeStock(ticker: string): Promise<Grade> {
  const response = await api.post<Grade>(`/stock/${ticker}/grade`);
  return response.data;
}

// Watchlist APIs
export async function fetchWatchlist(): Promise<WatchlistItem[]> {
  const response = await api.get<WatchlistItem[]>('/watchlist');
  return response.data;
}

export async function addToWatchlist(ticker: string): Promise<WatchlistItem> {
  const response = await api.post<WatchlistItem>('/watchlist', { ticker });
  return response.data;
}

export async function removeFromWatchlist(id: string): Promise<void> {
  await api.delete(`/watchlist/${id}`);
}

// Screener APIs
export async function runScreener(): Promise<ScreenerResponse> {
  const response = await api.post<ScreenerResponse>('/screener/run');
  return response.data;
}

export async function fetchLatestScreener(): Promise<ScreenerResponse> {
  const response = await api.get<ScreenerResponse>('/screener/latest');
  return response.data;
}

// Weekly Report APIs
export function generateWeeklyReportSSE(): string {
  return '/api/weekly-report/generate';
}

export async function fetchReportList(): Promise<{ id: string; date: string; title: string }[]> {
  const response = await api.get('/weekly-report/list');
  return response.data;
}

export async function fetchReport(id: string): Promise<Report> {
  const response = await api.get<Report>(`/weekly-report/${id}`);
  return response.data;
}

export async function deleteReport(id: string): Promise<void> {
  await api.delete(`/weekly-report/${id}`);
}

// Portfolio APIs
export async function fetchPortfolios(): Promise<Portfolio[]> {
  const response = await api.get<Portfolio[]>('/portfolio');
  return response.data;
}

export async function createPortfolio(data: {
  name: string;
  capital: number;
  holdings: { ticker: string; shares: number }[];
}): Promise<Portfolio> {
  const response = await api.post<Portfolio>('/portfolio', data);
  return response.data;
}

export async function fetchPortfolio(id: string): Promise<Portfolio> {
  const response = await api.get<Portfolio>(`/portfolio/${id}`);
  return response.data;
}

export async function updatePortfolio(
  id: string,
  data: Partial<{ name: string; capital: number; holdings: { ticker: string; shares: number }[] }>
): Promise<Portfolio> {
  const response = await api.put<Portfolio>(`/portfolio/${id}`, data);
  return response.data;
}

export async function deletePortfolio(id: string): Promise<void> {
  await api.delete(`/portfolio/${id}`);
}

export async function analyzePortfolio(id: string): Promise<PortfolioAnalysis> {
  const response = await api.get<PortfolioAnalysis>(`/portfolio/${id}/analysis`);
  return response.data;
}

// RRG APIs
export async function fetchRRG(benchmark: string = 'SPY', weeks: number = 52): Promise<RRGData> {
  const response = await api.get<RRGData>('/rrg', {
    params: { benchmark, weeks },
  });
  return response.data;
}

export default api;
