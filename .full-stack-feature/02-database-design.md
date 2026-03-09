# Event Scanner Database Design (Phase 2)

## Overview

The Event Scanner Phase 2 extends AlphaDesk's PostgreSQL database with a Complex Event Processing (CEP) system. This document specifies the new tables, relationships, indexing strategy, and SQLModel definitions required to detect, classify, score, and analyze corporate events for alpha prediction.

The design maintains full integration with existing Phase 1 tables (security, price_history, factor_definition, backtest, etc.) while introducing event-specific storage and processing capabilities.

---

## 1. Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                       PHASE 1: EXISTING TABLES                       │
├─────────────────────────────────────────────────────────────────────┤
│  security (ticker PK)                                               │
│  price_history (ticker FK → security)                              │
│  factor_definition (id PK)                                         │
│  backtest (id PK)                                                  │
│  backtest_result (backtest_id FK, date)                            │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────────────────────────────────────────────┐
            │        PHASE 2: EVENT SCANNER TABLES (NEW)          │
            ├─────────────────────────────────────────────────────┤
            │                                                     │
            │  event                                              │
            │  ├─ event_id (PK)                                   │
            │  ├─ ticker (FK → security)                          │
            │  ├─ event_type (earnings, M&A, insider_trade, ...) │
            │  ├─ event_classification (detected_classification)  │
            │  ├─ severity_score (1-5)                            │
            │  ├─ detected_at (PiT: detection timestamp)          │
            │  ├─ event_date (when event occurred)                │
            │  └─ source (SEC_EDGAR, YFINANCE)                    │
            │                                                     │
            │  event_classification_rule                          │
            │  ├─ rule_id (PK)                                    │
            │  ├─ classification (event_type)                     │
            │  ├─ pattern_type (keyword, filing_form, calendar)   │
            │  ├─ pattern_value (JSON for keywords/patterns)      │
            │  └─ confidence (0-100)                              │
            │                                                     │
            │  alpha_decay_window                                 │
            │  ├─ window_id (PK)                                  │
            │  ├─ event_id (FK → event)                           │
            │  ├─ window_type ([0,+1d], [0,+5d], [0,+21d], ...) │
            │  ├─ abnormal_return (measured return%)              │
            │  ├─ measured_at (PiT: measurement timestamp)        │
            │  └─ confidence (statistical significance)           │
            │                                                     │
            │  event_factor_bridge                                │
            │  ├─ bridge_id (PK)                                  │
            │  ├─ event_id (FK → event)                           │
            │  ├─ factor_id (FK → factor_definition)              │
            │  ├─ signal_value (event signal strength, -1 to +1)  │
            │  ├─ created_at (when bridge was created)            │
            │  └─ valid_until (when signal expires)               │
            │                                                     │
            │  event_source_mapping                               │
            │  ├─ mapping_id (PK)                                 │
            │  ├─ event_id (FK → event)                           │
            │  ├─ source_type (SEC_EDGAR_8K, YFINANCE_EARNINGS...) │
            │  ├─ source_url (link to filing or calendar)         │
            │  ├─ source_id (form accession number, etc.)         │
            │  └─ extracted_data (JSON: metadata)                 │
            │                                                     │
            │  event_alert_configuration                          │
            │  ├─ config_id (PK)                                  │
            │  ├─ user_id or portfolio_id (scope)                 │
            │  ├─ event_type_filter (specific types or all)       │
            │  ├─ severity_threshold (min 1-5)                    │
            │  ├─ enabled (boolean)                               │
            │  └─ updated_at                                      │
            │                                                     │
            │  event_correlation_analysis                         │
            │  ├─ analysis_id (PK)                                │
            │  ├─ event_type_1 (e.g., insider_trade)             │
            │  ├─ event_type_2 (e.g., M&A)                        │
            │  ├─ co_occurrence_count (# of coincident events)    │
            │  ├─ time_window_days (days within which occurred)   │
            │  ├─ correlation_strength (0-1)                      │
            │  └─ analyzed_period_end (PiT date)                  │
            │                                                     │
            └─────────────────────────────────────────────────────┘
```

---

## 2. New Table Definitions

### 2.1 event

**Purpose**: Core event storage. Every corporate event detected from SEC EDGAR or yfinance creates one record.

**PiT Strategy**:
- `detected_at` (timestamp): When the event was first detected by the system (immutable, set at insertion)
- `event_date` (date): When the corporate event actually occurred (what happened in the market)
- All queries filter by `detected_at` to ensure point-in-time consistency when backtesting

**Columns**:

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| event_id | BIGSERIAL | PK, NOT NULL | Unique identifier for this event |
| ticker | VARCHAR(10) | FK→security.ticker, NOT NULL | Security being affected |
| event_type | VARCHAR(50) | NOT NULL, CHECK IN (earnings, M&A, insider_trade, dividend_change, SEC_filing, management_change, guidance_revision, share_repurchase) | Event classification taxonomy |
| event_classification_id | INTEGER | FK→event_classification_rule.rule_id, NOT NULL | Rule used to classify this event |
| severity_score | SMALLINT | NOT NULL, CHECK BETWEEN 1 AND 5 | Severity impact (1=minimal, 5=severe) |
| detected_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | When system detected the event (PiT reference) |
| event_date | DATE | NOT NULL | When the event occurred in reality |
| source | VARCHAR(50) | NOT NULL, CHECK IN (SEC_EDGAR, YFINANCE, MANUAL) | Data source of event |
| headline | VARCHAR(255) | NOT NULL | Short description of event |
| description | TEXT | NULL | Detailed description or extracted text |
| metadata | JSONB | NULL | Source-specific metadata (accession number, filing form, etc.) |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Record creation time |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Last update time |

**Indexes**:
- `idx_event_ticker` (ticker)
- `idx_event_type` (event_type)
- `idx_event_detected_at` (detected_at DESC) — PiT enforcement
- `idx_event_event_date` (event_date DESC)
- `idx_event_severity` (severity_score DESC)
- `idx_event_ticker_detected` (ticker, detected_at DESC) — Common query pattern
- `idx_event_ticker_date_type` (ticker, event_date, event_type) — Timeline queries
- `idx_event_source` (source)

**Unique Constraint**:
- `uq_event_ticker_type_date_source` (ticker, event_type, event_date, source) — Prevent duplicate events from same source on same day

---

### 2.2 event_classification_rule

**Purpose**: Define rules for classifying raw detected events. Maps keywords, SEC filing forms, calendar events to event types.

**Columns**:

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| rule_id | SERIAL | PK, NOT NULL | Rule identifier |
| classification | VARCHAR(50) | NOT NULL, CHECK IN (earnings, M&A, insider_trade, ...) | Event type this rule produces |
| pattern_type | VARCHAR(50) | NOT NULL, CHECK IN (keyword, filing_form, calendar_event, net_trading_volume) | Pattern matching strategy |
| pattern_value | JSONB | NOT NULL | Pattern data: keywords array, form list, calendar event type, thresholds |
| confidence_score | SMALLINT | DEFAULT 80, CHECK BETWEEN 0 AND 100 | Confidence (0-100) that pattern indicates event |
| enabled | BOOLEAN | DEFAULT TRUE | Enable/disable rule without deletion |
| description | TEXT | NULL | Rule documentation |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Rule creation date |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Last update |

**Indexes**:
- `idx_classification_rule_enabled` (enabled) — Only query active rules
- `idx_classification_rule_type` (classification, enabled)
- `idx_classification_rule_pattern` (pattern_type)

**Example Records**:
```json
{
  "rule_id": 1,
  "classification": "earnings",
  "pattern_type": "calendar_event",
  "pattern_value": {"event_type": "earnings_date"},
  "confidence_score": 95
}

{
  "rule_id": 2,
  "classification": "insider_trade",
  "pattern_type": "filing_form",
  "pattern_value": {"forms": ["4", "5"]},
  "confidence_score": 100
}

{
  "rule_id": 3,
  "classification": "M&A",
  "pattern_type": "keyword",
  "pattern_value": {"keywords": ["acquisition", "merger", "acquired by", "acquired", "to acquire"]},
  "confidence_score": 75
}
```

---

### 2.3 alpha_decay_window

**Purpose**: Stores measured abnormal returns in predefined windows post-event. Enables alpha decay analysis and decay charts on event detail views.

**PiT Strategy**:
- `measured_at` (timestamp): When the alpha decay window was calculated/updated
- Links to `event.detected_at` for temporal consistency
- Data in this table accumulated as time passes (e.g., [0,+1d] window closes after 1 day post-event, then [0,+5d] closes after 5 days, etc.)

**Columns**:

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| window_id | BIGSERIAL | PK, NOT NULL | Unique identifier |
| event_id | BIGINT | FK→event.event_id, NOT NULL | Parent event |
| window_type | VARCHAR(20) | NOT NULL, CHECK IN ([0,+1d], [0,+5d], [0,+21d], [0,+63d]) | Time window post-event |
| abnormal_return | NUMERIC(12, 6) | NOT NULL | Measured abnormal return (%) during window |
| benchmark_return | NUMERIC(12, 6) | NULL | Benchmark return during window (optional) |
| volatility | NUMERIC(12, 6) | NULL | Stock volatility during window |
| volume_spike | NUMERIC(10, 4) | NULL | Volume as multiple of average (e.g., 2.5 = 250% of normal) |
| trading_volume | BIGINT | NULL | Total shares traded during window |
| confidence_score | SMALLINT | DEFAULT 50, CHECK BETWEEN 0 AND 100 | Statistical significance (0-100) |
| data_points | INTEGER | DEFAULT 0 | Number of price points in window (for validation) |
| measured_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | When measurement was taken (PiT) |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Record insertion |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Last update (if recalculated) |

**Indexes**:
- `idx_alpha_decay_event` (event_id)
- `idx_alpha_decay_window_type` (window_type)
- `idx_alpha_decay_measured_at` (measured_at DESC) — PiT queries
- `idx_alpha_decay_event_window` (event_id, window_type) — Unique window per event
- `idx_alpha_decay_confidence` (confidence_score DESC) — High-confidence windows

**Unique Constraint**:
- `uq_alpha_decay_event_window` (event_id, window_type) — One measurement per window per event

---

### 2.4 event_factor_bridge

**Purpose**: Bridge between detected events and the Factor Backtester. When an event is detected and classified, it becomes a backtestable factor signal.

**PiT Strategy**:
- `created_at`: When the bridge was created (event detected → factor signal generated)
- `valid_until`: When the signal expires (e.g., post-event alpha decay window closes)
- Queries filter by valid_until >= analysis_date to ensure temporal consistency

**Columns**:

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| bridge_id | BIGSERIAL | PK, NOT NULL | Unique identifier |
| event_id | BIGINT | FK→event.event_id, NOT NULL | Parent event |
| factor_id | INTEGER | FK→factor_definition.id, NOT NULL | Generated factor |
| signal_value | NUMERIC(8, 6) | NOT NULL, CHECK BETWEEN -1 AND 1 | Signal strength: -1 (strong short) to +1 (strong long) |
| signal_confidence | SMALLINT | DEFAULT 50, CHECK BETWEEN 0 AND 100 | Confidence in signal (0-100) |
| signal_expiry_window | VARCHAR(20) | DEFAULT [0,+21d] | Which alpha window this signal is valid for |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | When bridge created |
| valid_until | TIMESTAMP WITH TIME ZONE | NOT NULL | When signal expires (event_date + window duration) |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Last update |

**Indexes**:
- `idx_bridge_event` (event_id)
- `idx_bridge_factor` (factor_id)
- `idx_bridge_valid_until` (valid_until DESC) — Active signal queries
- `idx_bridge_factor_valid` (factor_id, valid_until DESC) — Factor backtest queries
- `idx_bridge_created_at` (created_at DESC)

**Unique Constraint**:
- `uq_bridge_event_factor` (event_id, factor_id) — One bridge per event-factor pair

**Signal Value Logic**:
- earnings + surprise_magnitude > 5%: signal_value = +0.8
- insider_trade + high_volume: signal_value = +0.6
- M&A + strategic_fit: signal_value = +0.7
- guidance_revision + downward: signal_value = -0.7

---

### 2.5 event_source_mapping

**Purpose**: Link events back to original data sources (SEC EDGAR accession numbers, yfinance URLs, etc.). Enables source tracing and deduplication.

**Columns**:

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| mapping_id | BIGSERIAL | PK, NOT NULL | Unique identifier |
| event_id | BIGINT | FK→event.event_id, NOT NULL | Parent event |
| source_type | VARCHAR(50) | NOT NULL, CHECK IN (SEC_EDGAR_8K, SEC_EDGAR_10K, SEC_EDGAR_10Q, SEC_EDGAR_SC13D, SEC_EDGAR_SC13G, SEC_EDGAR_FORM4, YFINANCE_EARNINGS, YFINANCE_DIVIDEND) | Specific source type |
| source_url | VARCHAR(500) | NOT NULL | URL to original source |
| source_id | VARCHAR(100) | NULL | Unique ID from source (e.g., accession number) |
| extracted_data | JSONB | NULL | Parsed/extracted metadata from source |
| raw_content_hash | VARCHAR(64) | NULL | SHA-256 hash of raw content for deduplication |
| ingested_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | When data was pulled from source |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Record creation |

**Indexes**:
- `idx_source_mapping_event` (event_id)
- `idx_source_mapping_type` (source_type)
- `idx_source_mapping_source_id` (source_id) — Deduplication
- `idx_source_mapping_hash` (raw_content_hash) — Deduplication
- `idx_source_mapping_ingested` (ingested_at DESC)

**Unique Constraint**:
- `uq_source_mapping_event_type` (event_id, source_type) — One mapping per source type per event

**Example extracted_data JSON**:
```json
{
  "accession_number": "0001193125-26-001234",
  "filing_date": "2026-03-10",
  "form_type": "8-K",
  "cik": "0000320193",
  "company_name": "Apple Inc.",
  "item_numbers": ["8.01"],
  "event_date": "2026-03-10"
}
```

---

### 2.6 event_alert_configuration

**Purpose**: User/portfolio alert preferences. Enables filtering events by type and severity.

**Columns**:

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| config_id | SERIAL | PK, NOT NULL | Configuration identifier |
| user_id | VARCHAR(100) | NOT NULL (or NULL if portfolio_id set) | User owning this config |
| portfolio_id | INTEGER | NULL (or NOT NULL if user_id set) | Portfolio owning this config |
| scope | VARCHAR(50) | DEFAULT global, CHECK IN (global, portfolio, ticker) | Scope of alerts |
| scope_value | VARCHAR(100) | NULL | Ticker or portfolio name if scope is portfolio/ticker |
| event_type_filter | TEXT | DEFAULT all, CHECK IN (all, earnings, M&A, insider_trade, dividend_change, SEC_filing, management_change, guidance_revision, share_repurchase) | Comma-separated event types to monitor |
| min_severity_threshold | SMALLINT | DEFAULT 1, CHECK BETWEEN 1 AND 5 | Minimum severity (1-5) to alert |
| alert_enabled | BOOLEAN | DEFAULT TRUE | Enable/disable alerts |
| notification_method | VARCHAR(50) | DEFAULT in_app, CHECK IN (in_app, email, webhook) | How to notify user |
| webhook_url | VARCHAR(500) | NULL | If notification_method = webhook |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Configuration creation |
| updated_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Last configuration update |

**Indexes**:
- `idx_alert_config_user` (user_id)
- `idx_alert_config_portfolio` (portfolio_id)
- `idx_alert_config_enabled` (alert_enabled)
- `idx_alert_config_scope` (scope, scope_value)

---

### 2.7 event_correlation_analysis

**Purpose**: Track event co-occurrence patterns. E.g., insider buying often precedes M&A.

**PiT Strategy**:
- `analyzed_period_end` (date): Data point for historical trend analysis
- New records appended periodically (e.g., weekly) with updated correlations

**Columns**:

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| analysis_id | BIGSERIAL | PK, NOT NULL | Unique identifier |
| event_type_1 | VARCHAR(50) | NOT NULL, CHECK IN (earnings, M&A, insider_trade, ...) | First event type |
| event_type_2 | VARCHAR(50) | NOT NULL, CHECK IN (earnings, M&A, insider_trade, ...) | Second event type |
| time_window_days | SMALLINT | DEFAULT 30, CHECK BETWEEN 1 AND 365 | Days within which events co-occurred |
| co_occurrence_count | INTEGER | DEFAULT 0 | Number of instances where both events occurred within window |
| total_event_type_1_count | INTEGER | DEFAULT 0 | Total occurrences of event_type_1 in period |
| total_event_type_2_count | INTEGER | DEFAULT 0 | Total occurrences of event_type_2 in period |
| correlation_strength | NUMERIC(6, 4) | DEFAULT 0.0, CHECK BETWEEN 0 AND 1 | Pearson correlation (0-1) |
| chi_square_statistic | NUMERIC(12, 4) | NULL | Chi-square test value (statistical significance) |
| p_value | NUMERIC(8, 6) | NULL | P-value for significance test |
| analyzed_period_start | DATE | NOT NULL | Period analysis began |
| analyzed_period_end | DATE | NOT NULL | Period analysis ended |
| created_at | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT NOW() | Analysis creation |

**Indexes**:
- `idx_correlation_event_types` (event_type_1, event_type_2)
- `idx_correlation_period` (analyzed_period_end DESC)
- `idx_correlation_strength` (correlation_strength DESC)

**Unique Constraint**:
- `uq_correlation_types_window` (event_type_1, event_type_2, time_window_days, analyzed_period_end) — One analysis per type pair per window per period

---

## 3. SQLModel Schema Definitions

```python
# backend/models/events.py

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, date, timedelta
from enum import Enum
import json
from decimal import Decimal
import sqlalchemy as sa

# Enums for validation

class EventTypeEnum(str, Enum):
    EARNINGS = "earnings"
    M_A = "M&A"
    INSIDER_TRADE = "insider_trade"
    DIVIDEND_CHANGE = "dividend_change"
    SEC_FILING = "SEC_filing"
    MANAGEMENT_CHANGE = "management_change"
    GUIDANCE_REVISION = "guidance_revision"
    SHARE_REPURCHASE = "share_repurchase"

class EventSourceEnum(str, Enum):
    SEC_EDGAR = "SEC_EDGAR"
    YFINANCE = "YFINANCE"
    MANUAL = "MANUAL"

class PatternTypeEnum(str, Enum):
    KEYWORD = "keyword"
    FILING_FORM = "filing_form"
    CALENDAR_EVENT = "calendar_event"
    NET_TRADING_VOLUME = "net_trading_volume"

class AlphaWindowTypeEnum(str, Enum):
    WINDOW_1D = "[0,+1d]"
    WINDOW_5D = "[0,+5d]"
    WINDOW_21D = "[0,+21d]"
    WINDOW_63D = "[0,+63d]"

class SourceTypeEnum(str, Enum):
    SEC_EDGAR_8K = "SEC_EDGAR_8K"
    SEC_EDGAR_10K = "SEC_EDGAR_10K"
    SEC_EDGAR_10Q = "SEC_EDGAR_10Q"
    SEC_EDGAR_SC13D = "SEC_EDGAR_SC13D"
    SEC_EDGAR_SC13G = "SEC_EDGAR_SC13G"
    SEC_EDGAR_FORM4 = "SEC_EDGAR_FORM4"
    YFINANCE_EARNINGS = "YFINANCE_EARNINGS"
    YFINANCE_DIVIDEND = "YFINANCE_DIVIDEND"

class AlertScopeEnum(str, Enum):
    GLOBAL = "global"
    PORTFOLIO = "portfolio"
    TICKER = "ticker"

class NotificationMethodEnum(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"

# Core Models

class EventClassificationRule(SQLModel, table=True):
    """Classification rules for event detection."""
    __tablename__ = "event_classification_rule"

    rule_id: Optional[int] = Field(default=None, primary_key=True)
    classification: EventTypeEnum = Field(index=True)
    pattern_type: PatternTypeEnum = Field(index=True)
    pattern_value: dict = Field(sa_column=sa.Column(sa.JSON))
    confidence_score: int = Field(default=80, ge=0, le=100)
    enabled: bool = Field(default=True, index=True)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Event(SQLModel, table=True):
    """Detected corporate event."""
    __tablename__ = "event"

    event_id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(foreign_key="security.ticker", index=True)
    event_type: EventTypeEnum = Field(index=True)
    event_classification_id: int = Field(foreign_key="event_classification_rule.rule_id")
    severity_score: int = Field(ge=1, le=5, index=True)
    detected_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    event_date: date = Field(index=True)
    source: EventSourceEnum = Field(index=True)
    headline: str = Field(max_length=255)
    description: Optional[str] = None
    metadata: Optional[dict] = Field(default=None, sa_column=sa.Column(sa.JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    classification_rule: EventClassificationRule = Relationship()
    alpha_decay_windows: List["AlphaDecayWindow"] = Relationship(back_populates="event")
    factor_bridges: List["EventFactorBridge"] = Relationship(back_populates="event")
    source_mappings: List["EventSourceMapping"] = Relationship(back_populates="event")

class AlphaDecayWindow(SQLModel, table=True):
    """Alpha decay measurements for event post-impact period."""
    __tablename__ = "alpha_decay_window"

    window_id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.event_id", index=True)
    window_type: AlphaWindowTypeEnum = Field(index=True)
    abnormal_return: Decimal = Field(decimal_places=6, precision=12)
    benchmark_return: Optional[Decimal] = Field(default=None, decimal_places=6, precision=12)
    volatility: Optional[Decimal] = Field(default=None, decimal_places=6, precision=12)
    volume_spike: Optional[Decimal] = Field(default=None, decimal_places=4, precision=10)
    trading_volume: Optional[int] = None
    confidence_score: int = Field(default=50, ge=0, le=100, index=True)
    data_points: int = Field(default=0)
    measured_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    event: Event = Relationship(back_populates="alpha_decay_windows")

class EventFactorBridge(SQLModel, table=True):
    """Bridge between events and backtestable factors."""
    __tablename__ = "event_factor_bridge"

    bridge_id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.event_id", index=True)
    factor_id: int = Field(foreign_key="factor_definition.id", index=True)
    signal_value: Decimal = Field(decimal_places=6, precision=8, ge=-1, le=1)
    signal_confidence: int = Field(default=50, ge=0, le=100)
    signal_expiry_window: AlphaWindowTypeEnum = Field(default="[0,+21d]")
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    valid_until: datetime = Field(index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    event: Event = Relationship(back_populates="factor_bridges")

class EventSourceMapping(SQLModel, table=True):
    """Maps events to original source URLs and metadata."""
    __tablename__ = "event_source_mapping"

    mapping_id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.event_id", index=True)
    source_type: SourceTypeEnum = Field(index=True)
    source_url: str = Field(max_length=500)
    source_id: Optional[str] = Field(default=None, max_length=100, index=True)
    extracted_data: Optional[dict] = Field(default=None, sa_column=sa.Column(sa.JSON))
    raw_content_hash: Optional[str] = Field(default=None, max_length=64, index=True)
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    event: Event = Relationship(back_populates="source_mappings")

class EventAlertConfiguration(SQLModel, table=True):
    """User alert preferences for events."""
    __tablename__ = "event_alert_configuration"

    config_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[str] = Field(default=None, index=True)
    portfolio_id: Optional[int] = Field(default=None, index=True)
    scope: AlertScopeEnum = Field(default=AlertScopeEnum.GLOBAL)
    scope_value: Optional[str] = Field(default=None, max_length=100)
    event_type_filter: str = Field(default="all")
    min_severity_threshold: int = Field(default=1, ge=1, le=5)
    alert_enabled: bool = Field(default=True, index=True)
    notification_method: NotificationMethodEnum = Field(default=NotificationMethodEnum.IN_APP)
    webhook_url: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class EventCorrelationAnalysis(SQLModel, table=True):
    """Event co-occurrence patterns."""
    __tablename__ = "event_correlation_analysis"

    analysis_id: Optional[int] = Field(default=None, primary_key=True)
    event_type_1: EventTypeEnum = Field(index=True)
    event_type_2: EventTypeEnum = Field(index=True)
    time_window_days: int = Field(default=30, ge=1, le=365)
    co_occurrence_count: int = Field(default=0)
    total_event_type_1_count: int = Field(default=0)
    total_event_type_2_count: int = Field(default=0)
    correlation_strength: Decimal = Field(
        default=Decimal(0),
        decimal_places=4,
        precision=6,
        ge=0,
        le=1
    )
    chi_square_statistic: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        precision=12
    )
    p_value: Optional[Decimal] = Field(default=None, decimal_places=6, precision=8)
    analyzed_period_start: date
    analyzed_period_end: date = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 4. Event Classification and Severity Storage Strategy

### 4.1 Classification Engine

The `event_classification_rule` table stores pattern-matching rules. When raw data is ingested:

1. **SEC EDGAR RSS parsing**:
   - Pattern type: `filing_form`
   - Extracts form type (8-K, 10-K, etc.)
   - Matches against rules: 8-K → `SEC_filing`, Form 4 → `insider_trade`, etc.

2. **SEC filing item matching**:
   - 8-K item 1.01 (material agreement) → `M&A`
   - 8-K item 2.05 (costs associated with exit/disposal) → Potential `guidance_revision`
   - 8-K item 5.02 (costs associated with exit/disposal) → `management_change`

3. **yfinance calendar integration**:
   - Pattern type: `calendar_event`
   - Earnings date → `earnings`
   - Ex-dividend date → `dividend_change`

4. **Keyword matching** (for NLP-enhanced detection later):
   - Pattern type: `keyword`
   - Keywords like ["acquisition", "merger", "acquired"] → `M&A`
   - Confidence scores reflect pattern reliability

5. **Volume anomalies** (Form 4 filing volume):
   - Pattern type: `net_trading_volume`
   - High insider buying volume in short period → `insider_trade` with high severity

### 4.2 Severity Scoring

Severity (1-5) determined by historical impact magnitude:

```python
def calculate_severity(event_type: str, magnitude: float) -> int:
    """
    magnitude = abnormal return over window [0, +5d]
    """
    if event_type == "earnings":
        # EPS surprise magnitude
        if magnitude > 10: return 5
        elif magnitude > 5: return 4
        elif magnitude > 2: return 3
        elif magnitude > 0.5: return 2
        else: return 1

    elif event_type == "M&A":
        # Deal impact (implied premium)
        if magnitude > 15: return 5
        elif magnitude > 8: return 4
        elif magnitude > 4: return 3
        elif magnitude > 2: return 2
        else: return 1

    elif event_type == "insider_trade":
        # Trading volume relative to market cap
        if magnitude > 20: return 5
        elif magnitude > 10: return 4
        elif magnitude > 5: return 3
        elif magnitude > 1: return 2
        else: return 1

    # ... similar for other types
```

Severity stored with event; can be refined retroactively as new price data arrives.

---

## 5. Alpha Decay Window Storage and Calculation

### 5.1 Window Design

Four predefined windows measure abnormal returns post-event:

```
event_date = 2026-01-15 (announced)
trading_days_offset: [0, +1d], [0, +5d], [0, +21d], [0, +63d]

price_date range for [0,+1d]: 2026-01-15 to 2026-01-16
price_date range for [0,+5d]: 2026-01-15 to 2026-01-22 (5 trading days)
price_date range for [0,+21d]: 2026-01-15 to 2026-02-09 (21 trading days)
price_date range for [0,+63d]: 2026-01-15 to 2026-03-31 (63 trading days)
```

### 5.2 Calculation Query Pattern

```sql
-- Calculate alpha decay for event on 2026-01-15 for 5-day window
WITH event_details AS (
    SELECT event_id, ticker, event_date, detected_at
    FROM event
    WHERE event_id = $1
),
prices_before AS (
    SELECT
        ticker,
        AVG(adjusted_close) as baseline_price,
        STDDEV_POP(daily_return) as baseline_volatility
    FROM price_history
    WHERE ticker = $2
        AND date < (SELECT event_date FROM event_details)
        AND date >= (SELECT event_date FROM event_details) - INTERVAL '252 days'
        AND ingestion_timestamp <= (SELECT detected_at FROM event_details)
),
prices_during_window AS (
    SELECT
        ticker,
        date,
        adjusted_close,
        (adjusted_close - LAG(adjusted_close) OVER (ORDER BY date)) /
            LAG(adjusted_close) OVER (ORDER BY date) as daily_return,
        SUM(volume) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
            as cumulative_volume
    FROM price_history
    WHERE ticker = $2
        AND date >= (SELECT event_date FROM event_details)
        AND date <= (SELECT event_date FROM event_details) + INTERVAL '5 days'
        AND ingestion_timestamp <= (SELECT detected_at FROM event_details) + INTERVAL '10 days'
),
abnormal_returns AS (
    SELECT
        (adjusted_close - (SELECT baseline_price FROM prices_before)) /
            (SELECT baseline_price FROM prices_before) * 100 as return_pct,
        (daily_return - (SELECT baseline_volatility FROM prices_before)) as excess_return
    FROM prices_during_window
),
window_summary AS (
    SELECT
        SUM(excess_return) / COUNT(*) as abnormal_return,
        STDDEV_POP(excess_return) as volatility,
        (SELECT cumulative_volume FROM prices_during_window ORDER BY date DESC LIMIT 1)
            as trading_volume
    FROM abnormal_returns
)
INSERT INTO alpha_decay_window
    (event_id, window_type, abnormal_return, volatility, trading_volume, measured_at)
SELECT
    $1,
    '[0,+5d]'::varchar,
    abnormal_return,
    volatility,
    trading_volume,
    NOW()
FROM window_summary;
```

### 5.3 PiT Enforcement for Alpha Decay

- When calculating alpha decay at analysis_date, only use price_history records where `ingestion_timestamp <= analysis_date`
- Store `measured_at` in alpha_decay_window to track when calculation occurred
- Supports retroactive updates: if price data was corrected, recalculate and update alpha_decay_window.updated_at

---

## 6. Event-to-Factor Bridge: Making Events Backtestable

### 6.1 Bridge Table Purpose

The `event_factor_bridge` table converts events into factor signals for the Factor Backtester. When an event is detected:

```
Event: Earnings surprise +8%
→ Classify as: earnings event_type
→ Calculate severity: 4/5 (8% surprise)
→ Create Factor: "earnings_event_earnings_surprise_Q126" (or reuse existing)
→ Create Bridge: event_id=123 → factor_id=456, signal_value=+0.8 (bullish)
→ Set valid_until: event_date + 21 days (alpha decay window)
```

### 6.2 Factor Generation from Events

**Automatic factor creation** (if not already exists):

```python
def create_event_signal_factor(event_type: EventTypeEnum, magnitude: float) -> int:
    """
    Creates or retrieves a factor for event signal.
    Returns factor_id.
    """
    factor_name = f"event_{event_type.value}_signal"

    # Check if factor exists
    factor = db.query(FactorDefinition).filter_by(
        factor_name=factor_name,
        factor_type="event"
    ).first()

    if factor:
        return factor.id

    # Create new factor
    new_factor = FactorDefinition(
        factor_name=factor_name,
        factor_type="event",
        description=f"Signal-based factor from {event_type} events",
        frequency="daily",
        is_published=True,
        publication_date=date.today()
    )
    db.add(new_factor)
    db.commit()
    return new_factor.id
```

### 6.3 Signal Value Calculation

Signal value (-1 to +1) represents predicted directional impact:

```python
def calculate_signal_value(
    event_type: EventTypeEnum,
    severity: int,
    direction: str  # "positive", "negative", "neutral"
) -> float:
    """
    Maps event characteristics to signal_value [-1, +1].
    -1: strong short signal
    +1: strong long signal
    0: neutral
    """
    base_signal = {
        EventTypeEnum.EARNINGS: 0.0,  # Depends on surprise direction
        EventTypeEnum.M_A: 0.5,  # Generally positive for acquirer short-term
        EventTypeEnum.INSIDER_TRADE: 0.6,  # High predictive power
        EventTypeEnum.DIVIDEND_CHANGE: 0.3,  # Weak signal
        EventTypeEnum.SEC_FILING: 0.2,  # Weak signal alone
        EventTypeEnum.MANAGEMENT_CHANGE: 0.4,  # Moderate
        EventTypeEnum.GUIDANCE_REVISION: -0.5,  # Usually negative
        EventTypeEnum.SHARE_REPURCHASE: 0.4,  # Moderate positive
    }

    severity_multiplier = severity / 5.0  # 0.2 to 1.0

    if direction == "positive":
        return base_signal[event_type] * severity_multiplier
    elif direction == "negative":
        return -base_signal[event_type] * severity_multiplier
    else:
        return 0.0
```

### 6.4 Query: List Backtestable Events for Factor Backtester

```sql
-- Get all active event signals for backtesting as of date 2026-01-01
SELECT
    efb.bridge_id,
    e.event_id,
    e.ticker,
    e.event_type,
    efb.factor_id,
    efb.signal_value,
    efb.signal_confidence,
    e.severity_score,
    e.event_date,
    e.detected_at,
    efb.valid_until,
    adw.abnormal_return as realized_alpha
FROM event_factor_bridge efb
JOIN event e ON efb.event_id = e.event_id
LEFT JOIN alpha_decay_window adw
    ON e.event_id = adw.event_id AND adw.window_type = '[0,+21d]'
WHERE efb.valid_until >= '2026-01-01'::date
    AND e.detected_at <= '2026-01-01'::timestamp
ORDER BY e.detected_at DESC;
```

---

## 7. Indexing Strategy

### 7.1 Query Patterns and Indexes

**Pattern 1: Event Timeline for Watchlist**
```sql
SELECT * FROM event
WHERE ticker = 'AAPL'
  AND detected_at <= '2026-01-01'
ORDER BY detected_at DESC
LIMIT 50;
```
**Index**: `idx_event_ticker_detected` (ticker, detected_at DESC)

**Pattern 2: Recent High-Severity Events**
```sql
SELECT * FROM event
WHERE severity_score >= 4
  AND detected_at <= '2026-01-01'
ORDER BY detected_at DESC;
```
**Index**: `idx_event_severity` (severity_score DESC), `idx_event_detected_at` (detected_at DESC)

**Pattern 3: Alpha Decay Calculation**
```sql
SELECT * FROM alpha_decay_window
WHERE event_id = $1
  AND window_type = '[0,+5d]';
```
**Index**: `idx_alpha_decay_event_window` (event_id, window_type)

**Pattern 4: Active Factor Signals**
```sql
SELECT * FROM event_factor_bridge
WHERE factor_id = $1
  AND valid_until >= NOW()
ORDER BY created_at DESC;
```
**Index**: `idx_bridge_factor_valid` (factor_id, valid_until DESC)

**Pattern 5: PiT Event Queries**
```sql
SELECT * FROM event
WHERE detected_at <= '2025-12-31'
  AND event_date >= '2025-01-01'
ORDER BY detected_at DESC;
```
**Index**: `idx_event_detected_at` (detected_at DESC), `idx_event_event_date` (event_date DESC)

### 7.2 Complete Index Summary

| Table | Index Name | Columns | Use Case |
|-------|-----------|---------|----------|
| event | idx_event_ticker | ticker | Filter by stock |
| event | idx_event_type | event_type | Filter by event type |
| event | idx_event_detected_at | detected_at DESC | PiT queries |
| event | idx_event_event_date | event_date DESC | Timeline filtering |
| event | idx_event_severity | severity_score DESC | High-impact events |
| event | idx_event_ticker_detected | (ticker, detected_at DESC) | Watchlist timeline |
| event | idx_event_ticker_date_type | (ticker, event_date, event_type) | Historical queries |
| event | idx_event_source | source | Deduplication |
| event_classification_rule | idx_classification_rule_enabled | enabled | Active rules only |
| event_classification_rule | idx_classification_rule_type | (classification, enabled) | Rule lookup |
| event_classification_rule | idx_classification_rule_pattern | pattern_type | Pattern matching |
| alpha_decay_window | idx_alpha_decay_event | event_id | Per-event decay |
| alpha_decay_window | idx_alpha_decay_window_type | window_type | Window filtering |
| alpha_decay_window | idx_alpha_decay_measured_at | measured_at DESC | PiT consistency |
| alpha_decay_window | idx_alpha_decay_event_window | (event_id, window_type) | Unique constraint |
| alpha_decay_window | idx_alpha_decay_confidence | confidence_score DESC | High-confidence data |
| event_factor_bridge | idx_bridge_event | event_id | Event-to-factor lookup |
| event_factor_bridge | idx_bridge_factor | factor_id | Factor signals |
| event_factor_bridge | idx_bridge_valid_until | valid_until DESC | Active signals |
| event_factor_bridge | idx_bridge_factor_valid | (factor_id, valid_until DESC) | Backtester queries |
| event_factor_bridge | idx_bridge_created_at | created_at DESC | Chronological |
| event_source_mapping | idx_source_mapping_event | event_id | Event source trace |
| event_source_mapping | idx_source_mapping_type | source_type | Source filtering |
| event_source_mapping | idx_source_mapping_source_id | source_id | Deduplication |
| event_source_mapping | idx_source_mapping_hash | raw_content_hash | Content deduplication |
| event_source_mapping | idx_source_mapping_ingested | ingested_at DESC | Ingestion timeline |
| event_alert_configuration | idx_alert_config_user | user_id | User preferences |
| event_alert_configuration | idx_alert_config_portfolio | portfolio_id | Portfolio-scoped alerts |
| event_alert_configuration | idx_alert_config_enabled | alert_enabled | Active alerts |
| event_alert_configuration | idx_alert_config_scope | (scope, scope_value) | Scope filtering |
| event_correlation_analysis | idx_correlation_event_types | (event_type_1, event_type_2) | Type pair lookup |
| event_correlation_analysis | idx_correlation_period | analyzed_period_end DESC | Time series |
| event_correlation_analysis | idx_correlation_strength | correlation_strength DESC | Strong correlations |

---

## 8. Alembic Migration

File: `/alembic/versions/002_add_event_scanner.py`

```python
"""
Add Event Scanner tables for Phase 2.

Revision ID: 002
Revises: 001
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Create Event Scanner tables."""

    # event_classification_rule
    op.create_table(
        'event_classification_rule',
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('classification', sa.String(50), nullable=False),
        sa.Column('pattern_type', sa.String(50), nullable=False),
        sa.Column('pattern_value', postgresql.JSON(), nullable=False),
        sa.Column('confidence_score', sa.SmallInteger(), nullable=False, server_default='80'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('rule_id'),
        sa.CheckConstraint("classification IN ('earnings', 'M&A', 'insider_trade', 'dividend_change', 'SEC_filing', 'management_change', 'guidance_revision', 'share_repurchase')"),
        sa.CheckConstraint("pattern_type IN ('keyword', 'filing_form', 'calendar_event', 'net_trading_volume')"),
        sa.CheckConstraint('confidence_score >= 0 AND confidence_score <= 100'),
        sa.Index('idx_classification_rule_enabled', 'enabled'),
        sa.Index('idx_classification_rule_type', 'classification', 'enabled'),
        sa.Index('idx_classification_rule_pattern', 'pattern_type'),
    )

    # event
    op.create_table(
        'event',
        sa.Column('event_id', sa.BigInteger(), nullable=False),
        sa.Column('ticker', sa.String(10), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_classification_id', sa.Integer(), nullable=False),
        sa.Column('severity_score', sa.SmallInteger(), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('headline', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_classification_id'], ['event_classification_rule.rule_id']),
        sa.PrimaryKeyConstraint('event_id'),
        sa.UniqueConstraint('ticker', 'event_type', 'event_date', 'source', name='uq_event_ticker_type_date_source'),
        sa.CheckConstraint("event_type IN ('earnings', 'M&A', 'insider_trade', 'dividend_change', 'SEC_filing', 'management_change', 'guidance_revision', 'share_repurchase')"),
        sa.CheckConstraint("severity_score >= 1 AND severity_score <= 5"),
        sa.CheckConstraint("source IN ('SEC_EDGAR', 'YFINANCE', 'MANUAL')"),
        sa.Index('idx_event_ticker', 'ticker'),
        sa.Index('idx_event_type', 'event_type'),
        sa.Index('idx_event_detected_at', 'detected_at'),
        sa.Index('idx_event_event_date', 'event_date'),
        sa.Index('idx_event_severity', 'severity_score'),
        sa.Index('idx_event_ticker_detected', 'ticker', 'detected_at'),
        sa.Index('idx_event_ticker_date_type', 'ticker', 'event_date', 'event_type'),
        sa.Index('idx_event_source', 'source'),
    )

    # alpha_decay_window
    op.create_table(
        'alpha_decay_window',
        sa.Column('window_id', sa.BigInteger(), nullable=False),
        sa.Column('event_id', sa.BigInteger(), nullable=False),
        sa.Column('window_type', sa.String(20), nullable=False),
        sa.Column('abnormal_return', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column('benchmark_return', sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column('volatility', sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column('volume_spike', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('trading_volume', sa.BigInteger(), nullable=True),
        sa.Column('confidence_score', sa.SmallInteger(), nullable=False, server_default='50'),
        sa.Column('data_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('measured_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['event_id'], ['event.event_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('window_id'),
        sa.UniqueConstraint('event_id', 'window_type', name='uq_alpha_decay_event_window'),
        sa.CheckConstraint("window_type IN ('[0,+1d]', '[0,+5d]', '[0,+21d]', '[0,+63d]')"),
        sa.CheckConstraint('confidence_score >= 0 AND confidence_score <= 100'),
        sa.Index('idx_alpha_decay_event', 'event_id'),
        sa.Index('idx_alpha_decay_window_type', 'window_type'),
        sa.Index('idx_alpha_decay_measured_at', 'measured_at'),
        sa.Index('idx_alpha_decay_event_window', 'event_id', 'window_type'),
        sa.Index('idx_alpha_decay_confidence', 'confidence_score'),
    )

    # event_factor_bridge
    op.create_table(
        'event_factor_bridge',
        sa.Column('bridge_id', sa.BigInteger(), nullable=False),
        sa.Column('event_id', sa.BigInteger(), nullable=False),
        sa.Column('factor_id', sa.Integer(), nullable=False),
        sa.Column('signal_value', sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column('signal_confidence', sa.SmallInteger(), nullable=False, server_default='50'),
        sa.Column('signal_expiry_window', sa.String(20), nullable=False, server_default='[0,+21d]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['event_id'], ['event.event_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['factor_id'], ['factor_definition.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('bridge_id'),
        sa.UniqueConstraint('event_id', 'factor_id', name='uq_bridge_event_factor'),
        sa.CheckConstraint('signal_value >= -1 AND signal_value <= 1'),
        sa.CheckConstraint('signal_confidence >= 0 AND signal_confidence <= 100'),
        sa.Index('idx_bridge_event', 'event_id'),
        sa.Index('idx_bridge_factor', 'factor_id'),
        sa.Index('idx_bridge_valid_until', 'valid_until'),
        sa.Index('idx_bridge_factor_valid', 'factor_id', 'valid_until'),
        sa.Index('idx_bridge_created_at', 'created_at'),
    )

    # event_source_mapping
    op.create_table(
        'event_source_mapping',
        sa.Column('mapping_id', sa.BigInteger(), nullable=False),
        sa.Column('event_id', sa.BigInteger(), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_url', sa.String(500), nullable=False),
        sa.Column('source_id', sa.String(100), nullable=True),
        sa.Column('extracted_data', postgresql.JSON(), nullable=True),
        sa.Column('raw_content_hash', sa.String(64), nullable=True),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['event_id'], ['event.event_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('mapping_id'),
        sa.UniqueConstraint('event_id', 'source_type', name='uq_source_mapping_event_type'),
        sa.CheckConstraint("source_type IN ('SEC_EDGAR_8K', 'SEC_EDGAR_10K', 'SEC_EDGAR_10Q', 'SEC_EDGAR_SC13D', 'SEC_EDGAR_SC13G', 'SEC_EDGAR_FORM4', 'YFINANCE_EARNINGS', 'YFINANCE_DIVIDEND')"),
        sa.Index('idx_source_mapping_event', 'event_id'),
        sa.Index('idx_source_mapping_type', 'source_type'),
        sa.Index('idx_source_mapping_source_id', 'source_id'),
        sa.Index('idx_source_mapping_hash', 'raw_content_hash'),
        sa.Index('idx_source_mapping_ingested', 'ingested_at'),
    )

    # event_alert_configuration
    op.create_table(
        'event_alert_configuration',
        sa.Column('config_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('portfolio_id', sa.Integer(), nullable=True),
        sa.Column('scope', sa.String(50), nullable=False, server_default='global'),
        sa.Column('scope_value', sa.String(100), nullable=True),
        sa.Column('event_type_filter', sa.Text(), nullable=False, server_default='all'),
        sa.Column('min_severity_threshold', sa.SmallInteger(), nullable=False, server_default='1'),
        sa.Column('alert_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notification_method', sa.String(50), nullable=False, server_default='in_app'),
        sa.Column('webhook_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('config_id'),
        sa.CheckConstraint("scope IN ('global', 'portfolio', 'ticker')"),
        sa.CheckConstraint("notification_method IN ('in_app', 'email', 'webhook')"),
        sa.CheckConstraint('min_severity_threshold >= 1 AND min_severity_threshold <= 5'),
        sa.Index('idx_alert_config_user', 'user_id'),
        sa.Index('idx_alert_config_portfolio', 'portfolio_id'),
        sa.Index('idx_alert_config_enabled', 'alert_enabled'),
        sa.Index('idx_alert_config_scope', 'scope', 'scope_value'),
    )

    # event_correlation_analysis
    op.create_table(
        'event_correlation_analysis',
        sa.Column('analysis_id', sa.BigInteger(), nullable=False),
        sa.Column('event_type_1', sa.String(50), nullable=False),
        sa.Column('event_type_2', sa.String(50), nullable=False),
        sa.Column('time_window_days', sa.SmallInteger(), nullable=False, server_default='30'),
        sa.Column('co_occurrence_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_event_type_1_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_event_type_2_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('correlation_strength', sa.Numeric(precision=6, scale=4), nullable=False, server_default='0.0'),
        sa.Column('chi_square_statistic', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('p_value', sa.Numeric(precision=8, scale=6), nullable=True),
        sa.Column('analyzed_period_start', sa.Date(), nullable=False),
        sa.Column('analyzed_period_end', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('analysis_id'),
        sa.UniqueConstraint('event_type_1', 'event_type_2', 'time_window_days', 'analyzed_period_end', name='uq_correlation_types_window'),
        sa.CheckConstraint("event_type_1 IN ('earnings', 'M&A', 'insider_trade', 'dividend_change', 'SEC_filing', 'management_change', 'guidance_revision', 'share_repurchase')"),
        sa.CheckConstraint("event_type_2 IN ('earnings', 'M&A', 'insider_trade', 'dividend_change', 'SEC_filing', 'management_change', 'guidance_revision', 'share_repurchase')"),
        sa.CheckConstraint('correlation_strength >= 0 AND correlation_strength <= 1'),
        sa.Index('idx_correlation_event_types', 'event_type_1', 'event_type_2'),
        sa.Index('idx_correlation_period', 'analyzed_period_end'),
        sa.Index('idx_correlation_strength', 'correlation_strength'),
    )

def downgrade() -> None:
    """Drop Event Scanner tables."""
    op.drop_table('event_correlation_analysis')
    op.drop_table('event_alert_configuration')
    op.drop_table('event_source_mapping')
    op.drop_table('event_factor_bridge')
    op.drop_table('alpha_decay_window')
    op.drop_table('event')
    op.drop_table('event_classification_rule')
```

---

## 9. Query Patterns for Event Timeline, Alpha Decay, and Factor Generation

### 9.1 Event Timeline Query (Watchlist View)

```sql
-- Get chronological event timeline for ticker, with PiT enforcement
SELECT
    e.event_id,
    e.ticker,
    e.event_type,
    e.severity_score,
    e.headline,
    e.event_date,
    e.detected_at,
    COUNT(DISTINCT adw.window_id) as decay_window_count,
    AVG(adw.abnormal_return) FILTER (WHERE adw.window_type = '[0,+5d]') as alpha_5d,
    COALESCE(efb.factor_id, NULL) as linked_factor_id
FROM event e
LEFT JOIN alpha_decay_window adw ON e.event_id = adw.event_id
LEFT JOIN event_factor_bridge efb ON e.event_id = efb.event_id
WHERE e.ticker = $1
    AND e.detected_at <= $2
ORDER BY e.detected_at DESC
LIMIT 100;
```

### 9.2 Alpha Decay Calculation Trigger

When a new event is detected, trigger calculation of all 4 alpha decay windows:

```python
def calculate_alpha_decay_for_event(event_id: int, session: Session):
    """
    Calculate alpha decay windows for event.
    Runs as background task after event creation.
    """
    event = session.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        return

    # Get baseline returns (252 days pre-event)
    baseline_start = event.event_date - timedelta(days=252)
    baseline_prices = session.query(PriceHistory).filter(
        PriceHistory.ticker == event.ticker,
        PriceHistory.date >= baseline_start,
        PriceHistory.date < event.event_date,
        PriceHistory.ingestion_timestamp <= event.detected_at
    ).order_by(PriceHistory.date).all()

    if not baseline_prices:
        return

    baseline_returns = calculate_returns(baseline_prices)
    baseline_vol = np.std(baseline_returns)

    for window_type, days in [
        ('[0,+1d]', 1),
        ('[0,+5d]', 5),
        ('[0,+21d]', 21),
        ('[0,+63d]', 63)
    ]:
        window_end = event.event_date + timedelta(days=days)

        # Get prices during window (PiT: only data known at detected_at)
        window_prices = session.query(PriceHistory).filter(
            PriceHistory.ticker == event.ticker,
            PriceHistory.date >= event.event_date,
            PriceHistory.date <= window_end,
            PriceHistory.ingestion_timestamp <= event.detected_at + timedelta(days=days+5)
        ).order_by(PriceHistory.date).all()

        if not window_prices:
            continue

        window_returns = calculate_returns(window_prices)
        abnormal_return = np.mean(window_returns) - np.mean(baseline_returns)

        decay_window = AlphaDecayWindow(
            event_id=event_id,
            window_type=window_type,
            abnormal_return=Decimal(str(abnormal_return * 100)),
            volatility=Decimal(str(np.std(window_returns))),
            confidence_score=min(100, len(window_prices) * 10),
            data_points=len(window_prices),
            measured_at=datetime.utcnow()
        )
        session.add(decay_window)

    session.commit()
```

### 9.3 Event-to-Factor Bridge Query (for Backtester)

```sql
-- Get all active event signals for backtesting as of date
WITH event_signals AS (
    SELECT
        efb.bridge_id,
        e.event_id,
        e.ticker,
        e.event_type,
        e.severity_score,
        efb.factor_id,
        efb.signal_value,
        efb.signal_confidence,
        e.detected_at,
        efb.valid_until,
        MAX(adw.abnormal_return) FILTER (
            WHERE adw.window_type = '[0,+21d]'
        ) OVER (PARTITION BY e.event_id) as realized_alpha_21d
    FROM event_factor_bridge efb
    JOIN event e ON efb.event_id = e.event_id
    LEFT JOIN alpha_decay_window adw ON e.event_id = adw.event_id
    WHERE efb.valid_until >= $1
        AND e.detected_at <= $1
)
SELECT *
FROM event_signals
WHERE realized_alpha_21d IS NOT NULL
ORDER BY e.detected_at DESC;
```

### 9.4 Event Correlation Analysis Query

```sql
-- Find event type co-occurrence patterns
WITH event_pairs AS (
    SELECT
        e1.ticker,
        e1.event_type as type_1,
        e1.event_date as date_1,
        e2.event_type as type_2,
        e2.event_date as date_2,
        ABS(EXTRACT(DAY FROM (e2.event_date - e1.event_date))) as days_apart
    FROM event e1
    JOIN event e2 ON e1.ticker = e2.ticker
        AND e1.event_id < e2.event_id
        AND ABS(EXTRACT(DAY FROM (e2.event_date - e1.event_date))) <= 30
    WHERE e1.detected_at <= $1
        AND e2.detected_at <= $1
)
SELECT
    type_1,
    type_2,
    COUNT(*) as co_occurrence_count,
    STDDEV_POP(days_apart) as avg_spacing_days
FROM event_pairs
GROUP BY type_1, type_2
ORDER BY co_occurrence_count DESC;
```

---

## 10. Integration with Existing Phase 1 Tables

### 10.1 Foreign Key Relationships

All new Event Scanner tables maintain referential integrity with Phase 1:

- `event.ticker` → `security.ticker` (security master)
- `event_factor_bridge.factor_id` → `factor_definition.id` (factor catalog)
- Alpha decay calculations use `price_history` (price master)

### 10.2 PiT Enforcement Across Phases

When analyzing events as of date D:

```python
# Phase 1: Get factor scores as of D
factor_scores = session.query(CustomFactorScore).filter(
    CustomFactorScore.calculation_date <= D,
    CustomFactorScore.ingestion_timestamp <= D
).all()

# Phase 2: Get event signals as of D
event_signals = session.query(EventFactorBridge).filter(
    EventFactorBridge.created_at <= D,
    EventFactorBridge.valid_until >= D
).all()

# Phase 2 (sub): Get alpha decay measurements as of D
decay_windows = session.query(AlphaDecayWindow).filter(
    AlphaDecayWindow.measured_at <= D,
    AlphaDecayWindow.event_id.in_([s.event_id for s in event_signals])
).all()

# Combine: events become additional factors in backtest
combined_factors = factor_scores + event_signals
```

### 10.3 Backtest Integration

Events feed into backtests via the `event_factor_bridge` table:

1. **Pre-backtest**: User selects event-based factors alongside traditional factors
2. **Backtest config**: Stores which event types + severity thresholds are included
3. **Backtest results**: Daily returns include allocation to event signals
4. **Post-backtest**: Alpha decay analysis compares predicted (signal_value) vs. realized (abnormal_return)

---

## 11. Example Data Flows

### Flow 1: Earnings Event Detection → Factor Signal

```
1. yfinance calendar ingestion (background task):
   "AAPL earnings announced 2026-01-15"

2. Rule matching (event_classification_rule):
   pattern_type = calendar_event
   pattern_value = {event_type: earnings_date}
   → Create Event(ticker=AAPL, event_type=earnings, ...)

3. Severity scoring:
   historical EPS surprise magnitude = 8% (previous 4 quarters)
   → severity_score = 4

4. Alpha decay calculation (background task over 63 days):
   Day 1: [0,+1d] abnormal_return = +2.1%
   Day 5: [0,+5d] abnormal_return = +3.8%
   Day 21: [0,+21d] abnormal_return = +4.2%
   Day 63: [0,+63d] abnormal_return = +2.1% (decay confirmed)

5. Factor bridge creation:
   signal_value = +0.75 (bullish signal based on alpha pattern)
   valid_until = 2026-02-05 (21-day window)
   → Event becomes backtestable factor

6. Backtest query:
   SELECT * FROM event_factor_bridge
   WHERE factor_id = 789 AND valid_until >= '2026-01-20'
   → Include in portfolio factor exposure on Jan 20
```

### Flow 2: Insider Trade Clustering → Correlation Detected

```
1. SEC EDGAR Form 4 ingestion:
   AAPL insiders buy $5M shares on 2026-01-10
   → Event(ticker=AAPL, event_type=insider_trade, severity=4)

2. One week later, M&A rumor filed (8-K item 1.01):
   AAPL to acquire TechCorp for $30B on 2026-01-17
   → Event(ticker=AAPL, event_type=M&A, severity=5)

3. Correlation analysis (weekly batch):
   co_occurrence_count += 1 (insider_trade → M&A within 7 days)
   correlation_strength = 0.72 (strong correlation detected)
   p_value = 0.003 (statistically significant)

4. Alert triggered (event_alert_configuration):
   user_config: min_severity=3, event_type_filter=[insider_trade, M&A]
   → User notified: "High-severity M&A event detected post-insider trading"
```

---

## 12. Summary

The Event Scanner Phase 2 schema:

- **Core tables**: `event`, `event_classification_rule`, `alpha_decay_window`, `event_factor_bridge`
- **Supporting tables**: `event_source_mapping`, `event_alert_configuration`, `event_correlation_analysis`
- **PiT enforcement**: All tables include `detected_at` or `measured_at` timestamps for temporal consistency
- **Indexing**: Optimized for event timeline queries, alpha decay retrieval, and factor backtester lookups
- **Integration**: Seamless FK relationships to existing security, price_history, and factor_definition tables
- **Scalability**: BIGSERIAL IDs for event and window tables; JSON metadata for flexible source data storage

This design enables:
- Real-time event detection from SEC EDGAR and yfinance
- Historical alpha decay measurement with statistical confidence
- Event signals as backtestable factors
- User-configurable event alerts
- Event correlation analysis for strategy discovery
- Full PiT compliance for backtesting reproducibility
