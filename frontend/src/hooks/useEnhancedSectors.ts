import { useQuery } from '@tanstack/react-query';
import { fetchEnhancedSectors, type EnhancedSectorData as EnhancedSector } from '../lib/api';

export type { EnhancedSectorData as EnhancedSector } from '../lib/api';

export function useEnhancedSectors(period: string = '1D') {
  return useQuery({
    queryKey: ['enhanced-sectors', period],
    queryFn: () => fetchEnhancedSectors(period as any),
    staleTime: 5 * 60 * 1000,
    retry: 2,
    retryDelay: 1000,
  });
}
