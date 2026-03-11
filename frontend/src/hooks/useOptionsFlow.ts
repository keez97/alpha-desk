import { useQuery } from '@tanstack/react-query';
import { fetchOptionsFlow, type OptionsFlowData } from '../lib/api';

export type { OptionsFlowData };

export function useOptionsFlow() {
  return useQuery({
    queryKey: ['optionsFlow'],
    queryFn: fetchOptionsFlow,
    staleTime: 10 * 60 * 1000, // 10 minutes
    retry: 2,
    retryDelay: 2000,
  });
}
