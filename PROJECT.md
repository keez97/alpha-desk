# AlphaDesk — Investment Dashboard

## Purpose
Investment dashboard for a sophisticated individual investor. Deployed on Railway (backend) and Vercel (frontend). Pulls live data from a multi-tier data pipeline (yfinance → FRED → financialdatasets.ai), with AI-powered analysis via Claude (OpenRouter) and synthetic estimation fallbacks when live sources are unavailable.

## Live URLs
- **Frontend:** https://alpha-desk-rho.vercel.app
- **Backend API:** https://web-production-39e24.up.railway.app
- **Repository:** https://github.com/keez97/alpha-desk

## User Personas
- **Primary:** Individual investor with institutional-grade analytical needs. Wants morning market pulse, weekly deep-dive reports, stock screening with AI grading, portfolio optimization, and sector rotation visualization.

## Tech Stack
| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | Python 3.11+, FastAPI, uvicorn | Async-first, excellent for data pipelines |
| Data (Tier 1) | financialdatasets.ai (FDS) | Institutional-grade financial data |
| Data (Tier 2) | FRED (Federal Reserve) | Free macro indicators, VIX, yield data |
| Data (Tier 3) | yfinance | Free real-time quotes, price history, options |
| Data (Tier 4) | Synthetic estimator | VIX/FRED-based estimation when all live sources fail |
| Data (Other) | Stooq, CBOE, CNN Fear & Greed | International indices, VIX term structure, sentiment |
| Computation | pandas, numpy, scipy | Industry-standard for financial math |
| AI | Claude Sonnet 4 via OpenRouter | Web search capability for live market analysis |
| Caching | In-memory TTLCache (backend), React Query pre-cache (frontend) | Fast response times, no DB overhead |
| Database | SQLite via SQLModel | Persistence for reports, watchlists, portfolios |
| Frontend | React 19, TypeScript, Vite | Fast dev experience, type safety |
| State | Zustand + React Query (TanStack) | Minimal boilerplate, excellent caching |
| Charts | Recharts + Plotly.js | Recharts for simple charts, Plotly for RRG/heatmaps |
| Animation | Framer Motion | RRG animated tails |
| Styling | Tailwind CSS v4 | Utility-first, design token friendly |
| Hosting | Railway (backend), Vercel (frontend) | Auto-deploy from main branch |

## Features
| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 1 | Morning Brief | ✅ Live | 16-panel dashboard: regime, VIX term structure, breadth, overnight gaps, sectors, RRG, factor decomposition, sentiment velocity, options flow, COT positioning, stress scenarios, momentum spillover, market drivers, earnings brief, sector transitions, morning report |
| 2 | Stock Screener | ✅ Live | Ticker search, AI grading, watchlist, quantitative screening |
| 3 | Weekly Market Report | ✅ Live | AI-generated weekly report with SSE streaming |
| 4 | Virtual Portfolio | ✅ Live | Portfolio builder, correlation heatmap, optimization, Monte Carlo |
| 5 | Relative Rotation Graph | ✅ Live | Four-quadrant RRG with animated tails, benchmark selector |
| 6 | Earnings Dashboard | ✅ Live | Earnings calendar, PEAD analysis, earnings confluence |
| 7 | Confluence Signals | ✅ Live | Multi-factor signal confluence with backtesting |
| 8 | Events & Catalysts | ✅ Live | Event tracking and catalyst identification |
| 9 | Sentiment Analysis | ✅ Live | Dedicated sentiment page with news ingestion |
| 10 | Backtester | ✅ Live | Strategy backtesting engine |
| 11 | Correlation Matrix | ✅ Live | Cross-asset correlation analysis |

## API Integrations
- **Yahoo Finance (yfinance):** No API key. Price history, real-time quotes, sector ETFs, options data.
- **FRED (Federal Reserve):** API key in `.env` (`FRED_API_KEY`). VIX, yield curve, macro indicators.
- **financialdatasets.ai:** API key in `.env` (`FDS_API_KEY`). Income statements, balance sheets, cash flow, institutional ownership.
- **OpenRouter → Claude:** API key in `.env` (`OPENROUTER_API_KEY`). Model: `claude-sonnet-4`. Web search tool for market drivers, weekly reports, stock grading.
- **Stooq:** No API key. International index data (DAX, FTSE, Nikkei, Hang Seng).
- **CBOE:** No API key. VIX term structure futures data.
- **CNN Fear & Greed:** No API key. Market sentiment indicator.

## Key Architectural Patterns

### Multi-Tier Data Pipeline
Every data fetch follows a cascade: FDS → FRED → yfinance → synthetic estimation. If a higher-tier source fails or times out, the next tier is tried. The synthetic estimator uses VIX-implied volatility and FRED macro data to generate directionally accurate estimates with zero external API calls.

### /all Aggregate Endpoint
The Morning Brief frontend loads via a single `GET /api/morning-brief/all` call that fetches all 16 panels in batched `asyncio.gather()` calls. Each sub-call is wrapped in a `safe()` helper with per-call timeouts (4-8s). Results are pre-cached in the frontend so individual panel hooks hit the cache instead of making separate API calls.

### Fast-Path Functions
For the `/all` endpoint, several services have `_fast()` variants that accept pre-fetched macro data as a parameter instead of making their own network calls. This eliminates redundant fetches and keeps the total response time under Railway's 30-second proxy timeout.

### Synthetic Estimation
When live data sources are unavailable (RSS feeds blocked from Railway cloud IPs, API timeouts, rate limits), the synthetic estimator generates market-data-derived values using VIX regime, yield curve shape, and FRED macro indicators.

## Environment Variables
```
OPENROUTER_API_KEY=    # Required for AI features (market drivers, reports, grading)
FDS_API_KEY=           # Optional, financial statements (tier 1 data)
FRED_API_KEY=          # Optional, macro indicators (tier 2 data)
```

## Local Setup
```bash
# 1. Clone and install
git clone https://github.com/keez97/alpha-desk.git && cd alpha-desk
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run locally
npm run dev
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
```

## Deployment
Both services auto-deploy from the `main` branch:
- **Backend (Railway):** Detects `requirements.txt`, runs uvicorn. 30-second proxy timeout limit.
- **Frontend (Vercel):** Builds React app, proxies `/api/*` to Railway backend URL.
