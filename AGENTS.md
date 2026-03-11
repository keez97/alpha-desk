# AlphaDesk — Contributor Guide

> This document is for any developer or AI agent working on the AlphaDesk codebase. It describes the actual development workflow, codebase organization, deployment constraints, and patterns you must follow.

## Development Workflow

### How Work Gets Done
- All development happens on the `main` branch with direct commits
- Both Railway (backend) and Vercel (frontend) auto-deploy from `main`
- There is no PR review process currently — test locally or verify via the deployed API after push
- Railway builds take 1-3 minutes; Vercel builds are near-instant

### Push Protocol
The repository lives at `/Users/karimatari/alpha-desk` on the local Mac. When working in a VM or remote environment where the folder is mounted:
```bash
# Commit via osascript (when in VM with mounted folder)
osascript -e 'do shell script "cd /Users/karimatari/alpha-desk && git add <files> && git commit -m \"message\""'
# Push
osascript -e 'do shell script "cd /Users/karimatari/alpha-desk && git push origin main 2>&1"'
```

### Documentation Update Rule
**Every commit that adds, modifies, or removes a feature, endpoint, service, or component MUST include corresponding updates to:**
1. `TASK_MANIFEST.md` — update the relevant feature's panel/component table
2. `project.md` — if a new feature, data source, or env var is added
3. `.context/` files — if architecture, data sources, or UI components change

Failure to keep docs in sync makes the codebase harder to navigate for future agents.

---

## Codebase Organization

### File Ownership
| Directory | Contains |
|-----------|----------|
| `backend/services/` | Business logic — data fetching, computation, AI calls (59 service files) |
| `backend/routers/` | FastAPI route handlers (35 router files) |
| `backend/config.py` | Environment variables, model config, cache TTLs |
| `frontend/src/pages/` | Full page views (11 pages) |
| `frontend/src/components/` | UI components organized by feature (14 directories) |
| `frontend/src/hooks/` | React Query hooks for data fetching (38 hooks) |
| `frontend/src/lib/api.ts` | Axios client, typed fetch functions, pre-cache system |
| `frontend/src/lib/utils.ts` | Formatting utilities |
| `frontend/src/stores/` | Zustand state stores |
| `*.md`, `.context/` | Project documentation |

### Backend Service Naming
- `*_service.py` — external API wrappers (yfinance, FRED, FDS, Claude)
- `*_engine.py` — computation engines (breadth, confluence, backtest, etc.)
- `*_calculator.py` — pure math functions (RRG, factors, statistics)
- `synthetic_estimator.py` — VIX/FRED-based fallback estimation
- `data_provider.py` — three-tier data facade (FDS → FRED → yfinance)
- `cache.py` — in-memory TTLCache implementation

### Frontend Conventions
- One hook per backend endpoint (e.g., `useOvernightReturns.ts` → `/api/overnight-returns`)
- One panel component per Morning Brief section (e.g., `OvernightPanel.tsx`)
- All API functions in `lib/api.ts` with TypeScript interfaces
- Pre-cache system: `/all` response seeds individual endpoint caches via `seedApiCache()`

---

## Deployment Constraints

### Railway Backend
| Constraint | Value | Impact |
|-----------|-------|--------|
| Proxy timeout | 30 seconds | `/all` must complete within 30s total |
| Per-call timeout in `/all` | 4-8 seconds | Each `safe()` wrapped sub-call |
| Cloud IP blocking | RSS feeds, some financial sites | Cannot fetch RSS from MarketWatch, CNBC, Yahoo Finance RSS |
| Memory | Limited (free/hobby tier) | Avoid loading large datasets into memory |
| Cold start | ~10-15 seconds | First request after idle may be slow |

### Vercel Frontend
| Constraint | Value | Impact |
|-----------|-------|--------|
| API proxy | Routes `/api/*` to Railway URL | Set in `vercel.json` rewrites |
| Build size | ~5.6MB JS (Plotly.js) | Consider dynamic imports for optimization |
| No server-side | Static SPA only | All data fetching via client-side React Query |

### Critical Rule: The 30-Second Budget
The `/api/morning-brief/all` endpoint fetches all 16 panels in 3 batches:
- **Batch 1** (3 concurrent): macro, breadth, VIX term structure → then regime (depends on macro)
- **Batch 2** (4 concurrent): sectors, sector perf, transitions, RRG
- **Batch 3+4** (7 concurrent): sentiment, options, earnings, overnight, positioning, scenario risk, spillover

