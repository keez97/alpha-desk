# AlphaDesk Earnings Surprise Predictor (Phase 3) — Database Design

## Overview

This document defines the PostgreSQL database schema for Phase 3 of the AlphaDesk project: **Earnings Surprise Prediction with SmartEstimate Consensus and PEAD Drift Tracking**.

Phase 3 introduces six new tables to support:

- **SmartEstimate Consensus**: Weighted analyst consensus with recency decay and accuracy tier adjustments
- **Earnings Surprises**: Comparison of actual earnings vs. consensus and smart estimates
- **Post-Earnings Announcement Drift (PEAD)**: Measurement of abnormal returns after earnings announcements
- **Analyst Accuracy Tracking**: Scorecard system to weight analysts by historical accuracy
- **Earnings Signals**: Pre-earnings directional trading signals derived from estimate divergence

All data sources are free: yfinance estimates + SEC EDGAR actuals.

---

## Architecture Principles

### Point-in-Time (PiT) Enforcement

All estimates and signals are timestamped with `estimate_date` or `signal_date` to support:
- Backtesting without look-ahead bias
- Historical replay of analyst consensus at any past date
- Proper out-of-sample testing against actual reported earnings

### Composite Uniqueness

Key tables use composite unique constraints to prevent duplicates:
- `earnings_estimate`: `(ticker, fiscal_quarter, estimate_type, analyst_broker, estimate_date)`
- `pead_measurement`: `(ticker, fiscal_quarter, measured_at)` — PEAD measured at specific point-in-time

### Decimal Precision

All financial values use PostgreSQL `NUMERIC(19,4)` for:
- EPS estimates (4 decimal places)
- Surprise percentages (4 decimal places)
- Cumulative abnormal returns (4 decimal places)

### Enums as Strings

For flexibility and easy querying, enum values are stored as VARCHAR:
- `estimate_type`: 'consensus', 'smart_estimate', 'individual'
- `signal_type`: 'buy', 'sell', 'hold'
- `report_time`: 'pre_market', 'post_market', 'during'
- `surprise_direction`: 'positive', 'negative', 'inline'

---

## Existing Tables (Not Recreated)

From **Phase 1** (Securities & Factor Framework):
- `security` — Master security data (ticker as PK)
- `security_lifecycle_event` — Delisting, acquisition events
- `price_history` — Daily OHLCV data
- `fundamentals_snapshot` — Quarterly/annual financials
- `factor_definitions` — Factor metadata
- `fama_french_factors` — Fama-French factor returns
- `custom_factor_scores` — Custom factor calculations per security/date
- `backtests` — Backtest configurations and results
- `backtest_configurations`, `backtest_factor_allocations`, `backtest_results`, `backtest_statistics`
- `factor_correlations` — Factor correlation matrix
- `alpha_decay_analysis` — Alpha decay windows
- `screener_factor_scores` — Factor scores for screening

From **Phase 2** (Event Scanner):
- `event` — Corporate events with severity scores
- `event_classification_rule` — Pattern matching rules for event classification
- `alpha_decay_window` — Abnormal returns windows by event
- `event_factor_bridge` — Links events to factor exposures
- `event_source_mapping` — Maps raw events to classified types
- `event_alert_configuration` — Alert thresholds for events
- `event_correlation_analysis` — Event-factor correlations

---

## New Tables (Phase 3)

### 1. earnings_estimate

**Purpose**: Individual analyst and consensus estimates for each fiscal quarter.

**PiT Enforcement**: Each estimate is timestamped with `estimate_date` (when the estimate was published). This allows backtesting to fetch estimates as they existed on any historical date without look-ahead bias.

```sql
CREATE TABLE earnings_estimate (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR NOT NULL,
    fiscal_quarter VARCHAR NOT NULL,
    estimate_type VARCHAR NOT NULL,
    eps_estimate NUMERIC(19, 4) NOT NULL,
    estimate_date TIMESTAMP WITH TIME ZONE NOT NULL,
    analyst_broker VARCHAR,
    revision_number INTEGER DEFAULT 0,
    ingestion_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (ticker) REFERENCES security(ticker),
    UNIQUE(ticker, fiscal_quarter, estimate_type, analyst_broker, estimate_date),
    INDEX idx_earnings_estimate_ticker (ticker),
    INDEX idx_earnings_estimate_fiscal_quarter (fiscal_quarter),
    INDEX idx_earnings_estimate_date (estimate_date),
    INDEX idx_earnings_estimate_type (estimate_type),
    INDEX idx_earnings_estimate_broker (analyst_broker),
    INDEX idx_earnings_estimate_ticker_quarter (ticker, fiscal_quarter),
    INDEX idx_earnings_estimate_ticker_date (ticker, estimate_date)
);
```

**SQLModel Definition**:

```python
class EarningsEstimate(SQLModel, table=True):
    """Individual analyst and consensus earnings estimates with PiT enforcement."""
    __tablename__ = "earnings_estimate"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "fiscal_quarter",
            "estimate_type",
            "analyst_broker",
            "estimate_date",
            name="uq_earnings_estimate_composite"
        ),
        Index("idx_earnings_estimate_ticker", "ticker"),
        Index("idx_earnings_estimate_fiscal_quarter", "fiscal_quarter"),
        Index("idx_earnings_estimate_date", "estimate_date"),
        Index("idx_earnings_estimate_type", "estimate_type"),
        Index("idx_earnings_estimate_broker", "analyst_broker"),
        Index("idx_earnings_estimate_ticker_quarter", "ticker", "fiscal_quarter"),
        Index("idx_earnings_estimate_ticker_date", "ticker", "estimate_date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(foreign_key="security.ticker", index=True)
    fiscal_quarter: str = Field(
        description="Fiscal quarter in format YYYYQ# (e.g., '2025Q4')"
    )
    estimate_type: str = Field(
        description="Type of estimate: 'consensus', 'smart_estimate', 'individual'"
    )
    eps_estimate: Decimal = Field(
        decimal_places=4,
        description="Earnings per share estimate"
    )
    estimate_date: datetime = Field(
        description="When the estimate was published (PiT timestamp)"
    )
    analyst_broker: Optional[str] = Field(
        default=None,
        description="Analyst/broker name (null for consensus/smart_estimate)"
    )
    revision_number: int = Field(
        default=0,
        description="Revision count for this estimate"
    )
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When data was ingested into the system"
    )

    # Relationships
    security: Optional[Security] = Relationship(back_populates="earnings_estimates")
```

---

### 2. earnings_actual

**Purpose**: Actual reported EPS after earnings announcement.

**PiT Enforcement**: `report_date` is when the actual was reported; `ingestion_timestamp` marks when it was added to the database.

```sql
CREATE TABLE earnings_actual (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR NOT NULL,
    fiscal_quarter VARCHAR NOT NULL,
    actual_eps NUMERIC(19, 4) NOT NULL,
    report_date DATE NOT NULL,
    report_time VARCHAR,
    surprise_vs_consensus NUMERIC(19, 4),
    surprise_vs_smart NUMERIC(19, 4),
    source VARCHAR NOT NULL,
    ingestion_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (ticker) REFERENCES security(ticker),
    UNIQUE(ticker, fiscal_quarter, report_date),
    INDEX idx_earnings_actual_ticker (ticker),
    INDEX idx_earnings_actual_fiscal_quarter (fiscal_quarter),
    INDEX idx_earnings_actual_report_date (report_date),
    INDEX idx_earnings_actual_ticker_quarter (ticker, fiscal_quarter)
);
```

**SQLModel Definition**:

```python
class EarningsActual(SQLModel, table=True):
    """Actual reported EPS after earnings announcement."""
    __tablename__ = "earnings_actual"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "fiscal_quarter",
            "report_date",
            name="uq_earnings_actual_composite"
        ),
        Index("idx_earnings_actual_ticker", "ticker"),
        Index("idx_earnings_actual_fiscal_quarter", "fiscal_quarter"),
        Index("idx_earnings_actual_report_date", "report_date"),
        Index("idx_earnings_actual_ticker_quarter", "ticker", "fiscal_quarter"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(foreign_key="security.ticker", index=True)
    fiscal_quarter: str = Field(
        description="Fiscal quarter in format YYYYQ# (e.g., '2025Q4')"
    )
    actual_eps: Decimal = Field(
        decimal_places=4,
        description="Actual reported earnings per share"
    )
    report_date: date = Field(
        description="Date when earnings were reported"
    )
    report_time: Optional[str] = Field(
        default=None,
        description="Time of report: 'pre_market', 'post_market', 'during'"
    )
    surprise_vs_consensus: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="Surprise % vs. consensus estimate: (actual - consensus) / abs(consensus) * 100"
    )
    surprise_vs_smart: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="Surprise % vs. smart estimate: (actual - smart) / abs(smart) * 100"
    )
    source: str = Field(
        description="Source of actual: 'yfinance' or 'sec_edgar'"
    )
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When data was ingested into the system"
    )

    # Relationships
    security: Optional[Security] = Relationship(back_populates="earnings_actuals")
```

---

### 3. smart_estimate_weights

**Purpose**: Configuration parameters for SmartEstimate calculation.

Supports time-decaying weights for recent estimates and accuracy tier adjustments.

```sql
CREATE TABLE smart_estimate_weights (
    id BIGSERIAL PRIMARY KEY,
    weight_type VARCHAR NOT NULL,
    parameter_name VARCHAR NOT NULL,
    parameter_value NUMERIC(19, 4) NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE(weight_type, parameter_name),
    INDEX idx_smart_estimate_weights_type (weight_type)
);
```

**SQLModel Definition**:

```python
class SmartEstimateWeights(SQLModel, table=True):
    """Configuration for SmartEstimate weighted consensus calculation."""
    __tablename__ = "smart_estimate_weights"
    __table_args__ = (
        UniqueConstraint(
            "weight_type",
            "parameter_name",
            name="uq_smart_estimate_weights_composite"
        ),
        Index("idx_smart_estimate_weights_type", "weight_type"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    weight_type: str = Field(
        description="Weight category: 'recency_decay', 'accuracy_tier', 'broker_size'"
    )
    parameter_name: str = Field(
        description="Parameter name (e.g., 'half_life_days', 'tier_1_weight', 'size_large_weight')"
    )
    parameter_value: Decimal = Field(
        decimal_places=4,
        description="Decimal value for the parameter"
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the parameter"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this weight was last updated"
    )
```

