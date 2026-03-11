import { useQuery } from '@tanstack/react-query';
import { fetchUpgradedRegime } from '../lib/api';

export function useUpgradedRegime() {
  return useQuery({
    queryKey: ['regime'],
    queryFn: fetchUpgradedRegime,
    staleTime: 5 * 60 * 1000,
    retry: 2,
    retryDelay: 2000,
  });
}
