import { useQuery, useMutation } from '@tanstack/react-query';
import api from '../lib/api';

export interface ConvictionStats {
  conviction: string;
  direction: string;
  totalSignals: number;
  winRate1D: number;
  winRate3D: number;
  winRate5D: number;
  winRate10D: number;
  avgReturn1D: number;
  avgReturn3D: number;
  avgReturn5D: number;
  avgReturn10D: number;
  maxDrawdown: number;
}

export interface DirectionStats {
  direction: string;
  totalSignals: number;
  winRate: number;
  avgReturn: number;
}

export interface EquityCurvePoint {
  date: string;
  cumReturn: number;
}

export interface ConfluenceBacktestResult {
  summary: {
    convictionStats: ConvictionStats[];
    directionStats: DirectionStats[];
  };
  equityCurve: EquityCurvePoint[];
  signalsAnalyzed: number;
  period: string;
  timestamp: string;
  error?: string;
}

export interface ConfluenceBacktestSummary {
  summary: {
    convictionStats: ConvictionStats[];
    directionStats: DirectionStats[];
  };
  signalsAnalyzed: number;
  period: string;
  timestamp: string;
  error?: string;
}

/**
 * Hook to run confluence backtest with full equity curve.
 */
export function useConfluenceBacktest(
  lookbackMonths: number = 12,
  enabled: boolean = false
) {
  return useQuery<ConfluenceBacktestResult>({
    queryKey: ['confluence-backtest', lookbackMonths],
    queryFn: () =>
      api
        .get(`/confluence-backtest/run`, {
          params: { lookback_months: lookbackMonths },
        })
        .then((r) => r.data),
    enabled,
    staleTime: 10 * 60 * 1000, // Cache for 10 minutes
    retry: false,
  });
}

/**
 * Hook to get just the summary statistics (faster, no equity curve).
 */
export function useConfluenceBacktestSummary(
  lookbackMonths: number = 12,
  enabled: boolean = false
) {
  return useQuery<ConfluenceBacktestSummary>({
    queryKey: ['confluence-backtest-summary', lookbackMonths],
    queryFn: () =>
      api
        .get(`/confluence-backtest/summary`, {
          params: { lookback_months: lookbackMonths },
        })
        .then((r) => r.data),
    enabled,
    staleTime: 10 * 60 * 1000, // Cache for 10 minutes
    retry: false,
  });
}

/**
 * Mutation to trigger a backtest run.
 */
export function useRunConfluenceBacktest() {
  return useMutation({
    mutationFn: (lookbackMonths: number) =>
      api
        .get(`/confluence-backtest/run`, {
          params: { lookback_months: lookbackMonths },
        })
        .then((r) => r.data as ConfluenceBacktestResult),
  });
}
