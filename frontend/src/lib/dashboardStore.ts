/**
 * Dashboard layout store — Zustand + localStorage persistence.
 * Manages which widgets are visible, their grid positions, and layout lock state.
 */
import { create } from 'zustand';
import { WIDGET_REGISTRY } from './widgetRegistry';

/** Single layout item — matches react-grid-layout's Layout interface */
export interface LayoutItem {
  i: string;
  x: number;
  y: number;
  w: number;
  h: number;
  minW?: number;
  minH?: number;
  maxW?: number;
  maxH?: number;
  static?: boolean;
  isDraggable?: boolean;
  isResizable?: boolean;
}

const STORAGE_KEY = 'alphadesk_dashboard_layout';
const VISIBLE_KEY = 'alphadesk_dashboard_visible';
const LOCK_KEY = 'alphadesk_dashboard_locked';
const VERSION_KEY = 'alphadesk_dashboard_version';
const LAYOUT_VERSION = 2; // Bump when default layout changes to reset stale caches

// ── Default layout matching current MorningBrief.tsx ──────────
// 12-column grid. Y values stack vertically. Each "row unit" ≈ 30px.
export const DEFAULT_VISIBLE = [
  'regime-card',
  'market-report',
  'sector-chart',
  'sector-transitions',
  'drivers',
  'momentum-spillover',
  'positioning',
  'scenario-risk',
  'sentiment',
  'options-flow',
  'earnings',
];

export const DEFAULT_LAYOUT: LayoutItem[] = [
  // Layer 1: Signal — full width regime card (compact)
  { i: 'regime-card', x: 0, y: 0, w: 12, h: 6, minW: 3, minH: 3 },
  // Layer 2: Market Report — full width (compact)
  { i: 'market-report', x: 0, y: 6, w: 12, h: 4, minW: 3, minH: 2 },
  // Layer 3: Context grid — sectors (8) | drivers (4)
  { i: 'sector-chart', x: 0, y: 10, w: 8, h: 5, minW: 3, minH: 3 },
  { i: 'drivers', x: 8, y: 10, w: 4, h: 5, minW: 3, minH: 3 },
  // Layer 4: Transitions (8) | momentum (4)
  { i: 'sector-transitions', x: 0, y: 15, w: 8, h: 4, minW: 3, minH: 3 },
  { i: 'momentum-spillover', x: 8, y: 15, w: 4, h: 4, minW: 3, minH: 3 },
  // Layer 5: Positioning + Scenarios — side by side
  { i: 'positioning', x: 0, y: 19, w: 6, h: 6, minW: 3, minH: 3 },
  { i: 'scenario-risk', x: 6, y: 19, w: 6, h: 6, minW: 3, minH: 3 },
  // Layer 6: Sentiment row — 3 across
  { i: 'sentiment', x: 0, y: 25, w: 4, h: 5, minW: 2, minH: 3 },
  { i: 'options-flow', x: 4, y: 25, w: 4, h: 5, minW: 2, minH: 3 },
  { i: 'earnings', x: 8, y: 25, w: 4, h: 5, minW: 2, minH: 3 },
];

// ── Store ─────────────────────────────────────────────────────
interface DashboardState {
  layout: LayoutItem[];
  visibleWidgets: string[];
  isLocked: boolean;
  // Actions
  setLayout: (layout: LayoutItem[]) => void;
  addWidget: (widgetId: string) => void;
  removeWidget: (widgetId: string) => void;
  toggleLock: () => void;
  resetToDefault: () => void;
}

function loadFromStorage<T>(key: string, fallback: T): T {
  try {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : fallback;
  } catch {
    return fallback;
  }
}

function saveToStorage(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage full or unavailable — silently fail
  }
}

// Check if stored layout is stale (older version) and reset if so
function getInitialLayout(): LayoutItem[] {
  const storedVersion = loadFromStorage<number>(VERSION_KEY, 0);
  if (storedVersion < LAYOUT_VERSION) {
    // Clear stale layout and save new version
    saveToStorage(STORAGE_KEY, DEFAULT_LAYOUT);
    saveToStorage(VISIBLE_KEY, DEFAULT_VISIBLE);
    saveToStorage(VERSION_KEY, LAYOUT_VERSION);
    return DEFAULT_LAYOUT;
  }
  return loadFromStorage<LayoutItem[]>(STORAGE_KEY, DEFAULT_LAYOUT);
}

function getInitialVisible(): string[] {
  const storedVersion = loadFromStorage<number>(VERSION_KEY, 0);
  if (storedVersion < LAYOUT_VERSION) return DEFAULT_VISIBLE;
  return loadFromStorage<string[]>(VISIBLE_KEY, DEFAULT_VISIBLE);
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  layout: getInitialLayout(),
  visibleWidgets: getInitialVisible(),
  isLocked: loadFromStorage<boolean>(LOCK_KEY, true), // Locked by default for new users

  setLayout: (layout) => {
    set({ layout });
    saveToStorage(STORAGE_KEY, layout);
    saveToStorage(VERSION_KEY, LAYOUT_VERSION);
  },

  addWidget: (widgetId) => {
    const { visibleWidgets, layout } = get();
    if (visibleWidgets.includes(widgetId)) return;

    const meta = WIDGET_REGISTRY[widgetId];
    if (!meta) return;

    // Find the bottom of the current layout to place the new widget
    const maxY = layout.reduce((max, item) => Math.max(max, item.y + item.h), 0);

    const newLayout = [
      ...layout,
      {
        i: widgetId,
        x: 0,
        y: maxY,
        w: meta.defaultW,
        h: meta.defaultH,
        minW: meta.minW,
        minH: meta.minH,
      },
    ];
    const newVisible = [...visibleWidgets, widgetId];

    set({ layout: newLayout, visibleWidgets: newVisible });
    saveToStorage(STORAGE_KEY, newLayout);
    saveToStorage(VISIBLE_KEY, newVisible);
  },

  removeWidget: (widgetId) => {
    const { visibleWidgets, layout } = get();
    const newVisible = visibleWidgets.filter(id => id !== widgetId);
    const newLayout = layout.filter(item => item.i !== widgetId);

    set({ layout: newLayout, visibleWidgets: newVisible });
    saveToStorage(STORAGE_KEY, newLayout);
    saveToStorage(VISIBLE_KEY, newVisible);
  },

  toggleLock: () => {
    const newLocked = !get().isLocked;
    set({ isLocked: newLocked });
    saveToStorage(LOCK_KEY, newLocked);
  },

  resetToDefault: () => {
    set({
      layout: DEFAULT_LAYOUT,
      visibleWidgets: DEFAULT_VISIBLE,
      isLocked: true,
    });
    saveToStorage(STORAGE_KEY, DEFAULT_LAYOUT);
    saveToStorage(VISIBLE_KEY, DEFAULT_VISIBLE);
    saveToStorage(LOCK_KEY, true);
    saveToStorage(VERSION_KEY, LAYOUT_VERSION);
  },
}));
