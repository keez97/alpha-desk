import { create } from 'zustand';

interface UIStore {
  activePage:
    | 'morning-brief'
    | 'screener'
    | 'weekly-report'
    | 'portfolio'
    | 'rrg';
  sidebarOpen: boolean;
  setActivePage: (page: UIStore['activePage']) => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  activePage: 'morning-brief',
  sidebarOpen: true,
  setActivePage: (page) => set({ activePage: page }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
}));
