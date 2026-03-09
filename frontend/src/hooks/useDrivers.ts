import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchDrivers, refreshDrivers } from '../lib/api';

export function useDrivers() {
  return useQuery({
    queryKey: ['drivers'],
    queryFn: fetchDrivers,
    staleTime: 10 * 60 * 1000,
  });
}

export function useRefreshDrivers() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: refreshDrivers,
    onSuccess: (data) => {
      queryClient.setQueryData(['drivers'], data);
    },
  });
}
