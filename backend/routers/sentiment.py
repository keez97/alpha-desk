"""
Sentiment API Router - REST endpoints for news sentiment analysis.

Provides access to article scores, ticker sentiment aggregates, alerts,
and sector heatmap visualizations.
"""

from fastapi import APIRouter, Depends, Query, Path, HTTPException
import logging
import re

logger = logging.getLogger(__name__)
from sqlmodel import Session
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal

from backend.database import get_session
from backend.repositories.sentiment_repo import SentimentRepository
from backend.services.sentiment_engine import SentimentEngine
from backend.services.news_ingestion import NewsIngestionService

router = APIRouter(prefix="/api/sentiment", tags=["sentiment"])


# ==================== Pydantic Response Models ====================


class ArticleResponse(BaseModel):
    """News article with sentiment score."""
    headline: str
    source: str
    published_at: datetime
    sentiment_score: float
    finbert_positive: float
    finbert_negative: float
    finbert_neutral: float
    source_url: Optional[str] = None
    lm_categories: Optional[Dict[str, int]] = None


class TickerSentimentResponse(BaseModel):
    """Ticker-level sentiment aggregate."""
    ticker: str
    window_type: str
    sentiment_score: float
    sentiment_velocity: float
    article_count: int
    computed_at: datetime


class SentimentAlertResponse(BaseModel):
    """Sentiment-based alert."""
    ticker: str
    alert_type: str
    sentiment_score: float
    price_return: Optional[float] = None
    divergence_magnitude: float
    alert_date: datetime
    resolved_at: Optional[datetime] = None


class SentimentHistoryItem(BaseModel):
    """Historical sentiment point."""
    computed_at: datetime
    sentiment_score: float
    sentiment_velocity: float
    article_count: int


class SentimentMoverResponse(BaseModel):
    """Top mover by sentiment velocity."""
    ticker: str
    sentiment_score: float
    sentiment_velocity: float
    article_count: int
    computed_at: datetime


class HeatmapCellResponse(BaseModel):
    """Sector heatmap cell."""
    sector: str
    window_type: str
    avg_sentiment: float
    article_count: int
    top_movers: Optional[Dict[str, float]] = None
    computed_at: datetime


class RefreshResponse(BaseModel):
    """News ingestion refresh result."""
    status: str
    articles_fetched: int
    articles_scored: int
    sentiments_computed: int
    alerts_generated: int
    errors: List[str] = []


# ==================== API Endpoints ====================


@router.get("/{ticker}", response_model=Dict[str, Any])
def get_sentiment(
    ticker: str = Path(..., min_length=1, max_length=10, description="Stock ticker"),
    session: Session = Depends(get_session),
):
    """
    Get current sentiment for a ticker across all time windows.

    Returns sentiment scores (24h, 7d, 30d), velocity, and Loughran-McDonald breakdown.

    Path parameters:
    - ticker: Stock ticker (e.g., AAPL)

    Returns dict with:
    - ticker: The requested ticker
    - windows: Dict with 24h, 7d, 30d sentiment data
    - breakdown: L-M category analysis
    """
    repo = SentimentRepository(session)

    result = {
        "ticker": ticker.upper(),
        "windows": {},
        "breakdown": {},
    }

    for window in ["24h", "7d", "30d"]:
        sentiment = repo.get_ticker_sentiment(ticker, window)

        if sentiment:
            result["windows"][window] = {
                "sentiment_score": float(sentiment.sentiment_score),
                "sentiment_velocity": float(sentiment.sentiment_velocity),
                "article_count": sentiment.article_count,
                "computed_at": sentiment.computed_at.isoformat(),
            }
        else:
            result["windows"][window] = None

    return result


