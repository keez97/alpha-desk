import { useQuery } from '@tanstack/react-query';
import { fetchQuote } from '../lib/api';

export function useStockQuote(ticker: string | null) {
  return useQuery({
    queryKey: ['quote', ticker],
    queryFn: () => fetchQuote(ticker!),
    enabled: !!ticker,
    staleTime: 60 * 1000, // 1 minute
  });
}
