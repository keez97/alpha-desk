# AlphaDesk Event Scanner Feature (Phase 2) - Full Stack Architecture

**Date:** 2026-03-10
**Feature:** Event Scanner (Complex Event Processing System)
**Status:** Architecture Design

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Backend Architecture](#backend-architecture)
3. [Frontend Architecture](#frontend-architecture)
4. [Integration Points](#integration-points)
5. [Data Flow Diagrams](#data-flow-diagrams)
6. [Implementation Roadmap](#implementation-roadmap)

---

## Architecture Overview

### System Context

The Event Scanner is a Complex Event Processing (CEP) system that:

- **Ingests** market events from multiple sources (SEC EDGAR, yfinance)
- **Processes** events through rule-based classification and severity scoring
- **Stores** event data with alpha decay metrics
- **Distributes** events to multiple consumers (UI timeline, factor backtester, screener)
- **Analyzes** abnormal returns in 4 temporal windows: [0,+1d], [0,+5d], [0,+21d], [0,+63d]

### Core Design Principles

1. **Event-Driven Architecture**: Events flow through distinct producer → processor → consumer stages
2. **Scalability**: Background polling (15min intervals) with rate-limited API calls
3. **Composability**: Events become backtestable factors automatically
4. **Real-time UI**: WebSocket-ready for future live event streaming
5. **Multi-tenant Safe**: Watchlist-based event filtering per portfolio
6. **Data Enrichment**: Events enriched with price data, volatility, insider info

---

## Backend Architecture

### 1. Data Models

#### Event Core Model

```
Event
├── id: UUID (PK)
├── ticker: str (FK → Securities)
├── event_type: enum [earnings, M&A, insider_trade, dividend_change, SEC_filing, management_change, guidance_revision, share_repurchase]
├── event_date: datetime
├── severity: int (1-5)
├── title: str
├── description: text
├── source: str (SEC_EDGAR | YFINANCE | INSIDER_TRADES | CUSTOM)
├── raw_data: jsonb (source-specific metadata)
├── created_at: datetime
├── updated_at: datetime
└── is_deleted: bool (soft delete)
```

#### Alpha Decay Model

```
AlphaDecayMetric
├── id: UUID (PK)
├── event_id: UUID (FK → Event)
├── window_days: int [1, 5, 21, 63]
├── returns_0_to_window: float (%)
├── volatility: float (annualized %)
├── abnormal_returns: float (% vs market)
├── sharpe_ratio: float
├── max_drawdown: float (%)
├── calculated_at: datetime
└── data_quality: str [COMPLETE, PARTIAL, INSUFFICIENT]
```

#### EventFactor Model (Bridge)

```
EventFactor
├── id: UUID (PK)
├── event_id: UUID (FK → Event)
├── factor_id: UUID (FK → Factor)
├── alpha_exposure: float (factor loading)
├── created_at: datetime
└── backtestable: bool
```

#### EventScreenerBadge Model

```
EventScreenerBadge
├── id: UUID (PK)
├── ticker: str (FK → Securities)
├── event_id: UUID (FK → Event)
├── severity: int (1-5)
├── event_type: str
├── ttl_hours: int (24/48/72 based on severity)
├── expires_at: datetime
└── display_count: int (how many events in this 24h window)
```

### 2. Service Layer Architecture

#### EventProducerService

**Responsibilities:**
- Poll SEC EDGAR RSS feed every 15 minutes
- Scrape yfinance earnings calendar daily
- Parse insider trading filings
- Extract dividend announcements
- Normalize events to common schema

**Key Methods:**

```python
class EventProducerService:
    # SEC EDGAR polling
    async def poll_sec_edgar(self, rate_limit=5/60) -> List[Event]:
        """Poll SEC EDGAR RSS with rate limiting"""
        # Filter by: 10-K, 10-Q, 8-K, S-1, DEF 14A filings
        # Extract: filing date, company ticker, change summary
        # Return: List of Event objects

    async def scrape_yfinance_earnings(self) -> List[Event]:
        """Scrape yfinance earnings calendar"""
        # Get upcoming earnings dates
        # Extract: ticker, earnings date, last surprise %
        # Filter: only tracked tickers

    async def parse_insider_trades(self, feed_url) -> List[Event]:
        """Parse SEC insider trading forms (Form 4)"""
        # Extract: insider name, transaction type, shares/value
        # Classify: LARGE_SELL, LARGE_BUY based on ownership %

    async def get_dividend_announcements(self) -> List[Event]:
        """Get dividend news from yfinance"""
        # Extract: ex-dividend date, dividend per share, yield change

    async def enrich_event(self, event: Event) -> Event:
        """Add market data context"""
        # Attach: current price, market cap, volatility
        # Attach: recent earnings surprise history
        # Attach: insider ownership % changes
```

#### EventProcessingEngine

**Responsibilities:**
- Classify raw events using rule-based system
- Score events 1-5 based on severity rules
- Detect duplicate events (deduplication)
- Cache processed events
- Calculate alpha decay metrics

**Key Methods:**

```python
class EventProcessingEngine:
    async def classify_event(self, raw_event: dict) -> str:
        """Rule-based classification"""
        # Rules:
        # - SEC filing + 10-K/10-Q → SEC_FILING
        # - SEC filing + 8-K + "merger" → M&A
        # - earnings + beat > 5% → earnings (POSITIVE)
        # - earnings + miss > 5% → earnings (NEGATIVE)
        # - Form 4 + insider > 10% → insider_trade
        # - dividend % change > 10% → dividend_change
        # - insider name change in 8-K → management_change
        # - forward guidance in 8-K → guidance_revision
        # - Form 1.0 / buyback announcement → share_repurchase

    async def score_severity(self, event: Event) -> int:
        """Severity scoring (1-5)"""
        # Severity Rules:
        # - Management change → 5
        # - M&A announcement → 5
        # - Earnings miss/beat > 10% → 5
        # - Insider buy by CEO → 4
        # - Earnings surprise 5-10% → 3
        # - Dividend increase → 2
        # - Routine SEC filing → 1
        # Modifiers:
        # - Company size: Large cap × 0.8, Small cap × 1.2
        # - Volatility: High vol × 1.1, Low vol × 0.9

    async def deduplicate_events(self, events: List[Event],
                                  window_hours: int = 24) -> List[Event]:
        """Remove duplicate events in time window"""
        # Group by: ticker, event_type, source
        # Keep: highest severity event
        # Window: 24 hours by default

    async def calculate_alpha_decay(self, event: Event,
                                     lookback_years: int = 2) -> AlphaDecayMetric:
        """Calculate abnormal returns post-event"""
        # For each window [1d, 5d, 21d, 63d]:
        # - Get ticker returns from event_date to event_date + window
        # - Get market returns (SPY) for same period
        # - Calculate abnormal returns = stock_return - market_return
        # - Calculate volatility (annualized std dev)
        # - Calculate sharpe ratio
        # - Calculate max drawdown
        # Return: AlphaDecayMetric with data quality flag
```

#### EventConsumerService

**Responsibilities:**
- Create backtestable factors from events
- Update screener with event badges
- Generate timeline feeds
- Clean up expired events
- Publish events to WebSocket (future)

**Key Methods:**

```python
class EventConsumerService:
    async def create_factor_from_event(self, event: Event) -> EventFactor:
        """Convert event to backtestable factor"""
        # Create Factor:
        # - name: f"event_{event_type}_{ticker}_{date}"
        # - description: f"Event-driven factor: {event.title}"
        # - type: MARKET_EVENT
        # - returns_series: {date: alpha_decay.abnormal_returns}
        # Link: EventFactor bridge
        # Return: EventFactor with backtestable=True

    async def update_screener_badges(self, event: Event) -> None:
        """Add event severity badge to screener results"""
        # Create EventScreenerBadge:
        # - severity: event.severity
        # - ttl_hours: 24 (severity 1-2), 48 (severity 3), 72 (severity 4-5)
        # - expires_at: now + ttl_hours
        # Cache in Redis with expiry
        # Aggregation: Show max 3 recent events per ticker

    async def get_timeline_feed(self, watchlist_id: str,
                                 limit: int = 50) -> List[Event]:
        """Get paginated timeline for /events page"""
        # Filter: events for tickers in watchlist
        # Filter: not deleted
        # Sort: event_date DESC, severity DESC
        # Include: alpha decay metrics
        # Paginate: cursor-based

    async def cleanup_expired_events(self) -> int:
        """Hard delete old screener badges"""
        # Delete EventScreenerBadge where expires_at < now
        # Return: count deleted

    async def get_event_detail(self, event_id: str) -> dict:
        """Return full event detail for detail panel"""
        # Include: Event, AlphaDecayMetric (all windows), raw_data
        # Include: historical similar events (same ticker, same type)
        # Include: factor backtest results if linked to factor
```

#### BackgroundPollingService

**Responsibilities:**
- Schedule event polling jobs
- Rate limit API calls
- Handle retries and errors
- Track last poll time

**Key Methods:**

```python
class BackgroundPollingService:
    async def start_polling_scheduler(self) -> None:
        """Start APScheduler background job"""
        # Job 1: poll_sec_edgar_rss() every 15 minutes
        #   - Rate limit: 5 requests/min to SEC
        #   - Retry: exponential backoff on 429 errors
        #   - Store last_poll_time in cache
        # Job 2: scrape_earnings_calendar() daily at 14:30 ET
        #   - Post market, before EOD processing
        # Job 3: calculate_alpha_decay_batch() daily at 16:30 ET
        #   - After market close
        #   - Calculate for events from past 3 months
        # Job 4: cleanup_expired_screener_badges() hourly
        #   - Delete expired badges

    async def trigger_manual_scan(self, scan_type: str = "all") -> dict:
        """Manually trigger event scan"""
        # scan_type: "sec_edgar" | "earnings" | "insider" | "all"
        # Return: {status, events_found, errors}
        # Rate limit: 1 manual scan per 5 minutes per user

    async def get_polling_status(self) -> dict:
        """Get current polling state"""
        # Return: {last_sec_poll, last_earnings_poll, next_poll, errors}
```

### 3. API Endpoints

#### Event CRUD & Timeline

```
GET /api/events
├── Query params:
│   ├── watchlist_id: str (required, filters by watchlist tickers)
│   ├── event_type: str (comma-separated enum)
│   ├── severity_min: int (1-5)
│   ├── date_from: ISO date
│   ├── date_to: ISO date
│   ├── ticker: str (optional, single ticker filter)
│   ├── limit: int (default 50, max 200)
│   └── cursor: str (pagination token)
└── Response: {events: [...], cursor: str, total: int}

POST /api/events
├── Body: {event_type, ticker, event_date, severity, title, description, source, raw_data}
└── Response: {id, ...event_data}

GET /api/events/{id}
├── Response: {event, alpha_decay_metrics: {...}, similar_events: [...], factor: {...}}

PATCH /api/events/{id}
├── Body: {severity?, description?, is_deleted?}
└── Response: {updated_event}

DELETE /api/events/{id}
├── (Soft delete: sets is_deleted=True)
└── Response: {success: bool}
```

#### Alpha Decay Analysis

```
GET /api/events/{id}/alpha-decay
├── Response: {
│   event: {...},
│   metrics: {
│     window_1d: {returns, abnormal_returns, volatility, sharpe},
│     window_5d: {...},
│     window_21d: {...},
│     window_63d: {...}
│   },
│   chart_data: [{date, price, market_price}, ...],
│   data_quality: COMPLETE|PARTIAL|INSUFFICIENT
├── }

POST /api/events/{id}/alpha-decay/recalculate
├── Body: {lookback_years: int}
└── Response: {success: bool, metrics: {...}}
```

#### Manual Scan & Status

```
POST /api/events/scan
├── Query params:
│   ├── type: str (sec_edgar | earnings | insider | all)
│   └── force: bool (skip rate limit check)
├── Response: {status: INITIATED, job_id, eta_seconds}

GET /api/events/scan/status/{job_id}
├── Response: {status: RUNNING|COMPLETED, events_found, errors, progress}

GET /api/events/polling-status
├── Response: {
│   last_poll: {sec_edgar: ISO, earnings: ISO, insider: ISO},
│   next_poll: {sec_edgar: ISO, earnings: ISO},
│   rate_limits: {sec_edgar: {limit: 300/min, used: 45}}
├── }
```

#### Screener Badge Integration

```
GET /api/screener/badges
├── Query params:
│   ├── tickers: str (comma-separated)
├── Response: {
│   "AAPL": [{event_id, event_type, severity, title, expires_at}, ...],
│   "GOOGL": [...]
├── }
```

### 4. Database Schema (PostgreSQL)

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(20) NOT NULL,
    event_type VARCHAR(30) NOT NULL,
    event_date TIMESTAMP NOT NULL,
    severity INT CHECK (severity >= 1 AND severity <= 5),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    source VARCHAR(50) NOT NULL,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (ticker) REFERENCES securities(ticker),
    INDEX (ticker, event_date DESC),
    INDEX (event_type, severity DESC),
    INDEX (created_at DESC),
    UNIQUE (ticker, event_type, event_date, source) -- Deduplication
);

CREATE TABLE alpha_decay_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL,
    window_days INT NOT NULL,
    returns_0_to_window FLOAT,
    volatility FLOAT,
    abnormal_returns FLOAT,
    sharpe_ratio FLOAT,
    max_drawdown FLOAT,
    calculated_at TIMESTAMP DEFAULT NOW(),
    data_quality VARCHAR(20),
    FOREIGN KEY (event_id) REFERENCES events(id),
    UNIQUE (event_id, window_days)
);

CREATE TABLE event_factors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL,
    factor_id UUID NOT NULL,
    alpha_exposure FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    backtestable BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (factor_id) REFERENCES factors(id),
    UNIQUE (event_id, factor_id)
);

CREATE TABLE event_screener_badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(20) NOT NULL,
    event_id UUID,
    severity INT,
    event_type VARCHAR(30),
    ttl_hours INT,
    expires_at TIMESTAMP NOT NULL,
    display_count INT DEFAULT 1,
    FOREIGN KEY (ticker) REFERENCES securities(ticker),
    FOREIGN KEY (event_id) REFERENCES events(id),
    INDEX (ticker, expires_at),
    INDEX (expires_at) -- For cleanup queries
);

-- Cache table for recent events (Redis alternative)
CREATE TABLE event_cache (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB,
    expires_at TIMESTAMP,
    INDEX (expires_at)
);
```

### 5. Caching Strategy

**Redis Cache Structure:**

```
events:timeline:{watchlist_id} → paginated event list (TTL: 5 min)
events:detail:{event_id} → full event detail (TTL: 15 min)
events:alpha-decay:{event_id} → alpha decay metrics (TTL: 1 day)
screener:badges:{ticker} → recent event badges (TTL: 24 hours)
polling:status → last poll timestamps (TTL: 1 min)
rate_limits:sec_edgar → call count (TTL: 60 sec)
```

### 6. Rate Limiting & Error Handling

**SEC EDGAR Rate Limiting:**
- Hard limit: 300 requests/minute (SEC requirement)
- Soft limit: 5 requests/60 seconds (our window)
- Strategy: Distributed token bucket in Redis
- Backoff: Exponential (1s, 2s, 4s, 8s, 16s max)

**Retry Logic:**
- Transient errors (429, 503): retry up to 3 times
- Permanent errors (400, 401): log and skip
- Network errors: retry with exponential backoff
- Circuit breaker: Disable source after 5 consecutive failures

---

## Frontend Architecture

### 1. Page Structure: /events

```
/events
├── Layout: Two-column
│   ├── Left Column: Timeline Feed (60%)
│   │   ├── EventFilters (compact header)
│   │   ├── EventTimeline (scrollable list)
│   │   └── EventCard (clickable rows)
│   │
│   └── Right Column: Detail Panel (40%)
│       ├── EventDetail (expanded view)
│       ├── AlphaDecayChart (4 windows)
│       ├── SimilarEventsSection
│       └── FactorBacktestSection
│
└── Responsive: Stack on mobile (timeline above)
```

### 2. Component Hierarchy

#### EventTimeline (Left Panel)

```typescript
interface EventTimeline {
  // Props
  watchlistId: string
  filters: EventFilters
  onSelectEvent: (eventId: string) => void

  // State
  events: Event[]
  isLoading: boolean
  hasMore: boolean

  // Render
  <EventFilters {...} />
  <VirtualizedList>
    {events.map(event => <EventCard event={event} />)}
  </VirtualizedList>
  {hasMore && <LoadMore />}
}
```

**EventCard Component:**

```typescript
interface EventCard {
  // Props
  event: Event
  isSelected: boolean
  onClick: (eventId: string) => void

  // Render (compact, ~60px height)
  <div className="border-neutral-800 p-2 cursor-pointer hover:bg-neutral-900">
    <div className="flex justify-between items-center">
      <span className="text-xs font-bold">{ticker}</span>
      <SeverityBadge severity={event.severity} />
    </div>
    <div className="text-[10px] text-neutral-400 mt-1">
      {event.title}
    </div>
    <div className="text-[10px] text-neutral-500 mt-1">
      {event.event_date} • {event.event_type}
    </div>
  </div>
}
```

**EventFilters Component:**

```typescript
interface EventFilters {
  // Props
  initialFilters: FilterState
  onFilterChange: (filters: FilterState) => void

  // State
  eventTypes: string[] (multi-select dropdown)
  severityMin: int (1-5 slider)
  dateRange: [ISO, ISO] (date picker)

  // Render (compact, single row)
  <div className="flex gap-2 p-2 border-b border-neutral-800">
    <TypeFilter />
    <SeverityFilter />
    <DateRangeFilter />
    <ClearButton />
  </div>
}
```

#### EventDetail (Right Panel)

```typescript
interface EventDetail {
  // Props
  eventId: string

  // State
  event: Event | null
  alphaDecay: AlphaDecayMetric[] | null
  isLoading: boolean
  similarEvents: Event[]
  linkedFactor: Factor | null

  // Render
  {isLoading && <Skeleton />}
  {event && (
    <>
      <EventHeader event={event} />
      <EventMetadata event={event} />
      <AlphaDecayChart metrics={alphaDecay} />
      <SimilarEventsSection events={similarEvents} />
      <FactorBacktestSection factor={linkedFactor} />
    </>
  )}
}
```

**EventHeader Component:**

```typescript
interface EventHeader {
  // Props
  event: Event

  // Render
  <div className="p-4 border-b border-neutral-800">
    <div className="flex justify-between items-start">
      <div>
        <h3 className="text-sm font-bold">{event.title}</h3>
        <p className="text-xs text-neutral-400 mt-1">{event.description}</p>
      </div>
      <SeverityBadge severity={event.severity} size="lg" />
    </div>
    <div className="flex gap-4 mt-3 text-xs">
      <span className="text-neutral-400">Ticker: <span className="text-white">{event.ticker}</span></span>
      <span className="text-neutral-400">Type: <span className="text-white">{event.event_type}</span></span>
      <span className="text-neutral-400">Date: <span className="text-white">{event.event_date}</span></span>
    </div>
  </div>
}
```

#### AlphaDecayChart

```typescript
interface AlphaDecayChart {
  // Props
  metrics: AlphaDecayMetric[]

  // Data transformation
  chartData = [
    {window: "1d", returns: metrics[0].returns_0_to_window, abnormal: metrics[0].abnormal_returns},
    {window: "5d", returns: metrics[1].returns_0_to_window, abnormal: metrics[1].abnormal_returns},
    {window: "21d", returns: metrics[2].returns_0_to_window, abnormal: metrics[2].abnormal_returns},
    {window: "63d", returns: metrics[3].returns_0_to_window, abnormal: metrics[3].abnormal_returns},
  ]

  // Render (Recharts bar chart)
  <div className="p-4 border-b border-neutral-800">
    <h4 className="text-xs font-bold mb-3">Alpha Decay</h4>
    <BarChart data={chartData} height={200}>
      <Bar dataKey="returns" fill="#10b981" />
      <Bar dataKey="abnormal" fill="#f59e0b" />
      <XAxis dataKey="window" />
      <Tooltip />
    </BarChart>
    <div className="grid grid-cols-4 gap-2 mt-3">
      {metrics.map(m => (
        <MetricBox key={m.window_days} metric={m} />
      ))}
    </div>
  </div>
}

interface MetricBox {
  // Props
  metric: AlphaDecayMetric

  // Render
  <div className="bg-neutral-900 p-2 rounded border border-neutral-800">
    <div className="text-[10px] text-neutral-400">{metric.window_days}d Window</div>
    <div className="text-xs font-bold mt-1">{metric.returns_0_to_window.toFixed(2)}%</div>
    <div className="text-[10px] text-neutral-400">Abnormal: {metric.abnormal_returns.toFixed(2)}%</div>
    <div className="text-[10px] text-neutral-400 mt-1">Sharpe: {metric.sharpe_ratio.toFixed(2)}</div>
  </div>
}
```

#### SimilarEventsSection

```typescript
interface SimilarEventsSection {
  // Props
  events: Event[]
  onEventClick: (eventId: string) => void

  // Render
  <div className="p-4 border-b border-neutral-800">
    <h4 className="text-xs font-bold mb-2">Similar Events</h4>
    <div className="space-y-2 max-h-[200px] overflow-y-auto">
      {events.map(e => (
        <div key={e.id} className="text-[10px] p-2 bg-neutral-900 cursor-pointer hover:bg-neutral-800 rounded"
             onClick={() => onEventClick(e.id)}>
          <div className="font-bold">{e.event_date}</div>
          <div className="text-neutral-400">{e.title}</div>
        </div>
      ))}
    </div>
  </div>
}
```

#### FactorBacktestSection

```typescript
interface FactorBacktestSection {
  // Props
  factor: Factor | null

  // Render
  {factor && (
    <div className="p-4">
      <h4 className="text-xs font-bold mb-2">Backtest Factor</h4>
      <div className="text-[10px] text-neutral-400 mb-2">
        This event has been converted to a backtestable factor.
      </div>
      <a href={`/backtester?factor=${factor.id}`} className="text-blue-400 text-xs hover:underline">
        View in Backtester →
      </a>
      <div className="grid grid-cols-2 gap-2 mt-3">
        <div>
          <span className="text-neutral-400 text-[10px]">Sharpe Ratio</span>
          <div className="text-xs font-bold">{factor.sharpe_ratio.toFixed(2)}</div>
        </div>
        <div>
          <span className="text-neutral-400 text-[10px]">Win Rate</span>
          <div className="text-xs font-bold">{(factor.win_rate * 100).toFixed(1)}%</div>
        </div>
      </div>
    </div>
  )}
}
```

#### SeverityBadge Component

```typescript
interface SeverityBadge {
  // Props
  severity: int (1-5)
  size?: "sm" | "lg" (default: "sm")

  // Color mapping
  colors = {
    1: "bg-blue-900 text-blue-300",
    2: "bg-cyan-900 text-cyan-300",
    3: "bg-yellow-900 text-yellow-300",
    4: "bg-orange-900 text-orange-300",
    5: "bg-red-900 text-red-300",
  }

  // Render
  <div className={`${colors[severity]} px-2 py-1 rounded text-xs font-bold`}>
    S{severity}
  </div>
}
```

### 3. State Management with TanStack React Query

**Custom Hooks:**

```typescript
// useEvents - Timeline feed
function useEvents(watchlistId: string, filters: EventFilters) {
  return useInfiniteQuery({
    queryKey: ['events', watchlistId, filters],
    queryFn: ({ pageParam = null }) =>
      axios.get('/api/events', {
        params: { watchlist_id: watchlistId, ...filters, cursor: pageParam }
      }),
    getNextPageParam: (lastPage) => lastPage.data.cursor,
  })
}

// useEventDetail - Right panel
function useEventDetail(eventId: string | null) {
  return useQuery({
    queryKey: ['event-detail', eventId],
    queryFn: () =>
      eventId ? axios.get(`/api/events/${eventId}`) : Promise.resolve(null),
    enabled: !!eventId,
    staleTime: 15 * 60 * 1000, // 15 min
  })
}

// useAlphaDecay - Chart data
function useAlphaDecay(eventId: string | null) {
  return useQuery({
    queryKey: ['alpha-decay', eventId],
    queryFn: () =>
      eventId ? axios.get(`/api/events/${eventId}/alpha-decay`) : Promise.resolve(null),
    enabled: !!eventId,
    staleTime: 24 * 60 * 60 * 1000, // 1 day
  })
}

// useSimilarEvents - Related events
function useSimilarEvents(eventType: string, ticker: string, limit: number = 5) {
  return useQuery({
    queryKey: ['similar-events', eventType, ticker],
    queryFn: () =>
      axios.get('/api/events', {
        params: { event_type: eventType, ticker, limit }
      }),
    staleTime: 60 * 60 * 1000, // 1 hour
  })
}

// usePollingStatus - Background job status
function usePollingStatus() {
  return useQuery({
    queryKey: ['polling-status'],
    queryFn: () => axios.get('/api/events/polling-status'),
    refetchInterval: 60 * 1000, // 1 min
  })
}

// useManualScan - Trigger manual scan
function useManualScan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (type: string) =>
      axios.post('/api/events/scan', { type }),
    onSuccess: () => {
      queryClient.invalidateQueries(['events'])
      queryClient.invalidateQueries(['polling-status'])
    }
  })
}
```

### 4. Screener Integration

**Modified Screener Page:**

```typescript
interface ScreenerRow {
  // Existing columns...

