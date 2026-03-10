from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Index
from datetime import datetime, timezone
from typing import Optional, List

# SecurityStatus: "ACTIVE", "DELISTED", "ACQUIRED", "BANKRUPT", "PENDING" (stored as strings)


class Security(SQLModel, table=True):
    """Security master data"""
    __tablename__ = "security"

    ticker: str = Field(primary_key=True)
    company_name: str = Field(index=True)
    sector: Optional[str] = None
    industry: Optional[str] = None
    cusip: Optional[str] = Field(default=None, index=True)
    isin: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    lifecycle_events: List["SecurityLifecycleEvent"] = Relationship(back_populates="security")
    price_history: List["PriceHistory"] = Relationship(back_populates="security")
    fundamentals: List["FundamentalsSnapshot"] = Relationship(back_populates="security")
    custom_factor_scores: List["CustomFactorScore"] = Relationship(back_populates="security")
    screener_scores: List["ScreenerFactorScore"] = Relationship(back_populates="security")
    earnings_estimates: List["EarningsEstimate"] = Relationship(back_populates="security")
    earnings_actuals: List["EarningsActual"] = Relationship(back_populates="security")
    pead_measurements: List["PEADMeasurement"] = Relationship(back_populates="security")
    earnings_signals: List["EarningsSignal"] = Relationship(back_populates="security")
    news_articles: List["NewsArticle"] = Relationship(back_populates="security")
    ticker_sentiments: List["TickerSentiment"] = Relationship(back_populates="security")
    sentiment_alerts: List["SentimentAlert"] = Relationship(back_populates="security")


class SecurityLifecycleEvent(SQLModel, table=True):
    """Tracks major lifecycle events for securities (delisting, acquisition, etc.)"""
    __tablename__ = "security_lifecycle_event"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(foreign_key="security.ticker", index=True)
    event_type: str = Field(index=True)
    event_date: datetime = Field(index=True)
    effective_date: datetime = Field()
    details: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    security: Optional[Security] = Relationship(back_populates="lifecycle_events")
