import { useQuery } from '@tanstack/react-query';
import { fetchVixTermStructure } from '../lib/api';

export function useVixTermStructure() {
  return useQuery({
    queryKey: ['vix-term-structure'],
    queryFn: fetchVixTermStructure,
    staleTime: 5 * 60 * 1000,
    retry: 2,
    retryDelay: 2000,
  });
}
