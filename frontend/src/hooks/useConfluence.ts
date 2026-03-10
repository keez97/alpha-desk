import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';

export interface SignalSource {
  source: string;
  detail: string;
  sentiment: 'bullish' | 'bearish' | 'neutral';
}

export interface ConfluentSignal {
  thesis: string;
  direction: 'bullish' | 'bearish' | 'neutral';
  conviction: 'HIGH' | 'MEDIUM' | 'LOW';
  sector: string;
  sectorTicker: string;
  signals: SignalSource[];
  suggestedAction: string;
  timeframe: string;
}

export interface SignalMatrixRow {
  ticker: string;
  name: string;
  rrg: { quadrant: string; momentum: number };
  macro: { regime: string; sectorImpact: string };
  performance: { change1d: number; change1m: number };
  confluence: 'bullish' | 'bearish' | 'neutral';
  signalCount: number;
}

export interface ConfluenceResponse {
  signals: ConfluentSignal[];
  macro_regime: {
    regime: string;
    risk_on?: boolean;
    risk_off?: boolean;
    vix_signal?: string;
    yield_rising?: boolean;
    dollar_weakening?: boolean;
  };
}

export interface MatrixResponse {
  matrix: SignalMatrixRow[];
  macro_regime: {
    regime: string;
    risk_on?: boolean;
    risk_off?: boolean;
    vix_signal?: string;
    yield_rising?: boolean;
    dollar_weakening?: boolean;
  };
}

export function useConfluence() {
  return useQuery({
    queryKey: ['confluence'],
    queryFn: async () => {
      const response = await api.get('/confluence/signals');
      return response.data.data as ConfluenceResponse;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useSignalMatrix() {
  return useQuery({
    queryKey: ['confluence', 'matrix'],
    queryFn: async () => {
      const response = await api.get('/confluence/matrix');
      return response.data.data as MatrixResponse;
    },
    staleTime: 5 * 60 * 1000,
  });
}
