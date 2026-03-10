"""
News Sentiment Scoring models for AlphaDesk Phase 4.

Provides FinBERT + Loughran-McDonald sentiment analysis with velocity tracking
and contrarian divergence alerts.
"""

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint, Index
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict


class NewsArticle(SQLModel, table=True):
    """Individual news articles with sentiment scores and metadata."""
    __tablename__ = "news_article"
    __table_args__ = (
        UniqueConstraint(
            "dedup_hash",
            name="uq_news_article_hash"
        ),
        Index("idx_news_article_ticker", "ticker"),
        Index("idx_news_article_published_at", "published_at"),
        Index("idx_news_article_source", "source"),
        Index("idx_news_article_sentiment_score", "sentiment_score"),
        Index("idx_news_article_ingestion_timestamp", "ingestion_timestamp"),
        Index("idx_news_article_dedup_hash", "dedup_hash"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(
        foreign_key="security.ticker",
        index=True,
        description="Primary security ticker mentioned in article"
    )
    source: str = Field(
        description="News source (e.g., 'reuters', 'bloomberg', 'finviz')"
    )
    headline: str = Field(
        description="Article headline/title"
    )
    body_snippet: Optional[str] = Field(
        default=None,
        description="First N words of article body for context"
    )
    published_at: datetime = Field(
        description="When article was published (PiT timestamp)"
    )
    tickers_mentioned: Optional[Dict[str, float]] = Field(
        default=None,
        description="JSON dict of all tickers mentioned with sentiment contribution weight"
    )
    sentiment_score: Decimal = Field(
        ge=Decimal("-1"),
        le=Decimal("1"),
        decimal_places=4,
        description="Overall sentiment score from -1 (bearish) to +1 (bullish)"
    )
    finbert_positive: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        decimal_places=4,
        description="FinBERT positive confidence (0-1)"
    )
    finbert_negative: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        decimal_places=4,
        description="FinBERT negative confidence (0-1)"
    )
    finbert_neutral: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        decimal_places=4,
        description="FinBERT neutral confidence (0-1)"
    )
    lm_categories: Optional[Dict[str, int]] = Field(
        default=None,
        description="Loughran-McDonald word counts: uncertainty, litigious, constraining, positive, negative"
    )
    source_url: Optional[str] = Field(
        default=None,
        description="URL to original article"
    )
    dedup_hash: str = Field(
        description="SHA256 hash of (headline, source) for deduplication",
        unique=True,
        index=True
    )
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When data was ingested into the system"
    )

    # Relationships
    security: Optional["Security"] = Relationship(back_populates="news_articles")


class TickerSentiment(SQLModel, table=True):
    """Aggregated sentiment metrics by ticker and time window."""
    __tablename__ = "ticker_sentiment"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "window_type",
            "computed_at",
            name="uq_ticker_sentiment_composite"
        ),
        Index("idx_ticker_sentiment_ticker", "ticker"),
        Index("idx_ticker_sentiment_window", "window_type"),
        Index("idx_ticker_sentiment_computed_at", "computed_at"),
        Index("idx_ticker_sentiment_ticker_window", "ticker", "window_type"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(
        foreign_key="security.ticker",
        index=True,
        description="Security ticker"
    )
    window_type: str = Field(
        description="Time window: '24h', '7d', or '30d'"
    )
    sentiment_score: Decimal = Field(
        ge=Decimal("-1"),
        le=Decimal("1"),
        decimal_places=4,
        description="Exponentially weighted average sentiment for window"
    )
    sentiment_velocity: Decimal = Field(
        ge=Decimal("-1"),
        le=Decimal("1"),
        decimal_places=4,
        description="First derivative: change in sentiment (rolling 7-day delta)"
    )
    article_count: int = Field(
        ge=0,
        description="Number of articles in this window"
    )
    computed_at: datetime = Field(
        description="When this aggregate was computed (PiT)"
    )
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When data was ingested into the system"
    )

    # Relationships
    security: Optional["Security"] = Relationship(back_populates="ticker_sentiments")


class SentimentAlert(SQLModel, table=True):
    """Sentiment-based alerts for contrarian and momentum signals."""
    __tablename__ = "sentiment_alert"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "alert_date",
            "alert_type",
            name="uq_sentiment_alert_composite"
        ),
        Index("idx_sentiment_alert_ticker", "ticker"),
        Index("idx_sentiment_alert_type", "alert_type"),
        Index("idx_sentiment_alert_date", "alert_date"),
        Index("idx_sentiment_alert_resolved", "resolved_at"),
        Index("idx_sentiment_alert_active", "ticker", "resolved_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(
        foreign_key="security.ticker",
        index=True,
        description="Security ticker"
    )
    alert_type: str = Field(
        description="Alert type: 'contrarian_bullish', 'contrarian_bearish', 'momentum_shift', 'velocity_spike'"
    )
    sentiment_score: Decimal = Field(
        ge=Decimal("-1"),
        le=Decimal("1"),
        decimal_places=4,
        description="Sentiment score at time of alert"
    )
    price_return: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="Price return at time of alert (%)"
    )
    divergence_magnitude: Decimal = Field(
        ge=Decimal("0"),
        decimal_places=4,
        description="Magnitude of sentiment-price divergence (absolute value)"
    )
    alert_date: datetime = Field(
        description="When alert was triggered"
    )
    resolved_at: Optional[datetime] = Field(
        default=None,
        description="When alert was resolved (sentiment/price converged)"
    )
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When data was ingested into the system"
    )

    # Relationships
    security: Optional["Security"] = Relationship(back_populates="sentiment_alerts")


class SentimentHeatmapCache(SQLModel, table=True):
    """Sector-level sentiment aggregation (cached for dashboard)."""
    __tablename__ = "sentiment_heatmap_cache"
    __table_args__ = (
        UniqueConstraint(
            "sector",
            "window_type",
            "computed_at",
            name="uq_sentiment_heatmap_composite"
        ),
        Index("idx_sentiment_heatmap_sector", "sector"),
        Index("idx_sentiment_heatmap_window", "window_type"),
        Index("idx_sentiment_heatmap_computed_at", "computed_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    sector: str = Field(
        description="GICS sector name (e.g., 'Technology', 'Healthcare')"
    )
    window_type: str = Field(
        description="Time window: '24h', '7d', or '30d'"
    )
    avg_sentiment: Decimal = Field(
        ge=Decimal("-1"),
        le=Decimal("1"),
        decimal_places=4,
        description="Average sentiment across sector tickers"
    )
    article_count: int = Field(
        ge=0,
        description="Total articles in sector for this window"
    )
    top_movers: Optional[Dict[str, float]] = Field(
        default=None,
        description="JSON: top 5 tickers by velocity magnitude with values"
    )
    computed_at: datetime = Field(
        description="When this cache was computed"
    )
