import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getEarningsCalendar,
  getEarningsHistory,
  getEarningsSignal,
  getEarningsPEAD,
  refreshEarnings,
  getScreenerEarningsSignals,
  type EarningsCalendarResponse,
  type EarningsHistoryResponse,
  type EarningsSignal,
  type EarningsPEADResponse,
  type ScreenerEarningsSignalsResponse,
} from '../lib/api';

export interface EarningsCalendarParams {
  page?: number;
  page_size?: number;
  sort_by?: 'days_to_earnings' | 'divergence_pct' | 'ticker' | 'earnings_date';
  sort_order?: 'asc' | 'desc';
  daysAhead?: number;
}

export function useEarningsCalendar(params?: EarningsCalendarParams) {
  return useQuery({
    queryKey: ['earnings-calendar', params],
    queryFn: () => getEarningsCalendar(params),
    staleTime: 60000,
    refetchInterval: 300000, // 5 minutes
  });
}

export function useEarningsHistory(ticker: string | null) {
  return useQuery({
    queryKey: ['earnings-history', ticker],
    queryFn: () => (ticker ? getEarningsHistory(ticker) : null),
    enabled: !!ticker,
    staleTime: 120000,
  });
}

export function useEarningsSignal(ticker: string | null) {
  return useQuery({
    queryKey: ['earnings-signal', ticker],
    queryFn: () => (ticker ? getEarningsSignal(ticker) : null),
    enabled: !!ticker,
    staleTime: 120000,
  });
}

export function useEarningsPEAD(ticker: string | null) {
  return useQuery({
    queryKey: ['earnings-pead', ticker],
    queryFn: () => (ticker ? getEarningsPEAD(ticker) : null),
    enabled: !!ticker,
    staleTime: 120000,
  });
}

export function useRefreshEarnings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => refreshEarnings(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['earnings-calendar'] });
      queryClient.invalidateQueries({ queryKey: ['earnings-signal'] });
      queryClient.invalidateQueries({ queryKey: ['earnings-history'] });
      queryClient.invalidateQueries({ queryKey: ['earnings-pead'] });
    },
  });
}

export function useScreenerEarningsSignals(tickers: string[]) {
  return useQuery({
    queryKey: ['screener-earnings-signals', tickers],
    queryFn: () => (tickers.length > 0 ? getScreenerEarningsSignals(tickers) : Promise.resolve({ signals: [] })),
    enabled: tickers.length > 0,
    staleTime: 120000,
  });
}
