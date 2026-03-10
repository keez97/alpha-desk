# AlphaDesk Earnings Surprise Predictor - Full-Stack Architecture (Phase 3)

**Date:** 2026-03-10
**Feature:** Earnings Surprise Predictor with SmartEstimate & PEAD Analysis
**Status:** Architecture Design

---

## Table of Contents

1. [Overview](#overview)
2. [Backend Architecture](#backend-architecture)
3. [Frontend Architecture](#frontend-architecture)
4. [Data Models](#data-models)
5. [API Specification](#api-specification)
6. [Data Flow Diagrams](#data-flow-diagrams)
7. [Integration Points](#integration-points)
8. [Implementation Roadmap](#implementation-roadmap)
9. [Performance & Scaling](#performance--scaling)
10. [Testing Strategy](#testing-strategy)
11. [Monitoring & Observability](#monitoring--observability)
12. [Security & Data Integrity](#security--data-integrity)

---

## Overview

The Earnings Surprise Predictor enhances AlphaDesk's analytical capabilities by introducing SmartEstimate-based consensus weighting with ~70% directional accuracy when diverging ≥2% from consensus. The system integrates PEAD (Post-Earnings Announcement Drift) drift tracking, analyst accuracy scoring, and seamless integration with existing Factor Backtester, Screener, and Event Scanner modules.

### Core Features

- **SmartEstimate Engine**: Weighted analyst consensus applying recency decay (30-day half-life), accuracy tiers (A/B/C), and broker size weighting
- **Signal Generation**: Buy/Sell/Hold signals triggered by ≥2% divergence from consensus
- **PEAD Analysis**: 60-day cumulative abnormal return tracking post-earnings
- **Analyst Scorecards**: Hit rate and directional accuracy metrics per broker
- **Screener Integration**: "Earnings Signal" column with divergence % and direction
- **Real-time Updates**: WebSocket support for signal changes

---

## Backend Architecture

### 1.1 Service Layer

#### SmartEstimateEngine Service

**Purpose**: Core calculation engine for weighted analyst consensus and divergence-based signals.

**Key Methods**:

```python
class SmartEstimateEngine:
    def fetch_estimates(ticker: str, quarter: str) -> EstimateSet:
        """
        Fetch analyst consensus estimates from yfinance.

        Returns:
            - consensus_eps: float
            - guidance_range: (low, high)
            - revision_trend_30d: float (% change)
            - num_analysts: int
        """
        pass

    def calculate_smart_estimate(
        ticker: str,
        quarter: str,
        estimates: List[Dict],
        broker_scorecards: Dict
    ) -> float:
        """
        Apply weighted averaging:
        1. Recency decay: weight = exp(-days_since_pub / 30)
        2. Accuracy tier: A=1.5x, B=1.0x, C=0.5x multiplier
        3. Broker size: weight = aum_percentile / 100

        Final weight = recency * accuracy * broker_size
        SmartEstimate = sum(estimate * weight) / sum(weights)
        """
        pass

    def compare_estimates(
        ticker: str,
        quarter: str,
        consensus_eps: float,
        smart_estimate_eps: float
    ) -> EstimateComparison:
        """
        Calculate divergence metrics.

        divergence_pct = (smart_estimate - consensus) / |consensus| * 100

        Returns divergence %, direction, magnitude tier
        """
        pass

    def generate_signal(
        ticker: str,
        quarter: str,
        divergence_pct: float,
        broker_breakdown: List[Dict]
    ) -> Signal:
        """
        Generate BUY/SELL/HOLD signal.

        Rules:
        - If divergence >= 2%: BUY (confidence = min(divergence/5, 1.0))
        - If divergence <= -2%: SELL (confidence = min(|divergence|/5, 1.0))
        - Otherwise: HOLD (confidence = 0.5)

        Returns Signal with reasoning and broker breakdown
        """
        pass
```

**Dependencies**:
- yfinance_service (consensus, guidance)
- weight_calculator (recency, accuracy, size)
- analyst_scorecards table (accuracy tier lookup)

---

#### EarningsDataService

**Purpose**: Real-time ingestion and maintenance of earnings estimates and actuals.

**Key Methods**:

```python
class EarningsDataService:
    def ingest_estimates(
        tickers: List[str],
        refresh: bool = False
    ) -> IngestResult:
        """
        Fetch analyst estimates from yfinance.

        Storage: earnings_estimates table with PiT timestamps
        - ticker, quarter, analyst_id, broker_id, estimate_eps, pub_date

        Returns: count of new/updated estimates
        """
        pass

    def ingest_actuals(
        tickers: List[str]
    ) -> IngestResult:
        """
        Poll yfinance post-earnings for actual EPS.

        Workflow:
        1. Fetch actual EPS from yfinance
        2. Match with historical estimates by quarter
        3. Calculate surprise: (actual - consensus) / |consensus| * 100
        4. Store in earnings_actuals table
        5. Emit earnings.actual_announced event

        Returns: count of new actuals, triggering PEAD measurement
        """
        pass

    def update_analyst_scorecards() -> ScoreUpdateResult:
        """
        Recalculate accuracy metrics for all brokers.

        Metrics:
        - Hit rate: % within ±0.05 EPS of actual
        - Directional accuracy: % correct sign of surprise
        - Accuracy tier: A (>80%), B (60-80%), C (<60%)

        Returns: count of updated scorecards
        """
        pass
```

**Dependencies**:
- yfinance_service (actuals, guidance)
- data_ingestion service (batch operations)
- event_producer (earnings.actual_announced)

---

#### PEADAnalyzer Service

**Purpose**: Post-earnings announcement drift tracking and analysis.

**Key Methods**:

```python
class PEADAnalyzer:
    def measure_pead(
        ticker: str,
        quarter: str,
        announce_date: datetime
    ) -> PEADData:
        """
        Measure cumulative abnormal returns (CAR) post-earnings.

        Workflow:
        1. Fetch daily returns for ticker (60 days post-announce)
        2. Fetch daily returns for SPY (market baseline)
        3. Calculate abnormal_return = ticker_ret - spy_ret
        4. Aggregate to CAR at: 1d, 5d, 21d, 60d

        Returns:
            - car_1d, car_5d, car_21d, car_60d: float (%)
            - surprise_pct: from earnings_actuals
            - signal_at_earnings: BUY/SELL/HOLD at announcement
            - signal_correct: bool (CAR sign matches signal)
        """
        pass

    def aggregate_pead_by_surprise() -> PEADAggregation:
        """
        Analyze PEAD patterns by surprise magnitude.

        Binning strategy:
        - Q1: 0-1% surprise
        - Q2: 1-2% surprise
        - Q3: 2-4% surprise
        - Q4: 4%+ surprise

        For each bin, calculate:
        - Median CAR at 1d, 5d, 21d, 60d
        - Mean CAR with std dev
        - Sample size

        Returns: Dict[bin_name -> AggregateCAR]
        """
        pass

    def get_pead_history(
        ticker: str,
        lookback_quarters: int = 12
    ) -> List[PEADRecord]:
        """
        Fetch historical PEAD for a ticker.

        Joins: pead_measurements + earnings_actuals + earnings_smart_estimates

        Returns: List of PEAD records with surprise and signal info
        """
        pass
```

**Dependencies**:
- yfinance_service (daily returns)
- market_data service (SPY baseline)
- statistics_calculator (CAR aggregation)

---

### 1.2 Data Layer

#### New Database Tables

**earnings_estimates**
```sql
CREATE TABLE earnings_estimates (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    quarter VARCHAR(8) NOT NULL,  -- "2025Q1"
    analyst_id INT,
    broker_id INT NOT NULL,
    estimate_eps NUMERIC(10, 2),
    pub_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (ticker) REFERENCES securities(ticker),
    FOREIGN KEY (broker_id) REFERENCES analysts_brokers(id),
    INDEX idx_ticker_quarter (ticker, quarter),
    INDEX idx_broker_id (broker_id),
    INDEX idx_created_at (created_at DESC)
);
```

**earnings_actuals**
```sql
CREATE TABLE earnings_actuals (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    quarter VARCHAR(8) NOT NULL,
    actual_eps NUMERIC(10, 2) NOT NULL,
    announce_date TIMESTAMP NOT NULL,
    announced_time VARCHAR(20),  -- "pre-market", "after-hours", "regular"
    consensus_eps NUMERIC(10, 2),
    surprise_pct NUMERIC(8, 4),  -- (actual - consensus) / |consensus| * 100
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (ticker) REFERENCES securities(ticker),
    UNIQUE (ticker, quarter),
    INDEX idx_announce_date (announce_date DESC),
    INDEX idx_ticker_quarter (ticker, quarter)
);
```

**earnings_smart_estimates**
```sql
CREATE TABLE earnings_smart_estimates (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    quarter VARCHAR(8) NOT NULL,
    consensus_eps NUMERIC(10, 2),
    smart_estimate_eps NUMERIC(10, 2),
    divergence_pct NUMERIC(8, 4),
    signal VARCHAR(20),  -- "BUY", "SELL", "HOLD"
    confidence NUMERIC(3, 2),  -- 0-1
    reasoning TEXT,
    calculated_at TIMESTAMP NOT NULL,
    is_active BOOL DEFAULT TRUE,
    FOREIGN KEY (ticker) REFERENCES securities(ticker),
    INDEX idx_ticker_active (ticker, is_active),
    INDEX idx_signal (signal),
    INDEX idx_calculated_at (calculated_at DESC)
);
```

**analyst_scorecards**
```sql
CREATE TABLE analyst_scorecards (
    id SERIAL PRIMARY KEY,
    broker_id INT NOT NULL,
    broker_name VARCHAR(100) NOT NULL,
    accuracy_tier VARCHAR(1),  -- "A", "B", "C"
    hit_rate NUMERIC(5, 2),  -- % within ±0.05 EPS
    directional_accuracy NUMERIC(5, 2),  -- % correct direction
    total_estimates INT,
    last_updated TIMESTAMP NOT NULL,
    UNIQUE (broker_id),
    INDEX idx_accuracy_tier (accuracy_tier)
);
```

**pead_measurements**
```sql
CREATE TABLE pead_measurements (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    quarter VARCHAR(8) NOT NULL,
    announce_date TIMESTAMP NOT NULL,
    car_1d NUMERIC(8, 4),  -- Cumulative Abnormal Return %
    car_5d NUMERIC(8, 4),
    car_21d NUMERIC(8, 4),
    car_60d NUMERIC(8, 4),
    surprise_pct NUMERIC(8, 4),
    signal_at_earnings VARCHAR(20),
    signal_correct BOOL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (ticker) REFERENCES securities(ticker),
    UNIQUE (ticker, quarter, announce_date),
    INDEX idx_ticker_announce (ticker, announce_date DESC),
    INDEX idx_announce_date (announce_date DESC)
);
```

---

### 1.3 API Router: `/api/earnings`

#### GET `/api/earnings/calendar`

**Purpose**: Return upcoming earnings with SmartEstimate signals, sorted by days-to-earnings.

**Query Parameters**:
```
- days_ahead: INT (default 30)
- sort_by: STRING (default "days_to_earnings")
- filter_signal: STRING (optional, "BUY", "SELL", "HOLD")
- limit: INT (default 50)
```

**Response** (200 OK):
```json
{
  "data": [
    {
      "ticker": "AAPL",
      "company_name": "Apple Inc",
      "announce_date": "2025-04-28T16:30:00Z",
      "days_to_earnings": 49,
      "consensus_eps": 1.52,
      "smart_estimate_eps": 1.58,
      "divergence_pct": 3.95,
      "signal": "BUY",
      "confidence": 0.79,
      "is_forecast": true,
      "last_updated": "2025-03-09T14:32:00Z"
    }
  ],
  "meta": {
    "count": 47,
    "next_earnings_date": "2025-03-10T16:30:00Z"
  }
}
```

---

#### GET `/api/earnings/{ticker}/history`

**Purpose**: Historical earnings comparison (actual vs consensus vs SmartEstimate).

**Query Parameters**:
```
- quarters: INT (default 8)
```

**Response** (200 OK):
```json
{
  "ticker": "AAPL",
  "history": [
    {
      "quarter": "2024Q4",
      "announce_date": "2025-01-29T16:30:00Z",
      "consensus_eps": 2.10,
      "smart_estimate_eps": 2.13,
      "actual_eps": 2.18,
      "divergence_pct": 1.43,
      "signal": "HOLD",
      "signal_correct": true,
      "surprise_pct": 3.81,
      "car_1d": 0.42,
      "car_5d": 1.25,
      "car_21d": 2.33,
      "car_60d": -0.87
    }
  ]
}
```

---

#### GET `/api/earnings/{ticker}/signal`

**Purpose**: Current pre-earnings signal for a single stock.

**Response** (200 OK):
```json
{
  "ticker": "AAPL",
  "quarter": "2025Q1",
  "announce_date": "2025-04-28T16:30:00Z",
  "days_to_earnings": 49,
  "signal": "BUY",
  "confidence": 0.79,
  "consensus_eps": 1.52,
  "smart_estimate_eps": 1.58,
  "divergence_pct": 3.95,
  "reasoning": "SmartEstimate diverges 3.95% above consensus, exceeding 2% threshold. Weighted by recent positive estimate revisions and strong accuracy tier of lead brokers.",
  "broker_breakdown": [
    {
      "broker": "Goldman Sachs",
      "estimate_eps": 1.62,
      "accuracy_tier": "A",
      "weight": 0.18,
      "days_since_pub": 3
    }
  ],
  "historical_signal_accuracy": 0.72,
  "calculated_at": "2025-03-09T14:32:00Z"
}
```

---

#### GET `/api/earnings/{ticker}/pead`

**Purpose**: PEAD drift analysis and historical performance.

**Query Parameters**:
```
- lookback_quarters: INT (default 12)
```

**Response** (200 OK):
```json
{
  "ticker": "AAPL",
  "pead_profile": [
    {
      "quarter": "2024Q4",
      "announce_date": "2025-01-29T16:30:00Z",
      "surprise_pct": 3.81,
      "surprise_magnitude_bin": "Q4 (4%+)",
      "signal_at_earnings": "BUY",
      "drift_timeline": [
        { "days_post_earnings": 1, "car": 0.42 },
        { "days_post_earnings": 5, "car": 1.25 },
        { "days_post_earnings": 21, "car": 2.33 },
        { "days_post_earnings": 60, "car": -0.87 }
      ]
    }
  ],
  "aggregate_pead_by_surprise": {
    "Q1_0_to_1pct": {
      "median_car_60d": 0.15,
      "mean_car_60d": 0.31,
      "sample_size": 4
    },
    "Q2_1_to_2pct": {
      "median_car_60d": 0.82,
      "mean_car_60d": 1.12,
      "sample_size": 3
    }
  }
}
```

---

#### POST `/api/earnings/refresh`

**Purpose**: Trigger manual data refresh (admin only).

**Request Body**:
```json
{
  "tickers": ["AAPL", "MSFT"],
  "refresh_estimates": true,
  "refresh_actuals": true,
  "update_scorecards": true
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "job_id": "refresh-earnings-20250309-143200",
  "estimates_ingested": 145,
  "actuals_ingested": 3,
  "scorecards_updated": 28,
  "next_scheduled_refresh": "2025-03-09T20:00:00Z"
}
```

---

#### GET `/api/earnings/screener-signals`

**Purpose**: Batch signals for integration with Screener module.

**Query Parameters**:
```
- tickers: LIST (required, comma-separated)
- min_divergence: FLOAT (optional, default 0)
```

**Response** (200 OK):
```json
{
  "data": [
    {
      "ticker": "AAPL",
      "signal": "BUY",
      "divergence_pct": 3.95,
      "confidence": 0.79,
      "days_to_earnings": 49,
      "announce_date": "2025-04-28T16:30:00Z"
    }
  ]
}
```

---

### 1.4 Event Integration

**Event Producer**: `earnings_event_producer`

Events emitted:
- `earnings.estimate_ingested` → New analyst estimates fetched
- `earnings.actual_announced` → Actual EPS published
- `earnings.signal_generated` → SmartEstimate divergence ≥2%

**Event Consumer**: `earnings_event_processor`

Subscriptions:
- `earnings.actual_announced` → Trigger `pead_analyzer.measure_pead()`
- `earnings.signal_generated` → Publish to WebSocket channel `earnings.signals`

---

## Frontend Architecture

### 2.1 New Page: `/earnings`

**Layout**:
```
┌──────────────────────────────────────────────┐
│ Earnings Surprise Predictor                  │
├──────────────────────────────────────────────┤
│ [Filters: Sort | Signal | Days Ahead]        │
│                                              │
│ ┌──────────────────────────────────────────┐ │
│ │ EarningsCalendar (sortable table)         │ │
│ │                                          │ │
│ │ Ticker│Days│Consensus│Smart│Divergence  │ │
│ │ AAPL  │ 49 │  1.52   │1.58 │ +3.95% BUY │ │
│ │ MSFT  │ 23 │  2.81   │2.78 │ -0.99% ⌐  │ │
│ └──────────────────────────────────────────┘ │
│                                              │
│ ┌──────────────────────────────────────────┐ │
│ │ Detail Panel (click to expand)            │ │
│ │                                          │ │
│ │ [SmartEstimateComparison Chart]          │ │
│ │ [AnalystScorecard Table]                 │ │
│ │ [PEADChart]                              │ │
│ └──────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

---

### 2.2 Component Specifications

#### EarningsCalendar Component

**Props**:
```typescript
interface EarningsCalendarProps {
  earnings: EarningRecord[];
  onRowClick: (ticker: string) => void;
  sortBy?: "days_to_earnings" | "signal" | "divergence_pct";
  filterSignal?: "BUY" | "SELL" | "HOLD";
}
```

**Features**:
- Sortable columns (click header to sort ascending/descending)
- Filter dropdown for BUY/SELL/HOLD signals
- Rows highlight by signal type (green, red, gray)
- Click row to open detail panel
- Real-time WebSocket updates for signal changes

**Styling**:
- Pure Tailwind on black background
- Borders: `border-neutral-800`
- Text: `text-xs text-neutral-300`
- Signal badges:
  - BUY: `bg-green-900/30 text-green-300`
  - SELL: `bg-red-900/30 text-red-300`
  - HOLD: `bg-gray-900/30 text-neutral-400`

---

#### SmartEstimateComparison Component

**Props**:
```typescript
interface SmartEstimateComparisonProps {
  ticker: string;
  history: EarningsComparisonRecord[];
}
```

**Chart Type**: Recharts BarChart
- X-axis: Quarter labels (Q4'24, Q1'25, etc.)
- Y-axis: EPS values
- Bars per quarter (3 series):
  - Consensus (blue, `#3b82f6`)
  - SmartEstimate (purple, `#a78bfa`)
  - Actual (green, `#10b981`)
- Tooltip: divergence %, surprise %
- Legend: top-left corner

**Styling**:
```
- CartesianGrid: stroke="rgb(23, 23, 23)"
- XAxis/YAxis: stroke="rgb(64, 64, 64)"
- Axis ticks: text-[10px] text-neutral-500
```

---

#### PEADChart Component

**Props**:
```typescript
interface PEADChartProps {
  ticker: string;
  pead_history: PEADRecord[];
  aggregate_pead?: PEADAggregation;
}
```

**Chart Type**: Recharts LineChart
- X-axis: Days post-earnings (0, 1, 5, 21, 60)
- Y-axis: CAR (Cumulative Abnormal Return %)
- Lines: One per historical earnings event
  - Color by surprise magnitude:
    - Q1 (0-1%): `#6b7280` (gray)
    - Q2 (1-2%): `#3b82f6` (blue)
    - Q3 (2-4%): `#f97316` (orange)
    - Q4 (4%+): `#ef4444` (red)
  - Line opacity: 0.6
- Hover: Highlight individual trajectory with tooltip
- Legend: bottom-right, toggleable by surprise bin

---

#### AnalystScorecard Component

**Props**:
```typescript
interface AnalystScorecardProps {
  ticker: string;
  broker_breakdown: BrokerEstimate[];
  analyst_scorecards: AnalystScorecard[];
}
```

**Table Columns**:
1. Broker Name
2. Accuracy Tier (A/B/C badge)
3. Hit Rate (%)
4. Directional Accuracy (%)
5. Latest Estimate EPS
6. Days Since Published
7. Weight in SmartEstimate (%)

**Styling**:
- Header: `bg-neutral-900 text-neutral-300 text-xs`
- Tier A rows: `bg-green-900/10`
- Tier B rows: `bg-blue-900/10`
- Tier C rows: `bg-red-900/10`
- Borders: `border-neutral-800`

---

#### EarningsSignalBadge Component

**Props**:
```typescript
interface EarningsSignalBadgeProps {
  signal: "BUY" | "SELL" | "HOLD";
  confidence: number;  // 0-1
  divergence_pct: number;
}
```

**HTML** (example):
```html
<div class="flex items-center gap-2 px-2 py-1 rounded bg-green-900/30">
  <span class="text-xs font-semibold text-green-300">BUY ↑</span>
  <span class="text-[10px] text-neutral-400">+3.95% | 79%</span>
</div>
```

---

### 2.3 Detail Panel

**Expandable side panel** triggered by clicking calendar row.

**Sections**:
1. **Signal Summary** (top)
   - Current signal badge with confidence
   - Divergence % and direction
   - Days to earnings countdown
   - Last updated timestamp

2. **SmartEstimate Comparison Chart** (full width)

3. **Broker Breakdown Table** (top 10 by weight)

4. **PEAD Analysis Section**
   - LineChart of historical PEAD trajectories
   - Summary table: surprise quartile → median CAR at 1d/5d/21d/60d
   - Insight text: "Large surprises (4%+) typically result in median 3.67% drift"

5. **Signal History** (mini table)
   - Last 5 earnings: signal issued, signal correct, surprise actual

---

### 2.4 Screener Integration

**Add column**: "Earnings Signal"

**Cell template**:
```
[TICKER] [SIGNAL] [DIVERGENCE %] [CONFIDENCE]
AAPL     BUY ↑   +3.95%         ■■■■■□ 79%
```

**Styling**:
- BUY: `text-green-400`, arrow ↑
- SELL: `text-red-400`, arrow ↓
- HOLD: `text-neutral-400`, arrow →
- Click cell → Navigate to `/earnings` with ticker detail open

---

### 2.5 State Management

**EarningsContext**:
```typescript
interface EarningsState {
  calendar: EarningRecord[];
  selectedTicker: string | null;
  detailData: EarningsDetail | null;
  scorecards: Map<string, AnalystScorecard[]>;
  pead_profiles: Map<string, PEADRecord[]>;
  loading: boolean;
  lastUpdated: DateTime;
  filter: {
    signal?: "BUY" | "SELL" | "HOLD";
    minDivergence?: number;
    daysAhead?: number;
  };
}

type EarningsAction =
  | { type: "FETCH_CALENDAR"; payload: EarningRecord[] }
  | { type: "SELECT_TICKER"; payload: string }
  | { type: "FETCH_DETAIL"; payload: EarningsDetail }
  | { type: "FETCH_PEAD"; payload: { ticker: string; data: PEADRecord[] } }
  | { type: "SET_FILTER"; payload: Partial<State['filter']> }
  | { type: "WEBSOCKET_SIGNAL_UPDATE"; payload: SignalUpdate };
```

---

### 2.6 Data Fetching

**useEarnings Hook**:
```typescript
function useEarnings(ticker?: string) {
  // GET /api/earnings/calendar (cached 1h, SWR)
  // GET /api/earnings/{ticker}/history (on ticker change)
  // GET /api/earnings/{ticker}/pead (on ticker change)
  // GET /api/earnings/{ticker}/signal (on ticker change)
  // WebSocket: subscribe to earnings.signals

  return {
    calendar,
    detail,
    pead,
    loading,
    error,
    refetch
  };
}
```

---

## Data Models

### 3.1 TypeScript (Frontend)

```typescript
interface Signal {
  ticker: string;
  quarter: string;
  signal: "BUY" | "SELL" | "HOLD";
  confidence: number;  // 0-1
  divergence_pct: number;
  consensus_eps: number;
  smart_estimate_eps: number;
  announce_date: string;  // ISO 8601
  days_to_earnings: number;
  is_forecast: boolean;
  reasoning: string;
  calculated_at: string;
}

interface EarningRecord extends Signal {
  company_name: string;
}

interface EarningsComparisonRecord {
  quarter: string;
  announce_date: string;
  consensus_eps: number;
  smart_estimate_eps: number;
  actual_eps: number;
  divergence_pct: number;
  signal: "BUY" | "SELL" | "HOLD";
  signal_correct: boolean;
  surprise_pct: number;
  car_1d: number;
  car_5d: number;
  car_21d: number;
  car_60d: number;
}

interface BrokerEstimate {
  broker: string;
  estimate_eps: number;
  accuracy_tier: "A" | "B" | "C";
  weight: number;  // 0-1
  days_since_pub: number;
}

interface PEADRecord {
  quarter: string;
  announce_date: string;
  surprise_pct: number;
  surprise_magnitude_bin: string;  // "Q1 (0-1%)", etc.
  signal_at_earnings: "BUY" | "SELL" | "HOLD";
  drift_timeline: Array<{
    days_post_earnings: number;
    car: number;
  }>;
}

interface PEADAggregation {
  [bin: string]: {
    median_car_60d: number;
    mean_car_60d: number;
    sample_size: number;
  };
}
```

### 3.2 Python (Backend)

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class AccuracyTier(str, Enum):
    A = "A"  # >80%
    B = "B"  # 60-80%
    C = "C"  # <60%

@dataclass
class SmartEstimateResult:
    ticker: str
    quarter: str
    consensus_eps: float
    smart_estimate_eps: float
    divergence_pct: float
    signal: SignalType
    confidence: float
    broker_breakdown: List[Dict]
    calculated_at: datetime

@dataclass
class PEADData:
    ticker: str
    quarter: str
    announce_date: datetime
    car_1d: float
    car_5d: float
    car_21d: float
    car_60d: float
    surprise_pct: float
    signal_at_earnings: SignalType
    signal_correct: Optional[bool]
```

---

## Data Flow Diagrams

### 4.1 Signal Generation Flow

```
1. Scheduled: EarningsDataService.ingest_estimates(tickers)
2. yfinance_service.fetch_analyst_estimates()
3. earnings_estimates table ← insert with PiT timestamp
4. SmartEstimateEngine.fetch_estimates()
5. SmartEstimateEngine.calculate_smart_estimate()
   - Apply recency decay: exp(-t/30)
   - Weight by accuracy tier (A/B/C)
   - Weight by broker size
6. SmartEstimateEngine.compare_estimates()
   - Calculate divergence %
7. SmartEstimateEngine.generate_signal()
   - If |divergence| ≥ 2%: BUY/SELL/HOLD
8. earnings_smart_estimates table ← insert signal
9. event_producer.emit("earnings.signal_generated")
10. WebSocket broadcast to /earnings page
11. EarningsCalendar updates in real-time
```

---

### 4.2 Post-Earnings Analysis Flow

```
1. Scheduled: EarningsDataService.ingest_actuals(tickers)
2. yfinance_service.fetch_actual_eps()
3. earnings_actuals table ← insert actual_eps
4. event_producer.emit("earnings.actual_announced")
5. earnings_event_consumer subscribes, triggers:
   PEADAnalyzer.measure_pead(ticker, quarter, announce_date)
6. Fetch 60-day returns post-announce
7. Calculate abnormal_returns = stock_ret - spy_ret
8. Compute CAR at 1d, 5d, 21d, 60d
9. pead_measurements table ← insert CAR timeline
10. PEADAnalyzer.aggregate_pead_by_surprise()
11. Refresh /api/earnings/{ticker}/pead endpoint
12. Frontend: PEADChart updates with new data
```

---

### 4.3 Frontend State Update Flow

```
1. User navigates to /earnings
2. EarningsCalendar mounts
3. useEarnings() → GET /api/earnings/calendar
4. EarningsContext dispatches FETCH_CALENDAR
5. Calendar renders, sorted by days_to_earnings
6. User clicks row (e.g., AAPL)
7. EarningsContext dispatches SELECT_TICKER("AAPL")
8. Detail panel opens, fetches:
   - GET /api/earnings/AAPL/history
   - GET /api/earnings/AAPL/pead
   - GET /api/earnings/AAPL/signal
9. EarningsContext dispatches FETCH_DETAIL
10. Charts render: SmartEstimateComparison, PEADChart, Scorecard
11. WebSocket listens to earnings.signals channel
12. New signal → WEBSOCKET_SIGNAL_UPDATE → Calendar re-renders
```

---

## Integration Points

### 5.1 Service Dependencies

| Service | Integration | Purpose |
|---------|-----------|---------|
| **yfinance_service** | fetch_estimates(), fetch_actuals() | Core data |
| **weight_calculator** | Recency decay, accuracy tier weighting | SmartEstimate |
| **statistics_calculator** | CAR computation, aggregation | PEAD |
| **portfolio_math** | Return calculations | Abnormal returns |
| **screener** | Filter by earnings signal | Signal column |
| **backtester** | Trade on signals, measure PEAD | Strategy testing |
| **factor_calculator** | Earnings surprise as factor | Factor exposure |
| **event_producer** | earnings events | Signal/actual broadcast |
| **event_consumer** | PEAD triggering | Post-earnings workflows |

### 5.2 Event Integration

**Earnings Event Channel**:
```
earnings.estimate_ingested → SmartEstimateEngine.calculate_smart_estimate()
earnings.signal_generated → WebSocket broadcast + Screener refresh
earnings.actual_announced → PEADAnalyzer.measure_pead()
```

---

## Implementation Roadmap

### Phase 3a: Backend Core (Weeks 1-2)
- [ ] SmartEstimateEngine service
- [ ] Recency decay + accuracy tier + broker size weighting
- [ ] EarningsDataService for ingestion
- [ ] Create database tables
- [ ] Implement /api/earnings endpoints (calendar, signal, history)

### Phase 3b: PEAD & Integration (Weeks 2-3)
- [ ] PEADAnalyzer service
- [ ] CAR calculation (1d, 5d, 21d, 60d)
- [ ] Aggregate PEAD by surprise quartile
- [ ] Create pead_measurements table
- [ ] Implement /api/earnings/{ticker}/pead endpoint
- [ ] Event integration: earnings.actual_announced → measure_pead()

### Phase 3c: Frontend (Weeks 3-4)
- [ ] EarningsContext + useEarnings hook
- [ ] EarningsCalendar component (sortable, filterable)
- [ ] SmartEstimateComparison chart
- [ ] PEADChart component
- [ ] AnalystScorecard table
- [ ] Build /earnings page layout

### Phase 3d: Polish & Integration (Weeks 4-5)
- [ ] WebSocket real-time signal updates
- [ ] Screener integration: "Earnings Signal" column
- [ ] Backtester strategy: earnings signals + PEAD exit
- [ ] Performance optimization (caching, indexing)
- [ ] QA & edge case testing

---

## Performance & Scaling

### Database Indexing

```sql
CREATE INDEX idx_earnings_smart_active ON earnings_smart_estimates(ticker, is_active);
CREATE INDEX idx_earnings_smart_signal ON earnings_smart_estimates(signal);
CREATE INDEX idx_earnings_actuals_ticker_quarter ON earnings_actuals(ticker, quarter);
CREATE INDEX idx_pead_ticker_announce ON pead_measurements(ticker, announce_date DESC);
CREATE INDEX idx_analyst_scorecards_tier ON analyst_scorecards(accuracy_tier);
```

### Caching Strategy

- **Calendar**: 1h (earnings dates immutable)
- **Signal**: 4h (recalculate at market open/close)
- **PEAD**: 24h (historical data immutable)
- **Scorecards**: 7d (accuracy metrics update weekly)

### API Rate Limiting

- `/api/earnings/calendar`: 100 req/min
- `/api/earnings/{ticker}/history`: 50 req/min per IP
- `/api/earnings/refresh`: 5 req/min (admin only)

### Batch Processing

- Nightly: `ingest_estimates()` (11 PM UTC)
- Weekly: `update_analyst_scorecards()` (Sunday 2 AM UTC)
- Post-market: `aggregate_pead_by_surprise()` (4:30 PM UTC)

---

## Testing Strategy

### Unit Tests

**SmartEstimateEngine**:
- Recency decay: exp(-t/30) formula correctness
- Accuracy tier weighting: A=1.5x, B=1.0x, C=0.5x
- Signal generation: ≥2% divergence threshold
- Edge cases: zero consensus, missing brokers

**PEADAnalyzer**:
- CAR calculation: abnormal_return aggregation
- Surprise binning: correct quartile assignment
- Aggregate statistics: median, mean, sample size

**EarningsDataService**:
- PiT timestamp handling
- Quarter matching logic
- Scorecard update edge cases

### Integration Tests

- Endpoints return properly formatted JSON
- Broker breakdown includes correct weights
- PEAD history joined with signal accuracy
- WebSocket signal updates propagate

### E2E Tests

- User navigates /earnings → Calendar loads
- Click row → Detail panel opens with all charts
- Screener displays "Earnings Signal" column
- New signal → WebSocket update → Badge changes

---

## Monitoring & Observability

### Key Metrics

- `earnings_estimates_ingested_count` (daily)
- `earnings_actuals_latency_minutes` (announce → ingestion)
- `signal_directional_accuracy_pct` (quarterly)
- `pead_measurement_completion_rate_pct`
- `api_earnings_p99_latency_ms`

### Logging

- Signal generation: ticker, signal, divergence, confidence
- Ingestion events: count, source, errors
- PEAD completion: ticker, quarter, CAR milestones

### Alerting

- No signals for >10 days → Alert
- PEAD measurement stalled >5 days → Alert
- Scorecard updates stale >10 days → Alert
- API p99 latency >500ms → Alert

---

## Security & Data Integrity

### Input Validation

- Ticker: `^[A-Z]{1,5}$`
- Quarter: `^20\d{2}Q[1-4]$`
- Divergence: [-100, +500] range
- Confidence: [0, 1] range

### Data Integrity

- Foreign key constraints on all ticker references
- NOT NULL on: consensus_eps, smart_estimate_eps
- UNIQUE constraints on (ticker, quarter)

### Audit Logging

- All scorecard updates with old/new values
- Manual refresh triggers with user ID
- API calls to /api/earnings/refresh

---

## Conclusion

This architecture delivers a production-grade Earnings Surprise Predictor with:

1. **SmartEstimate Engine**: ~70% directional accuracy through weighted consensus
2. **PEAD Analysis**: Post-announcement drift tracking over 60 days
3. **Analyst Scorecards**: Hit rate and directional accuracy per broker
4. **Real-time Signals**: WebSocket-driven updates to frontend
5. **Deep Integration**: Screener column, Backtester strategies, Factor exposure
6. **Scalable Backend**: Batch processing, caching, indexed queries
7. **Intuitive Frontend**: Calendar view, detail panels, interactive charts

The modular design enables incremental rollout, comprehensive testing, and easy maintenance.
