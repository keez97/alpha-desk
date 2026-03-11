import { useQuery } from '@tanstack/react-query';
import { fetchBreadth } from '../lib/api';

export function useBreadth() {
  return useQuery({
    queryKey: ['breadth'],
    queryFn: fetchBreadth,
    staleTime: 10 * 60 * 1000,
    retry: 2,
    retryDelay: 2000,
  });
}
