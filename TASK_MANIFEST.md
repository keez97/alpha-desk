# AlphaDesk — Feature Status Tracker

> **Last updated:** 2026-03-11
> **Rule:** This file must be updated whenever a feature is added, modified, or its status changes. See AGENTS.md for the documentation update protocol.

## Morning Brief
**Status:** ✅ Live | **Route:** `/morning-brief` | **Backend:** `/api/morning-brief/*`

The flagship feature. A 16-panel real-time market dashboard loaded via a single `/api/morning-brief/all` aggregate endpoint.

| Panel | Backend Service | Endpoint | Status | Notes |
|-------|----------------|----------|--------|-------|
| Market Regime | `regime_detector.py` | `/api/morning-brief/macro` | ✅ Live | Bear/bull/neutral with confidence score, key signals |
| VIX Term Structure | `vix_term_structure.py` | `/api/vix-term-structure` | ✅ Live | Spot vs 3M, contango/backwardation, percentile, roll yield |
| Market Breadth | `market_breadth_engine.py` | `/api/morning-brief/breadth` | ✅ Live | A/D ratio, McClellan, breadth thrust from S&P 100 |
| Overnight Gaps | `synthetic_estimator.py` | `/api/overnight-returns` | ✅ Live | 14 indices, VIX-implied gap estimation, z-score outliers |
| Sector Performance | `yfinance_service.py` | `/api/morning-brief/sectors` | ✅ Live | 11 sector ETFs, multi-period (1D/5D/1M/3M) |
| Sector RRG | `rrg_calculator.py` | `/api/rrg` | ✅ Live | Relative strength + momentum quadrant chart |
| Factor Decomposition | `factor_calculator.py` | `/api/factors/{ticker}` | ✅ Live | Beta, size, value, momentum for each sector ETF |
| News Sentiment | `sentiment_velocity.py` | `/api/sentiment-velocity` | ✅ Live | Market-data-derived scoring (fast path), VIX/price-based |
| Options Flow | `options_flow.py` | `/api/options-flow` | ✅ Live | IV skew, put/call ratio, GEX, vol imbalance |
| COT Positioning | `cot_positioning.py` | `/api/cot-positioning` | ✅ Live | Commercial/speculative positioning, reversal alerts |
| Stress Scenarios | `scenario_risk.py` | `/api/scenario-risk` | ✅ Live | VIX spike, yield steepen, correction impact estimates |
| Momentum Spillover | `cross_asset_momentum.py` | `/api/momentum-spillover` | ✅ Live | Cross-asset 1M/3M momentum with signal classification |
| Market Drivers | `claude_service.py` | `/api/morning-brief/drivers` | ✅ Live | AI-generated market drivers via Claude + web search |
| Earnings Brief | `earnings_brief.py` | `/api/earnings-brief` | ✅ Live | Upcoming earnings with expected moves |
| Sector Transitions | `sector_transitions.py` | `/api/sector-transitions` | ✅ Live | Business cycle positioning, favorable/unfavorable sectors |
| Morning Report | `claude_service.py` | (generated client-side) | ✅ Live | AI-generated summary from all panel data |

### Known Constraints
- Railway 30s proxy timeout — all `/all` sub-calls must finish within 4-8s each
- RSS feeds blocked from Railway cloud IPs — sentiment uses market-data-derived scoring instead
- Fast-path functions (`_fast()` variants) accept pre-fetched macro data to avoid redundant API calls
- Overnight gaps use synthetic VIX-based estimation (not live pre-market data)

---

## Stock Screener
**Status:** ✅ Live | **Route:** `/screener` | **Backend:** `/api/screener/*`, `/api/stock/*`

| Component | Status | Notes |
|-----------|--------|-------|
| Ticker search | ✅ Live | Debounced search with dropdown |
| AI stock grading | ✅ Live | Claude-powered A-F grading with metrics, risks, catalysts |
| Watchlist | ✅ Live | CRUD with cached grades |
| Quantitative screener | ✅ Live | Value + momentum screening |

