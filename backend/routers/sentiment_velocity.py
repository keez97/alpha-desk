"""
Sentiment Velocity API Router - REST endpoints for market sentiment velocity analysis.

Provides access to aggregate sentiment scores, velocity calculations,
contrarian divergence flags, and news density metrics.
"""

from fastapi import APIRouter, Query
import asyncio
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
    source: str = ""
    link: str = ""
    label: str = "neutral"
    confidence: float = 0.5


class HistoryPoint(BaseModel):
    """Daily sentiment history point."""

    date: str
    sentiment: float
    news_count: int


class SentimentVelocityResponse(BaseModel):
    """Aggregate sentiment velocity with contrarian flags."""

    timestamp: str
    scoring_model: str = Field("none", description="Scoring model used (finbert/keyword-fallback)")
    aggregate_score: float = Field(..., description="Consolidated sentiment -1 to +1")
    velocity: float = Field(..., description="Sentiment change rate (today vs 5d avg)")
    velocity_signal: str = Field(..., description="accelerating|decelerating|stable")
    contrarian_flag: Optional[str] = Field(None, description="overbought|oversold|null")
    news_density: int = Field(..., description="Number of articles analyzed")
    attention_level: str = Field(..., description="normal|elevated|extreme")
    top_headlines: List[Headline] = Field(..., description="Top 15 headlines by sentiment extremity")
    history_5d: List[HistoryPoint] = Field(..., description="5-day sentiment history")
    sentiment_distribution: Dict[str, int] = Field(default_factory=dict, description="positive/negative/neutral counts")


# ==================== API Endpoints ====================


@router.get("", response_model=SentimentVelocityResponse)
async def get_sentiment_velocity_data(
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
        result = await asyncio.wait_for(
            asyncio.to_thread(get_sentiment_velocity, ticker_list),
            timeout=12.0  # 12s timeout for RSS + scoring
        )

        # Build response, converting headline list to Headline objects
        headlines = [
            Headline(
                headline=h["headline"],
                ticker=h.get("ticker", "SPY"),
                sentiment=h["sentiment"],
                published_at=h["published_at"],
                source=h.get("source", ""),
                link=h.get("link", ""),
                label=h.get("label", "neutral"),
                confidence=h.get("confidence", 0.5),
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
            scoring_model=result.get("scoring_model", "none"),
            aggregate_score=max(-1.0, min(1.0, result["aggregate_score"])),
            velocity=result["velocity"],
            velocity_signal=result["velocity_signal"],
            contrarian_flag=result["contrarian_flag"],
            news_density=result["news_density"],
            attention_level=result["attention_level"],
            top_headlines=headlines,
            history_5d=history,
            sentiment_distribution=result.get("sentiment_distribution", {}),
        )

    except asyncio.TimeoutError:
        logger.warning("Sentiment velocity timed out after 12s")
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
