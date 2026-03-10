from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import UniqueConstraint, Index, JSON
from datetime import datetime, timezone
from datetime import date as DateType
from decimal import Decimal
from typing import Optional, List, Any, Dict
from backend.models.securities import Security

# Factor enums (stored as strings, not using Python Enum to avoid SQLModel conflicts)
# FactorType: "fama_french", "custom", "technical"
# FactorFrequency: "daily", "monthly", "quarterly", "annual"


class FactorDefinition(SQLModel, table=True):
    """Master definition of factors used in backtests"""
    __tablename__ = "factor_definition"
    __table_args__ = (
        UniqueConstraint("factor_name", name="uq_factor_name"),
        Index("idx_factor_type", "factor_type"),
        Index("idx_factor_published", "is_published"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    factor_name: str = Field(index=True, unique=True)
    factor_type: str = Field(index=True)  # Will store enum value as string
    description: Optional[str] = None
    frequency: str = Field(default="daily", index=True)  # Will store enum value as string
    is_published: bool = Field(default=False, index=True)
    publication_date: Optional[DateType] = None
    calculation_formula: Optional[str] = None
    data_requirements: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    fama_french_factors: List["FamaFrenchFactor"] = Relationship(back_populates="factor_definition")
    custom_factor_scores: List["CustomFactorScore"] = Relationship(back_populates="factor_definition")
    backtest_allocations: List["BacktestFactorAllocation"] = Relationship(back_populates="factor_definition")
    factor_correlations_1: List["FactorCorrelation"] = Relationship(
        back_populates="factor_definition_1",
        sa_relationship_kwargs={"foreign_keys": "FactorCorrelation.factor_1_id"},
    )
    factor_correlations_2: List["FactorCorrelation"] = Relationship(
        back_populates="factor_definition_2",
        sa_relationship_kwargs={"foreign_keys": "FactorCorrelation.factor_2_id"},
    )
    alpha_decay_analysis: List["AlphaDecayAnalysis"] = Relationship(back_populates="factor_definition")
    screener_scores: List["ScreenerFactorScore"] = Relationship(back_populates="factor_definition")


class FamaFrenchFactor(SQLModel, table=True):
    """Fama-French factor returns data"""
    __tablename__ = "fama_french_factor"
    __table_args__ = (
        UniqueConstraint("factor_id", "date", name="uq_ff_factor_date"),
        Index("idx_ff_factor_date", "factor_id", "date"),
        Index("idx_ff_ingestion", "ingestion_timestamp"),
        Index("idx_ff_created", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    factor_id: int = Field(foreign_key="factor_definition.id", index=True)
    date: DateType = Field(index=True)
    return_value: Decimal
    ingestion_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    factor_definition: Optional[FactorDefinition] = Relationship(back_populates="fama_french_factors")


class CustomFactorScore(SQLModel, table=True):
    """Custom factor scores for securities"""
    __tablename__ = "custom_factor_score"
    __table_args__ = (
        UniqueConstraint("factor_id", "ticker", "calculation_date", name="uq_custom_factor_ticker_date"),
        Index("idx_custom_factor_ticker", "factor_id", "ticker"),
        Index("idx_custom_ticker_date", "ticker", "calculation_date"),
        Index("idx_custom_ingestion", "ingestion_timestamp"),
        Index("idx_custom_created", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    factor_id: int = Field(foreign_key="factor_definition.id", index=True)
    ticker: str = Field(foreign_key="security.ticker", index=True)
    calculation_date: DateType = Field(index=True)
    factor_value: Decimal
    percentile_rank: Optional[Decimal] = None
    ingestion_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    factor_definition: Optional[FactorDefinition] = Relationship(back_populates="custom_factor_scores")
    security: Optional[Security] = Relationship(back_populates="custom_factor_scores")
