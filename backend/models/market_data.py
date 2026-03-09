from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint, Index
from datetime import datetime, timezone
from datetime import date as DateType
from decimal import Decimal
from typing import Optional
from backend.models.securities import Security


class PriceHistory(SQLModel, table=True):
    """Daily OHLCV price data for securities"""
    __tablename__ = "price_history"
    __table_args__ = (
        UniqueConstraint("ticker", "date", "data_source", name="uq_price_ticker_date_source"),
        Index("idx_price_ticker_date", "ticker", "date"),
        Index("idx_price_ingestion_pit", "ticker", "ingestion_timestamp"),
        Index("idx_price_date_range", "ticker", "date", "ingestion_timestamp"),
        Index("idx_price_created", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(foreign_key="security.ticker", index=True)
    date: DateType = Field(index=True)
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    adjusted_close: Decimal
    volume: int
    data_source: str = Field(default="yfinance", index=True)
    ingestion_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    security: Optional[Security] = Relationship(back_populates="price_history")


class FundamentalsSnapshot(SQLModel, table=True):
    """Point-in-time snapshots of fundamental metrics"""
    __tablename__ = "fundamentals_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "fiscal_period_end",
            "metric_name",
            "source_document_date",
            "data_source",
            name="uq_fundamentals_ticker_period_metric_source"
        ),
        Index("idx_fundamentals_ticker_metric", "ticker", "metric_name"),
        Index("idx_fundamentals_pit", "ticker", "source_document_date", "ingestion_timestamp"),
        Index("idx_fundamentals_date_range", "ticker", "fiscal_period_end", "source_document_date"),
        Index("idx_fundamentals_ingestion", "ingestion_timestamp"),
        Index("idx_fundamentals_created", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(foreign_key="security.ticker", index=True)
    fiscal_period_end: DateType
    metric_name: str = Field(index=True)
    metric_value: Decimal
    source_document_date: DateType
    document_type: str = Field(default="10-K", index=True)
    data_source: str = Field(default="factset", index=True)
    ingestion_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    security: Optional[Security] = Relationship(back_populates="fundamentals")
