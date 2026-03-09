# AlphaDesk — Full Architectural Plan

**Date:** 2026-03-09
**Status:** AWAITING APPROVAL
**Author:** Orchestration Agent

---

## 1. DEPENDENCY GRAPH ACROSS ALL 5 FEATURES

```
INFRASTRUCTURE (must build first)
├── Project scaffolding (monorepo, Vite, FastAPI)
├── SQLite schema + SQLModel models
├── Design system tokens + Tailwind config
├── Base layout shell (nav, dark theme, responsive grid)
├── Backend: yfinance service layer
├── Backend: financialdatasets.ai service layer
├── Backend: Claude API service layer (with base analyst persona)
└── Frontend: React Query setup, Zustand stores, shared hooks

FEATURE 1: MORNING BRIEF (no feature dependencies)
├── Backend: /api/morning-brief/macro → yfinance quotes
├── Backend: /api/morning-brief/sectors → yfinance sector ETFs + chart data
├── Backend: /api/morning-brief/drivers → Claude API w/ web_search
├── Frontend: MacroBar component
├── Frontend: SectorPanel component (table + normalised chart)
└── Frontend: DriversPanel component (AI cards with sources)

FEATURE 3: STOCK SCREENER (no feature dependencies, but shares infra with Feature 2)
├── Backend: /api/search?q= → yfinance ticker search
├── Backend: /api/stock/{ticker}/quote → live quote
├── Backend: /api/stock/{ticker}/grade → Claude API grading
├── Backend: /api/watchlist (CRUD) → SQLite
├── Backend: /api/screener/run → Claude API w/ web_search
├── Frontend: SearchBar + SearchResults
├── Frontend: StockGraderCard (letter grades, rationale)
├── Frontend: WatchlistSidebar
└── Frontend: ScreenerTab (proactive AI screen)

FEATURE 2: WEEKLY REPORT (depends on: same Claude/yfinance infra, benefits from screener prompt reuse)
├── Backend: /api/weekly-report/generate → Claude API streaming w/ web_search
├── Backend: /api/weekly-report/list → saved reports from SQLite
├── Backend: /api/weekly-report/{id} → fetch saved report
├── Frontend: ReportGenerator (streaming section-by-section)
├── Frontend: ReportViewer (collapsible sections, sortable tables)
├── Frontend: ReportHistory sidebar
└── Frontend: PDF export

FEATURE 4: VIRTUAL PORTFOLIO (depends on: watchlist/search from Feature 3)
├── Backend: /api/portfolio (CRUD) → SQLite
├── Backend: /api/portfolio/{id}/analysis → numpy/scipy computations
│   ├── Correlation matrix
│   ├── Max Sharpe optimisation
│   ├── Max Variance optimisation
│   └── Monte Carlo simulation
├── Frontend: PortfolioBuilder (add stocks, set capital)
├── Frontend: CorrelationHeatmap
├── Frontend: OptimisationComparison table
└── Frontend: MonteCarloFanChart

FEATURE 5: RRG (depends on: yfinance price history infra only)
├── Backend: /api/rrg?benchmark=SPY → RS-Ratio + RS-Momentum calc
├── Frontend: RRGChart (Plotly scatter + Framer Motion animation)
└── Frontend: BenchmarkSelector
```

**Build Order:**
1. Infrastructure (Sprint 0)
2. Feature 1: Morning Brief (first visible value)
3. Feature 3: Stock Screener (builds watchlist infra needed by Feature 4)
4. Feature 2: Weekly Report (most complex AI feature, shares screener logic)
5. Feature 4: Virtual Portfolio (uses watchlist from Feature 3)
6. Feature 5: RRG (independent, can parallelise with Feature 4)

---

## 2. COMPLETE API CONTRACT

### Base URL: `http://localhost:8000/api`

### Morning Brief

