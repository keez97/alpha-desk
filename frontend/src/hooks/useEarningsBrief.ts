import { useQuery } from '@tanstack/react-query';
import { fetchEarningsBrief } from '../lib/api';

export function useEarningsBrief() {
  return useQuery({
    queryKey: ['earnings-brief'],
    queryFn: () => fetchEarningsBrief(),
    staleTime: 30 * 60 * 1000,  // 30 minutes
    gcTime: 60 * 60 * 1000,     // 1 hour
  });
}
