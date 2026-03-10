import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

// Type definitions (local, not from api.ts)
export interface IntradaySignal {
  ticker: string;
  sector: string;
  interval: string;
  momentum: number;
  volumeSurge: number;
  vwapDeviation: number;
  isBreakout: boolean;
  price: number;
  timestamp: string;
}

export interface IntradayMomentumResponse {
  signals: IntradaySignal[];
  timestamp: string;
  sectors_scanned: number;
  interval: string;
  benchmark?: string;
  error?: string;
}

export interface TickerDetailResponse {
  ticker: string;
  interval: string;
  price?: number;
  momentum?: number;
  volumeSurge?: number;
  vwap?: number;
  vwapDeviation?: number;
  candles?: Array<{
    timestamp: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
  timestamp?: string;
  error?: string;
}

// Create local axios instance
const api = axios.create({ baseURL: '/api' });

export function useIntradayMomentum(
  interval: string = '5m',
  benchmark: string = 'SPY',
  weeks: number = 10
) {
  return useQuery({
    queryKey: ['intraday-momentum', interval, benchmark, weeks],
    queryFn: async () => {
      const { data } = await api.get<IntradayMomentumResponse>(
        '/intraday-momentum/scan',
        {
          params: { interval, benchmark, weeks },
        }
      );
      return data;
    },
    staleTime: 1 * 60 * 1000, // 1 minute - intraday data refreshes frequently
    refetchInterval: 2 * 60 * 1000, // Refetch every 2 minutes during market hours
  });
}

export function useScanIntradayMomentum() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params?: {
      interval?: string;
      benchmark?: string;
      weeks?: number;
    }) => {
      const { data } = await api.get<IntradayMomentumResponse>(
        '/intraday-momentum/scan',
        {
          params: params || {},
        }
      );
      return data;
    },
    onSuccess: (_, variables) => {
      // Invalidate all intraday momentum queries or specific ones
      queryClient.invalidateQueries({
        queryKey: ['intraday-momentum'],
      });
    },
  });
}

export function useTickerIntradayDetail(
  ticker: string | null,
  interval: string = '5m'
) {
  return useQuery({
    queryKey: ['intraday-ticker-detail', ticker, interval],
    queryFn: async () => {
      if (!ticker) return null;
      const { data } = await api.get<TickerDetailResponse>(
        `/intraday-momentum/${ticker}`,
        {
          params: { interval },
        }
      );
      return data;
    },
    enabled: !!ticker,
    staleTime: 1 * 60 * 1000, // 1 minute
    refetchInterval: 2 * 60 * 1000, // Refetch every 2 minutes
  });
}

// Helper function to filter breakout signals
export function getBreakoutSignals(signals: IntradaySignal[] | undefined) {
  return (signals || []).filter((s) => s.isBreakout);
}

// Helper function to count signals by interval
export function countSignalsByInterval(signals: IntradaySignal[] | undefined) {
  const counts = { '5m': 0, '15m': 0 };
  (signals || []).forEach((s) => {
    if (s.interval === '5m') counts['5m']++;
    else if (s.interval === '15m') counts['15m']++;
  });
  return counts;
}