---

## Weekly Market Report
**Status:** ✅ Live | **Route:** `/weekly-report` | **Backend:** `/api/weekly-report/*`

| Component | Status | Notes |
|-----------|--------|-------|
| Report generation | ✅ Live | SSE streaming via Claude + web search |
| Report viewer | ✅ Live | Collapsible sections |
| Report history | ✅ Live | Past reports with delete |

---

## Virtual Portfolio
**Status:** ✅ Live | **Route:** `/portfolio` | **Backend:** `/api/portfolio/*`

| Component | Status | Notes |
|-----------|--------|-------|
| Portfolio builder | ✅ Live | Create/edit with holdings management |
| Correlation heatmap | ✅ Live | Plotly heatmap |
| Portfolio optimization | ✅ Live | Max Sharpe vs min variance |
| Monte Carlo simulation | ✅ Live | Percentile band visualization |

---

## Relative Rotation Graph
**Status:** ✅ Live | **Route:** `/rrg` | **Backend:** `/api/rrg`

| Component | Status | Notes |
|-----------|--------|-------|
| RRG chart | ✅ Live | Four-quadrant scatter with animated tails |
| Benchmark selector | ✅ Live | SPY/QQQ/IWM/DIA + custom |
| Period selector | ✅ Live | 3M/6M/1Y/2Y |

---

## Earnings Dashboard
**Status:** ✅ Live | **Route:** `/earnings` | **Backend:** `/api/earnings/*`

| Component | Status | Notes |
|-----------|--------|-------|
| Earnings calendar | ✅ Live | Upcoming earnings dates |
| PEAD analysis | ✅ Live | Post-earnings announcement drift |
| Earnings confluence | ✅ Live | Multi-signal earnings analysis |

---

## Confluence Signals
**Status:** ✅ Live | **Route:** `/confluence` | **Backend:** `/api/confluence/*`

| Component | Status | Notes |
|-----------|--------|-------|
| Signal confluence | ✅ Live | Multi-factor signal detection |
| Confluence backtester | ✅ Live | Historical signal performance |

---

## Sentiment Analysis
**Status:** ✅ Live | **Route:** `/sentiment` | **Backend:** `/api/sentiment/*`

| Component | Status | Notes |
|-----------|--------|-------|
| Sentiment dashboard | ✅ Live | Dedicated sentiment page |
| News ingestion | ✅ Live | RSS feed aggregation (limited by cloud IP blocks) |

---

## Events & Catalysts
**Status:** ✅ Live | **Route:** `/events` | **Backend:** `/api/events/*`

| Component | Status | Notes |
|-----------|--------|-------|
| Event tracker | ✅ Live | Event polling and processing |
| Catalyst identification | ✅ Live | AI-driven catalyst detection |

---

## Backtester
**Status:** ✅ Live | **Route:** `/backtester` | **Backend:** `/api/backtest/*`

| Component | Status | Notes |
|-----------|--------|-------|
| Strategy backtester | ✅ Live | Historical strategy testing |
| Quick backtest | ✅ Live | Simplified one-click backtests |

---

## Correlation Matrix
**Status:** ✅ Live | **Route:** `/correlation` | **Backend:** `/api/correlation/*`

| Component | Status | Notes |
|-----------|--------|-------|
| Correlation analysis | ✅ Live | Cross-asset correlation visualization |

---

## Phase 2 Backlog
Items identified but not yet started:

| Item | Priority | Notes |
|------|----------|-------|
| Sector chart timeframe selector in Morning Brief | Medium | Currently hardcoded to 1D |
| Market drivers overhaul | Medium | Improve AI-generated driver quality |
| Factor decomposition labels | Low | Better label formatting |
| Live pre-market data for overnight gaps | Low | Replace synthetic estimation |
| FinBERT sentiment scoring | Low | Replace market-data-derived sentiment when RSS accessible |
