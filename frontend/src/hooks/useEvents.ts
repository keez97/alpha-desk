import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listEvents,
  getEvent,
  getAlphaDecay,
  getEventTimeline,
  getPollingStatus,
  triggerScan,
  getScreenerBadges,
  deleteEvent,
  type EventItem,
  type EventDetail,
  type AlphaDecayWindow,
  type PollingStatus,
  type EventsListResponse,
} from '../lib/api';

export interface EventFilters {
  ticker?: string;
  event_type?: string;
  severity_min?: number;
  severity_max?: number;
  date_start?: string;
  date_end?: string;
  page?: number;
  page_size?: number;
}

export function useEvents(filters?: EventFilters) {
  return useQuery({
    queryKey: ['events', filters],
    queryFn: () => listEvents(filters),
    staleTime: 60000,
  });
}

export function useEventDetail(id: number | null) {
  return useQuery({
    queryKey: ['event', id],
    queryFn: () => (id ? getEvent(id) : null),
    enabled: !!id,
    staleTime: 120000,
  });
}

export function useAlphaDecay(id: number | null) {
  return useQuery({
    queryKey: ['alphaDecay', id],
    queryFn: () => (id ? getAlphaDecay(id) : null),
    enabled: !!id,
    staleTime: 120000,
  });
}

export function useEventTimeline(filters?: EventFilters) {
  return useQuery({
    queryKey: ['eventTimeline', filters],
    queryFn: () => getEventTimeline(filters),
    refetchInterval: 60000,
    staleTime: 30000,
  });
}

export function usePollingStatus() {
  return useQuery({
    queryKey: ['pollingStatus'],
    queryFn: () => getPollingStatus(),
    refetchInterval: 30000,
    staleTime: 15000,
  });
}

export function useTriggerScan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => triggerScan(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['eventTimeline'] });
      queryClient.invalidateQueries({ queryKey: ['pollingStatus'] });
    },
  });
}

export function useScreenerBadges(tickers: string[]) {
  return useQuery({
    queryKey: ['screenerBadges', tickers],
    queryFn: () => (tickers.length > 0 ? getScreenerBadges(tickers) : Promise.resolve({})),
    enabled: tickers.length > 0,
    staleTime: 120000,
  });
}

export function useDeleteEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteEvent(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['eventTimeline'] });
    },
  });
}