**Example Configuration**:

```
weight_type='recency_decay', parameter_name='half_life_days', parameter_value=30.0
  → Estimates decay by 50% every 30 days

weight_type='accuracy_tier', parameter_name='tier_1_weight', parameter_value=1.5
  → Tier 1 (best) analysts get 1.5x weight

weight_type='accuracy_tier', parameter_name='tier_2_weight', parameter_value=1.0
  → Tier 2 analysts get 1.0x weight

weight_type='accuracy_tier', parameter_name='tier_3_weight', parameter_value=0.7
  → Tier 3 (worst) analysts get 0.7x weight

weight_type='broker_size', parameter_name='size_large_weight', parameter_value=1.2
  → Large brokers get 1.2x boost
```

---

### 4. analyst_scorecard

**Purpose**: Track historical accuracy of individual analysts and brokers.

Used to tier analysts into accuracy groups for SmartEstimate weighting.

```sql
CREATE TABLE analyst_scorecard (
    id BIGSERIAL PRIMARY KEY,
    analyst_broker VARCHAR NOT NULL,
    ticker VARCHAR,
    total_estimates INTEGER DEFAULT 0,
    accurate_count INTEGER DEFAULT 0,
    directional_accuracy NUMERIC(19, 4),
    avg_error_pct NUMERIC(19, 4),
    last_evaluated TIMESTAMP WITH TIME ZONE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    UNIQUE(analyst_broker, ticker, period_start, period_end),
    INDEX idx_analyst_scorecard_broker (analyst_broker),
    INDEX idx_analyst_scorecard_ticker (ticker),
    INDEX idx_analyst_scorecard_period (period_start, period_end)
);
```

**SQLModel Definition**:

```python
class AnalystScorecard(SQLModel, table=True):
    """Historical accuracy tracking for analysts and brokers."""
    __tablename__ = "analyst_scorecard"
    __table_args__ = (
        UniqueConstraint(
            "analyst_broker",
            "ticker",
            "period_start",
            "period_end",
            name="uq_analyst_scorecard_composite"
        ),
        Index("idx_analyst_scorecard_broker", "analyst_broker"),
        Index("idx_analyst_scorecard_ticker", "ticker"),
        Index("idx_analyst_scorecard_period", "period_start", "period_end"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    analyst_broker: str = Field(
        description="Analyst or broker name"
    )
    ticker: Optional[str] = Field(
        default=None,
        description="Specific ticker (null for aggregate across all stocks)"
    )
    total_estimates: int = Field(
        default=0,
        description="Total number of estimates evaluated"
    )
    accurate_count: int = Field(
        default=0,
        description="Count of estimates within ±5% of actual"
    )
    directional_accuracy: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="Percentage of correct direction predictions (0-100)"
    )
    avg_error_pct: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="Average absolute error as percentage"
    )
    last_evaluated: Optional[datetime] = Field(
        default=None,
        description="When accuracy was last calculated"
    )
    period_start: date = Field(
        description="Start date of evaluation period"
    )
    period_end: date = Field(
        description="End date of evaluation period"
    )
```

---

### 5. pead_measurement

**Purpose**: Post-Earnings Announcement Drift (PEAD) tracking.

Measures abnormal returns in multiple windows (1d, 5d, 21d, 60d) after earnings announcement, with support for PiT replay.

```sql
CREATE TABLE pead_measurement (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR NOT NULL,
    fiscal_quarter VARCHAR NOT NULL,
    earnings_date DATE NOT NULL,
    surprise_direction VARCHAR NOT NULL,
    surprise_magnitude NUMERIC(19, 4) NOT NULL,
    car_1d NUMERIC(19, 4),
    car_5d NUMERIC(19, 4),
    car_21d NUMERIC(19, 4),
    car_60d NUMERIC(19, 4),
    benchmark_ticker VARCHAR,
    measured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (ticker) REFERENCES security(ticker),
    UNIQUE(ticker, fiscal_quarter, measured_at),
    INDEX idx_pead_measurement_ticker (ticker),
    INDEX idx_pead_measurement_fiscal_quarter (fiscal_quarter),
    INDEX idx_pead_measurement_earnings_date (earnings_date),
    INDEX idx_pead_measurement_surprise_direction (surprise_direction),
    INDEX idx_pead_measurement_measured_at (measured_at)
);
```

**SQLModel Definition**:

