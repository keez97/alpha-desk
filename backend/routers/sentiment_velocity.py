"""
Sentiment Velocity API Router - REST endpoints for market sentiment velocity analysis.

Provides access to aggregate sentiment scores, velocity calculations,
contrarian divergence flags, and news density metrics.
"""

from fastapi import APIRouter, Query
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from backend.services.sentiment_velocity import get_sentiment_velocity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sentiment-velocity", tags=["sentiment-velocity"])


# ==================== Pydantic Response Models ====================


class Headline(BaseModel):
    """News headline with sentiment score."""

    headline: str
    ticker: str
    sentiment: float = Field(..., ge=-1, le=1)
    published_at: str


class HistoryPoint(BaseModel):
    """Daily sentiment history point."""

    date: str
    sentiment: float
    news_count: int


class SentimentVelocityResponse(BaseModel):
    """Aggregate sentiment velocity with contrarian flags."""

    timestamp: str
    aggregate_score: float = Field(..., ge=-1, le=1, description="Consolidated sentiment -1 to +1")
    velocity: float = Field(..., description="Sentiment change rate (today vs 5d avg)")
    velocity_signal: str = Field(..., description="accelerating|decelerating|stable")
    contrarian_flag: Optional[str] = Field(None, description="overbought|oversold|null")
    news_density: int = Field(..., description="Number of articles analyzed")
    attention_level: str = Field(..., description="normal|elevated|extreme")
    top_headlines: List[Headline] = Field(..., description="Top 10 headlines by sentiment extremity")
    history_5d: List[HistoryPoint] = Field(..., description="5-day sentiment history")


# ==================== API Endpoints ====================


@router.get("", response_model=SentimentVelocityResponse)
def get_sentiment_velocity_data(
    tickers: Optional[str] = Query(
        None,
        description="Comma-separated tickers (default: SPY,QQQ)",
    ),
):
    """
    Get aggregate market sentiment, velocity, and contrarian signals.

    This endpoint provides:
    - Aggregate sentiment score from recent news
    - Sentiment velocity (rate of change vs 5-day average)
    - Contrarian divergence flags (extreme sentiment vs price action)
    - News density and attention level classification
    - Top headlines ranked by sentiment extremity

    Query parameters:
    - tickers: Comma-separated ticker list (default: SPY,QQQ)

    Returns:
    - Dictionary with all sentiment and velocity metrics
    - Includes 5-day historical sentiment data for charting
    - Contrarian flags when sentiment-price divergence is extreme
    """
    # Parse tickers
    ticker_list = None
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

    try:
        result = get_sentiment_velocity(ticker_list)

        # Build response, converting headline list to Headline objects
        headlines = [
            Headline(
                headline=h["headline"],
                ticker=h["ticker"],
                sentiment=h["sentiment"],
                published_at=h["published_at"],
            )
            for h in result.get("top_headlines", [])
        ]

        history = [
            HistoryPoint(
                date=h["date"],
                sentiment=h["sentiment"],
                news_count=int(h["news_count"]),
            )
            for h in result.get("history_5d", [])
        ]

        return SentimentVelocityResponse(
            timestamp=result["timestamp"],
            aggregate_score=result["aggregate_score"],
            velocity=result["velocity"],
            velocity_signal=result["velocity_signal"],
            contrarian_flag=result["contrarian_flag"],
            news_density=result["news_density"],
            attention_level=result["attention_level"],
            top_headlines=headlines,
            history_5d=history,
        )

    except Exception as e:
        logger.error(f"Error fetching sentiment velocity: {e}", exc_info=True)
        # Return default response on error
        return SentimentVelocityResponse(
            timestamp=datetime.utcnow().isoformat(),
            aggregate_score=0.0,
            velocity=0.0,
            velocity_signal="stable",
            contrarian_flag=None,
            news_density=0,
            attention_level="normal",
            top_headlines=[],
            history_5d=[],
        )
