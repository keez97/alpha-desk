import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { runScreener, fetchLatestScreener } from '../lib/api';

export function useLatestScreener() {
  return useQuery({
    queryKey: ['screener', 'latest'],
    queryFn: fetchLatestScreener,
    staleTime: 5 * 60 * 1000,
  });
}

export function useRunScreener() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: runScreener,
    onSuccess: (data) => {
      queryClient.setQueryData(['screener', 'latest'], data);
    },
  });
}
