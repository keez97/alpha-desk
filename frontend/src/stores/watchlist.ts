import { create } from 'zustand';
import type { WatchlistItem } from '../lib/api';

interface WatchlistStore {
  items: WatchlistItem[];
  loading: boolean;
  setItems: (items: WatchlistItem[]) => void;
  addItem: (item: WatchlistItem) => void;
  removeItem: (id: string) => void;
  setLoading: (loading: boolean) => void;
}

export const useWatchlist = create<WatchlistStore>((set) => ({
  items: [],
  loading: false,
  setItems: (items) => set({ items }),
  addItem: (item) => set((state) => ({ items: [item, ...state.items] })),
  removeItem: (id) => set((state) => ({ items: state.items.filter((item) => item.id !== id) })),
  setLoading: (loading) => set({ loading }),
}));
