/**
 * Widget Registry — maps widget IDs to React components + metadata.
 * Each widget is a self-contained panel that can be placed on the dashboard grid.
 */
import { lazy, type ComponentType, type LazyExoticComponent } from 'react';

export interface WidgetMeta {
  id: string;
  name: string;
  description: string;
  category: 'signal' | 'context' | 'positioning' | 'sentiment' | 'new';
  /** Default grid dimensions (12-column grid) */
  defaultW: number;
  defaultH: number;
  minW: number;
  minH: number;
  /** Max dimensions (optional) */
  maxW?: number;
  maxH?: number;
  /** The lazy-loaded React component */
  component: LazyExoticComponent<ComponentType<any>> | ComponentType<any>;
}

// Lazy-load all panel components for code-splitting
const MarketRegimeCard = lazy(() =>
  import('../components/morning-brief/MarketRegimeCard').then(m => ({ default: m.MarketRegimeCard }))
);
const MarketReportPanel = lazy(() =>
  import('../components/morning-brief/MarketReportPanel').then(m => ({ default: m.MarketReportPanel }))
);
const SectorChart = lazy(() =>
  import('../components/morning-brief/SectorChart').then(m => ({ default: m.SectorChart }))
);
const SectorTransitionsPanel = lazy(() =>
  import('../components/morning-brief/SectorTransitionsPanel').then(m => ({ default: m.SectorTransitionsPanel }))
);
const DriversPanel = lazy(() =>
  import('../components/morning-brief/DriversPanel').then(m => ({ default: m.DriversPanel }))
);
const MomentumSpilloverPanel = lazy(() =>
  import('../components/morning-brief/MomentumSpilloverPanel').then(m => ({ default: m.MomentumSpilloverPanel }))
);
const PositioningPanel = lazy(() =>
  import('../components/morning-brief/PositioningPanel').then(m => ({ default: m.PositioningPanel }))
);
const ScenarioRiskPanel = lazy(() =>
  import('../components/morning-brief/ScenarioRiskPanel').then(m => ({ default: m.ScenarioRiskPanel }))
);
const SentimentVelocityPanel = lazy(() =>
  import('../components/morning-brief/SentimentVelocityPanel').then(m => ({ default: m.SentimentVelocityPanel }))
);
const OptionsFlowPanel = lazy(() =>
  import('../components/morning-brief/OptionsFlowPanel').then(m => ({ default: m.OptionsFlowPanel }))
);
const EarningsCalendarPanel = lazy(() =>
  import('../components/morning-brief/EarningsCalendarPanel').then(m => ({ default: m.EarningsCalendarPanel }))
);
const CrossAssetPulsePanel = lazy(() =>
  import('../components/morning-brief/CrossAssetPulsePanel').then(m => ({ default: m.CrossAssetPulsePanel }))
);
const SeasonalityPanel = lazy(() =>
  import('../components/morning-brief/SeasonalityPanel').then(m => ({ default: m.SeasonalityPanel }))
);