```python
class PEADMeasurement(SQLModel, table=True):
    """Post-Earnings Announcement Drift (PEAD) tracking with multiple return windows."""
    __tablename__ = "pead_measurement"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "fiscal_quarter",
            "measured_at",
            name="uq_pead_measurement_composite"
        ),
        Index("idx_pead_measurement_ticker", "ticker"),
        Index("idx_pead_measurement_fiscal_quarter", "fiscal_quarter"),
        Index("idx_pead_measurement_earnings_date", "earnings_date"),
        Index("idx_pead_measurement_surprise_direction", "surprise_direction"),
        Index("idx_pead_measurement_measured_at", "measured_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(foreign_key="security.ticker", index=True)
    fiscal_quarter: str = Field(
        description="Fiscal quarter in format YYYYQ# (e.g., '2025Q4')"
    )
    earnings_date: date = Field(
        description="Date of earnings announcement"
    )
    surprise_direction: str = Field(
        description="Direction of surprise: 'positive', 'negative', 'inline'"
    )
    surprise_magnitude: Decimal = Field(
        decimal_places=4,
        description="Magnitude of surprise as percentage"
    )
    car_1d: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="Cumulative abnormal return (CAR) over 1 day"
    )
    car_5d: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="CAR over 5 trading days"
    )
    car_21d: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="CAR over 21 trading days (1 month)"
    )
    car_60d: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="CAR over 60 trading days (3 months)"
    )
    benchmark_ticker: Optional[str] = Field(
        default=None,
        description="Benchmark ticker for abnormal return calculation (e.g., '^GSPC' for S&P 500)"
    )
    measured_at: datetime = Field(
        description="Point-in-time when PEAD was measured (for backtesting)"
    )

    # Relationships
    security: Optional[Security] = Relationship(back_populates="pead_measurements")
```

---

### 6. earnings_signal

**Purpose**: Pre-earnings trading signals derived from estimate divergence and other indicators.

**PiT Enforcement**: `signal_date` marks when the signal was generated. `valid_until` defines the signal's validity window.

```sql
CREATE TABLE earnings_signal (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR NOT NULL,
    fiscal_quarter VARCHAR NOT NULL,
    signal_date TIMESTAMP WITH TIME ZONE NOT NULL,
    signal_type VARCHAR NOT NULL,
    confidence INTEGER NOT NULL,
    smart_estimate_eps NUMERIC(19, 4) NOT NULL,
    consensus_eps NUMERIC(19, 4) NOT NULL,
    divergence_pct NUMERIC(19, 4) NOT NULL,
    days_to_earnings INTEGER NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    ingestion_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (ticker) REFERENCES security(ticker),
    UNIQUE(ticker, fiscal_quarter, signal_date),
    INDEX idx_earnings_signal_ticker (ticker),
    INDEX idx_earnings_signal_fiscal_quarter (fiscal_quarter),
    INDEX idx_earnings_signal_date (signal_date),
    INDEX idx_earnings_signal_type (signal_type),
    INDEX idx_earnings_signal_valid_until (valid_until),
    INDEX idx_earnings_signal_ticker_date (ticker, signal_date)
);
```

**SQLModel Definition**:

```python
class EarningsSignal(SQLModel, table=True):
    """Pre-earnings directional signals derived from estimate divergence."""
    __tablename__ = "earnings_signal"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "fiscal_quarter",
            "signal_date",
            name="uq_earnings_signal_composite"
        ),
        Index("idx_earnings_signal_ticker", "ticker"),
        Index("idx_earnings_signal_fiscal_quarter", "fiscal_quarter"),
        Index("idx_earnings_signal_date", "signal_date"),
        Index("idx_earnings_signal_type", "signal_type"),
        Index("idx_earnings_signal_valid_until", "valid_until"),
        Index("idx_earnings_signal_ticker_date", "ticker", "signal_date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(foreign_key="security.ticker", index=True)
    fiscal_quarter: str = Field(
        description="Fiscal quarter in format YYYYQ# (e.g., '2025Q4')"
    )
    signal_date: datetime = Field(
        description="When the signal was generated (PiT timestamp)"
    )
    signal_type: str = Field(
        description="Signal direction: 'buy', 'sell', 'hold'"
    )
    confidence: int = Field(
        ge=0,
        le=100,
        description="Confidence level (0-100)"
    )
    smart_estimate_eps: Decimal = Field(
        decimal_places=4,
        description="SmartEstimate EPS used in signal generation"
    )
    consensus_eps: Decimal = Field(
        decimal_places=4,
        description="Consensus EPS used in signal generation"
    )
    divergence_pct: Decimal = Field(
        decimal_places=4,
        description="Divergence between smart estimate and consensus as percentage"
    )
    days_to_earnings: int = Field(
        description="Days until earnings announcement at signal_date"
    )
    valid_until: datetime = Field(
        description="Signal validity window end (typically earnings announcement date)"
    )
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the signal was ingested into the system"
    )

    # Relationships
    security: Optional[Security] = Relationship(back_populates="earnings_signals")
```

---

## Relationship Updates to Existing Models

Add these relationship fields to the existing `Security` model in `/backend/models/securities.py`:

```python
# In Security class

# Phase 3 relationships for Earnings Surprise Predictor
earnings_estimates: List["EarningsEstimate"] = Relationship(back_populates="security")
earnings_actuals: List["EarningsActual"] = Relationship(back_populates="security")
pead_measurements: List["PEADMeasurement"] = Relationship(back_populates="security")
earnings_signals: List["EarningsSignal"] = Relationship(back_populates="security")
```

---

## Indexing Strategy

### Query Patterns

1. **Fetch latest estimates for a ticker**: `idx_earnings_estimate_ticker_date`
2. **Get all estimates for a fiscal quarter**: `idx_earnings_estimate_ticker_quarter`
3. **Retrieve actuals for PEAD calculation**: `idx_earnings_actual_ticker_quarter`
4. **Query signals by validity window**: `idx_earnings_signal_valid_until`
5. **Analyze analyst accuracy trends**: `idx_analyst_scorecard_period`
6. **PEAD analysis by surprise type**: `idx_pead_measurement_surprise_direction`