```
GET /api/morning-brief/macro
Response: {
  timestamp: string (ISO),
  data: {
    us_10y: { value: number, change: number },
    us_2y: { value: number, change: number },
    yield_spread: { value: number, change: number },
    vix: { value: number, change: number },
    dxy: { value: number, change: number },
    gold: { value: number, change: number },
    wti: { value: number, change: number },
    btc: { value: number, change: number },
    spy: { value: number, pct_change: number },
    qqq: { value: number, pct_change: number },
    iwm: { value: number, pct_change: number }
  }
}

GET /api/morning-brief/sectors?period=1D|5D|1M|3M
Response: {
  timestamp: string,
  sectors: [
    {
      ticker: string,
      name: string,
      price: number,
      daily_pct_change: number,
      chart_data: [ { date: string, normalised_price: number } ]
    }
  ]
}

GET /api/morning-brief/drivers
POST /api/morning-brief/drivers/refresh
Response: {
  generated_at: string,
  data_as_of: string,
  drivers: [
    {
      headline: string,
      explanation: string,
      sources: [ { title: string, url: string } ]
    }
  ]
}
```

### Stock Screener & Search

```
GET /api/search?q={query}
Response: {
  results: [
    { ticker: string, name: string, sector: string, type: "stock"|"etf"|"crypto"|"commodity" }
  ]
}

GET /api/stock/{ticker}/quote
Response: {
  ticker: string,
  name: string,
  sector: string,
  market_cap: number,
  price: number,
  daily_change: number,
  daily_pct_change: number,
  volume: number,
  fifty_two_week_high: number,
  fifty_two_week_low: number
}

POST /api/stock/{ticker}/grade
Response: {
  ticker: string,
  generated_at: string,
  data_as_of: string,
  grades: {
    [metric_name: string]: {
      score: "A"|"B"|"C"|"D"|"F",
      value: string,
      rationale: string
    }
  },
  overall_grade: string,
  summary: string,
  risks: string[],
  catalysts: string[]
}

POST /api/screener/run
Response: {
  generated_at: string,
  data_as_of: string,
  value_opportunities: [ StockScreenResult ],
  momentum_leaders: [ StockScreenResult ]
}
```

### Watchlist

```
GET    /api/watchlist              → { items: WatchlistItem[] }
POST   /api/watchlist              → body: { ticker: string } → WatchlistItem
DELETE /api/watchlist/{ticker}     → { success: boolean }
```

### Weekly Report

```
POST   /api/weekly-report/generate  → SSE stream of report sections (JSON chunks)
GET    /api/weekly-report/list      → { reports: ReportSummary[] }
GET    /api/weekly-report/{id}      → FullReport
DELETE /api/weekly-report/{id}      → { success: boolean }
```

Report JSON schema (each section streamed as it completes):
```json
{
  "id": "string",
  "generated_at": "string",
  "data_as_of": "string",
  "sections": {
    "value_opportunities": {
      "stocks": [{
        "ticker": "string",
        "company_name": "string",
        "sector": "string",
        "market_cap": "string",
        "current_price": "number",
        "pct_from_52w_low": "number",
        "forward_pe": "number",
        "peg_ratio": "number",
        "fcf_yield": "number",
        "ttm_revenue": "string",
        "eps_trend": "string",
        "debt_ebitda": "number",
        "current_ratio": "number",
        "thesis": "string",
        "risks": ["string"]
      }]
    },
    "momentum_leaders": {
      "stocks": [{
        "ticker": "string",
        "company_name": "string",
        "sector": "string",
        "perf_1w": "number",
        "perf_1m": "number",
        "perf_3m": "number",
        "rs_vs_sector": "number",
        "rs_vs_sp500": "number",
        "volume_ratio": "number",
        "new_high_weekly": "boolean",
        "new_high_monthly": "boolean",
        "catalyst": "string"
      }]
    },
    "macro_trends": {
      "indices": [{ "name": "string", "ticker": "string", "weekly_return": "number", "ytd_return": "number" }],
      "rates": { "us_2y": "object", "us_10y": "object", "us_30y": "object", "fed_funds_expectation": "string" },
      "data_prints": ["string"],
      "sector_rotation": "string",
      "liquidity": "string",
      "geopolitical": "string"
    },
    "risks_catalysts": {
      "upcoming_events": [{ "date": "string", "event": "string", "prior": "string", "consensus": "string" }],
      "earnings_next_week": [{ "ticker": "string", "expected_eps": "string", "expected_revenue": "string", "implied_move": "string" }],
      "vix_analysis": "string",
      "market_breadth": "string",
      "bond_equity_correlation": "string",
      "credit_signals": "string"
    },
    "sentiment": {
      "institutional_commentary": "string",
      "earnings_call_tone": "string",
      "overall_verdict": "Bullish|Neutral|Bearish",
      "reasons": ["string"]
    },
    "executive_summary": {
      "direction": "string",
      "top_opportunities": ["string"],
      "top_risks": ["string"],
      "spx_1w_bias": "string",
      "spx_1m_bias": "string"
    }
  }
}
```

