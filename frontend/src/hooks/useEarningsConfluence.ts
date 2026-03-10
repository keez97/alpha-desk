import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';

export interface UpcomingEarning {
  ticker: string;
  name: string;
  date: string;
  daysUntil: number;
}

export interface EarningsCatalyst {
  sectorTicker: string;
  sectorName: string;
  upcomingEarnings: UpcomingEarning[];
  catalystCount: number;
  confluenceBoost: 'HIGH' | 'MEDIUM' | 'NONE';
  originalConviction: string;
  combinedConviction: string;
}

export interface SectorEarningsDetail {
  sectorTicker: string;
  sectorName: string;
  holdings: string[];
  upcomingEarnings: UpcomingEarning[];
  timestamp: string;
}

export interface EarningsConfluenceResponse {
  catalysts: EarningsCatalyst[];
  timestamp: string;
  error?: string;
}

export interface SectorEarningsResponse {
  sectorTicker: string;
  sectorName: string;
  holdings: string[];
  upcomingEarnings: UpcomingEarning[];
  timestamp: string;
  error?: string;
}

export function useEarningsConfluence() {
  return useQuery({
    queryKey: ['earnings-confluence'],
    queryFn: async () => {
      const response = await api.get('/earnings-confluence/');
      return response.data.data as EarningsConfluenceResponse;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  });
}

export function useSectorEarnings(sectorTicker: string | null) {
  return useQuery({
    queryKey: ['sector-earnings', sectorTicker],
    queryFn: async () => {
      if (!sectorTicker) return null;
      const response = await api.get(`/earnings-confluence/${sectorTicker}`);
      return response.data.data as SectorEarningsResponse;
    },
    enabled: !!sectorTicker,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
