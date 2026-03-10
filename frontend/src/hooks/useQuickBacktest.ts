import { useQuery, useMutation } from '@tanstack/react-query';
import api from '../lib/api';

export interface TradeIdea {
  ticker: string;
  sectorName: string;
  quadrant: string;
  direction: 'long' | 'short' | 'avoid';
  thesis: string;
  suggestedPairTicker?: string;
  confidence: 'high' | 'medium' | 'low';
  rsRatio: number;
  rsMomentum: number;
  backtestConfig: {
    name: string;
    start_date: string;
    end_date: string;
    rebalance_frequency: string;
    transaction_costs: { commission_bps: number; slippage_bps: number };
    universe_selection: string;
    factor_allocations: Record<string, number>;
    ticker: string;
    short_ticker?: string;
    trade_type: string;
    direction: string;
    quadrant: string;
    confidence: string;
  };
}

interface QuickBacktestRequest {
  ticker: string;
  trade_type?: 'single' | 'pair';
  short_ticker?: string;
  benchmark?: string;
  weeks?: number;
}

export function useTradeIdeas(
  benchmark: string = 'SPY',
  weeks: number = 10,
  enabled: boolean = true
) {
  return useQuery({
    queryKey: ['trade-ideas', benchmark, weeks],
    queryFn: () =>
      api.get('/quick-backtest/trade-ideas', {
        params: { benchmark, weeks }
      }).then(r => r.data as TradeIdea[]),
    enabled,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
}

export function useQuickBacktest(
  ticker: string,
  enabled: boolean = true
) {
  return useQuery({
    queryKey: ['quick-backtest', ticker],
    queryFn: () =>
      api.post('/quick-backtest/from-rrg', { ticker }).then(r => r.data),
    enabled: enabled && !!ticker,
    staleTime: 2 * 60 * 1000, // Cache for 2 minutes
  });
}

export function useCreateQuickBacktest() {
  return useMutation({
    mutationFn: (request: QuickBacktestRequest) =>
      api.post('/quick-backtest/from-rrg', request).then(r => r.data),
  });
}
