"""
Tests for Sentiment API Endpoints - REST interface for news sentiment analysis.

Tests all sentiment endpoints, input validation, error handling, and query parameters.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlmodel import Session

from backend.main import app
from backend.repositories.sentiment_repo import SentimentRepository
from backend.services.sentiment_engine import calculate_dedup_hash


@pytest.fixture(name="client")
def test_client_fixture(session: Session):
    """Create test client with session override."""

    def get_session_override():
        return session

    app.dependency_overrides["backend.database.get_session"] = get_session_override

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()


class TestGetSentimentEndpoint:
    """Test GET /api/sentiment/{ticker} endpoint."""

    def test_get_sentiment_all_windows(self, session: Session, client: TestClient):
        """Test getting sentiment for all time windows."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        for window in ["24h", "7d", "30d"]:
            repo.save_ticker_sentiment(
                ticker="AAPL",
                window_type=window,
                sentiment_score=Decimal("0.5"),
                sentiment_velocity=Decimal("0.1"),
                article_count=10,
                computed_at=now,
            )

        response = client.get("/api/sentiment/AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert "windows" in data
        assert "24h" in data["windows"]
        assert "7d" in data["windows"]
        assert "30d" in data["windows"]

    def test_get_sentiment_partial_data(self, session: Session, client: TestClient):
        """Test getting sentiment when some windows have no data."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        # Only save 7d data
        repo.save_ticker_sentiment(
            ticker="MSFT",
            window_type="7d",
            sentiment_score=Decimal("0.6"),
            sentiment_velocity=Decimal("0.05"),
            article_count=15,
            computed_at=now,
        )

        response = client.get("/api/sentiment/MSFT")

        assert response.status_code == 200
        data = response.json()
        assert data["windows"]["7d"] is not None
        assert data["windows"]["24h"] is None
        assert data["windows"]["30d"] is None

    def test_get_sentiment_nonexistent_ticker(self, client: TestClient):
        """Test getting sentiment for non-existent ticker."""
        response = client.get("/api/sentiment/NONEXISTENT")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "NONEXISTENT"
        assert all(v is None for v in data["windows"].values())

    def test_get_sentiment_ticker_validation(self, client: TestClient):
        """Test input validation for ticker parameter."""
        # Empty ticker
        response = client.get("/api/sentiment/")
        assert response.status_code == 404

        # Ticker too long
        response = client.get("/api/sentiment/" + "A" * 20)
        assert response.status_code == 422

    def test_get_sentiment_case_insensitive(self, session: Session, client: TestClient):
        """Test that ticker lookup is case-insensitive."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        repo.save_ticker_sentiment(
            ticker="AAPL",
            window_type="7d",
            sentiment_score=Decimal("0.5"),
            sentiment_velocity=Decimal("0.1"),
            article_count=10,
            computed_at=now,
        )

        response = client.get("/api/sentiment/aapl")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"


