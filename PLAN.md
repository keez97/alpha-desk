# AlphaDesk Fix & Enhancement Plan

## Current State
The Morning Brief is working with real data-driven analysis (smart_analysis.py), but most other pages have network errors, crashes, or empty states. The platform needs to go from "technically running" to "actually useful."

---

## Phase 1: Fix All Crashes & Network Errors (Priority: Critical)

These are the showstoppers — pages that can't even load.

### 1.1 Backtester Crash — "backtests.map is not a function"
**Root cause:** Backend returns `{ backtests: [...], total: 0, limit: 50 }` but the frontend calls `.map()` directly on the response object instead of `.backtests`.
**Fix:** Update the frontend hook to unwrap `response.data.backtests` (or `response.data.backtests || []`). One-line fix.

### 1.2 RRG Graph — "Network Error"
**Root cause:** `calculate_rrg()` calls `get_history()` for each sector ETF + SPY benchmark. If yfinance is slow or rate-limited, the request times out (>30s). No try/except wrapper on the router endpoint.
**Fix:** Wrap the endpoint in try/except, add a timeout, and return cached/fallback RRG positions when live data fails. The enhanced_sectors quadrant inference logic already exists — reuse it.

### 1.3 Portfolio — "Network Error"
**Root cause:** The `/api/portfolios/analysis` endpoint crashes when `get_history()` returns empty data (tries `min()` on empty sequence). Also no try/except on the main endpoints.
**Fix:** Add defensive checks for empty data, wrap all endpoints in try/except, return meaningful error responses instead of 500s.

### 1.4 Weekly Report — Fails to Generate
**Root cause:** The endpoint uses SSE streaming that depends on OpenRouter. When the LLM call fails, the fallback mock data isn't formatted as SSE events — it's raw JSON that the frontend's EventSource can't parse.
**Fix:** Build a data-driven weekly report generator (like smart_analysis.py for morning brief) that returns proper SSE-formatted sections. No LLM dependency.

---

## Phase 2: Make Empty Pages Functional (Priority: High)

Pages that load but show nothing useful.

### 2.1 Event Scanner — Returns Nothing for Any Search
**Root cause:** Events depend on a background polling service that was never started, so the events table is empty. The search endpoint queries an empty database.
**Fix:** Build a lightweight event fetcher that pulls upcoming earnings dates, ex-dividend dates, and economic calendar data from yfinance/FRED on-demand (not background polling). Return real upcoming events for searched tickers.

### 2.2 Earnings Surprise Predictor — Empty
**Root cause:** Similar to events — the earnings data tables are empty. Services like `SmartEstimateEngine` and `PEADAnalyzer` need historical earnings data that was never ingested.
**Fix:** Build a yfinance-based earnings data fetcher that pulls actual vs. estimated EPS, calculates surprise %, and shows the last 4-8 quarters. Add PEAD (post-earnings announcement drift) analysis using price history around earnings dates.

### 2.3 Screener — Watchlist Side Network Error
**Root cause:** The watchlist fetch fails because the watchlist table might be empty or the endpoint has an unhandled error. The screener results side works (shows mock graded stocks) but the watchlist sidebar crashes.
**Fix:** Ensure the watchlist endpoint returns `[]` gracefully when empty (not an error), and add a clear "Add stocks to your watchlist" empty state in the UI.

---

## Phase 3: Deepen Analysis Quality (Priority: High)

Making features that "work" actually provide useful, actionable insights.

### 3.1 Morning Brief — Make It Deeper & More Actionable
**Current state:** Shows 5 data-driven drivers and a 4-section report. User says it's not deep enough.
**Enhancement plan:**
- Add specific trade ideas derived from sector rotation (e.g., "XLE breaking into Leading quadrant — consider energy overweight")
- Add key levels: SPY support/resistance from recent price action
- Add a "Risk Dashboard" section with VIX percentile, yield curve slope, credit spreads
- Add sector-level detail: top 3 and bottom 3 sectors with ETF tickers and % moves
- Make the narrative more opinionated — instead of "Technology sector is up 1.2%," say "Tech continues momentum — 3rd consecutive positive session, now +4.2% WTD"

### 3.2 Confluence Backtest — Make It Actually Useful
**Current state:** Shows generic backtest results without per-security or per-signal context.
**Enhancement plan:**
- Show which specific signals triggered for each security
- Add a signal agreement heatmap: rows = tickers, columns = signals, cells = bull/bear/neutral
- Add historical win rate per signal combination
- Show clear "High Confluence" vs "Low Confluence" classification with actionable labels

### 3.3 Stock Grading — Expand Beyond 3 Hardcoded Tickers
**Current state:** `_generate_ticker_aware_grade()` only has templates for AAPL, MSFT, NVDA. Everything else gets a generic HOLD.
**Fix:** Build a quantitative grading engine using real data: momentum score (price vs. 50/200 DMA), value score (P/E percentile), quality score (ROE, debt/equity from yfinance), and volatility score (realized vol vs. VIX). Generate letter grades from composite scores.

### 3.4 Sentiment Page — Data-Driven Sentiment
**Enhancement:** Instead of depending on news API, build a market-implied sentiment score from: put/call ratio trends, VIX term structure, sector fund flows (via ETF volume), and price-breadth divergences.

---

## Phase 4: UX Clarity & Polish (Priority: Medium)

### 4.1 Error States
- Replace all "Network Error" messages with specific, helpful messages ("Market data temporarily unavailable — showing last cached data" or "No earnings data found for AAPL — try a different ticker")
- Add retry buttons on all error states
- Show stale cached data with a "Last updated: X ago" badge instead of showing nothing

### 4.2 Loading States
- Fix the "Loading enhanced sectors..." infinite spinner — add a timeout that falls back to basic sector data
- Add skeleton loaders instead of blank screens

### 4.3 Empty States
- Events page: Show "Search for a ticker to see upcoming events" instead of blank
- Earnings page: Show "Enter a ticker to see earnings history and predictions"
- Backtester: Show "No backtests yet — create your first strategy" with a CTA

### 4.4 Data Freshness Indicators
- Add timestamps to every data card showing when data was last fetched
- Show a global "Market Status: Open/Closed" indicator
- Color-code staleness: green (<5 min), yellow (5-30 min), red (>30 min)

---

## Execution Order

| Step | What | Files Touched | Est. Effort |
|------|------|---------------|-------------|
| 1 | Fix backtester .map crash | 1 frontend file | 5 min |
| 2 | Fix RRG network error | 1 backend router | 15 min |
| 3 | Fix Portfolio network error | 1 backend router | 15 min |
| 4 | Fix Weekly Report (data-driven) | 2 backend files | 30 min |
| 5 | Fix Screener watchlist error | 1 backend + 1 frontend | 15 min |
| 6 | Build Events data fetcher | 1 new service + 1 router | 30 min |
| 7 | Build Earnings data fetcher | 1 new service + 1 router | 30 min |
| 8 | Quantitative stock grader | 1 backend service | 30 min |
| 9 | Deepen Morning Brief | 1 backend service | 20 min |
| 10 | Confluence signal detail | 1 backend + 1 frontend | 20 min |
| 11 | UX error/empty/loading states | Multiple frontend files | 30 min |

**Total estimated: ~4 hours of implementation**

---

## Key Principle

Every feature should work without any external LLM dependency. All analysis is data-driven using real market data from yfinance/FRED. The platform should be useful even if OpenRouter is completely offline — that's the "AI angle" handled internally through quantitative analysis rather than language model calls.
