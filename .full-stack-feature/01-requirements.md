# Requirements: Earnings Surprise Predictor (AlphaDesk V2 Phase 3)

## Problem Statement

Standard Wall Street consensus estimates (simple average of analyst forecasts) are a poor predictor of actual earnings. All analysts are weighted equally regardless of their track record, recency of estimate, or broker size. This means a stale estimate from 90 days ago by a historically inaccurate analyst carries the same weight as a fresh estimate from yesterday by a top-ranked analyst.

The Earnings Surprise Predictor implements a SmartEstimate methodology — a weighted analyst consensus that applies recency decay, accuracy-tier weighting, and broker-size adjustment. Research shows this approach achieves ~70% directional accuracy when the SmartEstimate diverges ≥2% from simple consensus. Combined with Post-Earnings Announcement Drift (PEAD) — the well-documented phenomenon where stock prices drift in the direction of earnings surprises for 60+ days (Bernard & Thomas 1989) — this creates a systematic alpha signal.

Primary user: investor who wants to know BEFORE earnings whether consensus is likely too high or too low, and how to position for the post-announcement drift.

## Acceptance Criteria

- [ ] SmartEstimate calculation: weighted consensus using recency decay (exponential, half-life ~30 days), analyst accuracy tier (based on historical hit rate), and broker size adjustment
- [ ] Consensus vs SmartEstimate divergence metric: flag stocks where divergence ≥2% (high-conviction signal)
- [ ] 70%+ directional accuracy target when divergence ≥2% (validated via backtesting)
- [ ] Upcoming earnings calendar: shows next earnings date, consensus EPS, SmartEstimate EPS, divergence %, directional signal
- [ ] Historical earnings surprise tracking: actual vs consensus vs SmartEstimate for past quarters
- [ ] PEAD drift visualization: cumulative abnormal return post-earnings for past surprises (0 to +60 days)
- [ ] Analyst scorecard: track individual analyst accuracy over time (for weighting)
- [ ] Pre-earnings signal generation: 1-5 days before earnings, generate buy/sell/hold signal based on SmartEstimate direction
- [ ] Integration with Factor Backtester: earnings surprise as a backtestable factor
- [ ] Integration with Screener: "Earnings Signal" column with divergence % and direction
- [ ] Integration with Event Scanner: earnings events feed into the event timeline
- [ ] PiT enforcement: analyst estimates timestamped at publication, not retroactively adjusted
- [ ] Free data sources only (yfinance analyst estimates, SEC EDGAR for actuals)

## Scope

### In Scope

- SmartEstimate engine: recency decay, accuracy tiers, broker size weighting
- Analyst estimate storage with PiT timestamps (when estimate was published)
- Analyst scorecard tracking (historical accuracy by analyst/broker)
- Earnings calendar dashboard showing upcoming earnings with signals
- Historical earnings surprise comparison (actual vs consensus vs SmartEstimate)
- PEAD drift chart (cumulative abnormal return post-earnings, 0-60 days)
- Pre-earnings directional signals (buy/sell/hold based on SmartEstimate)
- Backtester integration (earnings surprise as factor)
- Screener integration (earnings signal column)
- Event Scanner integration (earnings events)
- New /earnings page with earnings calendar + surprise analysis

### Out of Scope

- Paid analyst estimate APIs (Bloomberg, FactSet, Refinitiv)
- Revenue surprise prediction (EPS only for MVP)
- Whisper numbers or social media sentiment
- Options-based earnings strategies
- Intraday earnings reaction analysis
- Multi-quarter estimate revisions tracking

## Technical Constraints

- **Existing infrastructure**: PostgreSQL with PiT, SQLModel, Alembic, FastAPI, React 18 + TS + Vite
- **Data sources**: yfinance analyst estimates (free), SEC EDGAR for actuals, existing price_history for PEAD
- **Shared tables**: securities, price_history, factor_definitions, events (from Phase 2)
- **Styling**: Pure black Tailwind CSS theme, text-xs/text-[10px] compact institutional aesthetic
- **API conventions**: RESTful, /api/ prefix, FastAPI router pattern, BackgroundTasks for async
- **yfinance limitations**: Provides consensus EPS but limited individual analyst data. For MVP, derive accuracy tiers from consensus revision patterns rather than individual analyst tracking.

## Technology Stack

- Frontend: React 18 + TypeScript + Vite, Tailwind CSS v4, TanStack React Query, Recharts
- Backend: FastAPI, SQLModel ORM, Pydantic schemas, Alembic migrations
- Database: PostgreSQL (shared with Phases 1-2)
- Data sources: yfinance (analyst estimates, earnings dates), SEC EDGAR (actual EPS)
- Infrastructure: localhost development, git via GitHub

## Dependencies

- **Depends on Phase 1**: Factor Backtester for earnings surprise factor integration, PiT infrastructure, price_history for PEAD
- **Depends on Phase 2**: Event Scanner for earnings event detection (earnings dates already captured)
- **Affects Factor Backtester**: Earnings surprise becomes a backtestable factor
- **Affects Screener**: Earnings signal column
- **Affects Event Scanner**: Enriches earnings events with surprise magnitude
- **Foundation for Phase 4**: Earnings dates provide temporal anchors for news sentiment analysis

## Configuration

- Stack: fastapi-react-ts
- API Style: rest
- Complexity: complex

## Key Academic References

- Bernard & Thomas (1989): Post-Earnings Announcement Drift — prices drift 60+ days in surprise direction
- SmartEstimate methodology: Recency decay (exponential, ~30-day half-life), accuracy-weighted consensus
- FactSet research: SmartEstimate divergence ≥2% from consensus achieves ~70% directional accuracy
- Jegadeesh & Livnat (2006): Revenue and earnings surprises predict future returns
- Chan, Jegadeesh & Lakonishok (1996): Momentum and analyst estimate revisions
