# AlphaDesk Frontend — Quick Start

## Live App
**https://alpha-desk-rho.vercel.app** — deployed automatically from `main` branch.

## Local Development

### 1. Install dependencies
```bash
cd frontend && npm install
```

### 2. Start the dev server
```bash
npm run dev
# → http://localhost:5173
```
The dev server proxies `/api/*` to `http://localhost:8000`. Make sure the backend is running.

### 3. Build for production
```bash
npm run build    # Output in dist/
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

## Pages & Routes

| Route | Feature | Description |
|-------|---------|-------------|
| `/morning-brief` | Morning Brief | 16-panel real-time market dashboard |
| `/screener` | Stock Screener | Ticker search, AI grading, watchlist, screening |
| `/weekly-report` | Weekly Report | AI-generated market analysis with SSE streaming |
| `/portfolio` | Portfolio | Builder, correlation heatmap, optimization, Monte Carlo |
| `/rrg` | RRG | Relative Rotation Graph with animated sector tails |
| `/earnings` | Earnings | Calendar, PEAD analysis, earnings confluence |
| `/confluence` | Confluence | Multi-factor signal detection + backtesting |
| `/events` | Events | Event tracking and catalyst identification |
| `/sentiment` | Sentiment | Dedicated sentiment analysis page |
| `/backtester` | Backtester | Strategy backtesting engine |
| `/correlation` | Correlation | Cross-asset correlation matrix |

## Troubleshooting

**API calls failing locally?**
Ensure backend is running on `http://localhost:8000`. Check DevTools Network tab.

**Styles not appearing?**
Run `npm install`, clear browser cache.

**Build errors?**
Delete `node_modules` and `package-lock.json`, then `npm install` again.

**Morning Brief panels showing empty?**
The `/all` endpoint may have timed out on some panels. Check the backend logs on Railway. Individual panels fail gracefully — empty panels don't crash the page.

## Key Files to Know
- `src/lib/api.ts` — All API functions + pre-cache system
- `src/hooks/usePrefetchMorningBrief.ts` — Triggers the `/all` fetch and seeds cache
- `src/pages/MorningBrief.tsx` — Main dashboard page layout
- `src/components/morning-brief/` — All 16 panel components
- `vercel.json` — Production API proxy configuration