### Virtual Portfolio

```
GET    /api/portfolio                        → { portfolios: PortfolioSummary[] }
POST   /api/portfolio                        → body: { name, capital, holdings: [{ticker, weight?}] }
GET    /api/portfolio/{id}                   → PortfolioDetail
DELETE /api/portfolio/{id}                   → { success: boolean }
PUT    /api/portfolio/{id}                   → update holdings/name/capital
POST   /api/portfolio/{id}/analysis          → {
  correlation_matrix: { tickers: string[], matrix: number[][] },
  optimised_portfolios: {
    max_sharpe: { weights: {[ticker]: number}, expected_return: number, volatility: number, sharpe: number },
    max_variance: { weights: {[ticker]: number}, expected_return: number, volatility: number, sharpe: number }
  },
  monte_carlo: {
    simulations: number,
    days: number,
    percentile_paths: { p5: number[], p25: number[], p50: number[], p75: number[], p95: number[] },
    summary: {
      median_outcome: number,
      bear_case: number,
      bull_case: number,
      prob_gain: number,
      prob_20_gain: number,
      prob_20_loss: number,
      prob_30_drawdown: number
    }
  }
}
```

### RRG

```
GET /api/rrg?benchmark=SPY&weeks=10
Response: {
  benchmark: string,
  data_as_of: string,
  sectors: [
    {
      ticker: string,
      name: string,
      avg_volume_30d: number,
      trail: [
        { week: string, rs_ratio: number, rs_momentum: number }
      ],
      current_quadrant: "Leading"|"Weakening"|"Lagging"|"Improving"
    }
  ]
}
```

---

## 3. SQLITE SCHEMA

