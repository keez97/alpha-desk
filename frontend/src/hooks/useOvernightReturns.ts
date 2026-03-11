import { useQuery } from '@tanstack/react-query';
import { fetchOvernightReturns } from '../lib/api';

export function useOvernightReturns() {
  return useQuery({
    queryKey: ['overnight-returns'],
    queryFn: () => fetchOvernightReturns(),
    staleTime: 30 * 60 * 1000,  // 30 minutes
    gcTime: 60 * 60 * 1000,     // 1 hour
  });
}