### Composite Indexes

- `(ticker, fiscal_quarter)` — Core grouping for earnings data
- `(ticker, estimate_date)` — Historical point-in-time queries
- `(ticker, signal_date)` — Signal replay for backtesting
- `(analyst_broker, period_start, period_end)` — Analyst history trending

---

## Data Flow

### Ingestion Pipeline

1. **yfinance Estimates** → `earnings_estimate` (consensus + smart_estimate)
2. **Individual Analyst Data** → `earnings_estimate` (estimate_type='individual')
3. **SEC EDGAR Filings** → `earnings_actual` (source='sec_edgar')
4. **yfinance Actuals** → `earnings_actual` (source='yfinance')

### SmartEstimate Calculation

```python
# Pseudocode for SmartEstimate calculation
def calculate_smart_estimate(ticker: str, fiscal_quarter: str, as_of_date: datetime):
    """
    Fetch all individual estimates for a given date.
    Apply recency decay and accuracy tier weights.
    Return weighted average.
    """
    estimates = fetch_estimates(ticker, fiscal_quarter, on_or_before=as_of_date)

    for est in estimates:
        # Recency decay: exponential decay from estimate_date to as_of_date
        days_old = (as_of_date - est.estimate_date).days
        decay_weight = exp(-ln(2) / half_life_days * days_old)

        # Accuracy tier weight
        scorecard = fetch_analyst_scorecard(est.analyst_broker, ticker)
        tier_weight = get_tier_weight(scorecard.avg_error_pct)

        # Combined weight
        est.weight = decay_weight * tier_weight

    # Weighted average
    smart_estimate = sum(est.eps_estimate * est.weight for est in estimates) / sum(est.weight for est in estimates)

    return smart_estimate
```

### PEAD Measurement

```python
# After earnings announcement
def measure_pead(ticker: str, fiscal_quarter: str, earnings_date: date):
    """
    1. Fetch actual EPS and calculate surprise_vs_consensus
    2. Calculate cumulative abnormal returns (CAR) in 1d, 5d, 21d, 60d windows
    3. Store in pead_measurement
    """
    actual = fetch_actual(ticker, fiscal_quarter)
    consensus = fetch_consensus_as_of(ticker, fiscal_quarter, earnings_date)

    surprise_pct = (actual.eps - consensus.eps) / abs(consensus.eps) * 100
    surprise_direction = 'positive' if surprise_pct > 0.5 else ('negative' if surprise_pct < -0.5 else 'inline')

    car_1d = calculate_car(ticker, earnings_date, days=1, benchmark='^GSPC')
    car_5d = calculate_car(ticker, earnings_date, days=5, benchmark='^GSPC')
    # ... etc

    pead = PEADMeasurement(
        ticker=ticker,
        fiscal_quarter=fiscal_quarter,
        earnings_date=earnings_date,
        surprise_direction=surprise_direction,
        surprise_magnitude=surprise_pct,
        car_1d=car_1d,
        car_5d=car_5d,
        car_21d=car_21d,
        car_60d=car_60d,
        benchmark_ticker='^GSPC',
        measured_at=datetime.now(timezone.utc)
    )
    db.add(pead)
    db.commit()
```

---

## Alembic Migration: 003_earnings_surprise_predictor_tables.py

