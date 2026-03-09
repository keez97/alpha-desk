import { create } from 'zustand';
import type { Portfolio, PortfolioAnalysis } from '../lib/api';

interface PortfolioStore {
  portfolios: Portfolio[];
  selectedPortfolioId: string | null;
  analysis: PortfolioAnalysis | null;
  loading: boolean;
  setPortfolios: (portfolios: Portfolio[]) => void;
  setSelectedPortfolioId: (id: string | null) => void;
  setAnalysis: (analysis: PortfolioAnalysis | null) => void;
  setLoading: (loading: boolean) => void;
  addPortfolio: (portfolio: Portfolio) => void;
  updatePortfolio: (id: string, portfolio: Portfolio) => void;
  removePortfolio: (id: string) => void;
}

export const usePortfolioStore = create<PortfolioStore>((set) => ({
  portfolios: [],
  selectedPortfolioId: null,
  analysis: null,
  loading: false,
  setPortfolios: (portfolios) => set({ portfolios }),
  setSelectedPortfolioId: (id) => set({ selectedPortfolioId: id }),
  setAnalysis: (analysis) => set({ analysis }),
  setLoading: (loading) => set({ loading }),
  addPortfolio: (portfolio) => set((state) => ({ portfolios: [...state.portfolios, portfolio] })),
  updatePortfolio: (id, portfolio) =>
    set((state) => ({
      portfolios: state.portfolios.map((p) => (p.id === id ? portfolio : p)),
    })),
  removePortfolio: (id) =>
    set((state) => ({
      portfolios: state.portfolios.filter((p) => p.id !== id),
    })),
}));
