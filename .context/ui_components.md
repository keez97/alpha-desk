# AlphaDesk — UI Component Inventory

> **Last updated:** 2026-03-11

## Layout Components
| Component | File | Description |
|-----------|------|-------------|
| AppShell | `layout/AppShell.tsx` | Main layout wrapper with TopNav and Outlet |
| TopNav | `layout/TopNav.tsx` | Navigation bar with active page highlighting, model selector |
| MacroBar | `layout/MacroBar.tsx` | Horizontal scrolling macro indicators (regime, yields, VIX, dollar, oil) |

## Shared Components
| Component | File | Description |
|-----------|------|-------------|
| DataTable | `shared/DataTable.tsx` | Sortable table with financial number formatting |
| LoadingState | `shared/LoadingState.tsx` | Pulsing loading indicator |
| ErrorState | `shared/ErrorState.tsx` | Error display with retry button |
| DeltaBadge | `shared/DeltaBadge.tsx` | Green/red badge for percentage changes |
| GradeBadge | `shared/GradeBadge.tsx` | Letter grade badge (A-F) with color coding |
| Timestamp | `shared/Timestamp.tsx` | Formatted date/time display |

## Morning Brief Components (16 panels)
| Component | File | Backend Hook | Description |
|-----------|------|-------------|-------------|
| RegimePanel | `morning-brief/RegimePanel.tsx` | `useMacro` + `useUpgradedRegime` | Bear/bull/neutral regime with confidence, signals, recession probability |
| VixTermStructurePanel | `morning-brief/VixTermStructurePanel.tsx` | `useVixTermStructure` | VIX spot vs 3M, contango/backwardation, percentile, 30-day trend |
| BreadthPanel | `morning-brief/BreadthPanel.tsx` | `useBreadth` | A/D ratio, McClellan oscillator, breadth thrust, advancing/declining bar |
| OvernightPanel | `morning-brief/OvernightPanel.tsx` | `useOvernightReturns` | 14 indices overnight gaps, major indices + sectors grid, outlier flags |
| SectorPanel | `morning-brief/SectorPanel.tsx` | `useSectors` | 11 sector ETFs table with RS-ratio, RS-momentum, trend indicators |
| SectorChart | `morning-brief/SectorChart.tsx` | `useSectors` | Normalized sector performance line chart |
| EnhancedSectorPanel | `morning-brief/EnhancedSectorPanel.tsx` | `useEnhancedSectors` | Extended sector data with RRG quadrant assignments |
| SectorTransitionsPanel | `morning-brief/SectorTransitionsPanel.tsx` | `useSectorTransitions` | Business cycle positioning, favorable/unfavorable sector chips |
| SentimentVelocityPanel | `morning-brief/SentimentVelocityPanel.tsx` | `useSentimentVelocity` | Sentiment gauge, velocity, distribution bar, 5-day trend, headlines |
| OptionsFlowPanel | `morning-brief/OptionsFlowPanel.tsx` | `useOptionsFlow` | IV skew, put/call ratio, GEX, volume imbalance, call/put volume |
| PositioningPanel | `morning-brief/PositioningPanel.tsx` | `usePositioning` | COT commercial/speculative bars, reversal & divergence alerts |
| ScenarioRiskPanel | `morning-brief/ScenarioRiskPanel.tsx` | `useScenarioRisk` | VaR comparison, stress scenario cards with impact/probability/severity |
| MomentumSpilloverPanel | `morning-brief/MomentumSpilloverPanel.tsx` | `useMomentumSpillover` | Cross-asset 1M/3M momentum table with signal classification |
| DriversPanel | `morning-brief/DriversPanel.tsx` | `useDrivers` | AI-generated market driver cards with importance scores |
| EarningsCalendarPanel | `morning-brief/EarningsCalendarPanel.tsx` | `useEarningsBrief` | Upcoming earnings with expected moves |
| MarketReportPanel | `morning-brief/MarketReportPanel.tsx` | (generated from all data) | AI-generated morning narrative with collapsible sections |

## Screener Components
| Component | File | Description |
|-----------|------|-------------|
| SearchBar | `screener/SearchBar.tsx` | Debounced ticker search with dropdown results |
| StockGraderCard | `screener/StockGraderCard.tsx` | Stock grade display with expandable sections |
| WatchlistSidebar | `screener/WatchlistSidebar.tsx` | Watchlist list with add/remove actions |
| ScreenerResults | `screener/ScreenerResults.tsx` | Tabbed results: Value Opportunities / Momentum Leaders |

