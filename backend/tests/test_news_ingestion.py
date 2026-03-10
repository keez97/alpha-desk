"""
Tests for News Ingestion Service - yfinance integration, deduplication, and batch processing.

Tests news fetching from yfinance, article deduplication, batch scoring and storage,
refresh workflows, and error handling.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from sqlmodel import Session

from backend.services.news_ingestion import NewsIngestionService
from backend.repositories.sentiment_repo import SentimentRepository
from backend.models.sentiment import NewsArticle


class TestYFinanceNewsFetching:
    """Test news fetching from yfinance API."""

    def test_ingest_news_success(self, session: Session):
        """Test successful news ingestion from yfinance."""
        service = NewsIngestionService(session)

        mock_news = [
            {
                "title": "Apple Q1 earnings beat",
                "source": "Reuters",
                "providerPublishTime": int(datetime.now(timezone.utc).timestamp()),
                "link": "https://reuters.com/apple",
                "summary": "Apple reported stronger than expected earnings...",
            },
            {
                "title": "Apple announces new product",
                "source": "Bloomberg",
                "providerPublishTime": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
                "link": "https://bloomberg.com/apple",
                "summary": "Apple unveiled its latest innovation...",
            },
        ]

        with patch("backend.services.news_ingestion.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.news = mock_news
            mock_ticker.return_value = mock_instance

            result = service.ingest_news(["AAPL"])

            assert result["articles_fetched"] == 2
            assert "AAPL" in result["articles_by_ticker"]
            assert len(result["articles_by_ticker"]["AAPL"]) == 2

    def test_ingest_news_no_articles(self, session: Session):
        """Test news ingestion when no articles found."""
        service = NewsIngestionService(session)

        with patch("backend.services.news_ingestion.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.news = []
            mock_ticker.return_value = mock_instance

            result = service.ingest_news(["EMPTY"])

            assert result["articles_fetched"] == 0
            assert result["articles_by_ticker"]["EMPTY"] == []

    def test_ingest_news_multiple_tickers(self, session: Session):
        """Test news ingestion for multiple tickers."""
        service = NewsIngestionService(session)

        tickers_news = {
            "AAPL": [
                {
                    "title": "Apple news",
                    "source": "Reuters",
                    "providerPublishTime": int(datetime.now(timezone.utc).timestamp()),
                    "link": "https://reuters.com/apple",
                    "summary": "Apple update",
                }
            ],
            "MSFT": [
                {
                    "title": "Microsoft news",
                    "source": "Bloomberg",
                    "providerPublishTime": int(datetime.now(timezone.utc).timestamp()),
                    "link": "https://bloomberg.com/msft",
                    "summary": "Microsoft update",
                }
            ],
        }

        def mock_ticker_factory(ticker):
            mock_instance = MagicMock()
            mock_instance.news = tickers_news.get(ticker, [])
            return mock_instance

        with patch("backend.services.news_ingestion.yf.Ticker") as mock_ticker:
            mock_ticker.side_effect = mock_ticker_factory

            result = service.ingest_news(["AAPL", "MSFT"])

            assert result["articles_fetched"] == 2
            assert len(result["articles_by_ticker"]["AAPL"]) == 1
            assert len(result["articles_by_ticker"]["MSFT"]) == 1

    def test_ingest_news_api_error(self, session: Session):
        """Test error handling when yfinance API fails."""
        service = NewsIngestionService(session)

        with patch("backend.services.news_ingestion.yf.Ticker") as mock_ticker:
            mock_ticker.side_effect = Exception("yfinance API error")

            result = service.ingest_news(["AAPL"])

            assert result["articles_fetched"] == 0
            assert len(result["errors"]) > 0
            assert "AAPL" in result["errors"][0]

    def test_ingest_news_malformed_article(self, session: Session):
        """Test handling of malformed article data."""
        service = NewsIngestionService(session)

        mock_news = [
            {
                "title": "Valid article",
                "source": "Reuters",
                "providerPublishTime": int(datetime.now(timezone.utc).timestamp()),
                "link": "https://reuters.com/article",
                "summary": "Summary",
            },
            {
                # Missing required fields
                "source": "Bloomberg",
            },
        ]

        with patch("backend.services.news_ingestion.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.news = mock_news
            mock_ticker.return_value = mock_instance

            result = service.ingest_news(["TEST"])

            # Should have processed the valid article
            assert result["articles_fetched"] >= 1


class TestDeduplication:
    """Test article deduplication logic."""

    def test_process_batch_deduplication(self, session: Session):
        """Test that duplicate articles are skipped on save."""
        repo = SentimentRepository(session)
        service = NewsIngestionService(session)

        # First article
        articles = [
            {
                "ticker": "AAPL",
                "source": "reuters",
                "headline": "Apple announces earnings",
                "published_at": datetime.now(timezone.utc),
                "body_snippet": "Strong earnings report",
                "tickers_mentioned": None,
                "url": "https://reuters.com/1",
            },
            {
                "ticker": "AAPL",
                "source": "reuters",
                "headline": "Apple announces earnings",  # Duplicate headline
                "published_at": datetime.now(timezone.utc) - timedelta(hours=1),
                "body_snippet": "Different snippet",
                "tickers_mentioned": None,
                "url": "https://reuters.com/2",
            },
        ]

        with patch.object(service.engine, "score_article") as mock_score:
            mock_score.return_value = {
                "sentiment_score": Decimal("0.5"),
                "finbert_positive": Decimal("0.6"),
                "finbert_negative": Decimal("0.2"),
                "finbert_neutral": Decimal("0.2"),
                "lm_categories": {"uncertainty": 0, "litigious": 0, "constraining": 0, "positive": 3, "negative": 1},
            }

            result = service.process_batch(articles)

            # Should have scored one and identified one as duplicate
            assert result["articles_scored"] == 1
            assert result["articles_duplicated"] == 1

    def test_dedup_hash_matching(self, session: Session):
        """Test that duplicate detection uses hash matching."""
        repo = SentimentRepository(session)

        # Save first article
        from backend.services.sentiment_engine import calculate_dedup_hash

        headline = "Breaking news about company"
        source = "reuters"
        hash_val = calculate_dedup_hash(headline, source)

        repo.save_article(
            ticker="AAPL",
            source=source,
            headline=headline,
            published_at=datetime.now(timezone.utc),
            sentiment_score=Decimal("0.5"),
            finbert_positive=Decimal("0.6"),
            finbert_negative=Decimal("0.2"),
            finbert_neutral=Decimal("0.2"),
            dedup_hash=hash_val,
        )

        # Try to save duplicate
        result = repo.save_article(
            ticker="AAPL",
            source=source,
            headline=headline,
            published_at=datetime.now(timezone.utc),
            sentiment_score=Decimal("0.6"),
            finbert_positive=Decimal("0.7"),
            finbert_negative=Decimal("0.1"),
            finbert_neutral=Decimal("0.2"),
            dedup_hash=hash_val,
        )

        assert result is None  # Duplicate skipped

    def test_dedup_case_insensitive(self, session: Session):
        """Test that dedup is case-insensitive."""
        repo = SentimentRepository(session)

        from backend.services.sentiment_engine import calculate_dedup_hash

        headline_lower = "apple announces earnings"
        headline_upper = "APPLE ANNOUNCES EARNINGS"
        source = "reuters"

        hash_lower = calculate_dedup_hash(headline_lower, source)
        hash_upper = calculate_dedup_hash(headline_upper, source)

        assert hash_lower == hash_upper


class TestBatchProcessing:
    """Test batch processing of articles."""

    def test_process_batch_scoring(self, session: Session):
        """Test that batch processing scores articles."""
        service = NewsIngestionService(session)

        articles = [
            {
                "ticker": "AAPL",
                "source": "reuters",
                "headline": f"Article {i}",
                "published_at": datetime.now(timezone.utc),
                "body_snippet": f"Body snippet {i}",
                "tickers_mentioned": None,
                "url": f"https://reuters.com/{i}",
            }
            for i in range(3)
        ]

        with patch.object(service.engine, "score_article") as mock_score:
            mock_score.return_value = {
                "sentiment_score": Decimal("0.5"),
                "finbert_positive": Decimal("0.6"),
                "finbert_negative": Decimal("0.2"),
                "finbert_neutral": Decimal("0.2"),
                "lm_categories": {"uncertainty": 1, "litigious": 0, "constraining": 0, "positive": 2, "negative": 1},
            }

            result = service.process_batch(articles)

            assert result["articles_scored"] == 3
            assert mock_score.call_count == 3

    def test_process_batch_error_handling(self, session: Session):
        """Test error handling during batch processing."""
        service = NewsIngestionService(session)

        articles = [
            {
                "ticker": "AAPL",
                "source": "reuters",
                "headline": "Valid article",
                "published_at": datetime.now(timezone.utc),
                "body_snippet": "Body",
                "tickers_mentioned": None,
                "url": "https://reuters.com/1",
            },
            {
                "ticker": "MSFT",
                "source": "bloomberg",
                "headline": "Error article",
                "published_at": datetime.now(timezone.utc),
                "body_snippet": "Body",
                "tickers_mentioned": None,
                "url": "https://bloomberg.com/1",
            },
        ]

        with patch.object(service.engine, "score_article") as mock_score:
            # First succeeds, second fails
            mock_score.side_effect = [
                {
                    "sentiment_score": Decimal("0.5"),
                    "finbert_positive": Decimal("0.6"),
                    "finbert_negative": Decimal("0.2"),
                    "finbert_neutral": Decimal("0.2"),
                    "lm_categories": {},
                },
                Exception("Scoring failed"),
            ]

            result = service.process_batch(articles)

            assert result["articles_scored"] == 1
            assert result["articles_failed"] == 1

    def test_process_batch_statistics(self, session: Session):
        """Test that batch processing returns correct statistics."""
        service = NewsIngestionService(session)

        articles = [
            {
                "ticker": "AAPL",
                "source": "reuters",
                "headline": f"Article {i}",
                "published_at": datetime.now(timezone.utc),
                "body_snippet": f"Body {i}",
                "tickers_mentioned": None,
                "url": f"https://reuters.com/{i}",
            }
            for i in range(5)
        ]

        with patch.object(service.engine, "score_article") as mock_score:
            mock_score.return_value = {
                "sentiment_score": Decimal("0.5"),
                "finbert_positive": Decimal("0.6"),
                "finbert_negative": Decimal("0.2"),
                "finbert_neutral": Decimal("0.2"),
                "lm_categories": {},
            }

            result = service.process_batch(articles)

            assert result["articles_scored"] == 5
            assert result["articles_duplicated"] == 0
            assert result["articles_failed"] == 0
            assert "errors" in result


class TestRefreshWorkflow:
    """Test complete refresh workflow."""

    def test_refresh_all_basic(self, session: Session, sample_securities):
        """Test basic refresh_all workflow."""
        service = NewsIngestionService(session)

        mock_news = [
            {
                "title": "Article 1",
                "source": "Reuters",
                "providerPublishTime": int(datetime.now(timezone.utc).timestamp()),
                "link": "https://reuters.com/1",
                "summary": "Summary 1",
            }
        ]

        with patch("backend.services.news_ingestion.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.news = mock_news
            mock_ticker.return_value = mock_instance

            with patch.object(service.engine, "score_article") as mock_score:
                mock_score.return_value = {
                    "sentiment_score": Decimal("0.5"),
                    "finbert_positive": Decimal("0.6"),
                    "finbert_negative": Decimal("0.2"),
                    "finbert_neutral": Decimal("0.2"),
                    "lm_categories": {},
                }

                with patch.object(service.engine, "generate_heatmap") as mock_heatmap:
                    mock_heatmap.return_value = {"Technology": {"avg_sentiment": 0.5}}

                    result = service.refresh_all(tickers=["AAPL"])

                    assert "started_at" in result
                    assert "completed_at" in result
                    assert "sentiments_computed" in result

    def test_refresh_single_ticker(self, session: Session):
        """Test refresh_single_ticker convenience method."""
        service = NewsIngestionService(session)

        with patch.object(service, "refresh_all") as mock_refresh:
            mock_refresh.return_value = {"tickers_processed": 1}

            result = service.refresh_single_ticker("AAPL")

            mock_refresh.assert_called_once()
            # Check it was called with single ticker
            call_args = mock_refresh.call_args
            assert call_args[1]["tickers"] == ["AAPL"]

    def test_refresh_all_with_multiple_windows(self, session: Session, sample_securities):
        """Test that refresh computes all sentiment windows (24h, 7d, 30d)."""
        service = NewsIngestionService(session)

        mock_news = [
            {
                "title": "Article",
                "source": "Reuters",
                "providerPublishTime": int(datetime.now(timezone.utc).timestamp()),
                "link": "https://reuters.com/1",
                "summary": "Summary",
            }
        ]

        with patch("backend.services.news_ingestion.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.news = mock_news
            mock_ticker.return_value = mock_instance

            with patch.object(service.engine, "score_article") as mock_score:
                mock_score.return_value = {
                    "sentiment_score": Decimal("0.5"),
                    "finbert_positive": Decimal("0.6"),
                    "finbert_negative": Decimal("0.2"),
                    "finbert_neutral": Decimal("0.2"),
                    "lm_categories": {},
                }

                with patch.object(service.engine, "generate_heatmap") as mock_heatmap:
                    mock_heatmap.return_value = {}

                    result = service.refresh_all(tickers=["AAPL"])

                    # Should compute 3 windows per ticker
                    assert result["sentiments_computed"] == 3

    def test_refresh_error_handling(self, session: Session):
        """Test error handling during refresh workflow."""
        service = NewsIngestionService(session)

        with patch("backend.services.news_ingestion.yf.Ticker") as mock_ticker:
            mock_ticker.side_effect = Exception("Network error")

            with patch.object(service.engine, "generate_heatmap") as mock_heatmap:
                mock_heatmap.return_value = {}

                result = service.refresh_all(tickers=["AAPL"])

                assert len(result["errors"]) > 0
                assert "started_at" in result
                assert "completed_at" in result


class TestArticleExtraction:
    """Test article extraction and metadata handling."""

    def test_extract_article_metadata(self, session: Session):
        """Test that article metadata is correctly extracted."""
        service = NewsIngestionService(session)

        now = datetime.now(timezone.utc)
        timestamp = int(now.timestamp())

        mock_news = [
            {
                "title": "Company announces strategic partnership",
                "source": "Reuters",
                "providerPublishTime": timestamp,
                "link": "https://reuters.com/partnership",
                "summary": "Detailed summary of the partnership...",
            }
        ]

        with patch("backend.services.news_ingestion.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.news = mock_news
            mock_ticker.return_value = mock_instance

            result = service.ingest_news(["AAPL"])

            article = result["articles_by_ticker"]["AAPL"][0]
            assert article["headline"] == "Company announces strategic partnership"
            assert article["source"] == "Reuters"
            assert article["url"] == "https://reuters.com/partnership"
            assert article["ticker"] == "AAPL"

    def test_body_snippet_truncation(self, session: Session):
        """Test that long body snippets are truncated."""
        service = NewsIngestionService(session)

        long_summary = "A" * 1000  # Very long summary

        mock_news = [
            {
                "title": "Article",
                "source": "Reuters",
                "providerPublishTime": int(datetime.now(timezone.utc).timestamp()),
                "link": "https://reuters.com/1",
                "summary": long_summary,
            }
        ]

        with patch("backend.services.news_ingestion.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.news = mock_news
            mock_ticker.return_value = mock_instance

            result = service.ingest_news(["AAPL"])

            article = result["articles_by_ticker"]["AAPL"][0]
            # Should be truncated to first 500 chars
            assert len(article["body_snippet"]) <= 500


class TestStatisticsTracking:
    """Test that operations track and return statistics."""

    def test_ingest_statistics(self, session: Session):
        """Test that ingest_news tracks statistics."""
        service = NewsIngestionService(session)

        mock_news = [
            {
                "title": f"Article {i}",
                "source": "Reuters",
                "providerPublishTime": int(datetime.now(timezone.utc).timestamp()),
                "link": f"https://reuters.com/{i}",
                "summary": f"Summary {i}",
            }
            for i in range(3)
        ]

        with patch("backend.services.news_ingestion.yf.Ticker") as mock_ticker:
            mock_instance = MagicMock()
            mock_instance.news = mock_news
            mock_ticker.return_value = mock_instance

            result = service.ingest_news(["AAPL"])

            assert result["articles_fetched"] == 3
            assert "articles_by_ticker" in result
            assert "errors" in result

    def test_process_statistics_summary(self, session: Session):
        """Test that process_batch returns summary statistics."""
        service = NewsIngestionService(session)

        articles = [
            {
                "ticker": "AAPL",
                "source": "reuters",
                "headline": f"Article {i}",
                "published_at": datetime.now(timezone.utc),
                "body_snippet": f"Body {i}",
                "tickers_mentioned": None,
                "url": f"https://reuters.com/{i}",
            }
            for i in range(4)
        ]

        with patch.object(service.engine, "score_article") as mock_score:
            mock_score.return_value = {
                "sentiment_score": Decimal("0.5"),
                "finbert_positive": Decimal("0.6"),
                "finbert_negative": Decimal("0.2"),
                "finbert_neutral": Decimal("0.2"),
                "lm_categories": {},
            }

            result = service.process_batch(articles)

            assert "articles_scored" in result
            assert "articles_duplicated" in result
            assert "articles_failed" in result
            assert "errors" in result
