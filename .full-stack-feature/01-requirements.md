# Requirements: Factor Backtester (AlphaDesk V2 Phase 1)

## Problem Statement

AlphaDesk currently provides a stock screener with regime-adaptive grading, but users have no way to validate whether the factors driving those grades (value, momentum, quality, etc.) actually generate alpha historically. Without backtesting, users must trust signals on faith. The Factor Backtester solves this by providing a research-grade platform to both validate existing screener signals AND design custom multi-factor strategies with proper bias controls — functioning as a mini FactSet for individual and small-team investors.

Primary user: self-directed investor or small fund analyst who wants institutional-quality factor research without Bloomberg/FactSet pricing.

## Acceptance Criteria

- [ ] Users can select from pre-built Fama-French 5-factor library (MKT-RF, SMB, HML, RMW, CMA)
- [ ] Users can define custom factors from fundamental data (e.g., FCF yield, earnings yield)
- [ ] Users can set factor weights manually (sliders summing to 100%) or use equal-weight
- [ ] Walk-forward backtesting protocol: at each rebalance date, only data available up to that date is used
- [ ] Point-in-Time (PiT) enforcement at the database level — no look-ahead bias
- [ ] Survivorship-bias-free universe: includes delisted/acquired/bankrupt securities with full history
- [ ] Configurable transaction cost modeling (slippage, commissions)
- [ ] Configurable rebalance frequencies: monthly, quarterly, custom
- [ ] Equity curve chart: strategy vs benchmark cumulative returns with drawdown overlay
- [ ] Full statistical output: Sharpe, Sortino, Calmar, Max Drawdown, Information Ratio, Hit Rate, Turnover
- [ ] Rolling factor exposure chart showing time-varying betas to FF5 factors
- [ ] Pre/post-publication performance split with ~50% decay warning (per Dec 2025 alpha decay paper)
- [ ] Factor correlation matrix for multi-factor model construction
- [ ] Results exportable (JSON at minimum)
- [ ] Factor scores integrated as sortable/filterable columns in the existing Stock Screener
- [ ] Shared PiT data infrastructure designed to support future Event Scanner, Earnings Predictor, and Sentiment features

## Scope

### In Scope

- Fama-French 5-factor model implementation (standard double-sort methodology)
- Custom factor definition engine (any numeric function of fundamentals)
- Walk-forward backtesting with rolling-window factor regressions (60-month default)
- Quantile portfolio construction (quintile or decile, long-only or long-short)
- Transaction cost modeling (configurable slippage, default 10bps)
- Institutional-grade statistical output (12+ metrics)
- PostgreSQL migration for the data layer
- PiT database enforcement (ingestion_timestamp on all rows)
- Survivorship-bias-free universe tracking
- Kenneth French Data Library integration for factor returns
- Frontend: new /backtester page with sidebar config + results area
- Screener integration: factor scores as new columns
- Shared data infrastructure for Phases 2-4

### Out of Scope

- Live/paper trading or broker integration
- Automated order execution
- Real-time streaming data (batch processing only)
- Options or fixed income backtesting (equities only)
- Multi-asset factor models

## Technical Constraints

- **Database upgrade**: Migrate from SQLite to PostgreSQL for concurrent writes, better query performance, and PiT data volume
- **Existing stack**: FastAPI (Python) backend, React 18 + TypeScript + Vite frontend, TanStack React Query
- **Data source**: yfinance (already integrated) for price history; Kenneth French Data Library (free CSV) for factor returns; SEC EDGAR for fundamentals snapshots
- **Styling**: Pure black Tailwind CSS theme (just completed UI overhaul); text-xs/text-[10px] compact institutional aesthetic
- **AI integration**: OpenRouter (multi-model) already wired; stock grader already uses regime-adaptive weights
- **API conventions**: RESTful, JSON responses, /api/ prefix, FastAPI router pattern
- **Frontend patterns**: Recharts for line charts, Canvas for RRG-style charts, neutral-800 borders, compact p-4 layouts

## Technology Stack

- **Frontend**: React 18 + TypeScript + Vite, Tailwind CSS v4, TanStack React Query, Recharts + Canvas
- **Backend**: FastAPI (Python 3.14), SQLModel ORM, Pydantic schemas
- **Database**: PostgreSQL (upgrading from SQLite) with Alembic migrations
- **Data sources**: yfinance, Kenneth French Data Library, SEC EDGAR
- **Infrastructure**: localhost development, git via GitHub (keez97/alpha-desk)

## Dependencies

- **Affects existing Screener**: Factor scores become new sortable columns in screener results
- **Affects existing Morning Brief**: Top factor signals could surface in morning brief panels
- **Foundation for Phase 2 (Event Scanner)**: Shared PiT data infrastructure, event signals become backtestable factors
- **Foundation for Phase 3 (Earnings Predictor)**: Shared analyst estimate storage with PiT enforcement
- **Foundation for Phase 4 (News Sentiment)**: Shared temporal data infrastructure

## Configuration

- Stack: fastapi-react-ts
- API Style: rest
- Complexity: complex

## Key Academic References

- Fama & French (1993, 2015): Three-factor and five-factor models
- Look-Ahead-Bench (arXiv, Jan 2026): LLM look-ahead bias in financial workflows
- Not All Factors Crowd Equally (arXiv, Dec 2025): Post-publication alpha decay (~50%)
- FactSet PiT White Paper: 15-25% Sharpe inflation without PiT data
- Quantified Strategies: 4x return inflation from excluding delistings
- CFA Institute Practitioner's Guide to Factor Models (1994)
- Ledoit & Wolf (2004): Improved covariance estimation
