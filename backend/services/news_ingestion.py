"""
News Ingestion Service - Pull and process financial news from free sources.

Fetches headlines via feedparser RSS feeds, deduplicates, scores, and aggregates
sentiment across tickers and time windows.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
import logging
from sqlmodel import Session
import feedparser
import time

from backend.repositories.sentiment_repo import SentimentRepository
from backend.services.sentiment_engine import SentimentEngine, calculate_dedup_hash

logger = logging.getLogger(__name__)

# RSS feed sources
RSS_FEEDS = {
    "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "CNBC": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "Yahoo Finance": "https://finance.yahoo.com/news/rss",
    "Reuters": "https://feeds.reuters.com/reuters/businessNews",
}

# Ticker to company keywords mapping
TICKER_KEYWORDS = {
    # Technology Sector ETF
    "XLK": ["technology", "tech", "software", "semiconductor", "semiconductor"],
    # Healthcare Sector ETF
    "XLV": ["healthcare", "health", "pharmaceutical", "pharma", "medical", "biotech"],
    # Energy Sector ETF
    "XLE": ["energy", "oil", "gas", "petroleum", "coal", "renewable"],
    # Financials Sector ETF
    "XLF": ["finance", "financial", "bank", "banking", "insurance", "mortgage"],
    # Industrials Sector ETF
    "XLI": ["industrial", "manufacturing", "aerospace", "defense", "supply chain"],
    # Consumer Discretionary ETF
    "XLY": ["consumer", "retail", "restaurant", "hotel", "automotive"],
    # Consumer Staples ETF
    "XLP": ["staples", "food", "beverage", "grocery", "consumer staples"],
    # Materials Sector ETF
    "XLB": ["materials", "mining", "metals", "chemical", "steel"],
    # Real Estate ETF
    "XLRE": ["real estate", "reit", "property", "housing", "commercial"],
    # Utilities Sector ETF
    "XLU": ["utility", "utilities", "power", "electric", "water"],
    # Nasdaq 100 ETF
    "QQQ": ["nasdaq", "tech", "technology", "growth"],
    # S&P 500 ETF
    "SPY": ["s&p", "sp500", "market", "stocks", "wall street", "equities", "market"],
}

# Module-level cache with TTL
_rss_cache = {
    "articles": [],
    "fetch_time": None,
    "ttl_seconds": 600,  # 10 minutes
}


def _is_cache_valid() -> bool:
    """Check if RSS cache is still valid."""
    fetch_time = _rss_cache.get("fetch_time")
    if fetch_time is None:
        return False
    elapsed = time.time() - fetch_time
    return elapsed < _rss_cache.get("ttl_seconds", 600)


def _match_ticker(headline: str) -> str:
    """
    Match article headline against ticker keywords to determine relevant ticker.

    Args:
        headline: Article headline text

    Returns:
        Ticker symbol (or "SPY" if no match)
    """
    headline_lower = headline.lower()

    for ticker, keywords in TICKER_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in headline_lower:
                return ticker

    return "SPY"  # Default to general market news


def fetch_rss_articles(max_per_source: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch articles from all RSS feeds.

    Uses module-level cache with 10-minute TTL to avoid hammering feeds.

    Args:
        max_per_source: Maximum articles to fetch from each source

    Returns:
        List of article dictionaries with keys:
        - headline: Article title
        - source: Source name (MarketWatch, CNBC, etc.)
        - published_at: datetime object
        - url: Article URL
        - body_snippet: Summary text
    """
    # Check cache
    if _is_cache_valid():
        logger.info("Using cached RSS articles")
        return _rss_cache["articles"]

    articles = []

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            logger.info(f"Fetching RSS feed from {source_name}: {feed_url}")
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                logger.warning(f"Feed parsing issues for {source_name}: {feed.bozo_exception}")

            article_count = 0
            for entry in feed.entries:
                if article_count >= max_per_source:
                    break

                try:
                    # Extract published date
                    published_at = datetime.now(timezone.utc)
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published_at = datetime.fromtimestamp(
                            time.mktime(entry.published_parsed),
                            tz=timezone.utc
                        )
                    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                        published_at = datetime.fromtimestamp(
                            time.mktime(entry.updated_parsed),
                            tz=timezone.utc
                        )

                    # Extract body snippet
                    body_snippet = ""
                    if hasattr(entry, "summary"):
                        body_snippet = entry.summary[:500]
                    elif hasattr(entry, "description"):
                        body_snippet = entry.description[:500]

                    # feedparser entries support both attr and dict access
                    title = getattr(entry, "title", "") or entry.get("title", "")
                    link = getattr(entry, "link", "") or entry.get("link", "")

                    article = {
                        "headline": title,
                        "title": title,  # alias for smart_analysis compatibility
                        "source": source_name,
                        "publisher": source_name,  # alias for frontend compat
                        "published_at": published_at.isoformat() if isinstance(published_at, datetime) else str(published_at),
                        "publishedAt": published_at.isoformat() if isinstance(published_at, datetime) else str(published_at),
                        "url": link,
                        "body_snippet": body_snippet,
                    }

                    articles.append(article)
                    article_count += 1

                except Exception as e:
                    logger.warning(f"Error processing entry from {source_name}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching RSS feed from {source_name}: {e}")
            continue

    # Update cache
    _rss_cache["articles"] = articles
    _rss_cache["fetch_time"] = time.time()

    logger.info(f"Fetched {len(articles)} articles from RSS feeds")
    return articles