@router.get("/{ticker}/history", response_model=List[SentimentHistoryItem])
def get_sentiment_history(
    ticker: str = Path(..., min_length=1, max_length=10),
    window_type: str = Query("7d", description="Window type: 24h, 7d, or 30d"),
    days: int = Query(30, ge=1, le=180, description="Number of days of history"),
    session: Session = Depends(get_session),
):
    """
    Get historical sentiment time series for a ticker.

    Returns sentiment scores over time, useful for charting sentiment trends.

    Path parameters:
    - ticker: Stock ticker

    Query parameters:
    - window_type: Aggregation window (24h, 7d, 30d)
    - days: Days of history to retrieve (1-180)
    """
    repo = SentimentRepository(session)

    if window_type not in ["24h", "7d", "30d"]:
        raise HTTPException(status_code=400, detail="Invalid window_type")

    sentiments = repo.get_sentiment_history(ticker, window_type, days=days)

    return [
        SentimentHistoryItem(
            computed_at=s.computed_at,
            sentiment_score=float(s.sentiment_score),
            sentiment_velocity=float(s.sentiment_velocity),
            article_count=s.article_count,
        )
        for s in sentiments
    ]


@router.get("/alerts", response_model=List[SentimentAlertResponse])
def get_alerts(
    active_only: bool = Query(True, description="Only return unresolved alerts"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    session: Session = Depends(get_session),
):
    """
    Get sentiment-based alerts (contrarian divergence, momentum shifts, velocity spikes).

    Query parameters:
    - active_only: Filter to unresolved alerts only (default true)
    - limit: Maximum results (1-500)

    Returns list of active sentiment alerts sorted by date.
    """
    repo = SentimentRepository(session)

    alerts = repo.get_active_alerts(limit=limit) if active_only else []

    return [
        SentimentAlertResponse(
            ticker=a.ticker,
            alert_type=a.alert_type,
            sentiment_score=float(a.sentiment_score),
            price_return=float(a.price_return) if a.price_return else None,
            divergence_magnitude=float(a.divergence_magnitude),
            alert_date=a.alert_date,
            resolved_at=a.resolved_at,
        )
        for a in alerts
    ]


@router.get("/movers", response_model=List[SentimentMoverResponse])
def get_movers(
    window_type: str = Query("7d", description="Window type: 24h, 7d, or 30d"),
    limit: int = Query(20, ge=1, le=100, description="Number of movers to return"),
    session: Session = Depends(get_session),
):
    """
    Get top tickers by sentiment velocity magnitude.

    Useful for finding tickers with the most rapidly changing sentiment.

    Query parameters:
    - window_type: Aggregation window (24h, 7d, 30d)
    - limit: Number of results (1-100)

    Returns tickers sorted by absolute velocity.
    """
    repo = SentimentRepository(session)

    if window_type not in ["24h", "7d", "30d"]:
        raise HTTPException(status_code=400, detail="Invalid window_type")

    movers = repo.get_sentiment_movers(limit=limit, window_type=window_type)

    return [
        SentimentMoverResponse(
            ticker=m["ticker"],
            sentiment_score=Decimal(str(m["sentiment_score"])),
            sentiment_velocity=Decimal(str(m["sentiment_velocity"])),
            article_count=m["article_count"],
            computed_at=datetime.fromisoformat(m["computed_at"]),
        )
        for m in movers
    ]


@router.get("/news/{ticker}", response_model=List[ArticleResponse])
def get_news(
    ticker: str = Path(..., min_length=1, max_length=10, description="Stock ticker"),
    limit: int = Query(50, ge=1, le=500, description="Maximum articles"),
    session: Session = Depends(get_session),
):
    """
    Get recent scored articles for a ticker.

    Returns articles with sentiment scores, FinBERT confidences, and L-M breakdown.

    Path parameters:
    - ticker: Stock ticker

    Query parameters:
    - limit: Maximum articles to return (1-500)
    """
    repo = SentimentRepository(session)

    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(days=30)

    articles = repo.get_articles_for_ticker(ticker, since, limit=limit)

    return [
        ArticleResponse(
            headline=a.headline,
            source=a.source,
            published_at=a.published_at,
            sentiment_score=float(a.sentiment_score),
            finbert_positive=float(a.finbert_positive),
            finbert_negative=float(a.finbert_negative),
            finbert_neutral=float(a.finbert_neutral),
            source_url=a.source_url,
            lm_categories=a.lm_categories,
        )
        for a in articles
    ]


@router.get("/heatmap", response_model=List[HeatmapCellResponse])
def get_heatmap(
    window_type: str = Query("7d", description="Window type: 24h, 7d, or 30d"),
    session: Session = Depends(get_session),
):
    """
    Get sector-level sentiment aggregation (heatmap).

    Returns average sentiment and top movers by sector, useful for rotation analysis.

    Query parameters:
    - window_type: Aggregation window (24h, 7d, 30d)
    """
    repo = SentimentRepository(session)

    if window_type not in ["24h", "7d", "30d"]:
        raise HTTPException(status_code=400, detail="Invalid window_type")

    heatmap = repo.get_heatmap(window_type=window_type)

    return [
        HeatmapCellResponse(
            sector=h.sector,
            window_type=h.window_type,
            avg_sentiment=float(h.avg_sentiment),
            article_count=h.article_count,
            top_movers=h.top_movers,
            computed_at=h.computed_at,
        )
        for h in heatmap
    ]


@router.post("/refresh", response_model=RefreshResponse)
def trigger_refresh(
    tickers: Optional[str] = Query(None, description="Comma-separated ticker list (optional)"),
    session: Session = Depends(get_session),
):
    """
    Trigger news ingestion and sentiment refresh.

    Pulls news, scores articles, aggregates sentiment, detects divergences,
    and regenerates sector heatmap. This is a blocking call.

    Query parameters:
    - tickers: Comma-separated list (optional, uses watchlist if omitted)

    Returns refresh statistics.
    """
    service = NewsIngestionService(session)

    try:
        # Parse tickers if provided
        ticker_list = None
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
            if len(ticker_list) > 100:
                raise HTTPException(status_code=400, detail="Maximum 100 tickers allowed")
            if not all(re.match(r'^[A-Z]{1,10}$', t) for t in ticker_list):
                raise HTTPException(status_code=400, detail="Invalid ticker format")

        result = service.refresh_all(tickers=ticker_list)

        return RefreshResponse(
            status="success",
            articles_fetched=result.get("articles_ingest_fetched", 0),
            articles_scored=result.get("articles_scored", 0),
            sentiments_computed=result.get("sentiments_computed", 0),
            alerts_generated=result.get("alerts_generated", 0),
            errors=result.get("errors", []),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sentiment refresh error: {str(e)}", exc_info=True)
        return RefreshResponse(
            status="error",
            articles_fetched=0,
            articles_scored=0,
            sentiments_computed=0,
            alerts_generated=0,
            errors=["Refresh operation failed. Please try again later."],
        )


# ==================== Additional Query Endpoints ====================


@router.get("/batch/sentiment", response_model=Dict[str, Dict[str, Any]])
def get_sentiment_batch(
    tickers: str = Query(..., description="Comma-separated ticker list (e.g., 'AAPL,MSFT,TSLA')"),
    window_type: str = Query("7d", description="Window type: 24h, 7d, or 30d"),
    session: Session = Depends(get_session),
):
    """
    Batch get sentiment for multiple tickers.

    Query parameters:
    - tickers: Comma-separated list (max 50)
    - window_type: Aggregation window

    Returns dict mapping tickers to sentiment data.
    """
    repo = SentimentRepository(session)

    # Parse and validate tickers
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if len(ticker_list) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 tickers allowed")
    if not all(re.match(r'^[A-Z]{1,10}$', t) for t in ticker_list):
        raise HTTPException(status_code=400, detail="Invalid ticker format")

    if window_type not in ["24h", "7d", "30d"]:
        raise HTTPException(status_code=400, detail="Invalid window_type")

    result = {}
    for ticker in ticker_list:
        sentiment = repo.get_ticker_sentiment(ticker, window_type)

        if sentiment:
            result[ticker] = {
                "sentiment_score": float(sentiment.sentiment_score),
                "sentiment_velocity": float(sentiment.sentiment_velocity),
                "article_count": sentiment.article_count,
                "computed_at": sentiment.computed_at.isoformat(),
            }
        else:
            result[ticker] = None

    return result
