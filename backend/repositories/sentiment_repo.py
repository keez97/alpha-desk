"""
Repository for News Sentiment Scoring CRUD operations and queries.

Provides database access layer for articles, ticker sentiment aggregates,
sentiment alerts, and heatmap caches.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal
from sqlmodel import Session, select
from backend.models.sentiment import (
    NewsArticle,
    TickerSentiment,
    SentimentAlert,
    SentimentHeatmapCache,
)


class SentimentRepository:
    """Repository for sentiment-related database operations."""

    def __init__(self, session: Session):
        self.session = session

    # ==================== NewsArticle CRUD ====================

    def save_article(
        self,
        ticker: str,
        source: str,
        headline: str,
        published_at: datetime,
        sentiment_score: Decimal,
        finbert_positive: Decimal,
        finbert_negative: Decimal,
        finbert_neutral: Decimal,
        dedup_hash: str,
        body_snippet: Optional[str] = None,
        tickers_mentioned: Optional[Dict[str, float]] = None,
        lm_categories: Optional[Dict[str, int]] = None,
        source_url: Optional[str] = None,
    ) -> Optional[NewsArticle]:
        """
        Save a news article with deduplication check on hash.

        Args:
            ticker: Primary ticker mentioned
            source: News source
            headline: Article headline
            published_at: Publication time (PiT)
            sentiment_score: Sentiment score (-1 to +1)
            finbert_positive: FinBERT positive confidence
            finbert_negative: FinBERT negative confidence
            finbert_neutral: FinBERT neutral confidence
            dedup_hash: SHA256 hash for deduplication
            body_snippet: Optional first N words of body
            tickers_mentioned: Optional dict of all tickers with weights
            lm_categories: Optional Loughran-McDonald word counts
            source_url: Optional URL to article

        Returns:
            Created NewsArticle or None if duplicate
        """
        # Check for duplicate
        existing = self.session.exec(
            select(NewsArticle).where(NewsArticle.dedup_hash == dedup_hash)
        ).first()

        if existing:
            return None  # Skip duplicate

        article = NewsArticle(
            ticker=ticker,
            source=source,
            headline=headline,
            body_snippet=body_snippet,
            published_at=published_at,
            tickers_mentioned=tickers_mentioned,
            sentiment_score=sentiment_score,
            finbert_positive=finbert_positive,
            finbert_negative=finbert_negative,
            finbert_neutral=finbert_neutral,
            lm_categories=lm_categories,
            source_url=source_url,
            dedup_hash=dedup_hash,
        )
        self.session.add(article)
        self.session.commit()
        self.session.refresh(article)
        return article

    def get_articles_for_ticker(
        self,
        ticker: str,
        since: datetime,
        limit: int = 100,
    ) -> List[NewsArticle]:
        """
        Get recent articles for a ticker.

        Args:
            ticker: Security ticker
            since: Get articles published after this time
            limit: Maximum number of articles (default 100)

        Returns:
            List of NewsArticle objects ordered by published_at DESC
        """
        query = select(NewsArticle).where(
            NewsArticle.ticker == ticker,
            NewsArticle.published_at >= since,
        ).order_by(NewsArticle.published_at.desc()).limit(limit)

        return self.session.exec(query).all()

    def get_articles_by_date_range(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[NewsArticle]:
        """
        Get articles within a date range.

        Args:
            ticker: Security ticker
            start_date: Range start
            end_date: Range end

        Returns:
            List of NewsArticle objects
        """
        query = select(NewsArticle).where(
            NewsArticle.ticker == ticker,
            NewsArticle.published_at >= start_date,
            NewsArticle.published_at <= end_date,
        ).order_by(NewsArticle.published_at.desc())

        return self.session.exec(query).all()

    # ==================== TickerSentiment CRUD ====================

    def save_ticker_sentiment(
        self,
        ticker: str,
        window_type: str,
        sentiment_score: Decimal,
        sentiment_velocity: Decimal,
        article_count: int,
        computed_at: Optional[datetime] = None,
    ) -> TickerSentiment:
        """
        Save aggregated sentiment for a ticker and window.

        Args:
            ticker: Security ticker
            window_type: '24h', '7d', or '30d'
            sentiment_score: Weighted average sentiment
            sentiment_velocity: Change in sentiment (first derivative)
            article_count: Number of articles in window
            computed_at: When computed (default now)

        Returns:
            Created TickerSentiment object
        """
        if computed_at is None:
            computed_at = datetime.now(timezone.utc)

        sentiment = TickerSentiment(
            ticker=ticker,
            window_type=window_type,
            sentiment_score=sentiment_score,
            sentiment_velocity=sentiment_velocity,
            article_count=article_count,
            computed_at=computed_at,
        )
        self.session.add(sentiment)
        self.session.commit()
        self.session.refresh(sentiment)
        return sentiment

    def get_ticker_sentiment(
        self,
        ticker: str,
        window_type: str,
    ) -> Optional[TickerSentiment]:
        """
        Get most recent sentiment for a ticker and window.

        Args:
            ticker: Security ticker
            window_type: '24h', '7d', or '30d'

        Returns:
            Most recent TickerSentiment or None
        """
        query = select(TickerSentiment).where(
            TickerSentiment.ticker == ticker,
            TickerSentiment.window_type == window_type,
        ).order_by(TickerSentiment.computed_at.desc())

        return self.session.exec(query).first()

    def get_sentiment_history(
        self,
        ticker: str,
        window_type: str,
        days: int = 30,
    ) -> List[TickerSentiment]:
        """
        Get sentiment time series for a ticker.

        Args:
            ticker: Security ticker
            window_type: '24h', '7d', or '30d'
            days: Number of days of history (default 30)

        Returns:
            List of TickerSentiment objects ordered by computed_at DESC
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = select(TickerSentiment).where(
            TickerSentiment.ticker == ticker,
            TickerSentiment.window_type == window_type,
            TickerSentiment.computed_at >= since,
        ).order_by(TickerSentiment.computed_at.desc())

        return self.session.exec(query).all()

    # ==================== SentimentAlert CRUD ====================

    def save_alert(
        self,
        ticker: str,
        alert_type: str,
        sentiment_score: Decimal,
        divergence_magnitude: Decimal,
        alert_date: Optional[datetime] = None,
        price_return: Optional[Decimal] = None,
    ) -> SentimentAlert:
        """
        Save a sentiment alert.

        Args:
            ticker: Security ticker
            alert_type: 'contrarian_bullish', 'contrarian_bearish', 'momentum_shift', 'velocity_spike'
            sentiment_score: Sentiment at time of alert
            divergence_magnitude: Magnitude of divergence
            alert_date: When alert triggered (default now)
            price_return: Price return at time (%)

        Returns:
            Created SentimentAlert object
        """
        if alert_date is None:
            alert_date = datetime.now(timezone.utc)

        alert = SentimentAlert(
            ticker=ticker,
            alert_type=alert_type,
            sentiment_score=sentiment_score,
            price_return=price_return,
            divergence_magnitude=divergence_magnitude,
            alert_date=alert_date,
        )
        self.session.add(alert)
        self.session.commit()
        self.session.refresh(alert)
        return alert

    def get_active_alerts(
        self,
        severity_min: Optional[str] = None,
        limit: int = 100,
    ) -> List[SentimentAlert]:
        """
        Get unresolved (active) sentiment alerts.

        Args:
            severity_min: Optional minimum alert type filter
            limit: Maximum results (default 100)

        Returns:
            List of unresolved SentimentAlert objects ordered by alert_date DESC
        """
        query = select(SentimentAlert).where(
            SentimentAlert.resolved_at.is_(None),
        ).order_by(SentimentAlert.alert_date.desc()).limit(limit)

        return self.session.exec(query).all()

    def resolve_alert(self, alert_id: int, resolved_at: Optional[datetime] = None) -> Optional[SentimentAlert]:
        """
        Mark an alert as resolved.

        Args:
            alert_id: Alert ID
            resolved_at: When resolved (default now)

        Returns:
            Updated SentimentAlert or None if not found
        """
        alert = self.session.exec(
            select(SentimentAlert).where(SentimentAlert.id == alert_id)
        ).first()

        if not alert:
            return None

        if resolved_at is None:
            resolved_at = datetime.now(timezone.utc)

        alert.resolved_at = resolved_at
        self.session.add(alert)
        self.session.commit()
        self.session.refresh(alert)
        return alert

    # ==================== Sentiment Analytics ====================

    def get_sentiment_movers(
        self,
        limit: int = 20,
        window_type: str = "7d",
    ) -> List[Dict[str, Any]]:
        """
        Get top tickers by sentiment velocity magnitude.

        Args:
            limit: Number of results (1-500)
            window_type: '24h', '7d', or '30d'

        Returns:
            List of dicts with ticker, velocity, sentiment_score, article_count
        """
        query = select(TickerSentiment).where(
            TickerSentiment.window_type == window_type,
        ).order_by(
            # Order by absolute value of velocity
            TickerSentiment.sentiment_velocity.desc(),
        ).limit(limit)

        results = self.session.exec(query).all()

        return [
            {
                "ticker": ts.ticker,
                "sentiment_score": float(ts.sentiment_score),
                "sentiment_velocity": float(ts.sentiment_velocity),
                "article_count": ts.article_count,
                "computed_at": ts.computed_at.isoformat(),
            }
            for ts in results
        ]

    # ==================== SentimentHeatmapCache CRUD ====================

    def save_heatmap_cache(
        self,
        sector: str,
        window_type: str,
        avg_sentiment: Decimal,
        article_count: int,
        top_movers: Optional[Dict[str, float]] = None,
        computed_at: Optional[datetime] = None,
    ) -> SentimentHeatmapCache:
        """
        Save sector-level heatmap cache.

        Args:
            sector: GICS sector name
            window_type: '24h', '7d', or '30d'
            avg_sentiment: Average sentiment for sector
            article_count: Total articles in sector
            top_movers: Top 5 tickers with velocity values
            computed_at: When computed (default now)

        Returns:
            Created SentimentHeatmapCache object
        """
        if computed_at is None:
            computed_at = datetime.now(timezone.utc)

        cache = SentimentHeatmapCache(
            sector=sector,
            window_type=window_type,
            avg_sentiment=avg_sentiment,
            article_count=article_count,
            top_movers=top_movers,
            computed_at=computed_at,
        )
        self.session.add(cache)
        self.session.commit()
        self.session.refresh(cache)
        return cache

    def get_heatmap(
        self,
        window_type: str = "7d",
    ) -> List[SentimentHeatmapCache]:
        """
        Get current sector heatmap.

        Args:
            window_type: '24h', '7d', or '30d'

        Returns:
            List of SentimentHeatmapCache ordered by avg_sentiment DESC
        """
        query = select(SentimentHeatmapCache).where(
            SentimentHeatmapCache.window_type == window_type,
        ).order_by(
            SentimentHeatmapCache.computed_at.desc(),
            SentimentHeatmapCache.avg_sentiment.desc(),
        ).distinct()

        return self.session.exec(query).all()

    def get_heatmap_latest(
        self,
        window_type: str = "7d",
    ) -> List[SentimentHeatmapCache]:
        """
        Get latest heatmap for each sector.

        Args:
            window_type: '24h', '7d', or '30d'

        Returns:
            List of latest SentimentHeatmapCache for each sector
        """
        from sqlalchemy import func

        # Get the latest computed_at for each sector
        subquery = select(
            SentimentHeatmapCache.sector,
            func.max(SentimentHeatmapCache.computed_at).label("max_computed_at")
        ).where(
            SentimentHeatmapCache.window_type == window_type,
        ).group_by(SentimentHeatmapCache.sector)

        query = select(SentimentHeatmapCache).from_statement(
            select(SentimentHeatmapCache).join(
                subquery,
                (SentimentHeatmapCache.sector == subquery.c.sector) &
                (SentimentHeatmapCache.computed_at == subquery.c.max_computed_at)
            )
        )

        return self.session.exec(query).all()
