"""
Event Scanner models for the AlphaDesk Event Scanner Phase 2.

These tables track corporate events, factor signals, and alpha decay windows
for integration with the Factor Backtester.
"""

from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import UniqueConstraint, Index, JSON
from datetime import datetime, timezone
from datetime import date as DateType
from decimal import Decimal
from typing import Optional, List, Any, Dict

# Event type enum: earnings, m_and_a, insider_trade, dividend_change, sec_filing, management_change, guidance_revision, share_repurchase
# Event source enum: SEC_EDGAR, YFINANCE, MANUAL
# Window type enum: 1d, 5d, 21d, 63d


class Event(SQLModel, table=True):
    """
    Corporate events detected from various sources.

    Tracks earnings announcements, M&A, insider trades, dividends, SEC filings,
    management changes, guidance revisions, and share repurchases.
    """
    __tablename__ = "event"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "event_type",
            "event_date",
            "source",
            name="uq_event_ticker_type_date_source"
        ),
        Index("idx_event_ticker", "ticker"),
        Index("idx_event_type", "event_type"),
        Index("idx_event_severity", "severity_score"),
        Index("idx_event_detected", "detected_at"),
        Index("idx_event_date", "event_date"),
        Index("idx_event_source", "source"),
        Index("idx_event_ticker_detected", "ticker", "detected_at"),
    )

    event_id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(foreign_key="security.ticker", index=True)
    event_type: str = Field(index=True)  # earnings, m_and_a, insider_trade, etc.
    severity_score: int = Field(ge=1, le=5)  # 1-5 scale
    detected_at: datetime = Field(index=True)  # Point-in-time timestamp
    event_date: DateType = Field(index=True)  # When the event occurred
    source: str = Field(index=True)  # SEC_EDGAR, YFINANCE, MANUAL
    headline: str
    description: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("metadata", JSON, nullable=True))  # JSON for source-specific data
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    alpha_decay_windows: List["AlphaDecayWindow"] = Relationship(back_populates="event")
    factor_bridges: List["EventFactorBridge"] = Relationship(back_populates="event")
    source_mappings: List["EventSourceMapping"] = Relationship(back_populates="event")


class EventClassificationRule(SQLModel, table=True):
    """
    Rules for classifying and filtering events.

    Defines patterns to match against raw event data for automated classification.
    """
    __tablename__ = "event_classification_rule"
    __table_args__ = (
        Index("idx_rule_classification", "classification"),
        Index("idx_rule_pattern_type", "pattern_type"),
        Index("idx_rule_enabled", "enabled"),
    )

    rule_id: Optional[int] = Field(default=None, primary_key=True)
    classification: str  # Event type or category name
    pattern_type: str  # keyword, filing_form, calendar_event
    pattern_value: Dict[str, Any] = Field(default={}, sa_column=Column(JSON, nullable=False))  # JSON pattern definition
    confidence_score: int = Field(ge=0, le=100)  # 0-100 confidence
    enabled: bool = Field(default=True, index=True)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlphaDecayWindow(SQLModel, table=True):
    """
    Abnormal returns and decay analysis windows for events.

    Measures alpha generated in different time windows after an event.
    Supports PiT (point-in-time) measured_at timestamps for backtesting.
    """
    __tablename__ = "alpha_decay_window"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "window_type",
            "measured_at",
            name="uq_decay_event_window_measured"
        ),
        Index("idx_decay_event", "event_id"),
        Index("idx_decay_window_type", "window_type"),
        Index("idx_decay_measured", "measured_at"),
        Index("idx_decay_event_measured", "event_id", "measured_at"),
    )

    window_id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.event_id", index=True)
    window_type: str  # 1d, 5d, 21d, 63d
    abnormal_return: Decimal = Field(decimal_places=8)  # Decimal for precision
    benchmark_return: Decimal = Field(decimal_places=8)
    measured_at: datetime = Field(index=True)  # PiT timestamp
    confidence: Optional[Decimal] = Field(default=None, decimal_places=4)  # 0-1
    sample_size: Optional[int] = None  # Number of observations in window
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    event: Optional[Event] = Relationship(back_populates="alpha_decay_windows")


