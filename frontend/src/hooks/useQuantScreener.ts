import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { runQuantScreen, getScreenPresets } from '../lib/api';
import type { QuantFilter } from '../lib/api';

export function useQuantScreen(filters: QuantFilter) {
  return useQuery({
    queryKey: ['quant-screen', filters],
    queryFn: () => runQuantScreen(filters),
    staleTime: 5 * 60 * 1000,
  });
}

export function useScreenPresets() {
  return useQuery({
    queryKey: ['screen-presets'],
    queryFn: getScreenPresets,
    staleTime: 30 * 60 * 1000,
  });
}

export function useRunQuantScreen() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (filters: QuantFilter) => runQuantScreen(filters),
    onSuccess: (data, filters) => {
      queryClient.setQueryData(['quant-screen', filters], data);
    },
  });
}
