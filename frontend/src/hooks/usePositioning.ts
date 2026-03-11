import { useQuery } from '@tanstack/react-query';
import {
  fetchPositioning,
  type MarketPositioning,
  type PositioningAlert,
  type PositioningData,
} from '../lib/api';

export type { MarketPositioning, PositioningAlert, PositioningData };

export function usePositioning() {
  return useQuery({
    queryKey: ['cot-positioning'],
    queryFn: fetchPositioning,
    staleTime: 60 * 60 * 1000, // 1 hour (COT reports refresh weekly)
    retry: 2,
    retryDelay: 2000,
  });
}
