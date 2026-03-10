from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import UniqueConstraint, Index, JSON
from datetime import datetime, timezone
from datetime import date as DateType
from decimal import Decimal
from typing import Optional, List, Any, Dict
from backend.models.factors import FactorDefinition
from backend.models.securities import Security

# BacktestStatus: "DRAFT", "RUNNING", "COMPLETED", "FAILED" (stored as strings)


class Backtest(SQLModel, table=True):
    """Main backtest run record"""
    __tablename__ = "backtest"
    __table_args__ = (
        Index("idx_backtest_status", "status"),
        Index("idx_backtest_created", "created_at"),
        Index("idx_backtest_completed", "completed_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    backtest_type: str = Field(default="factor_combination")
    status: str = Field(default="DRAFT")  # Will store enum value as string
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("metadata", JSON, nullable=True))

    # Relationships
    configuration: Optional["BacktestConfiguration"] = Relationship(back_populates="backtest")
    factor_allocations: List["BacktestFactorAllocation"] = Relationship(back_populates="backtest")
    results: List["BacktestResult"] = Relationship(back_populates="backtest")
    statistics: List["BacktestStatistic"] = Relationship(back_populates="backtest")
    factor_correlations: List["FactorCorrelation"] = Relationship(back_populates="backtest")
    alpha_decay_analyses: List["AlphaDecayAnalysis"] = Relationship(back_populates="backtest")


class BacktestConfiguration(SQLModel, table=True):
    """Configuration parameters for a backtest"""
    __tablename__ = "backtest_configuration"
    __table_args__ = (
        UniqueConstraint("backtest_id", name="uq_config_backtest_id"),
        Index("idx_config_dates", "start_date", "end_date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    backtest_id: int = Field(foreign_key="backtest.id", unique=True)
    start_date: DateType
    end_date: DateType
    rebalance_frequency: str = Field(default="monthly")
    universe_selection: str = Field(default="sp500")
    commission_bps: Decimal = Field(default=Decimal("5.0"))
    slippage_bps: Decimal = Field(default=Decimal("2.0"))
    benchmark_ticker: str = Field(default="SPY")
    rolling_window_months: int = Field(default=60)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    backtest: Optional[Backtest] = Relationship(back_populates="configuration")


class BacktestFactorAllocation(SQLModel, table=True):
    """Factor weights in a backtest"""
    __tablename__ = "backtest_factor_allocation"
    __table_args__ = (
        UniqueConstraint("backtest_id", "factor_id", name="uq_alloc_backtest_factor"),
        Index("idx_alloc_backtest", "backtest_id"),
        Index("idx_alloc_weight", "weight"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    backtest_id: int = Field(foreign_key="backtest.id", index=True)
    factor_id: int = Field(foreign_key="factor_definition.id", index=True)
    weight: Decimal
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    backtest: Optional[Backtest] = Relationship(back_populates="factor_allocations")
    factor_definition: Optional[FactorDefinition] = Relationship(back_populates="backtest_allocations")


class BacktestResult(SQLModel, table=True):
    """Daily backtest results"""
    __tablename__ = "backtest_result"
    __table_args__ = (
        UniqueConstraint("backtest_id", "date", name="uq_result_backtest_date"),
        Index("idx_result_backtest_date", "backtest_id", "date"),
        Index("idx_result_date", "date"),
        Index("idx_result_created", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    backtest_id: int = Field(foreign_key="backtest.id", index=True)
    date: DateType = Field(index=True)
    portfolio_value: Decimal
    daily_return: Decimal
    benchmark_return: Optional[Decimal] = None
    turnover: Optional[Decimal] = None
    factor_exposures: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    holdings_count: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    backtest: Optional[Backtest] = Relationship(back_populates="results")


class BacktestStatistic(SQLModel, table=True):
    """Aggregate statistics from a backtest"""
    __tablename__ = "backtest_statistic"
    __table_args__ = (
        Index("idx_stat_backtest_metric", "backtest_id", "metric_name"),
        Index("idx_stat_period", "period_start", "period_end"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    backtest_id: int = Field(foreign_key="backtest.id", index=True)
    metric_name: str = Field(index=True)
    metric_value: Decimal
    period_start: Optional[DateType] = None
    period_end: Optional[DateType] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    backtest: Optional[Backtest] = Relationship(back_populates="statistics")


class FactorCorrelation(SQLModel, table=True):
    """Correlation between factors in a backtest"""
    __tablename__ = "factor_correlation"
    __table_args__ = (
        UniqueConstraint(
            "backtest_id",
            "factor_1_id",
            "factor_2_id",
            "as_of_date",
            name="uq_corr_backtest_factors_date"
        ),
        Index("idx_corr_backtest", "backtest_id"),
        Index("idx_corr_factors", "factor_1_id", "factor_2_id"),
        Index("idx_corr_date", "as_of_date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    backtest_id: int = Field(foreign_key="backtest.id", index=True)
    factor_1_id: int = Field(foreign_key="factor_definition.id", index=True)
    factor_2_id: int = Field(foreign_key="factor_definition.id", index=True)
    correlation_value: Decimal
    as_of_date: DateType = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    backtest: Optional[Backtest] = Relationship(back_populates="factor_correlations")
    factor_definition_1: Optional[FactorDefinition] = Relationship(
        back_populates="factor_correlations_1",
        sa_relationship_kwargs={"foreign_keys": "[FactorCorrelation.factor_1_id]"},
    )
    factor_definition_2: Optional[FactorDefinition] = Relationship(
        back_populates="factor_correlations_2",
        sa_relationship_kwargs={"foreign_keys": "[FactorCorrelation.factor_2_id]"},
    )


class AlphaDecayAnalysis(SQLModel, table=True):
    """Analysis of alpha decay after factor publication"""
    __tablename__ = "alpha_decay_analysis"
    __table_args__ = (
        UniqueConstraint(
            "factor_id",
            "backtest_id",
            "months_post_publication",
            name="uq_decay_factor_backtest_months"
        ),
        Index("idx_decay_factor", "factor_id"),
        Index("idx_decay_backtest", "backtest_id"),
        Index("idx_decay_months", "months_post_publication"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    factor_id: int = Field(foreign_key="factor_definition.id", index=True)
    backtest_id: int = Field(foreign_key="backtest.id", index=True)
    pre_publication_return: Decimal
    post_publication_return: Decimal
    decay_percentage: Decimal
    months_post_publication: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    factor_definition: Optional[FactorDefinition] = Relationship(back_populates="alpha_decay_analysis")
    backtest: Optional[Backtest] = Relationship(back_populates="alpha_decay_analyses")


class ScreenerFactorScore(SQLModel, table=True):
    """Factor scores used in screener results"""
    __tablename__ = "screener_factor_score"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "factor_id",
            "score_date",
            name="uq_screener_ticker_factor_date"
        ),
        Index("idx_screener_ticker", "ticker"),
        Index("idx_screener_factor", "factor_id"),
        Index("idx_screener_date", "score_date"),
        Index("idx_screener_ingestion", "ingestion_timestamp"),
        Index("idx_screener_quintile", "quintile"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(foreign_key="security.ticker", index=True)
    score_date: DateType = Field(index=True)
    factor_id: int = Field(foreign_key="factor_definition.id", index=True)
    factor_score: Decimal
    quintile: Optional[int] = None
    ingestion_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    security: Optional[Security] = Relationship(back_populates="screener_scores")
    factor_definition: Optional[FactorDefinition] = Relationship(back_populates="screener_scores")