```python
"""
Earnings Surprise Predictor tables for AlphaDesk Phase 3.

Revision ID: 003
Revises: 002
Create Date: 2026-03-10

Adds 6 new tables for earnings estimates, actuals, SmartEstimate configuration,
analyst accuracy tracking, PEAD measurement, and earnings signals.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from decimal import Decimal

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all Earnings Surprise Predictor tables."""

    # earnings_estimate table
    op.create_table(
        'earnings_estimate',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('fiscal_quarter', sa.String(), nullable=False),
        sa.Column('estimate_type', sa.String(), nullable=False),
        sa.Column('eps_estimate', sa.Numeric(19, 4), nullable=False),
        sa.Column('estimate_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('analyst_broker', sa.String(), nullable=True),
        sa.Column('revision_number', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'ticker', 'fiscal_quarter', 'estimate_type', 'analyst_broker', 'estimate_date',
            name='uq_earnings_estimate_composite'
        ),
        sa.Index('idx_earnings_estimate_ticker', 'ticker'),
        sa.Index('idx_earnings_estimate_fiscal_quarter', 'fiscal_quarter'),
        sa.Index('idx_earnings_estimate_date', 'estimate_date'),
        sa.Index('idx_earnings_estimate_type', 'estimate_type'),
        sa.Index('idx_earnings_estimate_broker', 'analyst_broker'),
        sa.Index('idx_earnings_estimate_ticker_quarter', 'ticker', 'fiscal_quarter'),
        sa.Index('idx_earnings_estimate_ticker_date', 'ticker', 'estimate_date'),
    )

    # earnings_actual table
    op.create_table(
        'earnings_actual',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('fiscal_quarter', sa.String(), nullable=False),
        sa.Column('actual_eps', sa.Numeric(19, 4), nullable=False),
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('report_time', sa.String(), nullable=True),
        sa.Column('surprise_vs_consensus', sa.Numeric(19, 4), nullable=True),
        sa.Column('surprise_vs_smart', sa.Numeric(19, 4), nullable=True),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'ticker', 'fiscal_quarter', 'report_date',
            name='uq_earnings_actual_composite'
        ),
        sa.Index('idx_earnings_actual_ticker', 'ticker'),
        sa.Index('idx_earnings_actual_fiscal_quarter', 'fiscal_quarter'),
        sa.Index('idx_earnings_actual_report_date', 'report_date'),
        sa.Index('idx_earnings_actual_ticker_quarter', 'ticker', 'fiscal_quarter'),
    )

    # smart_estimate_weights table
    op.create_table(
        'smart_estimate_weights',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('weight_type', sa.String(), nullable=False),
        sa.Column('parameter_name', sa.String(), nullable=False),
        sa.Column('parameter_value', sa.Numeric(19, 4), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'weight_type', 'parameter_name',
            name='uq_smart_estimate_weights_composite'
        ),
        sa.Index('idx_smart_estimate_weights_type', 'weight_type'),
    )

    # analyst_scorecard table
    op.create_table(
        'analyst_scorecard',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('analyst_broker', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=True),
        sa.Column('total_estimates', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('accurate_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('directional_accuracy', sa.Numeric(19, 4), nullable=True),
        sa.Column('avg_error_pct', sa.Numeric(19, 4), nullable=True),
        sa.Column('last_evaluated', sa.DateTime(timezone=True), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'analyst_broker', 'ticker', 'period_start', 'period_end',
            name='uq_analyst_scorecard_composite'
        ),
        sa.Index('idx_analyst_scorecard_broker', 'analyst_broker'),
        sa.Index('idx_analyst_scorecard_ticker', 'ticker'),
        sa.Index('idx_analyst_scorecard_period', 'period_start', 'period_end'),
    )

    # pead_measurement table
    op.create_table(
        'pead_measurement',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('fiscal_quarter', sa.String(), nullable=False),
        sa.Column('earnings_date', sa.Date(), nullable=False),
        sa.Column('surprise_direction', sa.String(), nullable=False),
        sa.Column('surprise_magnitude', sa.Numeric(19, 4), nullable=False),
        sa.Column('car_1d', sa.Numeric(19, 4), nullable=True),
        sa.Column('car_5d', sa.Numeric(19, 4), nullable=True),
        sa.Column('car_21d', sa.Numeric(19, 4), nullable=True),
        sa.Column('car_60d', sa.Numeric(19, 4), nullable=True),
        sa.Column('benchmark_ticker', sa.String(), nullable=True),
        sa.Column('measured_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'ticker', 'fiscal_quarter', 'measured_at',
            name='uq_pead_measurement_composite'
        ),
        sa.Index('idx_pead_measurement_ticker', 'ticker'),
        sa.Index('idx_pead_measurement_fiscal_quarter', 'fiscal_quarter'),
        sa.Index('idx_pead_measurement_earnings_date', 'earnings_date'),
        sa.Index('idx_pead_measurement_surprise_direction', 'surprise_direction'),
        sa.Index('idx_pead_measurement_measured_at', 'measured_at'),
    )

    # earnings_signal table
    op.create_table(
        'earnings_signal',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('fiscal_quarter', sa.String(), nullable=False),
        sa.Column('signal_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('signal_type', sa.String(), nullable=False),
        sa.Column('confidence', sa.Integer(), nullable=False),
        sa.Column('smart_estimate_eps', sa.Numeric(19, 4), nullable=False),
        sa.Column('consensus_eps', sa.Numeric(19, 4), nullable=False),
        sa.Column('divergence_pct', sa.Numeric(19, 4), nullable=False),
        sa.Column('days_to_earnings', sa.Integer(), nullable=False),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ingestion_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticker'], ['security.ticker']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'ticker', 'fiscal_quarter', 'signal_date',
            name='uq_earnings_signal_composite'
        ),
        sa.Index('idx_earnings_signal_ticker', 'ticker'),
        sa.Index('idx_earnings_signal_fiscal_quarter', 'fiscal_quarter'),
        sa.Index('idx_earnings_signal_date', 'signal_date'),
        sa.Index('idx_earnings_signal_type', 'signal_type'),
        sa.Index('idx_earnings_signal_valid_until', 'valid_until'),
        sa.Index('idx_earnings_signal_ticker_date', 'ticker', 'signal_date'),
    )


def downgrade() -> None:
    """Drop all Earnings Surprise Predictor tables."""

    op.drop_table('earnings_signal')
    op.drop_table('pead_measurement')
    op.drop_table('analyst_scorecard')
    op.drop_table('smart_estimate_weights')
    op.drop_table('earnings_actual')
    op.drop_table('earnings_estimate')
```

---

## Complete SQLModel Module

Save this as `/backend/models/earnings.py`:

```python
"""
Earnings Surprise Predictor models for AlphaDesk Phase 3.

Provides SmartEstimate weighted consensus, PEAD tracking, and analyst accuracy scoring
using free data from yfinance and SEC EDGAR.
"""

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint, Index
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional, List


class EarningsEstimate(SQLModel, table=True):
    """Individual analyst and consensus earnings estimates with PiT enforcement."""
    __tablename__ = "earnings_estimate"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "fiscal_quarter",
            "estimate_type",
            "analyst_broker",
            "estimate_date",
            name="uq_earnings_estimate_composite"
        ),
        Index("idx_earnings_estimate_ticker", "ticker"),
        Index("idx_earnings_estimate_fiscal_quarter", "fiscal_quarter"),
        Index("idx_earnings_estimate_date", "estimate_date"),
        Index("idx_earnings_estimate_type", "estimate_type"),
        Index("idx_earnings_estimate_broker", "analyst_broker"),
        Index("idx_earnings_estimate_ticker_quarter", "ticker", "fiscal_quarter"),
        Index("idx_earnings_estimate_ticker_date", "ticker", "estimate_date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(foreign_key="security.ticker", index=True)
    fiscal_quarter: str = Field(
        description="Fiscal quarter in format YYYYQ# (e.g., '2025Q4')"
    )
    estimate_type: str = Field(
        description="Type of estimate: 'consensus', 'smart_estimate', 'individual'"
    )
    eps_estimate: Decimal = Field(
        decimal_places=4,
        description="Earnings per share estimate"
    )
    estimate_date: datetime = Field(
        description="When the estimate was published (PiT timestamp)"
    )
    analyst_broker: Optional[str] = Field(
        default=None,
        description="Analyst/broker name (null for consensus/smart_estimate)"
    )
    revision_number: int = Field(
        default=0,
        description="Revision count for this estimate"
    )
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When data was ingested into the system"
    )

    # Relationships
    security: Optional["Security"] = Relationship(back_populates="earnings_estimates")


class EarningsActual(SQLModel, table=True):
    """Actual reported EPS after earnings announcement."""
    __tablename__ = "earnings_actual"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "fiscal_quarter",
            "report_date",
            name="uq_earnings_actual_composite"
        ),
        Index("idx_earnings_actual_ticker", "ticker"),
        Index("idx_earnings_actual_fiscal_quarter", "fiscal_quarter"),
        Index("idx_earnings_actual_report_date", "report_date"),
        Index("idx_earnings_actual_ticker_quarter", "ticker", "fiscal_quarter"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(foreign_key="security.ticker", index=True)
    fiscal_quarter: str = Field(
        description="Fiscal quarter in format YYYYQ# (e.g., '2025Q4')"
    )
    actual_eps: Decimal = Field(
        decimal_places=4,
        description="Actual reported earnings per share"
    )
    report_date: date = Field(
        description="Date when earnings were reported"
    )
    report_time: Optional[str] = Field(
        default=None,
        description="Time of report: 'pre_market', 'post_market', 'during'"
    )
    surprise_vs_consensus: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="Surprise % vs. consensus estimate: (actual - consensus) / abs(consensus) * 100"
    )
    surprise_vs_smart: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="Surprise % vs. smart estimate: (actual - smart) / abs(smart) * 100"
    )
    source: str = Field(
        description="Source of actual: 'yfinance' or 'sec_edgar'"
    )
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When data was ingested into the system"
    )

    # Relationships
    security: Optional["Security"] = Relationship(back_populates="earnings_actuals")


class SmartEstimateWeights(SQLModel, table=True):
    """Configuration for SmartEstimate weighted consensus calculation."""
    __tablename__ = "smart_estimate_weights"
    __table_args__ = (
        UniqueConstraint(
            "weight_type",
            "parameter_name",
            name="uq_smart_estimate_weights_composite"
        ),
        Index("idx_smart_estimate_weights_type", "weight_type"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    weight_type: str = Field(
        description="Weight category: 'recency_decay', 'accuracy_tier', 'broker_size'"
    )
    parameter_name: str = Field(
        description="Parameter name (e.g., 'half_life_days', 'tier_1_weight', 'size_large_weight')"
    )
    parameter_value: Decimal = Field(
        decimal_places=4,
        description="Decimal value for the parameter"
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the parameter"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this weight was last updated"
    )


class AnalystScorecard(SQLModel, table=True):
    """Historical accuracy tracking for analysts and brokers."""
    __tablename__ = "analyst_scorecard"
    __table_args__ = (
        UniqueConstraint(
            "analyst_broker",
            "ticker",
            "period_start",
            "period_end",
            name="uq_analyst_scorecard_composite"
        ),
        Index("idx_analyst_scorecard_broker", "analyst_broker"),
        Index("idx_analyst_scorecard_ticker", "ticker"),
        Index("idx_analyst_scorecard_period", "period_start", "period_end"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    analyst_broker: str = Field(
        description="Analyst or broker name"
    )
    ticker: Optional[str] = Field(
        default=None,
        description="Specific ticker (null for aggregate across all stocks)"
    )
    total_estimates: int = Field(
        default=0,
        description="Total number of estimates evaluated"
    )
    accurate_count: int = Field(
        default=0,
        description="Count of estimates within ±5% of actual"
    )
    directional_accuracy: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="Percentage of correct direction predictions (0-100)"
    )
    avg_error_pct: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="Average absolute error as percentage"
    )
    last_evaluated: Optional[datetime] = Field(
        default=None,
        description="When accuracy was last calculated"
    )
    period_start: date = Field(
        description="Start date of evaluation period"
    )
    period_end: date = Field(
        description="End date of evaluation period"
    )


class PEADMeasurement(SQLModel, table=True):
    """Post-Earnings Announcement Drift (PEAD) tracking with multiple return windows."""
    __tablename__ = "pead_measurement"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "fiscal_quarter",
            "measured_at",
            name="uq_pead_measurement_composite"
        ),
        Index("idx_pead_measurement_ticker", "ticker"),
        Index("idx_pead_measurement_fiscal_quarter", "fiscal_quarter"),
        Index("idx_pead_measurement_earnings_date", "earnings_date"),
        Index("idx_pead_measurement_surprise_direction", "surprise_direction"),
        Index("idx_pead_measurement_measured_at", "measured_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(foreign_key="security.ticker", index=True)
    fiscal_quarter: str = Field(
        description="Fiscal quarter in format YYYYQ# (e.g., '2025Q4')"
    )
    earnings_date: date = Field(
        description="Date of earnings announcement"
    )
    surprise_direction: str = Field(
        description="Direction of surprise: 'positive', 'negative', 'inline'"
    )
    surprise_magnitude: Decimal = Field(
        decimal_places=4,
        description="Magnitude of surprise as percentage"
    )
    car_1d: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="Cumulative abnormal return (CAR) over 1 day"
    )
    car_5d: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="CAR over 5 trading days"
    )
    car_21d: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="CAR over 21 trading days (1 month)"
    )
    car_60d: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="CAR over 60 trading days (3 months)"
    )
    benchmark_ticker: Optional[str] = Field(
        default=None,
        description="Benchmark ticker for abnormal return calculation (e.g., '^GSPC' for S&P 500)"
    )
    measured_at: datetime = Field(
        description="Point-in-time when PEAD was measured (for backtesting)"
    )

    # Relationships
    security: Optional["Security"] = Relationship(back_populates="pead_measurements")


class EarningsSignal(SQLModel, table=True):
    """Pre-earnings directional signals derived from estimate divergence."""
    __tablename__ = "earnings_signal"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "fiscal_quarter",
            "signal_date",
            name="uq_earnings_signal_composite"
        ),
        Index("idx_earnings_signal_ticker", "ticker"),
        Index("idx_earnings_signal_fiscal_quarter", "fiscal_quarter"),
        Index("idx_earnings_signal_date", "signal_date"),
        Index("idx_earnings_signal_type", "signal_type"),
        Index("idx_earnings_signal_valid_until", "valid_until"),
        Index("idx_earnings_signal_ticker_date", "ticker", "signal_date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(foreign_key="security.ticker", index=True)
    fiscal_quarter: str = Field(
        description="Fiscal quarter in format YYYYQ# (e.g., '2025Q4')"
    )
    signal_date: datetime = Field(
        description="When the signal was generated (PiT timestamp)"
    )
    signal_type: str = Field(
        description="Signal direction: 'buy', 'sell', 'hold'"
    )
    confidence: int = Field(
        ge=0,
        le=100,
        description="Confidence level (0-100)"
    )
    smart_estimate_eps: Decimal = Field(
        decimal_places=4,
        description="SmartEstimate EPS used in signal generation"
    )
    consensus_eps: Decimal = Field(
        decimal_places=4,
        description="Consensus EPS used in signal generation"
    )
    divergence_pct: Decimal = Field(
        decimal_places=4,
        description="Divergence between smart estimate and consensus as percentage"
    )
    days_to_earnings: int = Field(
        description="Days until earnings announcement at signal_date"
    )
    valid_until: datetime = Field(
        description="Signal validity window end (typically earnings announcement date)"
    )
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the signal was ingested into the system"
    )

    # Relationships
    security: Optional["Security"] = Relationship(back_populates="earnings_signals")
```