```sql
-- Watchlist
CREATE TABLE watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT UNIQUE NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_grade TEXT,          -- cached JSON of most recent AI grade
    last_grade_at TIMESTAMP
);

-- Virtual Portfolios
CREATE TABLE portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    capital REAL NOT NULL DEFAULT 100000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE portfolio_holding (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL REFERENCES portfolio(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    weight REAL,  -- NULL means "let optimizer decide"
    UNIQUE(portfolio_id, ticker)
);

-- Weekly Reports
CREATE TABLE weekly_report (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_as_of TEXT,
    report_json TEXT NOT NULL,  -- full JSON blob
    summary TEXT               -- executive summary text for list view
);

-- Morning Brief Cache
CREATE TABLE morning_brief_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,  -- "drivers", "macro", "sectors"
    data_json TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Stock Grade Cache
CREATE TABLE stock_grade_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    grade_json TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, generated_at)
);

-- Screener Cache
CREATE TABLE screener_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screen_type TEXT NOT NULL,  -- "value" or "momentum"
    results_json TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. CLAUDE API CALLS — PROMPT INVENTORY

All calls use model `claude-sonnet-4-20250514` with the base analyst persona as system prompt.

| # | Feature | Endpoint | Tools | Streaming | Prompt ID |
|---|---------|----------|-------|-----------|-----------|
| 1 | Morning Brief | /api/morning-brief/drivers | web_search | No | PROMPT_MORNING_DRIVERS_V1 |
| 2 | Weekly Report | /api/weekly-report/generate | web_search | Yes (SSE) | PROMPT_WEEKLY_REPORT_V1 |
| 3 | Stock Grader | /api/stock/{ticker}/grade | None (data pre-fetched) | No | PROMPT_STOCK_GRADE_V1 |
| 4 | AI Screener | /api/screener/run | web_search | No | PROMPT_SCREENER_V1 |

**System Prompt (all calls):**
```
You are a data-driven equity analyst. Provide structured analysis using only verifiable market data, price action, macro indicators, earnings results, and reputable institutional sources. Avoid speculation. Social sentiment is allowed only as a minor, secondary signal. All claims must be traceable to observable data. Format all output for a sophisticated institutional investor who values precision and evidence over narrative.
```

**PROMPT_MORNING_DRIVERS_V1:**
```
Identify the 5 most significant market-moving factors active in US equity markets today ({date}).

For each driver, provide:
1. A bold headline (max 12 words)
2. A 2-3 sentence data-grounded explanation
3. 2-3 source URLs from your search

Return valid JSON only:
{
  "drivers": [
    { "headline": "...", "explanation": "...", "sources": [{"title": "...", "url": "..."}] }
  ]
}
```

**PROMPT_STOCK_GRADE_V1:**
```
Grade {ticker} ({company_name}) across the following metrics using the data provided.

Data context:
{pre_fetched_data_json}

For each metric, assign a letter grade (A/B/C/D/F) with the actual value and a one-sentence rationale.

Metrics to grade:
- Sector rotation positioning
- Distance from 52-week low
- Forward P/E vs sector median
- Net debt / EBITDA
- Revenue growth (YoY)
- Operating margin vs peers
- Beta
- Max drawdown (1Y)
- 30-day realised volatility
- Average daily volume vs 90-day avg
- Institutional ownership %
- Short interest %
- FCF yield
- PEG ratio