  // New: Event badges column
  <div className="flex gap-1">
    {eventBadges.map(badge => (
      <EventBadgeScreener
        key={badge.event_id}
        badge={badge}
        onBadgeClick={() => navigateToEvent(badge.event_id)}
      />
    ))}
  </div>
}

// EventBadgeScreener - Compact version for screener
interface EventBadgeScreener {
  // Props
  badge: EventScreenerBadge
  onBadgeClick: () => void

  // Render (very compact)
  <div className="text-[9px] px-1 py-0.5 rounded cursor-pointer hover:opacity-80"
       style={{background: severityColors[badge.severity]}}
       onClick={onBadgeClick}
       title={badge.event_type}>
    {badge.event_type.slice(0, 3)}
  </div>
}
```

**Hook to fetch screener badges:**

```typescript
function useScreenerBadges(tickers: string[]) {
  return useQuery({
    queryKey: ['screener-badges', tickers.join(',')],
    queryFn: () =>
      axios.get('/api/screener/badges', {
        params: { tickers: tickers.join(',') }
      }),
    staleTime: 5 * 60 * 1000, // 5 min
    enabled: tickers.length > 0,
  })
}
```

### 5. Page Layout (Full /events Page)

```typescript
export default function EventsPage() {
  const { watchlistId } = useParams()
  const [selectedEventId, setSelectedEventId] = useState(null)
  const [filters, setFilters] = useState<EventFilters>({})

  const { data: eventsData, isLoading, hasNextPage, fetchNextPage } =
    useEvents(watchlistId, filters)

  const { data: detailData, isLoading: detailLoading } =
    useEventDetail(selectedEventId)

  return (
    <div className="flex h-screen bg-black text-white">
      {/* Left Column: Timeline */}
      <div className="w-3/5 border-r border-neutral-800 flex flex-col overflow-hidden">
        <div className="flex-shrink-0 border-b border-neutral-800">
          <h2 className="text-xs font-bold p-4">Events Timeline</h2>
          <EventFilters
            initialFilters={filters}
            onFilterChange={setFilters}
          />
        </div>

        <div className="flex-1 overflow-y-auto">
          <EventTimeline
            watchlistId={watchlistId}
            filters={filters}
            onSelectEvent={setSelectedEventId}
            isLoading={isLoading}
            hasMore={hasNextPage}
            onLoadMore={fetchNextPage}
          />
        </div>
      </div>

      {/* Right Column: Detail Panel */}
      <div className="w-2/5 flex flex-col overflow-hidden bg-neutral-950">
        {selectedEventId ? (
          <EventDetail
            eventId={selectedEventId}
            isLoading={detailLoading}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-neutral-500">
            <p className="text-xs">Select an event to view details</p>
          </div>
        )}
      </div>
    </div>
  )
}
```

### 6. Styling Guidelines

**Consistency with existing AlphaDesk theme:**

```css
/* Color Palette */
--bg-black: #000000
--bg-neutral-950: #0a0a0a
--bg-neutral-900: #1a1a1a
--border-neutral-800: #2a2a2a
--text-neutral-500: #717171
--text-neutral-400: #a3a3a3
--text-white: #ffffff

