import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchWatchlist, addToWatchlist, removeFromWatchlist } from '../lib/api';
import type { WatchlistItem } from '../lib/api';

export function useWatchlistQuery() {
  return useQuery({
    queryKey: ['watchlist'],
    queryFn: fetchWatchlist,
    staleTime: 5 * 60 * 1000,
  });
}

export function useAddToWatchlist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: addToWatchlist,
    onSuccess: (newItem) => {
      queryClient.setQueryData(['watchlist'], (old: WatchlistItem[] | undefined) => {
        return old ? [newItem, ...old] : [newItem];
      });
    },
  });
}

export function useRemoveFromWatchlist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: removeFromWatchlist,
    onSuccess: (_, id) => {
      queryClient.setQueryData(['watchlist'], (old: WatchlistItem[] | undefined) => {
        return old ? old.filter((item) => item.id !== id) : [];
      });
    },
  });
}