Each call is wrapped in `safe(name, fn, *args, timeout_s=N)` which returns `None` on timeout. The total wall-clock time must stay under 30 seconds.

**When adding a new panel to `/all`:**
1. Create a `_fast()` variant of the service function that accepts pre-fetched `macro_data`
2. The `_fast()` function must make zero network calls — use only the data passed to it
3. Add it to the appropriate batch in `morning_brief.py`
4. Wrap it in `safe()` with a 4s timeout
5. Match the response shape expected by the frontend's `fetchXxx()` function in `api.ts`

---

## Key Patterns

### Multi-Tier Data Cascade
```
FDS (financialdatasets.ai) → FRED → yfinance → synthetic estimation
```
The `data_provider.py` facade tries each tier in order. Most services use `yfinance_service.py` directly for real-time data, and `fred_service.py` for macro indicators. The synthetic estimator (`synthetic_estimator.py`) provides VIX-implied estimates when all live sources fail.

### Fast-Path Pattern
For the `/all` endpoint, slow services have `_fast()` variants:
- `get_sentiment_velocity_fast(macro_data)` — generates sentiment from VIX + price action, no RSS
- `get_scenario_risk_fast(macro_data)` — computes scenarios from macro data, no price history fetch
- `synthetic_estimator.estimate_overnight_returns(tickers)` — VIX-implied gaps, no market data API

These accept pre-fetched macro data from Batch 1 so they make zero network calls.

### Pre-Cache System (Frontend)
The frontend makes one call to `/api/morning-brief/all`, then seeds a pre-cache map:
```typescript
// In api.ts — seedApiCache()
'/sentiment-velocity' → allData.sentiment_velocity
'/scenario-risk'      → allData.scenario_risk
'/overnight-returns'  → allData.overnight_returns
// ... etc
```
When individual hooks call `api.get('/sentiment-velocity')`, they hit the pre-cache first. This avoids 16 separate API calls on page load.

**Important:** The pre-cache returns `{ data: cached }`, so the frontend `fetchXxx()` function receives `raw = cached_data`. If the standalone endpoint wraps data in `{ data: ... }` but the `/all` response doesn't, the frontend will fail silently. Always match the response shape.

### Synthetic Estimation
When live data is unavailable:
- **Overnight gaps:** VIX-implied volatility → daily vol → overnight gap with beta scaling and cross-sectional dispersion
- **Sentiment:** VIX level + SPY/QQQ price action → aggregate score + synthetic headlines
- **Scenarios:** Pre-fetched macro data → hardcoded stress scenarios with VIX-adjusted descriptions
- **Momentum spillover:** FRED macro indicators → cross-asset momentum estimates

---

## Common Pitfalls

1. **Changing imports in sentiment_velocity.py** — commit `ef967e6` broke `/all` by changing internal imports to use `data_provider.get_macro_data()`. The exact cause is unclear but likely related to thread interactions. Stick with `yfinance_service` imports or avoid network calls entirely via `_fast()` functions.

2. **Response shape mismatches** — The standalone `/api/overnight-returns` endpoint wraps data in `{ data: { indices, summary } }`, but the service function returns `{ indices, summary }` at top level. The `/all` endpoint must wrap it to match: `"overnight_returns": {"timestamp": ts, "data": overnight_raw}`.

3. **Railway timeouts** — Any service that makes network calls and takes >4s will return `None` from `safe()`. The frontend handles this gracefully (shows empty panel), but it means data is missing. Always prefer `_fast()` variants in `/all`.

4. **RSS feeds from cloud IPs** — MarketWatch, CNBC, Yahoo Finance RSS feeds are blocked when fetched from Railway's cloud IP range. User-Agent changes don't help. The workaround is synthetic headline generation from market data.

5. **Cache TTL interactions** — Backend services have their own in-memory TTL caches (typically 5-30 min). The frontend React Query has separate stale times (typically 30 min). Don't assume one cache invalidation affects the other.

---

## Escalation Guide

| Issue | Where to look |
|-------|--------------|
| Panel empty in Morning Brief | Check `safe()` timeout in `morning_brief.py`, check Railway logs for the service |
| API 502 Bad Gateway | Railway build failed or proxy timeout — check Railway dashboard |
| Frontend not updating after deploy | Vercel may be serving cached build — check deployment status |
| Data looks stale | Check backend TTL cache in the service file, frontend staleTime in the hook |
| New panel not showing | Verify: router registered in `main.py`, pre-cache mapping in `api.ts`, hook created, component added to page |
