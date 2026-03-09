# Requirements: Event Scanner (AlphaDesk V2 Phase 2)

## Problem Statement

Investors miss alpha-generating corporate events because they lack systematic event detection and classification. Events like SEC filings, earnings surprises, M&A announcements, insider transactions, and dividend changes create predictable short-term alpha windows (research shows alpha concentrates in the first month post-event, decaying ~50% thereafter). AlphaDesk's Factor Backtester provides factor-level research, but events — which are the discrete catalysts that drive factor returns — are invisible to users.

The Event Scanner solves this by providing a Complex Event Processing (CEP) system that automatically detects, classifies, and scores corporate events from free data sources, measures their historical alpha decay windows, and feeds event signals into the existing Factor Backtester as backtestable factors.

Primary user: self-directed investor or small fund analyst who wants real-time awareness of market-moving events with quantified alpha expectations.

## Acceptance Criteria

- [ ] Three-layer CEP architecture: Event Producers → Processing Engine → Event Consumers
- [ ] Event detection from SEC EDGAR RSS feeds (8-K, 10-K, 10-Q, SC 13D/G, Form 4)
- [ ] Event detection from yfinance calendar (earnings dates, ex-dividend dates)
- [ ] Event classification taxonomy: earnings, M&A, insider_trade, dividend_change, SEC_filing, management_change, guidance_revision, share_repurchase
- [ ] Event severity scoring (1-5 scale based on historical impact magnitude)
- [ ] Alpha decay tracking per event type: measure abnormal returns in windows [0, +1d], [0, +5d], [0, +21d], [0, +63d]
- [ ] Event timeline visualization: chronological feed showing events for watchlist/universe
- [ ] Event detail view: event metadata, historical alpha window chart, related securities
- [ ] Event-based factor generation: event signals become backtestable factors in Factor Backtester
- [ ] Screener integration: "Recent Events" column with severity badges
- [ ] PiT enforcement: events timestamped at detection time, not retroactively backdated
- [ ] Configurable alerts: user sets event type + severity threshold filters
- [ ] Event correlation analysis: which event types cluster together (e.g., insider buying before M&A)
- [ ] Historical event database: store all detected events with full metadata for backtesting
- [ ] Batch and near-real-time modes: scheduled polling (every 15 min) + manual refresh

## Scope

### In Scope

- SEC EDGAR RSS feed parsing (8-K, 10-K, 10-Q, insider filings, 13D/G)
- yfinance earnings calendar and dividend calendar integration
- Event classification engine (rule-based + keyword matching)
- Event severity scoring based on historical price impact analysis
- Alpha decay window measurement (abnormal returns post-event)
- CEP three-layer architecture (producers, processing engine, consumers)
- New /events page with timeline feed and event detail panels
- Integration with Factor Backtester (events as backtestable factors)
- Integration with Screener (event badges on stock rows)
- PiT-safe event storage using existing PostgreSQL infrastructure
- Background polling service (configurable interval, default 15 min)

### Out of Scope

- Paid data APIs (Polygon, Benzinga, Bloomberg)
- Natural language processing of filing text (that's Phase 4: News Sentiment)
- Real-time WebSocket streaming (batch polling only)
- Options-based event trading strategies
- Cross-asset event analysis (equities only)
- Automated trading or order generation

## Technical Constraints

- **Existing infrastructure**: PostgreSQL with PiT enforcement, SQLModel ORM, Alembic migrations (from Phase 1)
- **Existing stack**: FastAPI (Python) backend, React 18 + TypeScript + Vite frontend, TanStack React Query
- **Shared data layer**: Must use existing securities, price_history, and fundamentals_snapshot tables from Phase 1
- **Data sources**: SEC EDGAR RSS (free, no API key), yfinance (already integrated, free)
- **Styling**: Pure black Tailwind CSS theme, text-xs/text-[10px] compact institutional aesthetic
- **API conventions**: RESTful, JSON responses, /api/ prefix, FastAPI router pattern
- **Background tasks**: FastAPI BackgroundTasks (from Phase 1 pattern)
- **SEC EDGAR**: RSS feeds at https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=8-K&dateb=&owner=include&count=40&search_text=&action=getcompany — rate limit: 10 requests/sec with User-Agent header

## Technology Stack

- **Frontend**: React 18 + TypeScript + Vite, Tailwind CSS v4, TanStack React Query, Recharts
- **Backend**: FastAPI (Python), SQLModel ORM, Pydantic schemas, Alembic migrations
- **Database**: PostgreSQL (shared with Phase 1)
- **Data sources**: SEC EDGAR RSS, yfinance earnings/dividend calendars
- **Infrastructure**: localhost development, git via GitHub (keez97/alpha-desk)

## Dependencies

- **Depends on Phase 1**: Uses existing securities table, PiT infrastructure, PostgreSQL setup, price_history for alpha decay calculation
- **Affects Factor Backtester**: Event signals become new backtestable factors
- **Affects Screener**: Event badges appear on screener results
- **Foundation for Phase 3 (Earnings Predictor)**: Earnings event detection feeds into earnings surprise tracking
- **Foundation for Phase 4 (News Sentiment)**: Event timestamps provide anchoring for sentiment analysis windows

## Configuration

- Stack: fastapi-react-ts
- API Style: rest
- Complexity: complex

## Key Academic References

- Alpha decay research (Dec 2025): ~50% post-publication alpha decay; alpha concentrates in first month
- Complex Event Processing literature: three-layer producer/engine/consumer architecture
- Post-Earnings Announcement Drift (Bernard & Thomas 1989): 60+ day drift after earnings surprises
- Insider trading predictive power: Form 4 filings predict 3-6 month returns
- SEC filing impact studies: 8-K filings create 1-5 day alpha windows depending on content