/* Typography */
--font-bold: font-bold
--text-xs: 12px
--text-[10px]: 10px
--leading-tight: 1.25

/* Spacing */
--p-4: 16px
--p-2: 8px
--gap-2: 8px
--gap-4: 16px

/* Borders */
--border-width: 1px
--border-color: border-neutral-800

/* Component Specifics */
--card-bg: bg-neutral-950
--card-hover: hover:bg-neutral-900
--input-bg: bg-neutral-900
--input-border: border-neutral-700
```

---

## Integration Points

### 1. Factor Backtester Integration

**How Events Become Factors:**

```
Event Created
  ↓
Event Processed (Classification + Scoring)
  ↓
Alpha Decay Calculated (returns in [1d, 5d, 21d, 63d] windows)
  ↓
EventConsumerService.create_factor_from_event()
  ↓
Creates Factor object:
  - name: event_{type}_{ticker}_{date}
  - type: MARKET_EVENT
  - returns_series: {date: abnormal_return}
  ↓
EventFactor bridge links event to factor
  ↓
Factor available in /backtester for backtesting
  ↓
Backtest results displayed in EventDetail panel
```

**Factor Data Structure for Backtester:**

```python
{
    "id": "factor_event_earnings_aapl_2026_02_01",
    "name": "Earnings Event: AAPL (2026-02-01)",
    "type": "MARKET_EVENT",
    "description": "AAPL announced Q1 earnings with 8% EPS beat",
    "event_id": "event_uuid_123",
    "creation_date": "2026-02-01",
    "returns_series": {
        "2026-02-01": 0.045,  # +4.5% abnormal return
        "2026-02-02": 0.063,  # cumulative through day 1
        "2026-02-05": 0.078,  # cumulative through day 5
        "2026-02-22": 0.085,  # cumulative through day 21
        "2026-04-04": 0.092   # cumulative through day 63
    },
    "metadata": {
        "severity": 4,
        "event_type": "earnings",
        "ticker": "AAPL",
        "source": "YFINANCE"
    }
}
```

### 2. Screener Integration

**Data Flow:**

```
Event Created with severity > 1
  ↓
