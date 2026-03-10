import { useQuery } from '@tanstack/react-query';
import { fetchStockFactors, type StockFactorData as StockFactor } from '../lib/api';

export type { StockFactorData as StockFactor } from '../lib/api';

export function useStockFactors(ticker: string | null) {
  return useQuery({
    queryKey: ['stock-factors', ticker],
    queryFn: () => fetchStockFactors(ticker!),
    enabled: !!ticker,
    staleTime: 10 * 60 * 1000,
  });
}
