import { useQuery } from '@tanstack/react-query';
import { fetchSectors } from '../lib/api';

export function useSectors(period: '1D' | '5D' | '1M' | '3M' = '1D') {
  return useQuery({
    queryKey: ['sectors', period],
    queryFn: () => fetchSectors(period),
    staleTime: 5 * 60 * 1000,
  });
}
