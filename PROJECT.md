# AlphaDesk — Investment Dashboard

## Purpose
Local-first investment dashboard for a sophisticated individual investor. Architected for future SaaS expansion. Pulls live data from Yahoo Finance and financialdatasets.ai, with AI-powered analysis via Claude API.

## User Personas
- **Primary:** Individual investor with institutional-grade analytical needs. Wants morning market pulse, weekly deep-dive reports, stock screening with AI grading, portfolio optimization, and sector rotation visualization.

## Tech Stack
| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | Python 3.11+, FastAPI, uvicorn | Async-first, excellent for data pipelines |
| Data | yfinance, financialdatasets.ai | Free/affordable market data sources |
| Computation | pandas, numpy, scipy | Industry-standard for financial math |
| AI | Claude API (claude-sonnet-4-20250514) | Web search capability for live market analysis |
| Database | SQLite via SQLModel | Zero-config persistence, sufficient for single-user |
| Frontend | React 18, TypeScript, Vite | Fast dev experience, type safety |
| State | Zustand + React Query (TanStack) | Minimal boilerplate, excellent caching |
| Charts | Recharts + Plotly.js | Recharts for simple charts, Plotly for RRG |
| Animation | Framer Motion | RRG animated tails |
| Styling | Tailwind CSS | Utility-first, design token friendly |
| Dev Runner | concurrently | Single `npm run dev` for full stack |

## Features
| # | Feature | Status |
|---|---------|--------|
| 1 | Morning Brief | TODO |
| 2 | Weekly Market Report | TODO |
| 3 | Stock Screener | TODO |
| 4 | Virtual Portfolio Builder | TODO |
| 5 | Relative Rotation Graph | TODO |

## API Integrations
- **Yahoo Finance (yfinance):** No API key. Price history, real-time quotes, ticker search, short interest.
- **financialdatasets.ai:** API key in `.env`. Income statements, balance sheets, cash flow, earnings estimates, institutional ownership.
- **Claude API:** API key in `.env`. Model: claude-sonnet-4-20250514. Web search tool for market analysis.

## Local Setup
```bash
# 1. Clone and install
git clone <repo-url> && cd alpha-desk
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..

# 2. Configure environment
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# 3. Run
npm run dev
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
```
