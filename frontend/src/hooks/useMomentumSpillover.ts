import { useQuery } from '@tanstack/react-query';
import {
  fetchMomentumSpillover,
  type AssetMomentum,
  type MomentumSignal,
  type MomentumMatrix,
  type MomentumSpilloverData,
} from '../lib/api';

export type { AssetMomentum, MomentumSignal, MomentumMatrix, MomentumSpilloverData };

export function useMomentumSpillover() {
  return useQuery({
    queryKey: ['momentumSpillover'],
    queryFn: fetchMomentumSpillover,
    staleTime: 15 * 60 * 1000, // 15 minutes
    retry: 2,
    retryDelay: 2000,
  });
}