class NewsIngestionService:
    """Service for news ingestion, scoring, and aggregation."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = SentimentRepository(session)
        self.engine = SentimentEngine(session)

    def ingest_news(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Pull headlines from RSS feeds and match them to tickers.

        Process:
        1. Fetch articles from RSS feeds using feedparser
        2. Match articles to tickers via keyword matching
        3. Extract headline, source, published_at, url
        4. Return raw articles organized by ticker

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary with:
            - articles_fetched: Total count
            - articles_by_ticker: Dict of ticker -> article list
            - errors: List of error messages
        """
        stats = {
            "articles_fetched": 0,
            "articles_by_ticker": {},
            "errors": [],
        }

        # Initialize empty lists for all tickers
        for ticker in tickers:
            stats["articles_by_ticker"][ticker] = []

        try:
            # Fetch all articles from RSS feeds
            rss_articles = fetch_rss_articles(max_per_source=10)

            if not rss_articles:
                logger.warning("No articles fetched from RSS feeds")
                return stats

            # Match articles to tickers and organize
            for rss_article in rss_articles:
                try:
                    # Match article to a ticker based on headline keywords
                    matched_ticker = _match_ticker(rss_article["headline"])

                    # Only include if ticker is in requested list
                    if matched_ticker not in stats["articles_by_ticker"]:
                        # Ticker not requested, but include anyway for tracking
                        pass

                    pub_at = rss_article.get("published_at", datetime.now(timezone.utc))
                    if isinstance(pub_at, datetime):
                        pub_at = pub_at.isoformat()

                    article = {
                        "ticker": matched_ticker,
                        "headline": rss_article.get("headline", ""),
                        "source": rss_article.get("source", "unknown"),
                        "published_at": pub_at,
                        "publishedAt": pub_at,
                        "url": rss_article.get("url", ""),
                        "body_snippet": rss_article.get("body_snippet", ""),
                    }

                    # Add to matched ticker
                    if matched_ticker not in stats["articles_by_ticker"]:
                        stats["articles_by_ticker"][matched_ticker] = []

                    stats["articles_by_ticker"][matched_ticker].append(article)
                    stats["articles_fetched"] += 1

                except Exception as e:
                    logger.warning(f"Error processing RSS article: {e}")
                    stats["errors"].append(f"Article processing: {str(e)}")
                    continue

            logger.info(f"Ingested {stats['articles_fetched']} articles from RSS feeds")

        except Exception as e:
            logger.error(f"Error fetching RSS feeds: {e}")
            stats["errors"].append(f"RSS fetch: {str(e)}")

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