EventConsumerService.update_screener_badges()
  ↓
Creates EventScreenerBadge in cache:
  {ticker, event_id, severity, event_type, ttl_hours, expires_at}
  ↓
Screener page queries /api/screener/badges
  ↓
Displays compact EventBadge on each ticker row
  ↓
User clicks badge → navigates to /events?eventId=...
  ↓
Detail panel opens in /events page
```

**Badge Display Rules:**

```
Severity 1-2: Show up to 2 most recent badges, TTL 24h
Severity 3:   Show up to 2 most recent badges, TTL 48h
Severity 4-5: Show up to 3 most recent badges, TTL 72h

Display precedence: S5 > S4 > S3 > S2 > S1
Aggregation: If > 3 events in 24h, show "+N more"
Color coding: Use SeverityBadge component colors
```

### 3. Morning Brief Integration (Future)

**Potential Extension:**

```
Morning Brief page could include:
- "New High-Severity Events" section
- Most recent S4-S5 events across watchlist
- Link to /events page for full timeline
```

---

## Data Flow Diagrams

### Event Ingestion Flow

```
┌─────────────────────┐
│  Event Producers    │
├─────────────────────┤
│ SEC EDGAR RSS Feed  │ ──┐
│ yfinance Calendar   │   │
│ Insider Trades Form │   │
│ Dividend Feeds      │   │
└─────────────────────┘   │
                          │
                          v
            ┌──────────────────────────┐
            │ EventProducerService     │
            ├──────────────────────────┤
            │ poll_sec_edgar()         │
            │ scrape_earnings()        │
            │ parse_insider_trades()   │
            │ get_dividends()          │
            │ enrich_event()           │
            └──────────────────────────┘
                          │
                          v
        ┌─────────────────────────────────┐
        │ EventProcessingEngine           │
        ├─────────────────────────────────┤
        │ classify_event()                │
        │ score_severity()                │
        │ deduplicate_events()            │
        │ calculate_alpha_decay()         │
        └─────────────────────────────────┘
                          │
                    ┌─────┴────┬──────────┬─────────────┐
                    │          │          │             │
                    v          v          v             v
            ┌────────────┐ ┌───────┐ ┌──────────┐ ┌─────────┐
            │  Database  │ │Cache  │ │ Timeline │ │Screener │
            │  (Event)   │ │(Redis)│ │   (UI)   │ │Badges   │
            └────────────┘ └───────┘ └──────────┘ └─────────┘
                    │
                    v
        ┌────────────────────────┐
        │ EventConsumerService   │
        ├────────────────────────┤
        │ create_factor_from_    │
        │   event()              │
        │ update_screener_       │
        │   badges()             │
        │ cleanup_expired_       │
        │   events()             │
        └────────────────────────┘
                    │
            ┌───────┴──────┬──────────┐
            │              │          │
            v              v          v
        ┌────────┐  ┌──────────┐ ┌─────────┐
        │ Factor │  │ Screener │ │Timeline │
        │Database│  │ Cache    │ │ Feed    │
        └────────┘  └──────────┘ └─────────┘