class EventFactorBridge(SQLModel, table=True):
    """
    Links events to factor signals and strength.

    Maps events to factor definitions and encodes the strength of the signal
    as a normalized value between -1 and +1.
    """
    __tablename__ = "event_factor_bridge"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "factor_id",
            name="uq_bridge_event_factor"
        ),
        Index("idx_bridge_event", "event_id"),
        Index("idx_bridge_factor", "factor_id"),
        Index("idx_bridge_valid_until", "valid_until"),
    )

    bridge_id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.event_id", index=True)
    factor_id: int = Field(foreign_key="factor_definition.id", index=True)
    signal_value: Decimal = Field(ge=Decimal("-1"), le=Decimal("1"), decimal_places=6)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: Optional[datetime] = None  # When signal expires

    # Relationships
    event: Optional[Event] = Relationship(back_populates="factor_bridges")
    factor_definition: Optional["FactorDefinition"] = Relationship()


class EventSourceMapping(SQLModel, table=True):
    """
    Maps events to their original sources.

    Tracks source URLs, IDs (accession numbers, etc.), and extracted metadata.
    Enables audit trail and deduplication across sources.
    """
    __tablename__ = "event_source_mapping"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "source_type",
            "source_id",
            name="uq_source_event_type_id"
        ),
        Index("idx_source_event", "event_id"),
        Index("idx_source_type", "source_type"),
        Index("idx_source_id", "source_id"),
    )

    mapping_id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.event_id", index=True)
    source_type: str  # SEC_EDGAR, YFINANCE, INSIDER_TRADING, etc.
    source_url: Optional[str] = None
    source_id: str  # Accession number, filing ID, trade ID, etc.
    extracted_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON, nullable=True))  # JSON from source
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    event: Optional[Event] = Relationship(back_populates="source_mappings")


class EventAlertConfiguration(SQLModel, table=True):
    """
    Configuration for event alerts and notifications.

    Defines which events to alert on, severity thresholds, and ticker filters.
    """
    __tablename__ = "event_alert_configuration"
    __table_args__ = (
        Index("idx_alert_enabled", "enabled"),
    )

    config_id: Optional[int] = Field(default=None, primary_key=True)
    event_type_filter: List[str] = Field(default=[], sa_column=Column(JSON, nullable=False))  # JSON array of event types
    severity_threshold: int = Field(ge=1, le=5, default=1)  # Min severity (1-5)
    enabled: bool = Field(default=True, index=True)
    tickers_filter: Optional[List[str]] = Field(default=None, sa_column=Column(JSON, nullable=True))  # JSON array of tickers or null for all
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EventCorrelationAnalysis(SQLModel, table=True):
    """
    Analysis of co-occurrence patterns between event types.

    Tracks how often different event types occur together and their
    temporal correlation strength.
    """
    __tablename__ = "event_correlation_analysis"
    __table_args__ = (
        UniqueConstraint(
            "event_type_1",
            "event_type_2",
            "analyzed_period_end",
            name="uq_corr_event_types_period"
        ),
        Index("idx_corr_event_1", "event_type_1"),
        Index("idx_corr_event_2", "event_type_2"),
        Index("idx_corr_analyzed_period", "analyzed_period_end"),
        Index("idx_corr_strength", "correlation_strength"),
    )

    analysis_id: Optional[int] = Field(default=None, primary_key=True)
    event_type_1: str  # First event type
    event_type_2: str  # Second event type
    co_occurrence_count: int = Field(ge=0)  # How many times they co-occurred
    time_window_days: int  # Lookback window for correlation
    correlation_strength: Decimal = Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=6)
    analyzed_period_end: DateType  # As-of date for this analysis
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
