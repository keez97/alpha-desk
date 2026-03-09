import { useQuery } from '@tanstack/react-query';
import { fetchRRG } from '../lib/api';

export function useRRG(benchmark: string = 'SPY', weeks: number = 52) {
  return useQuery({
    queryKey: ['rrg', benchmark, weeks],
    queryFn: () => fetchRRG(benchmark, weeks),
    staleTime: 10 * 60 * 1000,
  });
}