class TestSentimentHistoryEndpoint:
    """Test GET /api/sentiment/{ticker}/history endpoint."""

    def test_get_sentiment_history_default(self, session: Session, client: TestClient):
        """Test getting sentiment history with default parameters."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        for i in range(10):
            repo.save_ticker_sentiment(
                ticker="AAPL",
                window_type="7d",
                sentiment_score=Decimal(str(0.5 + i * 0.05)),
                sentiment_velocity=Decimal("0"),
                article_count=10,
                computed_at=now - timedelta(days=i),
            )

        response = client.get("/api/sentiment/AAPL/history")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10  # Default 30 days

    def test_get_sentiment_history_custom_window(self, session: Session, client: TestClient):
        """Test sentiment history with custom window type."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        repo.save_ticker_sentiment(
            ticker="MSFT",
            window_type="24h",
            sentiment_score=Decimal("0.6"),
            sentiment_velocity=Decimal("0.1"),
            article_count=5,
            computed_at=now,
        )

        response = client.get("/api/sentiment/MSFT/history?window_type=24h")

        assert response.status_code == 200
        data = response.json()
        if data:
            assert all(item["sentiment_score"] == 0.6 for item in data)

    def test_get_sentiment_history_custom_days(self, session: Session, client: TestClient):
        """Test sentiment history with custom days parameter."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        for i in range(20):
            repo.save_ticker_sentiment(
                ticker="GOOGL",
                window_type="7d",
                sentiment_score=Decimal("0.5"),
                sentiment_velocity=Decimal("0"),
                article_count=10,
                computed_at=now - timedelta(days=i),
            )

        response = client.get("/api/sentiment/GOOGL/history?days=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

    def test_sentiment_history_validation(self, client: TestClient):
        """Test input validation for history parameters."""
        # Invalid window type
        response = client.get("/api/sentiment/AAPL/history?window_type=invalid")
        assert response.status_code == 400

        # Days out of range
        response = client.get("/api/sentiment/AAPL/history?days=200")
        assert response.status_code == 422

        # Days too small
        response = client.get("/api/sentiment/AAPL/history?days=0")
        assert response.status_code == 422


class TestAlertsEndpoint:
    """Test GET /api/sentiment/alerts endpoint."""

    def test_get_active_alerts(self, session: Session, client: TestClient):
        """Test getting active sentiment alerts."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        for i in range(3):
            repo.save_alert(
                ticker=f"TEST{i}",
                alert_type="contrarian_bullish",
                sentiment_score=Decimal("-0.7"),
                divergence_magnitude=Decimal("0.8"),
                alert_date=now - timedelta(hours=i),
            )

        response = client.get("/api/sentiment/alerts")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_get_alerts_only_active(self, session: Session, client: TestClient):
        """Test that endpoint returns only active (unresolved) alerts."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        # Create active alert
        alert1 = repo.save_alert(
            ticker="AAPL",
            alert_type="contrarian_bullish",
            sentiment_score=Decimal("-0.8"),
            divergence_magnitude=Decimal("0.9"),
            alert_date=now,
        )

        # Create resolved alert
        alert2 = repo.save_alert(
            ticker="MSFT",
            alert_type="momentum_shift",
            sentiment_score=Decimal("0.5"),
            divergence_magnitude=Decimal("0.6"),
            alert_date=now,
        )
        repo.resolve_alert(alert2.id)

        response = client.get("/api/sentiment/alerts?active_only=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["ticker"] == "AAPL"

    def test_get_alerts_with_limit(self, session: Session, client: TestClient):
        """Test alerts endpoint with limit parameter."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        for i in range(10):
            repo.save_alert(
                ticker=f"TEST{i}",
                alert_type="contrarian_bullish",
                sentiment_score=Decimal("0.5"),
                divergence_magnitude=Decimal("0.6"),
                alert_date=now - timedelta(hours=i),
            )

        response = client.get("/api/sentiment/alerts?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

    def test_alerts_validation(self, client: TestClient):
        """Test input validation for alerts endpoint."""
        # Invalid limit
        response = client.get("/api/sentiment/alerts?limit=600")
        assert response.status_code == 422

        # Negative limit
        response = client.get("/api/sentiment/alerts?limit=-1")
        assert response.status_code == 422


class TestMoversEndpoint:
    """Test GET /api/sentiment/movers endpoint."""

    def test_get_movers_default(self, session: Session, client: TestClient):
        """Test getting sentiment movers with default parameters."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        for i in range(10):
            repo.save_ticker_sentiment(
                ticker=f"TEST{i}",
                window_type="7d",
                sentiment_score=Decimal("0.5"),
                sentiment_velocity=Decimal(str(0.1 + i * 0.02)),
                article_count=10,
                computed_at=now,
            )

        response = client.get("/api/sentiment/movers")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 20  # Default limit

    def test_get_movers_custom_window(self, session: Session, client: TestClient):
        """Test movers with custom window type."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        for window in ["24h", "7d", "30d"]:
            for i in range(3):
                repo.save_ticker_sentiment(
                    ticker=f"TEST{i}_{window}",
                    window_type=window,
                    sentiment_score=Decimal("0.5"),
                    sentiment_velocity=Decimal(str(0.1 + i * 0.05)),
                    article_count=10,
                    computed_at=now,
                )

        response = client.get("/api/sentiment/movers?window_type=24h")

        assert response.status_code == 200

    def test_get_movers_with_limit(self, session: Session, client: TestClient):
        """Test movers with custom limit."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        for i in range(20):
            repo.save_ticker_sentiment(
                ticker=f"MOVER{i}",
                window_type="7d",
                sentiment_score=Decimal("0.5"),
                sentiment_velocity=Decimal(str(0.1 + i * 0.01)),
                article_count=10,
                computed_at=now,
            )

        response = client.get("/api/sentiment/movers?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

    def test_movers_validation(self, client: TestClient):
        """Test input validation for movers endpoint."""
        # Invalid window type
        response = client.get("/api/sentiment/movers?window_type=invalid")
        assert response.status_code == 400

        # Limit out of range
        response = client.get("/api/sentiment/movers?limit=200")
        assert response.status_code == 422


class TestNewsEndpoint:
    """Test GET /api/sentiment/news/{ticker} endpoint."""

    def test_get_news_for_ticker(self, session: Session, client: TestClient):
        """Test getting recent news articles for a ticker."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        for i in range(5):
            hash_val = calculate_dedup_hash(f"Article {i}", "reuters")
            repo.save_article(
                ticker="AAPL",
                source="reuters",
                headline=f"Article {i}",
                published_at=now - timedelta(hours=i),
                sentiment_score=Decimal(str(0.5 + i * 0.1)),
                finbert_positive=Decimal("0.6"),
                finbert_negative=Decimal("0.2"),
                finbert_neutral=Decimal("0.2"),
                dedup_hash=hash_val,
            )

        response = client.get("/api/sentiment/news/AAPL")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5

    def test_get_news_with_limit(self, session: Session, client: TestClient):
        """Test news endpoint with limit."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        for i in range(20):
            hash_val = calculate_dedup_hash(f"Article {i}", "reuters")
            repo.save_article(
                ticker="MSFT",
                source="reuters",
                headline=f"Article {i}",
                published_at=now - timedelta(hours=i),
                sentiment_score=Decimal("0.5"),
                finbert_positive=Decimal("0.6"),
                finbert_negative=Decimal("0.2"),
                finbert_neutral=Decimal("0.2"),
                dedup_hash=hash_val,
            )

        response = client.get("/api/sentiment/news/MSFT?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10

    def test_get_news_nonexistent_ticker(self, client: TestClient):
        """Test news endpoint with non-existent ticker."""
        response = client.get("/api/sentiment/news/NONEXISTENT")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_news_validation(self, client: TestClient):
        """Test input validation for news endpoint."""
        # Limit too large
        response = client.get("/api/sentiment/news/AAPL?limit=600")
        assert response.status_code == 422

        # Negative limit
        response = client.get("/api/sentiment/news/AAPL?limit=-1")
        assert response.status_code == 422


class TestHeatmapEndpoint:
    """Test GET /api/sentiment/heatmap endpoint."""

    def test_get_heatmap_default(self, session: Session, client: TestClient):
        """Test getting sector sentiment heatmap."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        sectors = ["Technology", "Healthcare", "Finance"]
        for sector in sectors:
            repo.save_heatmap_cache(
                sector=sector,
                window_type="7d",
                avg_sentiment=Decimal(str(0.4 + hash(sector) % 5 * 0.1)),
                article_count=100,
                top_movers={"TOP1": 0.15, "TOP2": 0.10},
                computed_at=now,
            )

        response = client.get("/api/sentiment/heatmap")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_heatmap_custom_window(self, session: Session, client: TestClient):
        """Test heatmap with custom window type."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        repo.save_heatmap_cache(
            sector="Tech",
            window_type="24h",
            avg_sentiment=Decimal("0.5"),
            article_count=50,
            computed_at=now,
        )

        response = client.get("/api/sentiment/heatmap?window_type=24h")

        assert response.status_code == 200

    def test_heatmap_validation(self, client: TestClient):
        """Test input validation for heatmap endpoint."""
        # Invalid window type
        response = client.get("/api/sentiment/heatmap?window_type=invalid")
        assert response.status_code == 400


class TestRefreshEndpoint:
    """Test POST /api/sentiment/refresh endpoint."""

    def test_trigger_refresh(self, session: Session, client: TestClient):
        """Test triggering sentiment refresh."""
        from unittest.mock import patch

        with patch("backend.routers.sentiment.NewsIngestionService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.refresh_all.return_value = {
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "articles_ingest_fetched": 50,
                "articles_scored": 48,
                "articles_duplicated": 2,
                "sentiments_computed": 15,
                "alerts_generated": 3,
                "errors": [],
            }

            response = client.post("/api/sentiment/refresh")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["articles_fetched"] == 50
            assert data["articles_scored"] == 48

    def test_refresh_with_tickers(self, session: Session, client: TestClient):
        """Test refresh with custom ticker list."""
        from unittest.mock import patch

        with patch("backend.routers.sentiment.NewsIngestionService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.refresh_all.return_value = {
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "articles_ingest_fetched": 20,
                "articles_scored": 18,
                "articles_duplicated": 2,
                "sentiments_computed": 6,
                "alerts_generated": 1,
                "errors": [],
            }

            response = client.post("/api/sentiment/refresh?tickers=AAPL,MSFT,GOOGL")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_refresh_error_handling(self, session: Session, client: TestClient):
        """Test refresh error handling."""
        from unittest.mock import patch

        with patch("backend.routers.sentiment.NewsIngestionService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.refresh_all.side_effect = Exception("Service error")

            response = client.post("/api/sentiment/refresh")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"

    def test_refresh_validation(self, client: TestClient):
        """Test input validation for refresh endpoint."""
        from unittest.mock import patch

        with patch("backend.routers.sentiment.NewsIngestionService"):
            # Too many tickers
            response = client.post("/api/sentiment/refresh?tickers=" + ",".join([f"TEST{i}" for i in range(120)]))
            assert response.status_code == 400

            # Invalid ticker format
            response = client.post("/api/sentiment/refresh?tickers=INVALID@CHAR")
            assert response.status_code == 400


class TestBatchSentimentEndpoint:
    """Test GET /api/sentiment/batch/sentiment endpoint."""

    def test_batch_sentiment_multiple_tickers(self, session: Session, client: TestClient):
        """Test batch getting sentiment for multiple tickers."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        for ticker in ["AAPL", "MSFT", "GOOGL"]:
            repo.save_ticker_sentiment(
                ticker=ticker,
                window_type="7d",
                sentiment_score=Decimal(str(0.4 + hash(ticker) % 5 * 0.1)),
                sentiment_velocity=Decimal("0.05"),
                article_count=10,
                computed_at=now,
            )

        response = client.get("/api/sentiment/batch/sentiment?tickers=AAPL,MSFT,GOOGL")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "AAPL" in data
        assert "MSFT" in data
        assert "GOOGL" in data

    def test_batch_sentiment_custom_window(self, session: Session, client: TestClient):
        """Test batch sentiment with custom window type."""
        repo = SentimentRepository(session)

        now = datetime.now(timezone.utc)

        repo.save_ticker_sentiment(
            ticker="TEST",
            window_type="24h",
            sentiment_score=Decimal("0.5"),
            sentiment_velocity=Decimal("0.1"),
            article_count=5,
            computed_at=now,
        )

        response = client.get("/api/sentiment/batch/sentiment?tickers=TEST&window_type=24h")

        assert response.status_code == 200

    def test_batch_sentiment_validation(self, client: TestClient):
        """Test input validation for batch sentiment."""
        # Missing tickers parameter
        response = client.get("/api/sentiment/batch/sentiment")
        assert response.status_code == 422

        # Too many tickers
        response = client.get("/api/sentiment/batch/sentiment?tickers=" + ",".join([f"TEST{i}" for i in range(60)]))
        assert response.status_code == 400

        # Invalid window type
        response = client.get("/api/sentiment/batch/sentiment?tickers=AAPL&window_type=invalid")
        assert response.status_code == 400
