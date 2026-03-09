# AlphaDesk — Task Manifest

## Sprint 0: Infrastructure
| ID | Task | Agent | Branch | Status | Dependencies |
|----|------|-------|--------|--------|-------------|
| S0-01 | Initialise monorepo with root package.json | Backend | feature/infra/monorepo-init | TODO | — |
| S0-02 | Scaffold FastAPI backend | Backend | feature/infra/backend-scaffold | TODO | S0-01 |
| S0-03 | Scaffold Vite + React + TS frontend | Frontend | feature/infra/frontend-scaffold | TODO | S0-01 |
| S0-04 | Configure Tailwind with AlphaDesk tokens | UI | feature/infra/tailwind-config | TODO | S0-03 |
| S0-05 | Create SQLite schema + SQLModel models | Backend | feature/infra/db-schema | TODO | S0-02 |
| S0-06 | Build yfinance service layer | Backend | feature/infra/yfinance-service | TODO | S0-02 |
| S0-07 | Build financialdatasets.ai service layer | Backend | feature/infra/fds-service | TODO | S0-02 |
| S0-08 | Build Claude API service layer | Backend | feature/infra/claude-service | TODO | S0-02 |
| S0-09 | Create AppShell layout with routing | Frontend | feature/infra/app-shell | TODO | S0-03, S0-04 |
| S0-10 | Set up React Query + Zustand stores | Frontend | feature/infra/state-setup | TODO | S0-03 |
| S0-11 | Create shared components | Frontend+UI | feature/infra/shared-components | TODO | S0-04 |
| S0-12 | Configure CORS and error handling | Backend | feature/infra/middleware | TODO | S0-02 |
| S0-13 | Create frontend API client | Frontend | feature/infra/api-client | TODO | S0-03 |
| S0-14 | Set up prompt templates module | Backend | feature/infra/prompts | TODO | S0-08 |

## Sprint 1: Morning Brief
| ID | Task | Agent | Branch | Status | Dependencies |
|----|------|-------|--------|--------|-------------|
| S1-01 | Implement /api/morning-brief/macro | Backend | feature/morning-brief/macro-api | TODO | S0-06 |
| S1-02 | Implement /api/morning-brief/sectors | Backend | feature/morning-brief/sectors-api | TODO | S0-06 |
| S1-03 | Implement /api/morning-brief/drivers | Backend | feature/morning-brief/drivers-api | TODO | S0-08, S0-14 |
| S1-04 | Build MacroBar component | Frontend | feature/morning-brief/macro-bar | TODO | S0-11, S1-01 |
| S1-05 | Build SectorPanel + SectorChart | Frontend | feature/morning-brief/sector-panel | TODO | S0-11, S1-02 |
| S1-06 | Build DriversPanel | Frontend | feature/morning-brief/drivers-panel | TODO | S0-11, S1-03 |
| S1-07 | Compose MorningBrief page | Frontend | feature/morning-brief/page | TODO | S1-04–S1-06 |
| S1-08 | Style and polish Morning Brief | UI | feature/morning-brief/polish | TODO | S1-07 |

## Sprint 2: Stock Screener
| ID | Task | Agent | Branch | Status | Dependencies |
|----|------|-------|--------|--------|-------------|
| S2-01 | Implement /api/search | Backend | feature/screener/search-api | TODO | S0-06 |
| S2-02 | Implement /api/stock/{ticker}/quote | Backend | feature/screener/quote-api | TODO | S0-06 |
| S2-03 | Implement /api/stock/{ticker}/grade | Backend | feature/screener/grade-api | TODO | S0-06, S0-07, S0-08 |
| S2-04 | Implement /api/watchlist CRUD | Backend | feature/screener/watchlist-api | TODO | S0-05 |
| S2-05 | Implement /api/screener/run | Backend | feature/screener/screener-api | TODO | S0-08 |
| S2-06 | Build SearchBar + results | Frontend | feature/screener/search-ui | TODO | S2-01 |
| S2-07 | Build StockGraderCard | Frontend | feature/screener/grader-card | TODO | S2-03 |
| S2-08 | Build WatchlistSidebar | Frontend | feature/screener/watchlist-ui | TODO | S2-04 |
| S2-09 | Build ScreenerResults tab | Frontend | feature/screener/results-ui | TODO | S2-05 |
| S2-10 | Compose Screener page | Frontend+UI | feature/screener/page | TODO | S2-06–S2-09 |

## Sprint 3: Weekly Report
| ID | Task | Agent | Branch | Status | Dependencies |
|----|------|-------|--------|--------|-------------|
| S3-01 | Implement /api/weekly-report/generate (SSE) | Backend | feature/report/generate-api | TODO | S0-08 |
| S3-02 | Implement /api/weekly-report/list and /{id} | Backend | feature/report/list-api | TODO | S0-05 |
| S3-03 | Build ReportGenerator (streaming) | Frontend | feature/report/generator-ui | TODO | S3-01 |
| S3-04 | Build ReportViewer | Frontend | feature/report/viewer-ui | TODO | S3-02 |
| S3-05 | Build ReportHistory sidebar | Frontend | feature/report/history-ui | TODO | S3-02 |
| S3-06 | Implement PDF export | Frontend | feature/report/pdf-export | TODO | S3-04 |
| S3-07 | Compose WeeklyReport page | Frontend+UI | feature/report/page | TODO | S3-03–S3-06 |

## Sprint 4: Virtual Portfolio
| ID | Task | Agent | Branch | Status | Dependencies |
|----|------|-------|--------|--------|-------------|
| S4-01 | Implement /api/portfolio CRUD | Backend | feature/portfolio/crud-api | TODO | S0-05 |
| S4-02 | Implement /api/portfolio/{id}/analysis | Backend | feature/portfolio/analysis-api | TODO | S0-06 |
| S4-03 | Build PortfolioBuilder | Frontend | feature/portfolio/builder-ui | TODO | S4-01 |
| S4-04 | Build CorrelationHeatmap + OptimisationTable | Frontend | feature/portfolio/analysis-ui | TODO | S4-02 |
| S4-05 | Build MonteCarloChart | Frontend | feature/portfolio/monte-carlo-ui | TODO | S4-02 |
| S4-06 | Compose Portfolio page | Frontend+UI | feature/portfolio/page | TODO | S4-03–S4-05 |

## Sprint 5: RRG
| ID | Task | Agent | Branch | Status | Dependencies |
|----|------|-------|--------|--------|-------------|
| S5-01 | Implement RRG calculator | Backend | feature/rrg/calculator | TODO | S0-06 |
| S5-02 | Implement /api/rrg endpoint | Backend | feature/rrg/api | TODO | S5-01 |
| S5-03 | Build RRGChart with animation | Frontend | feature/rrg/chart-ui | TODO | S5-02 |
| S5-04 | Compose RRG page | Frontend+UI | feature/rrg/page | TODO | S5-03 |

## Sprint 6: Integration & Polish
| ID | Task | Agent | Branch | Status | Dependencies |
|----|------|-------|--------|--------|-------------|
| S6-01 | Full integration test | Review | — | TODO | All |
| S6-02 | Error handling audit | Review | — | TODO | All |
| S6-03 | Performance and caching pass | Backend+Frontend | — | TODO | All |
| S6-04 | Final UI polish | UI | — | TODO | All |
