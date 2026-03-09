import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchPortfolios,
  createPortfolio,
  fetchPortfolio,
  updatePortfolio,
  deletePortfolio,
  analyzePortfolio,
} from '../lib/api';
import type { Portfolio } from '../lib/api';

export function usePortfolios() {
  return useQuery({
    queryKey: ['portfolios'],
    queryFn: fetchPortfolios,
    staleTime: 5 * 60 * 1000,
  });
}

export function usePortfolio(id: string | null) {
  return useQuery({
    queryKey: ['portfolio', id],
    queryFn: () => fetchPortfolio(id!),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreatePortfolio() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Parameters<typeof createPortfolio>[0]) => createPortfolio(data),
    onSuccess: (newPortfolio) => {
      queryClient.setQueryData(['portfolios'], (old: Portfolio[] | undefined) => {
        return old ? [...old, newPortfolio] : [newPortfolio];
      });
    },
  });
}

export function useUpdatePortfolio() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof updatePortfolio>[1] }) =>
      updatePortfolio(id, data),
    onSuccess: (updated) => {
      queryClient.setQueryData(['portfolio', updated.id], updated);
      queryClient.setQueryData(['portfolios'], (old: Portfolio[] | undefined) => {
        return old ? old.map((p) => (p.id === updated.id ? updated : p)) : [updated];
      });
    },
  });
}

export function useDeletePortfolio() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deletePortfolio,
    onSuccess: (_, id) => {
      queryClient.removeQueries({ queryKey: ['portfolio', id] });
      queryClient.setQueryData(['portfolios'], (old: Portfolio[] | undefined) => {
        return old ? old.filter((p) => p.id !== id) : [];
      });
    },
  });
}

export function useAnalyzePortfolio(id: string | null) {
  return useQuery({
    queryKey: ['portfolio', id, 'analysis'],
    queryFn: () => analyzePortfolio(id!),
    enabled: !!id,
  });
}