```

### UI Event Selection Flow

```
┌──────────────────────────────────────┐
│    /events Page Loads                │
└──────────────────────────────────────┘
          │
          v
┌──────────────────────────────────────┐
│ useEvents(watchlistId, filters)      │
│ → Fetch /api/events                  │
│ → Display in EventTimeline (left)    │
└──────────────────────────────────────┘
          │
          v
┌──────────────────────────────────────┐
│ User Clicks EventCard                │
│ → setSelectedEventId(id)             │
└──────────────────────────────────────┘
          │
          v
┌──────────────────────────────────────┐
│ useEventDetail(selectedEventId)      │
│ → Fetch /api/events/{id}             │
│ → Display in EventDetail (right)     │
└──────────────────────────────────────┘
          │
          v
┌──────────────────────────────────────┐
│ useAlphaDecay(selectedEventId)       │
│ → Fetch /api/events/{id}/alpha-decay │
│ → Render AlphaDecayChart             │
└──────────────────────────────────────┘
          │
          v
┌──────────────────────────────────────┐
│ useSimilarEvents(type, ticker)       │
│ → Fetch /api/events (filtered)       │
│ → Render SimilarEventsSection        │
└──────────────────────────────────────┘
```

---

## Implementation Roadmap

### Phase 2A: Backend Foundation (Weeks 1-2)

**Sprint 1: Data Models & Schema**
- [ ] Create Event, AlphaDecayMetric, EventFactor, EventScreenerBadge models
- [ ] Design and migrate PostgreSQL schema
- [ ] Create indexes for efficient querying
- [ ] Set up Redis cache structure

**Sprint 2: Core Services**
- [ ] Implement EventProducerService with SEC EDGAR polling
- [ ] Implement yfinance earnings scraper
- [ ] Implement EventProcessingEngine (classify, score, deduplicate)
- [ ] Implement alpha decay calculator
- [ ] Add comprehensive error handling & retry logic

**Sprint 3: API Endpoints & Integration**
- [ ] Create /api/events CRUD endpoints
- [ ] Create /api/events/{id}/alpha-decay endpoint
- [ ] Create /api/events/scan manual trigger
- [ ] Create /api/screener/badges endpoint
- [ ] Implement rate limiting & caching

### Phase 2B: Background Tasks & Consumers (Weeks 3-4)

**Sprint 4: Background Polling**
- [ ] Implement BackgroundPollingService with APScheduler
- [ ] Set up 15-min SEC EDGAR polling job
- [ ] Set up daily earnings calendar job
- [ ] Set up daily alpha decay batch calculation
- [ ] Add monitoring & alerting for polling failures

**Sprint 5: Event Consumers**
- [ ] Implement EventConsumerService.create_factor_from_event()
- [ ] Implement EventConsumerService.update_screener_badges()
- [ ] Link events to factors in database
- [ ] Set up badge TTL expiry cleanup job
- [ ] Add WebSocket prep (future real-time updates)

### Phase 2C: Frontend Implementation (Weeks 5-6)

**Sprint 6: Components & Layout**
- [ ] Create /events page layout (two-column)
- [ ] Build EventTimeline & EventCard components
- [ ] Build EventFilters component
- [ ] Build EventDetail panel
- [ ] Build EventHeader component

**Sprint 7: Charts & Detail Views**
- [ ] Build AlphaDecayChart (Recharts bar chart)
- [ ] Build MetricBox components for alpha decay
- [ ] Build SimilarEventsSection
- [ ] Build FactorBacktestSection with links
- [ ] Build SeverityBadge component

**Sprint 8: State Management & Integration**
- [ ] Implement all React Query hooks
- [ ] Integrate EventTimeline with useEvents
- [ ] Integrate EventDetail with useEventDetail
- [ ] Integrate AlphaDecayChart with useAlphaDecay
- [ ] Add manual scan trigger button

### Phase 2D: Screener & Polish (Weeks 7-8)

**Sprint 9: Screener Integration**
- [ ] Modify Screener page layout for event badges
- [ ] Build EventBadgeScreener component
- [ ] Implement useScreenerBadges hook
- [ ] Add badge click navigation to /events
- [ ] Add event count indicators

**Sprint 10: Testing & Optimization**
- [ ] Unit tests for EventProcessingEngine (classify, score)
- [ ] Integration tests for API endpoints
- [ ] E2E tests for timeline, filtering, detail view
- [ ] Performance testing (large watchlists)
- [ ] Frontend bundle size optimization

**Sprint 11: Deployment & Monitoring**
- [ ] Database migration scripts
- [ ] API documentation updates
- [ ] Frontend route configuration
- [ ] Monitoring for event ingestion, CEP, API latency
- [ ] Error tracking & alerting

---

## Technical Considerations

### Scalability

**Event Volume Projections:**
- SEC EDGAR: ~5,000 filings/day → ~200/hour for tracked companies
- Earnings announcements: ~100/day during earnings season
- Insider trades: ~500/day
- Total: ~800 events/day, ~33/hour peak

**Storage:**
- Event records: ~300 KB each (with raw_data) → ~250 MB/year
- Alpha decay metrics: ~20 KB × 4 windows → ~29 MB/year
- Screener badges: ~500 B each, TTL-based cleanup → minimal storage

### Reliability

**Deduplication Strategy:**
- Unique constraint on (ticker, event_type, event_date, source)
- Rolling 24-hour deduplication window in processor
- Manual dedup option in API

**Data Quality Flags:**
- AlphaDecayMetric.data_quality: COMPLETE | PARTIAL | INSUFFICIENT
- INCOMPLETE if: missing price data, market closure, data gaps
- Display in UI with warning indicator

**Rate Limiting:**
- SEC EDGAR: 300 req/min (federal limit)
- yfinance: No strict limit, use exponential backoff
- Circuit breaker pattern for failing sources

### Security

**Input Validation:**
- Ticker format: ^[A-Z]{1,5}$
- Event dates: valid ISO format, not future-dated
- Severity: 1-5 integer
- Event types: whitelist enum validation

**Authorization:**
- Only show events for tickers in user's watchlist
- Factor backtests inherit event permissions
- Screener badges filtered by user's watchlist

---

## Appendix: API Response Examples

### GET /api/events Response

```json
{
  "events": [
    {
      "id": "event_uuid_1",
      "ticker": "AAPL",
      "event_type": "earnings",
      "event_date": "2026-02-01T16:00:00Z",
      "severity": 4,
      "title": "Q1 2026 Earnings: 8% EPS Beat",
      "description": "Apple announced Q1 FY2026 earnings with EPS of $2.15 vs. consensus $1.99",
      "source": "YFINANCE",
      "created_at": "2026-02-01T16:05:00Z"
    },
    {
      "id": "event_uuid_2",
      "ticker": "GOOGL",
      "event_type": "M&A",
      "event_date": "2026-01-28T09:30:00Z",
      "severity": 5,
      "title": "Announces Acquisition of DataStart",
      "description": "Google to acquire DataStart for $8.5B in all-cash transaction",
      "source": "SEC_EDGAR",
      "created_at": "2026-01-28T10:00:00Z"
    }
  ],
  "cursor": "eyJpZCI6ICJldmVudF91dWlkXzIsICJkYXRlIjogIjIwMjYtMDEtMjgifQ==",
  "total": 347
}
```

### GET /api/events/{id}/alpha-decay Response

```json
{
  "event": {
    "id": "event_uuid_1",
    "ticker": "AAPL",
    "event_type": "earnings",
    "severity": 4,
    "title": "Q1 2026 Earnings: 8% EPS Beat"
  },
  "metrics": {
    "window_1d": {
      "returns_0_to_window": 2.45,
      "abnormal_returns": 1.87,
      "volatility": 18.5,
      "sharpe_ratio": 1.23,
      "max_drawdown": -0.5
    },
    "window_5d": {
      "returns_0_to_window": 4.12,
      "abnormal_returns": 3.45,
      "volatility": 16.2,
      "sharpe_ratio": 1.58,
      "max_drawdown": -1.2
    },
    "window_21d": {
      "returns_0_to_window": 5.67,
      "abnormal_returns": 4.89,
      "volatility": 15.8,
      "sharpe_ratio": 1.95,
      "max_drawdown": -2.1
    },
    "window_63d": {
      "returns_0_to_window": 6.23,
      "abnormal_returns": 5.12,
      "volatility": 16.1,
      "sharpe_ratio": 1.87,
      "max_drawdown": -3.0
    }
  },
  "data_quality": "COMPLETE"
}
```

### GET /api/screener/badges Response

```json
{
  "AAPL": [
    {
      "event_id": "event_uuid_1",
      "event_type": "earnings",
      "severity": 4,
      "title": "Q1 2026 Earnings Beat",
      "expires_at": "2026-02-04T16:00:00Z"
    },
    {
      "event_id": "event_uuid_3",
      "event_type": "insider_trade",
      "severity": 2,
      "title": "CEO purchased 10,000 shares",
      "expires_at": "2026-02-02T09:30:00Z"
    }
  ],
  "GOOGL": [
    {
      "event_id": "event_uuid_2",
      "event_type": "M&A",
      "severity": 5,
      "title": "Acquisition of DataStart",
      "expires_at": "2026-02-07T09:30:00Z"
    }
  ]
}
```

---

## Summary

This architecture provides a complete, production-ready design for the AlphaDesk Event Scanner feature. Key highlights:

- **Layered CEP System**: Producer → Processor → Consumer pattern enables modularity
- **Rich Event Context**: Alpha decay metrics capture post-event returns across 4 time windows
- **Seamless Integration**: Events become factors for backtesting and badges for screener
- **Scalable Infrastructure**: Background polling, rate limiting, caching, and deduplication
- **Clean UI**: Two-column timeline + detail layout with Recharts visualizations
- **React Query State Management**: Automatic caching, refetching, and invalidation
- **Type-Safe Components**: Full TypeScript interfaces for all models and responses

The 11-sprint, 8-week roadmap provides clear milestones from backend foundation through frontend polish, screener integration, and deployment readiness.