export const WIDGET_REGISTRY: Record<string, WidgetMeta> = {
  'regime-card': {
    id: 'regime-card',
    name: 'Market Regime',
    description: 'Composite regime signal with layers, VIX structure, breadth, and overnight gaps',
    category: 'signal',
    defaultW: 12,
    defaultH: 6,
    minW: 3,
    minH: 3,
    component: MarketRegimeCard,
  },
  'market-report': {
    id: 'market-report',
    name: 'Market Report',
    description: 'AI-generated morning market analysis and key themes',
    category: 'context',
    defaultW: 12,
    defaultH: 4,
    minW: 3,
    minH: 2,
    component: MarketReportPanel,
  },
  'sector-chart': {
    id: 'sector-chart',
    name: 'Sector Performance',
    description: 'Sector ETF performance chart with period selection',
    category: 'context',
    defaultW: 8,
    defaultH: 5,
    minW: 3,
    minH: 3,
    component: SectorChart,
  },
  'sector-transitions': {
    id: 'sector-transitions',
    name: 'Sector Transitions',
    description: 'RRG quadrant transitions and sector rotation signals',
    category: 'context',
    defaultW: 8,
    defaultH: 4,
    minW: 3,
    minH: 3,
    component: SectorTransitionsPanel,
  },
  'drivers': {
    id: 'drivers',
    name: 'Market Drivers',
    description: 'Key market-moving themes and catalysts',
    category: 'context',
    defaultW: 4,
    defaultH: 5,
    minW: 3,
    minH: 3,
    component: DriversPanel,
  },
  'momentum-spillover': {
    id: 'momentum-spillover',
    name: 'Factor Decomposition',
    description: 'Cross-asset momentum and factor analysis',
    category: 'context',
    defaultW: 4,
    defaultH: 4,
    minW: 3,
    minH: 3,
    component: MomentumSpilloverPanel,
  },
  'positioning': {
    id: 'positioning',
    name: 'COT Positioning',
    description: 'Commitment of Traders positioning across futures markets',
    category: 'positioning',
    defaultW: 6,
    defaultH: 6,
    minW: 3,
    minH: 3,
    component: PositioningPanel,
  },
  'scenario-risk': {
    id: 'scenario-risk',
    name: 'Scenario & Risk',
    description: 'VaR analysis, stress scenarios, and historical analogs',
    category: 'positioning',
    defaultW: 6,
    defaultH: 6,
    minW: 3,
    minH: 3,
    component: ScenarioRiskPanel,
  },
  'sentiment': {
    id: 'sentiment',
    name: 'Sentiment Velocity',
    description: 'Multi-source sentiment analysis with velocity tracking',
    category: 'sentiment',
    defaultW: 4,
    defaultH: 5,
    minW: 2,
    minH: 3,
    component: SentimentVelocityPanel,
  },
  'options-flow': {
    id: 'options-flow',
    name: 'Options Flow',
    description: 'Notable options activity and unusual flow signals',
    category: 'sentiment',
    defaultW: 4,
    defaultH: 5,
    minW: 2,
    minH: 3,
    component: OptionsFlowPanel,
  },
  'earnings': {
    id: 'earnings',
    name: 'Earnings Calendar',
    description: 'Upcoming earnings with expected move and positioning',
    category: 'sentiment',
    defaultW: 4,
    defaultH: 5,
    minW: 2,
    minH: 3,
    component: EarningsCalendarPanel,
  },
  'cross-asset-pulse': {
    id: 'cross-asset-pulse',
    name: 'Cross-Asset Pulse',
    description: 'SPY, TLT, GLD, DXY, HYG sparklines with daily change',
    category: 'new',
    defaultW: 6,
    defaultH: 4,
    minW: 3,
    minH: 3,
    component: CrossAssetPulsePanel,
  },
  'seasonality': {
    id: 'seasonality',
    name: 'Sector Seasonality',
    description: 'Monthly average return heatmap for 11 SPDR sector ETFs',
    category: 'new',
    defaultW: 6,
    defaultH: 5,
    minW: 3,
    minH: 3,
    component: SeasonalityPanel,
  },
};

export const WIDGET_CATEGORIES = [
  { key: 'signal', label: 'Signal' },
  { key: 'context', label: 'Context' },
  { key: 'positioning', label: 'Positioning' },
  { key: 'sentiment', label: 'Sentiment' },
  { key: 'new', label: 'New' },
] as const;

export function getWidgetMeta(id: string): WidgetMeta | undefined {
  return WIDGET_REGISTRY[id];
}

export function getAllWidgets(): WidgetMeta[] {
  return Object.values(WIDGET_REGISTRY);
}

export function getWidgetsByCategory(category: string): WidgetMeta[] {
  return Object.values(WIDGET_REGISTRY).filter(w => w.category === category);
}
