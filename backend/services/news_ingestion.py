"""
News Ingestion Service - Pull and process financial news from free sources.

Fetches headlines via yfinance news API, deduplicates, scores, and aggregates
sentiment across tickers and time windows.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from decimal import Decimal
import logging
from sqlmodel import Session

from backend.repositories.sentiment_repo import SentimentRepository
from backend.services.sentiment_engine import SentimentEngine, calculate_dedup_hash

logger = logging.getLogger(__name__)


class NewsIngestionService:
    """Service for news ingestion, scoring, and aggregation."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = SentimentRepository(session)
        self.engine = SentimentEngine(session)

    def ingest_news(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Pull headlines from yfinance news API for specified tickers.

        Process:
        1. Iterate through tickers
        2. Fetch news from yfinance.Ticker.news
        3. Extract headline, source, published_at, url
        4. Return raw articles for processing

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary with:
            - articles_fetched: Total count
            - articles_by_ticker: Dict of ticker -> article list
            - errors: List of error messages
        """
        import yfinance as yf

        stats = {
            "articles_fetched": 0,
            "articles_by_ticker": {},
            "errors": [],
        }

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                news = stock.news

                if not news or len(news) == 0:
                    logger.info(f"No news found for {ticker}")
                    stats["articles_by_ticker"][ticker] = []
                    continue

                articles = []
                for item in news:
                    try:
                        article = {
                            "ticker": ticker,
                            "headline": item.get("title", ""),
                            "source": item.get("source", "unknown"),
                            "published_at": datetime.fromtimestamp(
                                item.get("providerPublishTime", 0),
                                tz=timezone.utc
                            ),
                            "url": item.get("link", ""),
                            "body_snippet": item.get("summary", "")[:500],  # First 500 chars
                        }
                        articles.append(article)
                        stats["articles_fetched"] += 1
                    except Exception as e:
                        logger.warning(f"Error processing article for {ticker}: {e}")
                        continue

                stats["articles_by_ticker"][ticker] = articles

            except Exception as e:
                logger.error(f"Error fetching news for {ticker}: {e}")
                stats["errors"].append(f"{ticker}: {str(e)}")

        return stats

    def process_batch(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Score articles and store in database with deduplication.

        Process:
        1. For each article:
           a. Calculate dedup_hash
           b. Score with sentiment_engine
           c. Save to database (skip if duplicate)
        2. Return processing statistics

        Args:
            articles: List of raw articles

        Returns:
            Dictionary with:
            - articles_scored: Count of newly scored
            - articles_duplicated: Count of duplicates skipped
            - articles_failed: Count of failures
            - errors: List of error messages
        """
        stats = {
            "articles_scored": 0,
            "articles_duplicated": 0,
            "articles_failed": 0,
            "errors": [],
        }

        for article in articles:
            try:
                # Calculate dedup hash
                dedup_hash = calculate_dedup_hash(
                    article.get("headline", ""),
                    article.get("source", "")
                )

                # Score article
                score_result = self.engine.score_article(
                    headline=article.get("headline", ""),
                    body_snippet=article.get("body_snippet", ""),
                )

                if "error" in score_result:
                    stats["articles_failed"] += 1
                    stats["errors"].append(f"Scoring error: {score_result['error']}")
                    continue

                # Save to database
                saved = self.repo.save_article(
                    ticker=article.get("ticker", ""),
                    source=article.get("source", ""),
                    headline=article.get("headline", ""),
                    published_at=article.get("published_at", datetime.now(timezone.utc)),
                    sentiment_score=score_result.get("sentiment_score", Decimal("0")),
                    finbert_positive=score_result.get("finbert_positive", Decimal("0.33")),
                    finbert_negative=score_result.get("finbert_negative", Decimal("0.33")),
                    finbert_neutral=score_result.get("finbert_neutral", Decimal("0.34")),
                    dedup_hash=dedup_hash,
                    body_snippet=article.get("body_snippet"),
                    tickers_mentioned=article.get("tickers_mentioned"),
                    lm_categories=score_result.get("lm_categories"),
                    source_url=article.get("url"),
                )

                if saved:
                    stats["articles_scored"] += 1
                else:
                    stats["articles_duplicated"] += 1

            except Exception as e:
                logger.error(f"Error processing article: {e}")
                stats["articles_failed"] += 1
                stats["errors"].append(str(e))

        return stats

    def refresh_all(self, tickers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Full refresh pipeline: ingest, score, aggregate, detect divergences.

        Process:
        1. Ingest news for tickers
        2. Process and score articles
        3. Compute ticker sentiment for all windows (24h, 7d, 30d)
        4. Compute velocity for each ticker
        5. Detect divergences and generate alerts
        6. Regenerate heatmap

        Args:
            tickers: Ticker list (optional, defaults to all in watchlist)

        Returns:
            Dictionary with complete refresh statistics
        """
        stats = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "tickers_processed": 0,
            "articles_processed": 0,
            "sentiments_computed": 0,
            "alerts_generated": 0,
            "errors": [],
        }

        if tickers is None:
            # Get all tickers from watchlist or database
            from sqlmodel import select
            from backend.models.watchlist import Watchlist

            watchlist_items = self.session.exec(select(Watchlist)).all()
            tickers = [item.ticker for item in watchlist_items]

        logger.info(f"Starting sentiment refresh for {len(tickers)} tickers")

        # Step 1: Ingest news
        ingest_result = self.ingest_news(tickers)
        stats["articles_ingest_fetched"] = ingest_result["articles_fetched"]

        # Step 2: Process and score
        all_articles = []
        for ticker_articles in ingest_result["articles_by_ticker"].values():
            all_articles.extend(ticker_articles)

        process_result = self.process_batch(all_articles)
        stats["articles_scored"] = process_result["articles_scored"]
        stats["articles_duplicated"] = process_result["articles_duplicated"]

        # Step 3: Compute ticker sentiments
        for ticker in tickers:
            try:
                for window in ["24h", "7d", "30d"]:
                    sentiment = self.engine.compute_ticker_sentiment(ticker, window)

                    # Compute velocity for 7d windows only
                    velocity = Decimal("0")
                    if window == "7d":
                        velocity_result = self.engine.compute_velocity(ticker)
                        velocity = velocity_result.get("sentiment_velocity", Decimal("0"))

                    self.repo.save_ticker_sentiment(
                        ticker=ticker,
                        window_type=window,
                        sentiment_score=sentiment.get("sentiment_score", Decimal("0")),
                        sentiment_velocity=velocity,
                        article_count=sentiment.get("article_count", 0),
                    )
                    stats["sentiments_computed"] += 1

            except Exception as e:
                logger.error(f"Error computing sentiment for {ticker}: {e}")
                stats["errors"].append(f"{ticker}: {str(e)}")

        # Step 4: Detect divergences (would require price data)
        # For now, just log that this step is skipped
        logger.info("Divergence detection requires price data integration (skipped for MVP)")

        # Step 5: Generate heatmap
        try:
            heatmap = self.engine.generate_heatmap()
            stats["heatmap_sectors"] = len(heatmap)
        except Exception as e:
            logger.error(f"Error generating heatmap: {e}")
            stats["errors"].append(f"Heatmap generation: {str(e)}")

        stats["completed_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"Sentiment refresh completed: {stats}")
        return stats

    def refresh_single_ticker(self, ticker: str) -> Dict[str, Any]:
        """
        Refresh sentiment for a single ticker only.

        Args:
            ticker: Single ticker symbol

        Returns:
            Refresh statistics for that ticker
        """
        return self.refresh_all(tickers=[ticker])
