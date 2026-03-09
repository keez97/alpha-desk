import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  createBacktest,
  runBacktest,
  getBacktestStatus,
  getBacktestResults,
  exportBacktest,
  listBacktests,
  deleteBacktest,
  getFactors,
  createFactor,
  CreateBacktestRequest,
  Backtest,
  BacktestStatus,
  BacktestResult,
  Factor,
} from '../lib/api';

export function useFactors() {
  return useQuery({
    queryKey: ['factors'],
    queryFn: getFactors,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

export function useCreateBacktest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateBacktestRequest) => createBacktest(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] });
    },
  });
}

export function useRunBacktest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => runBacktest(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['backtest', 'status', id] });
    },
  });
}

export function useBacktestStatus(id?: number | null, enabled: boolean = true) {
  return useQuery({
    queryKey: ['backtest', 'status', id],
    queryFn: () => (id ? getBacktestStatus(id) : Promise.resolve(null)),
    enabled: enabled && !!id,
    refetchInterval: 2000, // Poll every 2 seconds
    staleTime: 0, // Always refetch
  });
}

export function useBacktestResults(id?: number | null) {
  return useQuery({
    queryKey: ['backtest', 'results', id],
    queryFn: () => (id ? getBacktestResults(id) : Promise.resolve(null)),
    enabled: !!id,
    staleTime: 60 * 1000, // 1 minute
  });
}

export function useBacktestList() {
  return useQuery({
    queryKey: ['backtests'],
    queryFn: listBacktests,
    staleTime: 30 * 1000, // 30 seconds
  });
}

export function useDeleteBacktest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteBacktest(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] });
    },
  });
}

export function useExportBacktest(id?: number | null) {
  return useQuery({
    queryKey: ['backtest', 'export', id],
    queryFn: () => (id ? exportBacktest(id) : Promise.resolve(null)),
    enabled: !!id,
    staleTime: Infinity, // Don't auto-refetch
  });
}
