import { useQuery } from '@tanstack/react-query';
import {
  fetchSectorTransitions,
  type FactorDecomposition,
  type Transition,
  type CycleOverlay,
  type SectorTransitionsData,
} from '../lib/api';

export type { FactorDecomposition, Transition, CycleOverlay, SectorTransitionsData };

export function useSectorTransitions() {
  return useQuery({
    queryKey: ['sectorTransitions'],
    queryFn: fetchSectorTransitions,
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}
