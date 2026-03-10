import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getSentiment,
  getSentimentHistory,
  getSentimentAlerts,
  getSentimentMovers,
  getSentimentNews,
  getSentimentHeatmap,
  refreshSentiment,
  type SentimentData,
  type SentimentHistoryPoint,
  type SentimentAlert,
  type SentimentMover,
  type NewsArticle,
  type SentimentHeatmapSector,
} from '../lib/api';

export function useSentiment(ticker: string | null) {
  return useQuery({
    queryKey: ['sentiment', ticker],
    queryFn: () => (ticker ? getSentiment(ticker) : null),
    enabled: !!ticker,
    staleTime: 30000,
  });
}

export function useSentimentHistory(ticker: string | null, days: number = 30) {
  return useQuery({
    queryKey: ['sentiment-history', ticker, days],
    queryFn: () => (ticker ? getSentimentHistory(ticker, days) : null),
    enabled: !!ticker,
    staleTime: 60000,
  });
}

export function useSentimentAlerts() {
  return useQuery({
    queryKey: ['sentiment-alerts'],
    queryFn: () => getSentimentAlerts(),
    staleTime: 30000,
    refetchInterval: 60000,
  });
}

export function useSentimentMovers(limit: number = 20) {
  return useQuery({
    queryKey: ['sentiment-movers', limit],
    queryFn: () => getSentimentMovers(limit),
    staleTime: 30000,
    refetchInterval: 60000,
  });
}

export function useSentimentNews(ticker: string | null, limit: number = 20) {
  return useQuery({
    queryKey: ['sentiment-news', ticker, limit],
    queryFn: () => (ticker ? getSentimentNews(ticker, limit) : null),
    enabled: !!ticker,
    staleTime: 60000,
  });
}

export function useSentimentHeatmap() {
  return useQuery({
    queryKey: ['sentiment-heatmap'],
    queryFn: () => getSentimentHeatmap(),
    staleTime: 60000,
    refetchInterval: 120000,
  });
}

export function useRefreshSentiment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => refreshSentiment(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sentiment'] });
      queryClient.invalidateQueries({ queryKey: ['sentiment-history'] });
      queryClient.invalidateQueries({ queryKey: ['sentiment-alerts'] });
      queryClient.invalidateQueries({ queryKey: ['sentiment-movers'] });
      queryClient.invalidateQueries({ queryKey: ['sentiment-news'] });
      queryClient.invalidateQueries({ queryKey: ['sentiment-heatmap'] });
    },
  });
}