Return valid JSON only matching this schema:
{
  "ticker": "string",
  "grades": { "metric_name": { "score": "A-F", "value": "string", "rationale": "string" } },
  "overall_grade": "string",
  "summary": "string",
  "risks": ["string"],
  "catalysts": ["string"]
}
```

**PROMPT_WEEKLY_REPORT_V1** and **PROMPT_SCREENER_V1** follow the same pattern — full templates documented in `.context/analyst_prompts.md`.

---

## 5. FOLDER STRUCTURE

```
alpha-desk/
├── package.json                 # root: concurrently script
├── PROJECT.md
├── AGENTS.md
├── TASK_MANIFEST.md
├── .context/
│   ├── architecture.md
│   ├── data_sources.md
│   ├── ui_components.md
│   ├── db_schema.md
│   └── analyst_prompts.md
├── backend/
│   ├── requirements.txt
│   ├── main.py                  # FastAPI app entry
│   ├── config.py                # env vars, API keys
│   ├── database.py              # SQLite + SQLModel setup
│   ├── models/
│   │   ├── __init__.py
│   │   ├── watchlist.py
│   │   ├── portfolio.py
│   │   ├── report.py
│   │   └── cache.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── yfinance_service.py  # all yfinance data fetching
│   │   ├── fds_service.py       # financialdatasets.ai client
│   │   ├── claude_service.py    # Claude API calls + prompt construction
│   │   ├── portfolio_math.py    # optimisation, Monte Carlo, correlation
│   │   └── rrg_calculator.py    # RS-Ratio / RS-Momentum math
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── morning_brief.py
│   │   ├── stock.py
│   │   ├── watchlist.py
│   │   ├── screener.py
│   │   ├── weekly_report.py
│   │   ├── portfolio.py
│   │   └── rrg.py
│   └── prompts/
│       ├── __init__.py
│       ├── base.py              # base analyst persona
│       ├── morning_drivers.py
│       ├── stock_grader.py
│       ├── weekly_report.py
│       └── screener.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── styles/
│       │   ├── globals.css
│       │   └── tokens.ts         # design tokens
│       ├── lib/
│       │   ├── api.ts            # axios/fetch client
│       │   └── utils.ts          # formatting helpers
│       ├── stores/
│       │   ├── watchlist.ts      # Zustand
│       │   ├── portfolio.ts
│       │   └── ui.ts
│       ├── hooks/
│       │   ├── useMacro.ts       # React Query hooks
│       │   ├── useSectors.ts
│       │   ├── useDrivers.ts
│       │   ├── useStockQuote.ts
│       │   ├── useStockGrade.ts
│       │   ├── useWatchlist.ts
│       │   ├── usePortfolio.ts
│       │   ├── useWeeklyReport.ts
│       │   ├── useScreener.ts
│       │   └── useRRG.ts
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppShell.tsx
│       │   │   ├── Sidebar.tsx
│       │   │   ├── TopNav.tsx
│       │   │   └── MacroBar.tsx
│       │   ├── morning-brief/
│       │   │   ├── SectorPanel.tsx
│       │   │   ├── SectorChart.tsx
│       │   │   └── DriversPanel.tsx
│       │   ├── screener/
│       │   │   ├── SearchBar.tsx
│       │   │   ├── StockGraderCard.tsx
│       │   │   ├── WatchlistSidebar.tsx
│       │   │   └── ScreenerResults.tsx
│       │   ├── weekly-report/
│       │   │   ├── ReportGenerator.tsx
│       │   │   ├── ReportViewer.tsx
│       │   │   ├── ReportSection.tsx
│       │   │   ├── SortableTable.tsx
│       │   │   └── ReportHistory.tsx
│       │   ├── portfolio/
│       │   │   ├── PortfolioBuilder.tsx
│       │   │   ├── CorrelationHeatmap.tsx
│       │   │   ├── OptimisationTable.tsx
│       │   │   └── MonteCarloChart.tsx
│       │   ├── rrg/
│       │   │   ├── RRGChart.tsx
│       │   │   └── BenchmarkSelector.tsx
│       │   └── shared/
│       │       ├── DataTable.tsx
│       │       ├── LoadingState.tsx
│       │       ├── ErrorState.tsx
│       │       ├── DeltaBadge.tsx
│       │       ├── GradeBadge.tsx
│       │       └── Timestamp.tsx
│       └── pages/
│           ├── MorningBrief.tsx
│           ├── Screener.tsx
│           ├── WeeklyReport.tsx
│           ├── Portfolio.tsx
│           └── RRG.tsx
```

---

## 6. TASK DECOMPOSITION — FULL BUILD PLAN

### Sprint 0: Infrastructure (16 tasks)
| ID | Task | Agent | Dependencies |
|----|------|-------|-------------|
| S0-01 | Initialise monorepo, root package.json with concurrently | Backend | None |
| S0-02 | Scaffold FastAPI backend with main.py, config, requirements.txt | Backend | S0-01 |
| S0-03 | Scaffold Vite + React + TS frontend | Frontend | S0-01 |
| S0-04 | Configure Tailwind with AlphaDesk tokens (dark mode) | UI | S0-03 |
| S0-05 | Create SQLite schema + SQLModel models | Backend | S0-02 |
| S0-06 | Build yfinance service layer | Backend | S0-02 |
| S0-07 | Build financialdatasets.ai service layer | Backend | S0-02 |
| S0-08 | Build Claude API service layer + base persona | Backend | S0-02 |
| S0-09 | Create AppShell layout (nav, sidebar, routing) | Frontend | S0-03, S0-04 |
| S0-10 | Set up React Query provider + Zustand stores | Frontend | S0-03 |
| S0-11 | Create shared components (DataTable, LoadingState, ErrorState, DeltaBadge, Timestamp) | Frontend+UI | S0-04 |
| S0-12 | Configure CORS, error handling middleware | Backend | S0-02 |
| S0-13 | Create API client (frontend) with base URL config | Frontend | S0-03 |
| S0-14 | Set up prompt templates module | Backend | S0-08 |
| S0-15 | Write all .context/ documentation files | Orchestration | None |
| S0-16 | Write PROJECT.md, AGENTS.md, TASK_MANIFEST.md | Orchestration | None |

### Sprint 1: Morning Brief (8 tasks)
| ID | Task | Agent | Dependencies |
|----|------|-------|-------------|
| S1-01 | Implement /api/morning-brief/macro endpoint | Backend | S0-06 |
| S1-02 | Implement /api/morning-brief/sectors endpoint | Backend | S0-06 |
| S1-03 | Implement /api/morning-brief/drivers endpoint | Backend | S0-08, S0-14 |
| S1-04 | Build MacroBar component | Frontend | S0-11, S1-01 |
| S1-05 | Build SectorPanel + SectorChart | Frontend | S0-11, S1-02 |
| S1-06 | Build DriversPanel | Frontend | S0-11, S1-03 |
| S1-07 | Compose MorningBrief page | Frontend | S1-04, S1-05, S1-06 |
| S1-08 | Style and polish Morning Brief | UI | S1-07 |

### Sprint 2: Stock Screener (10 tasks)
| ID | Task | Agent | Dependencies |
|----|------|-------|-------------|
| S2-01 | Implement /api/search endpoint | Backend | S0-06 |
| S2-02 | Implement /api/stock/{ticker}/quote endpoint | Backend | S0-06 |
| S2-03 | Implement /api/stock/{ticker}/grade endpoint | Backend | S0-06, S0-07, S0-08 |
| S2-04 | Implement /api/watchlist CRUD endpoints | Backend | S0-05 |
| S2-05 | Implement /api/screener/run endpoint | Backend | S0-08 |
| S2-06 | Build SearchBar + search results | Frontend | S2-01 |
| S2-07 | Build StockGraderCard | Frontend | S2-03 |
| S2-08 | Build WatchlistSidebar | Frontend | S2-04 |
| S2-09 | Build ScreenerResults tab | Frontend | S2-05 |
| S2-10 | Compose Screener page + style | Frontend+UI | S2-06–S2-09 |

### Sprint 3: Weekly Report (7 tasks)
| ID | Task | Agent | Dependencies |
|----|------|-------|-------------|
| S3-01 | Implement /api/weekly-report/generate (SSE streaming) | Backend | S0-08 |
| S3-02 | Implement /api/weekly-report/list and /{id} | Backend | S0-05 |
| S3-03 | Build ReportGenerator (streaming UI) | Frontend | S3-01 |
| S3-04 | Build ReportViewer (collapsible sections, sortable tables) | Frontend | S3-02 |
| S3-05 | Build ReportHistory sidebar | Frontend | S3-02 |
| S3-06 | Implement PDF export | Frontend | S3-04 |
| S3-07 | Compose WeeklyReport page + style | Frontend+UI | S3-03–S3-06 |

### Sprint 4: Virtual Portfolio (6 tasks)
| ID | Task | Agent | Dependencies |
|----|------|-------|-------------|
| S4-01 | Implement /api/portfolio CRUD endpoints | Backend | S0-05 |
| S4-02 | Implement /api/portfolio/{id}/analysis (correlation, optimisation, Monte Carlo) | Backend | S0-06, portfolio_math.py |
| S4-03 | Build PortfolioBuilder component | Frontend | S4-01 |
| S4-04 | Build CorrelationHeatmap + OptimisationTable | Frontend | S4-02 |
| S4-05 | Build MonteCarloChart | Frontend | S4-02 |
| S4-06 | Compose Portfolio page + style | Frontend+UI | S4-03–S4-05 |

### Sprint 5: RRG (4 tasks)
| ID | Task | Agent | Dependencies |
|----|------|-------|-------------|
| S5-01 | Implement RRG calculator (JdK methodology) | Backend | S0-06 |
| S5-02 | Implement /api/rrg endpoint | Backend | S5-01 |
| S5-03 | Build RRGChart with Framer Motion animation | Frontend | S5-02 |
| S5-04 | Compose RRG page + style | Frontend+UI | S5-03 |

### Sprint 6: Integration & Polish (4 tasks)
| ID | Task | Agent | Dependencies |
|----|------|-------|-------------|
| S6-01 | Full integration test — all pages, all API calls | Review | All |
| S6-02 | Error handling audit — loading/error states everywhere | Review | All |
| S6-03 | Performance pass — caching, stale data display | Backend+Frontend | All |
| S6-04 | Final UI polish pass | UI | All |

**Total: 55 tasks across 7 sprints**

---

## 7. DESIGN SYSTEM TOKENS

```
Colors:
  bg-primary:    #0f1117  (dark charcoal)
  bg-secondary:  #1a1d27  (card backgrounds)
  bg-tertiary:   #252836  (hover states, borders)
  text-primary:  #e5e7eb  (main text)
  text-secondary:#9ca3af  (labels, timestamps)
  accent-blue:   #3b82f6  (links, active states)
  success-green: #10b981  (positive values)
  danger-red:    #ef4444  (negative values)
  warning-amber: #f59e0b  (neutral/watch)
  border:        #2d3148