## Weekly Report Components
| Component | File | Description |
|-----------|------|-------------|
| ReportGenerator | `weekly-report/ReportGenerator.tsx` | Generate button with SSE streaming progress |
| ReportViewer | `weekly-report/ReportViewer.tsx` | Full report with collapsible sections |
| ReportSection | `weekly-report/ReportSection.tsx` | Individual collapsible section |
| ReportHistory | `weekly-report/ReportHistory.tsx` | Past reports list with delete |

## Portfolio Components
| Component | File | Description |
|-----------|------|-------------|
| PortfolioBuilder | `portfolio/PortfolioBuilder.tsx` | Create/edit portfolios with holdings management |
| CorrelationHeatmap | `portfolio/CorrelationHeatmap.tsx` | Plotly heatmap of correlation matrix |
| OptimisationTable | `portfolio/OptimisationTable.tsx` | Max Sharpe vs min variance comparison |
| MonteCarloChart | `portfolio/MonteCarloChart.tsx` | Recharts area chart with percentile bands |

## RRG Components
| Component | File | Description |
|-----------|------|-------------|
| RRGChart | `rrg/RRGChart.tsx` | Plotly scatter with animated quadrant tails |
| BenchmarkSelector | `rrg/BenchmarkSelector.tsx` | Dropdown for benchmark ticker |

## Other Feature Components
| Directory | Components | Description |
|-----------|-----------|-------------|
| `earnings/` | Earnings calendar, PEAD, confluence panels | Earnings analysis dashboard |
| `confluence/` | Signal confluence, backtest results | Multi-factor signal confluence |
| `events/` | Event tracker, catalyst cards | Event and catalyst tracking |
| `sentiment/` | Sentiment dashboard, news feed | Dedicated sentiment analysis page |
| `backtester/` | Strategy builder, backtest results | Strategy backtesting interface |
| `correlation/` | Correlation matrix, heatmap | Cross-asset correlation analysis |
| `settings/` | Model selector, API key config | App settings and configuration |

## Pages (11 total)
| Page | File | Route | Description |
|------|------|-------|-------------|
| MorningBrief | `pages/MorningBrief.tsx` | `/morning-brief` | 16-panel market dashboard |
| Screener | `pages/Screener.tsx` | `/screener` | Stock search and grading |
| WeeklyReport | `pages/WeeklyReport.tsx` | `/weekly-report` | AI report generation |
| Portfolio | `pages/Portfolio.tsx` | `/portfolio` | Portfolio management |
| RRG | `pages/RRG.tsx` | `/rrg` | Relative Rotation Graph |
| Earnings | `pages/Earnings.tsx` | `/earnings` | Earnings dashboard |
| Confluence | `pages/Confluence.tsx` | `/confluence` | Signal confluence |
| Events | `pages/Events.tsx` | `/events` | Events & catalysts |
| Sentiment | `pages/Sentiment.tsx` | `/sentiment` | Sentiment analysis |
| Backtester | `pages/Backtester.tsx` | `/backtester` | Strategy backtesting |
| Correlation | `pages/Correlation.tsx` | `/correlation` | Correlation analysis |

## React Query Hooks (38 total)
All hooks follow the pattern: `useXxx()` → calls `fetchXxx()` from `lib/api.ts` → `api.get('/endpoint')`.

Key hooks for Morning Brief (all pre-cached from `/all`):
`useMacro`, `useBreadth`, `useVixTermStructure`, `useUpgradedRegime`, `useSectors`, `useEnhancedSectors`, `useSectorTransitions`, `useSentimentVelocity`, `useOptionsFlow`, `usePositioning`, `useScenarioRisk`, `useMomentumSpillover`, `useDrivers`, `useEarningsBrief`, `useOvernightReturns`

Other hooks:
`useStockQuote`, `useStockGrade`, `useWatchlist`, `useScreener`, `useQuantScreener`, `useWeeklyReport`, `usePortfolio`, `useRRG`, `useBacktester`, `useQuickBacktest`, `useConfluence`, `useConfluenceBacktest`, `useCorrelation`, `useEarnings`, `useEarningsConfluence`, `useEvents`, `useIntradayMomentum`, `useNotifications`, `usePositionSizing`, `useRotationAlerts`, `useSentiment`, `useStockFactors`, `usePrefetchMorningBrief`
