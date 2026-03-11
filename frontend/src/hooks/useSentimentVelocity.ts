import { useQuery } from '@tanstack/react-query';
import {
  fetchSentimentVelocity,
  type Headline,
  type HistoryPoint,
  type SentimentVelocityData,
} from '../lib/api';

export type { Headline, HistoryPoint, SentimentVelocityData };

export function useSentimentVelocity(tickers?: string) {
  return useQuery({
    queryKey: ['sentiment-velocity', tickers],
    queryFn: () => fetchSentimentVelocity(tickers),
    staleTime: 15 * 60 * 1000, // 15 minutes
    retry: 2,
    retryDelay: 2000,
  });
}