Typography:
  font-family:   'Inter', system-ui, sans-serif
  font-mono:     'JetBrains Mono', monospace (for numbers)

Spacing:
  Base unit: 4px

Border radius:
  cards: 8px
  buttons: 6px
  badges: 4px
```

---

## 8. KEY ARCHITECTURAL DECISIONS

1. **No GitHub repo management** — The `gh` CLI is not available in this environment. I will build the project locally with proper git history. The user can push to GitHub afterward.

2. **API key handling** — The financialdatasets.ai key and Claude API key will be stored in a `.env` file (gitignored) and loaded via `python-dotenv`. The user must supply their own `ANTHROPIC_API_KEY`.

3. **Caching strategy** — Morning brief data cached in SQLite with 4-hour TTL. Stock grades cached for 24 hours. Weekly reports persisted permanently. Frontend uses React Query with staleTime of 5 minutes for live data.

4. **Streaming for Weekly Report** — Backend uses FastAPI's `StreamingResponse` with SSE. Frontend consumes via `EventSource`. Each report section is a discrete SSE event.

5. **Monte Carlo in backend** — All heavy computation stays in Python (numpy/scipy). Frontend only renders the pre-computed percentile paths.

6. **No authentication** — This is a personal-use localhost app. No auth layer. Can be added later for SaaS.

7. **Single `npm run dev` command** — Root package.json uses `concurrently` to run both `uvicorn backend.main:app --reload` and `npm run dev --prefix frontend`.

---

## WHAT HAPPENS NEXT (after APPROVE)

1. I write all context documents (PROJECT.md, AGENTS.md, TASK_MANIFEST.md, .context/*)
2. I scaffold the entire project structure (both backend and frontend)
3. I build Sprint 0 infrastructure tasks
4. I proceed feature by feature through Sprints 1-5
5. I run integration and polish in Sprint 6

Each "agent" will be implemented as a sub-agent with full context bundles, working on isolated concerns within the codebase.

---

**Type APPROVE to begin build.**
