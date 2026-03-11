# AlphaDesk Frontend — Build Summary

> **Last updated:** 2026-03-11

## Overview
React 19 + TypeScript + Vite frontend for the AlphaDesk investment dashboard. Dark theme, real-time market data, AI-driven insights, and advanced portfolio analysis. Deployed on Vercel with API proxy to Railway backend.

## Live URL
https://alpha-desk-rho.vercel.app

## Project Structure
```
frontend/
├── src/
│   ├── App.tsx                          # React Router + QueryClientProvider
│   ├── main.tsx                         # Entry point
│   ├── styles/
│   │   ├── globals.css                  # Tailwind imports and theme
│   │   └── tokens.ts                    # Color palette constants
│   ├── lib/
│   │   ├── api.ts                       # Axios client, typed fetch functions, pre-cache system
│   │   └── utils.ts                     # Formatting utilities
│   ├── stores/                          # Zustand state (watchlist, portfolio, ui)
│   ├── hooks/                           # 38 React Query hooks
│   ├── components/
│   │   ├── layout/                      # AppShell, TopNav, MacroBar
│   │   ├── shared/                      # DataTable, LoadingState, ErrorState, badges
│   │   ├── morning-brief/              # 16 panel components
│   │   ├── screener/                    # Search, grading, watchlist, results
│   │   ├── weekly-report/              # Generator, viewer, history
│   │   ├── portfolio/                   # Builder, heatmap, optimization, Monte Carlo
│   │   ├── rrg/                         # RRG chart, benchmark selector
│   │   ├── earnings/                    # Earnings calendar, PEAD
│   │   ├── confluence/                  # Signal confluence
│   │   ├── events/                      # Event tracking
│   │   ├── sentiment/                   # Sentiment dashboard
│   │   ├── backtester/                  # Strategy backtesting
│   │   ├── correlation/                 # Correlation matrix
│   │   └── settings/                    # Model selector
│   └── pages/                           # 11 page views
├── vite.config.ts                       # Vite + React + Tailwind + API proxy
├── vercel.json                          # Vercel deployment config with API rewrites
├── tsconfig.app.json                    # TypeScript strict mode
└── package.json                         # Dependencies
```

## Pages (11)
| Page | Route | Key Components |
|------|-------|---------------|
| Morning Brief | `/morning-brief` | 16 panels: regime, VIX, breadth, overnight, sectors, RRG, factors, sentiment, options, COT, scenarios, momentum, drivers, earnings, transitions, report |
| Screener | `/screener` | Search, grading, watchlist, quantitative screening |
| Weekly Report | `/weekly-report` | SSE streaming generation, viewer, history |
| Portfolio | `/portfolio` | Builder, correlation heatmap, optimization, Monte Carlo |
| RRG | `/rrg` | Four-quadrant rotation graph with animated tails |
| Earnings | `/earnings` | Calendar, PEAD analysis, confluence |
| Confluence | `/confluence` | Multi-factor signal detection + backtesting |
| Events | `/events` | Event tracker, catalysts |
| Sentiment | `/sentiment` | Dedicated sentiment analysis page |
| Backtester | `/backtester` | Strategy testing engine |
| Correlation | `/correlation` | Cross-asset correlation matrix |

## Key Architecture: Pre-Cache System
The Morning Brief uses a single `/api/morning-brief/all` call to fetch all panel data at once. The response is then distributed to individual hooks via a pre-cache:

```typescript
// api.ts — seedApiCache() maps /all fields to endpoint paths
'/sentiment-velocity' → allData.sentiment_velocity
'/scenario-risk'      → allData.scenario_risk
'/overnight-returns'  → allData.overnight_returns
// ... 16 total mappings

// api.get() interceptor checks pre-cache before HTTP
const cached = _preCache.get(pathOnly);
if (cached) return { data: cached };  // No network call
```

This means the 16 panels make 1 API call total, not 16.

## Dependencies
- **React 19**, react-dom, react-router-dom
- **@tanstack/react-query** — server state with stale-while-revalidate
- **zustand** — lightweight client state
- **axios** — HTTP client
- **recharts** — React charting (line, area, bar)
- **plotly.js + react-plotly.js** — advanced charts (RRG, heatmaps)
- **framer-motion** — animations
- **tailwindcss v4** — utility-first styling
- **vite** — build tool and dev server
- **typescript ~5.9** — strict mode

## Design System
- **Theme:** Dark (Bloomberg Terminal-inspired)
- **Background:** `#0f1117` → `#1a1d27` → `#252836`
- **Text:** `#e5e7eb` (primary), `#9ca3af` (secondary)
- **Accent:** Blue `#3b82f6`, Green `#10b981`, Red `#ef4444`, Amber `#f59e0b`
- **Font:** Inter (body), JetBrains Mono (numbers/code)
- **Numbers:** Right-aligned, monospaced, color-coded (green positive, red negative)

## API Configuration
- **Local dev:** Vite proxy `/api/*` → `http://localhost:8000`
- **Production:** Vercel rewrites `/api/*` → Railway backend URL

## File Counts
- **Pages:** 11
- **Components:** ~70+ across 14 directories
- **Hooks:** 38
- **Stores:** 3
- **Total TypeScript/React files:** ~100+
