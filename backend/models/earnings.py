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
