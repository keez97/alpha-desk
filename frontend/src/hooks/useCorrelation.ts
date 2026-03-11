import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import type { AxiosError } from 'axios';

// ────── Types ──────────────────────────────────────────────────

export interface PairsTrade {
  ticker1: string;
  ticker2: string;
  sector1: string;
  sector2: string;
  correlation: number;
  quadrant1: string;
  quadrant2: string;
  trade_type: string;
  conviction: number;
}

export interface HedgingPair {
  ticker1: string;
  ticker2: string;
  sector1: string;
  sector2: string;
  correlation: number;
  hedge_type: string;
}

export interface CorrelationData {
  timestamp: string;
  lookback_days: number;
  matrix: number[][];
  tickers: string[];
  sectors: string[];
  pairs_trades: PairsTrade[];
  hedging_pairs: HedgingPair[];
  error?: string;
}

export interface PairDetails {
  timestamp: string;
  lookback_days: number;
  ticker1: string;
  ticker2: string;
  current_spread: number;
  spread_mean: number;
  spread_std: number;
  z_score: number;
  rolling_correlation_20d: number;
  overall_correlation: number;
  spread_history: number[];
  error?: string;
}

// ────── Hooks ──────────────────────────────────────────────────

/**
 * Fetch correlation matrix for all sector ETFs
 */
export function useCorrelationMatrix(lookback: number = 90) {
  return useQuery<CorrelationData, AxiosError>({
    queryKey: ['correlationMatrix', lookback],
    queryFn: async () => {
      const { data } = await axios.get<CorrelationData>(
        `/api/correlation/matrix?lookback=${lookback}`,
        { timeout: 15000 } // 15 second timeout
      );
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
    retryDelay: 5000, // 5 second delay between retries
  });
}

/**
 * Fetch identified pairs trade opportunities
 */
export function usePairsTrades(lookback: number = 90) {
  return useQuery<
    { timestamp: string; lookback_days: number; pairs_trades: PairsTrade[] },
    AxiosError
  >({
    queryKey: ['pairsTrades', lookback],
    queryFn: async () => {
      const { data } = await axios.get(
        `/api/correlation/pairs?lookback=${lookback}`,
        { timeout: 15000 } // 15 second timeout
      );
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
    retryDelay: 5000, // 5 second delay between retries
  });
}

/**
 * Fetch detailed pair analysis
 */
export function usePairDetails(
  ticker1: string,
  ticker2: string,
  lookback: number = 90
) {
  return useQuery<PairDetails, AxiosError>({
    queryKey: ['pairDetails', ticker1, ticker2, lookback],
    queryFn: async () => {
      const { data } = await axios.get<PairDetails>(
        `/api/correlation/pair/${ticker1}/${ticker2}?lookback=${lookback}`,
        { timeout: 15000 } // 15 second timeout
      );
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
    retryDelay: 5000, // 5 second delay between retries
  });
}
