# AlphaDesk — UI Component Inventory

## Layout Components
| Component | Props | Description |
|-----------|-------|-------------|
| AppShell | children | Main layout wrapper with nav + content area |
| TopNav | — | App title, navigation links |
| Sidebar | children | Collapsible sidebar for watchlist/history |
| MacroBar | data: MacroData | Horizontal data bar at top of morning brief |

## Shared Components
| Component | Props | Description |
|-----------|-------|-------------|
| DataTable | columns, data, sortable?, onSort? | Sortable table with financial formatting |
| LoadingState | message? | Skeleton/spinner placeholder |
| ErrorState | error, onRetry? | Error display with retry button |
| DeltaBadge | value: number, format?: 'pct'\|'abs' | Green/red badge for +/- values |
| GradeBadge | grade: A-F | Colour-coded letter grade |
| Timestamp | date: string, label?: string | "Generated at" / "Data as of" display |

## Feature Components
### Morning Brief
- SectorPanel: sector ETF table + period selector
- SectorChart: multi-line normalised chart (Recharts)
- DriversPanel: AI-generated driver cards

### Screener
- SearchBar: ticker search with autocomplete
- StockGraderCard: full grade display with expandable sections
- WatchlistSidebar: persistent watchlist panel
- ScreenerResults: value + momentum tabs

### Weekly Report
- ReportGenerator: generate button + streaming progress
- ReportViewer: collapsible sections with rendered tables
- ReportSection: individual collapsible section
- SortableTable: enhanced DataTable for report data
- ReportHistory: past reports list

### Portfolio
- PortfolioBuilder: stock picker + capital input
- CorrelationHeatmap: Plotly heatmap
- OptimisationTable: side-by-side portfolio comparison
- MonteCarloChart: fan chart with percentile bands

### RRG
- RRGChart: Plotly scatter + Framer Motion animated tails
- BenchmarkSelector: dropdown for benchmark ticker
