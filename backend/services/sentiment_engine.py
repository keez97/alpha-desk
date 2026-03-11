"""
Sentiment Engine - LLM-based FinBERT scoring and sentiment analysis.

Implements article scoring, ticker sentiment aggregation, velocity calculation,
and contrarian divergence detection using OpenRouter LLM with structured prompts.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
import math
import json
import hashlib
import logging
from sqlmodel import Session

from backend.repositories.sentiment_repo import SentimentRepository
from backend.models.sentiment import TickerSentiment
from backend.services.claude_service import _call_llm, USE_MOCK
from backend.config import LLM_PROVIDER

logger = logging.getLogger(__name__)

# Check if API key is available for LLM scoring
USE_LLM_SCORING = LLM_PROVIDER != "none"


class SentimentEngine:
    """Sentiment analysis engine using LLM-based FinBERT-like scoring."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = SentimentRepository(session)

    def score_article(
        self,
        headline: str,
        body_snippet: str,
    ) -> Dict[str, Any]:
        """
        Score an article using LLM with structured prompt for FinBERT-like output.

        Process:
        1. Call OpenRouter LLM with structured prompt
        2. Extract sentiment score (-1 to +1)
        3. Extract FinBERT-style confidences (positive, negative, neutral)
        4. Extract Loughran-McDonald category counts
        5. Return structured result

        Args:
            headline: Article headline
            body_snippet: First N words of article body

        Returns:
            Dictionary with:
            - sentiment_score: -1 to +1 score
            - finbert_positive: 0-1 confidence
            - finbert_negative: 0-1 confidence
            - finbert_neutral: 0-1 confidence
            - lm_categories: Dict with uncertainty, litigious, constraining, positive, negative counts
            - error: Optional error message
        """
        if not USE_LLM_SCORING:
            logger.warning("LLM scoring disabled - returning neutral score")
            return {
                "sentiment_score": Decimal("0"),
                "finbert_positive": Decimal("0.33"),
                "finbert_negative": Decimal("0.33"),
                "finbert_neutral": Decimal("0.34"),
                "lm_categories": {
                    "uncertainty": 0,
                    "litigious": 0,
                    "constraining": 0,
                    "positive": 0,
                    "negative": 0,
                },
            }

        try:
            prompt = self._build_scoring_prompt(headline, body_snippet)
            system_prompt = "You are a financial sentiment analysis expert. Return JSON responses only."
            logger.info("Scoring article with LLM")

            text_content = _call_llm(system_prompt, prompt, max_tokens=500)
            parsed = self._parse_scoring_response(text_content)

            if parsed:
                return parsed

            logger.warning(f"Failed to parse LLM response: {text_content[:200]}")
            return self._neutral_score()

        except Exception as e:
            logger.error(f"Error scoring article: {e}")
            return self._neutral_score()

    def compute_ticker_sentiment(
        self,
        ticker: str,
        window_type: str,
    ) -> Dict[str, Any]:
        """
        Compute aggregated sentiment for a ticker over a time window.

        Process:
        1. Retrieve articles for ticker in the specified window
        2. Apply exponential weighting (more recent = higher weight)
        3. Calculate weighted average sentiment
        4. Return aggregation with article count

        Args:
            ticker: Security ticker
            window_type: '24h', '7d', or '30d'

        Returns:
            Dictionary with:
            - sentiment_score: Weighted average
            - article_count: Number of articles
            - weights_detail: Optional details on weighting
        """
        now = datetime.now(timezone.utc)

        # Determine lookback window
        if window_type == "24h":
            lookback_hours = 24
        elif window_type == "7d":
            lookback_hours = 7 * 24
        elif window_type == "30d":
            lookback_hours = 30 * 24
        else:
            logger.warning(f"Unknown window_type: {window_type}, defaulting to 7d")
            lookback_hours = 7 * 24

        since = now - timedelta(hours=lookback_hours)

        # Get articles for ticker
        articles = self.repo.get_articles_for_ticker(ticker, since, limit=500)

        if not articles:
            return {
                "sentiment_score": Decimal("0"),
                "article_count": 0,
                "error": "No articles found",
            }

        # Apply exponential weighting (half-life = 1/3 of window)
        half_life_hours = lookback_hours / 3.0
        lambda_param = math.log(2) / half_life_hours

        weighted_sum = Decimal("0")
        weight_sum = Decimal("0")

        for article in articles:
            hours_since = (now - article.published_at).total_seconds() / 3600.0
            weight = Decimal(str(math.exp(-lambda_param * hours_since)))

            weighted_sum += article.sentiment_score * weight
            weight_sum += weight

        if weight_sum == 0:
            return {
                "sentiment_score": Decimal("0"),
                "article_count": len(articles),
                "error": "Weight calculation error",
            }

        sentiment_score = weighted_sum / weight_sum

        return {
            "sentiment_score": sentiment_score,
            "article_count": len(articles),
        }

    def compute_velocity(
        self,
        ticker: str,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        Calculate sentiment velocity (first derivative over N days).

        Process:
        1. Get sentiment history for past N days (7d window)
        2. Calculate 7-day rolling sentiment
        3. Compute delta from N days ago to now
        4. Return velocity with direction

        Args:
            ticker: Security ticker
            days: Number of days to calculate velocity over (default 7)

        Returns:
            Dictionary with:
            - sentiment_velocity: Change in sentiment score
            - direction: 'accelerating' (velocity > 0) or 'decelerating'
        """
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)

        # Get recent sentiment history
        sentiments = self.repo.get_sentiment_history(
            ticker,
            window_type="7d",
            days=days
        )

        if len(sentiments) < 2:
            return {
                "sentiment_velocity": Decimal("0"),
                "direction": "neutral",
                "error": "Insufficient data",
            }

        # Sort by computed_at ASC (oldest first)
        sentiments = sorted(sentiments, key=lambda s: s.computed_at)

        # Get earliest and latest
        oldest = sentiments[0]
        latest = sentiments[-1]

        # Calculate velocity
        sentiment_velocity = latest.sentiment_score - oldest.sentiment_score

        direction = "accelerating" if sentiment_velocity > 0 else "decelerating"

        return {
            "sentiment_velocity": sentiment_velocity,
            "direction": direction,
            "days_calculated": days,
        }

    def detect_divergences(
        self,
        ticker: str,
        price_return: Decimal,
    ) -> Optional[Dict[str, Any]]:
        """
        Detect sentiment-price divergence for contrarian alerts.

        Rules:
        - If sentiment <= -0.5 AND price_return >= 0: contrarian_bullish
        - If sentiment >= 0.5 AND price_return <= 0: contrarian_bearish
        - If velocity > 0.3 AND price_return < -5: momentum_shift (sentiment bullish but price falling)
        - If velocity < -0.3 AND price_return > 5: momentum_shift (sentiment bearish but price rising)

        Args:
            ticker: Security ticker
            price_return: Price return over window (%)

        Returns:
            Dictionary with divergence details or None if no divergence
        """
        # Get current sentiment
        sentiment = self.repo.get_ticker_sentiment(ticker, "7d")

        if not sentiment:
            return None

        divergence_mag = abs(float(sentiment.sentiment_score) + float(price_return) / 100.0)

        # Check contrarian signals
        if sentiment.sentiment_score <= Decimal("-0.5") and price_return >= Decimal("0"):
            return {
                "alert_type": "contrarian_bullish",
                "divergence_magnitude": Decimal(str(divergence_mag)),
                "sentiment_score": sentiment.sentiment_score,
                "price_return": price_return,
                "message": "Extreme bearish sentiment despite positive price return",
            }

        if sentiment.sentiment_score >= Decimal("0.5") and price_return <= Decimal("0"):
            return {
                "alert_type": "contrarian_bearish",
                "divergence_magnitude": Decimal(str(divergence_mag)),
                "sentiment_score": sentiment.sentiment_score,
                "price_return": price_return,
                "message": "Extreme bullish sentiment despite negative price return",
            }

        # Check momentum shifts
        if sentiment.sentiment_velocity > Decimal("0.3") and price_return < Decimal("-5"):
            return {
                "alert_type": "momentum_shift",
                "divergence_magnitude": Decimal(str(divergence_mag)),
                "sentiment_score": sentiment.sentiment_score,
                "price_return": price_return,
                "message": "Sentiment accelerating bullish but price falling sharply",
            }

        if sentiment.sentiment_velocity < Decimal("-0.3") and price_return > Decimal("5"):
            return {
                "alert_type": "momentum_shift",
                "divergence_magnitude": Decimal(str(divergence_mag)),
                "sentiment_score": sentiment.sentiment_score,
                "price_return": price_return,
                "message": "Sentiment accelerating bearish but price rising sharply",
            }

        # Check velocity spike
        if abs(sentiment.sentiment_velocity) > Decimal("0.5"):
            return {
                "alert_type": "velocity_spike",
                "divergence_magnitude": abs(sentiment.sentiment_velocity),
                "sentiment_score": sentiment.sentiment_score,
                "price_return": price_return,
                "message": f"Sentiment velocity spike: {sentiment.sentiment_velocity}",
            }

        return None

    def generate_heatmap(self) -> Dict[str, Any]:
        """
        Generate sector-level sentiment aggregation.

        Process:
        1. Get all ticker sentiments for current window
        2. Group by sector from Securities table
        3. Calculate average sentiment by sector
        4. Find top movers (by velocity) in each sector
        5. Cache results

        Returns:
            Dictionary with sector aggregations
        """
        from sqlmodel import select
        from backend.models.securities import Security

        now = datetime.now(timezone.utc)
        window_type = "7d"

        # Get all ticker sentiments (most recent for each ticker)
        query = select(TickerSentiment).where(
            TickerSentiment.window_type == window_type,
        ).distinct()

        sentiments = self.session.exec(query).all()

        if not sentiments:
            return {"error": "No sentiment data available"}

        # Group by sector
        sector_data: Dict[str, List] = {}

        for ts in sentiments:
            # Get sector from Security table
            security = self.session.exec(
                select(Security).where(Security.ticker == ts.ticker)
            ).first()

            sector = security.sector if security and security.sector else "Unknown"

            if sector not in sector_data:
                sector_data[sector] = []

            sector_data[sector].append(ts)

        # Calculate aggregates and cache
        result = {}

        for sector, ticker_sentiments in sector_data.items():
            if not ticker_sentiments:
                continue
            # Average sentiment
            avg_sentiment = sum(ts.sentiment_score for ts in ticker_sentiments) / len(ticker_sentiments)
            total_articles = sum(ts.article_count for ts in ticker_sentiments)

            # Top movers by velocity
            sorted_by_velocity = sorted(
                ticker_sentiments,
                key=lambda ts: abs(ts.sentiment_velocity),
                reverse=True
            )
            top_movers = {
                ts.ticker: float(ts.sentiment_velocity)
                for ts in sorted_by_velocity[:5]
            }

            # Save to cache
            self.repo.save_heatmap_cache(
                sector=sector,
                window_type=window_type,
                avg_sentiment=avg_sentiment,
                article_count=total_articles,
                top_movers=top_movers,
                computed_at=now,
            )

            result[sector] = {
                "avg_sentiment": float(avg_sentiment),
                "article_count": total_articles,
                "ticker_count": len(ticker_sentiments),
                "top_movers": top_movers,
            }

        return result

    # ==================== Private Helpers ====================

    def _build_scoring_prompt(self, headline: str, body_snippet: str) -> str:
        """Build the LLM prompt for article scoring."""
        # Sanitize inputs to prevent prompt injection
        safe_headline = headline.replace("{", "{{").replace("}", "}}").strip()[:500]
        safe_body = body_snippet.replace("{", "{{").replace("}", "}}").strip()[:2000]
        return f"""Analyze the following financial news article for sentiment.

<ARTICLE_HEADLINE>
{safe_headline}
</ARTICLE_HEADLINE>
<ARTICLE_EXCERPT>
{safe_body}
</ARTICLE_EXCERPT>

Return a JSON object with:
{{
  "sentiment_score": <float from -1.0 (bearish) to +1.0 (bullish)>,
  "finbert_positive": <float 0.0-1.0 confidence>,
  "finbert_negative": <float 0.0-1.0 confidence>,
  "finbert_neutral": <float 0.0-1.0 confidence>,
  "lm_categories": {{
    "uncertainty": <int count of uncertainty words>,
    "litigious": <int count of litigious words>,
    "constraining": <int count of constraining words>,
    "positive": <int count of positive words>,
    "negative": <int count of negative words>
  }},
  "reasoning": "<brief explanation of scoring>"
}}

Ensure positive + negative + neutral sum to ~1.0.
Sentiment_score should match the overall tone: negative sentiment → -1, positive → +1.
"""

    def _parse_scoring_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response into structured sentiment data."""
        try:
            # Try to find JSON in response
            json_start = text.find("{")
            json_end = text.rfind("}") + 1

            if json_start < 0 or json_end <= json_start:
                return None

            json_str = text[json_start:json_end]
            data = json.loads(json_str)

            return {
                "sentiment_score": Decimal(str(data.get("sentiment_score", 0))),
                "finbert_positive": Decimal(str(data.get("finbert_positive", 0.33))),
                "finbert_negative": Decimal(str(data.get("finbert_negative", 0.33))),
                "finbert_neutral": Decimal(str(data.get("finbert_neutral", 0.34))),
                "lm_categories": data.get("lm_categories", {
                    "uncertainty": 0,
                    "litigious": 0,
                    "constraining": 0,
                    "positive": 0,
                    "negative": 0,
                }),
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error parsing sentiment response: {e}")
            return None

    def _neutral_score(self) -> Dict[str, Any]:
        """Return neutral sentiment score."""
        return {
            "sentiment_score": Decimal("0"),
            "finbert_positive": Decimal("0.33"),
            "finbert_negative": Decimal("0.33"),
            "finbert_neutral": Decimal("0.34"),
            "lm_categories": {
                "uncertainty": 0,
                "litigious": 0,
                "constraining": 0,
                "positive": 0,
                "negative": 0,
            },
        }


def calculate_dedup_hash(headline: str, source: str) -> str:
    """Calculate SHA256 hash for article deduplication."""
    content = f"{headline}|{source}".lower().strip()
    return hashlib.sha256(content.encode()).hexdigest()