---

## Summary of Changes

### New Tables (6)
1. **earnings_estimate** — 1M+ rows expected; indexes on ticker, date, type
2. **earnings_actual** — ~1,000s rows; unique per ticker/quarter/date
3. **smart_estimate_weights** — Configuration table; dozens of rows
4. **analyst_scorecard** — Hundreds to thousands of rows; updated quarterly
5. **pead_measurement** — ~1,000s rows; one per earnings event
6. **earnings_signal** — ~10,000s rows; pre-earnings trading signals

### Updated Existing Tables
- **security** — Add 4 new relationships for Phase 3

### Storage & Performance
- Total new data: ~50-100 GB at scale (millions of earnings estimates)
- Composite indexes minimize full-table scans
- Point-in-time enforcement enables accurate backtesting
- No modification to Phase 1 or Phase 2 schemas

### Data Sources
- **yfinance**: Free consensus estimates, smart estimates, actuals
- **SEC EDGAR**: Authoritative actual EPS from 10-Q/10-K filings
- **Analyst broker data**: Free tier from various market data providers

---

## Next Steps

1. Generate Alembic migration: `alembic revision --autogenerate -m "earnings_surprise_predictor_tables"`
2. Run migration: `alembic upgrade head`
3. Implement earnings data ingestion pipelines (Phase 3 implementation)
4. Build SmartEstimate calculation engine
5. Implement PEAD analysis and trader feedback loop
