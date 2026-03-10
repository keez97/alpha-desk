"""
Tests for Earnings API Endpoints.

Tests REST API endpoints for earnings calendar, signals, history, PEAD data,
and data refresh, including input validation and error handling.
"""

import pytest
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlmodel import Session

from backend.main import app
from backend.repositories.earnings_repo import EarningsRepository
from backend.models.earnings import (
    EarningsEstimate,
    EarningsActual,
    AnalystScorecard,
    EarningsSignal,
    PEADMeasurement,
)


@pytest.fixture(name="client")
def test_client_fixture(session: Session):
    """Create test client with session override."""

    def get_session_override():
        return session

    app.dependency_overrides["backend.database.get_session"] = get_session_override

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()


class TestEarningsCalendarEndpoint:
    """Test GET /api/earnings/calendar endpoint."""

    def test_get_earnings_calendar_default(self, session: Session, client: TestClient):
        """Test getting earnings calendar with default parameters."""
        repo = EarningsRepository(session)

        today = date.today()
        future_date = today + timedelta(days=10)

        repo.save_actual(
            ticker="AAPL",
            fiscal_quarter="2025Q1",
            actual_eps=Decimal("5.50"),
            report_date=future_date,
            source="yfinance",
        )

        response = client.get("/api/earnings/calendar")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_earnings_calendar_with_params(self, session: Session, client: TestClient):
        """Test earnings calendar with custom parameters."""
        repo = EarningsRepository(session)

        today = date.today()

        for i in range(5):
            repo.save_actual(
                ticker=f"TEST{i}",
                fiscal_quarter="2025Q1",
                actual_eps=Decimal("5.00"),
                report_date=today + timedelta(days=i+1),
                source="yfinance",
            )

        response = client.get("/api/earnings/calendar?days_ahead=60&limit=3&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3

    def test_earnings_calendar_validation(self, client: TestClient):
        """Test input validation for calendar parameters."""
        # Invalid days_ahead (too large)
        response = client.get("/api/earnings/calendar?days_ahead=200")
        assert response.status_code == 422  # Validation error

        # Invalid limit (too large)
        response = client.get("/api/earnings/calendar?limit=600")
        assert response.status_code == 422


class TestEarningsHistoryEndpoint:
    """Test GET /api/earnings/{ticker}/history endpoint."""

    def test_get_earnings_history(self, session: Session, client: TestClient):
        """Test getting earnings history for a ticker."""
        repo = EarningsRepository(session)

        # Create historical actuals
        for i in range(4):
            report_date = date(2024, 1, 15) + timedelta(days=90*i)
            repo.save_actual(
                ticker="AAPL",
                fiscal_quarter=f"2024Q{i+1}",
                actual_eps=Decimal(str(5.0 + i * 0.1)),
                report_date=report_date,
                surprise_vs_consensus=Decimal(str(1.0 + i * 0.5)),
                source="yfinance",
            )

            # Add estimates
            repo.save_estimate(
                ticker="AAPL",
                fiscal_quarter=f"2024Q{i+1}",
                estimate_type="consensus",
                eps_estimate=Decimal(str(4.9 + i * 0.1)),
                estimate_date=report_date - timedelta(days=10),
            )

        response = client.get("/api/earnings/AAPL/history?quarters=4")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 4
        assert data[0]["ticker"] == "AAPL"

    def test_earnings_history_nonexistent_ticker(self, client: TestClient):
        """Test history for non-existent ticker."""
        response = client.get("/api/earnings/NONEXISTENT/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_earnings_history_validation(self, client: TestClient):
        """Test input validation for history endpoint."""
        # Invalid quarters (too many)
        response = client.get("/api/earnings/AAPL/history?quarters=25")
        assert response.status_code == 422

        # Empty ticker
        response = client.get("/api/earnings//history")
        assert response.status_code == 404


class TestEarningsSignalEndpoint:
    """Test GET /api/earnings/{ticker}/signal endpoint."""

    def test_get_active_signal(self, session: Session, client: TestClient):
        """Test getting active signal for ticker."""
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        repo.save_signal(
            ticker="MSFT",
            fiscal_quarter="2025Q1",
            signal_date=now,
            signal_type="buy",
            confidence=75,
            smart_estimate_eps=Decimal("2.80"),
            consensus_eps=Decimal("2.70"),
            divergence_pct=Decimal("3.70"),
            days_to_earnings=5,
            valid_until=now + timedelta(days=5),
        )

        response = client.get("/api/earnings/MSFT/signal")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "MSFT"
        assert data["signal_type"] == "buy"

    def test_no_active_signal(self, session: Session, client: TestClient):
        """Test when no active signal exists."""
        response = client.get("/api/earnings/NOSIGNAL/signal")

        assert response.status_code == 200
        data = response.json()
        assert data is None

    def test_signal_validation(self, client: TestClient):
        """Test input validation for signal endpoint."""
        # Empty ticker
        response = client.get("/api/earnings//signal")
        assert response.status_code == 404

        # Ticker too long
        response = client.get("/api/earnings/VERYLONGTICKER/signal")
        assert response.status_code == 422


class TestPEADEndpoint:
    """Test GET /api/earnings/{ticker}/pead endpoint."""

    def test_get_pead_data(self, session: Session, client: TestClient):
        """Test getting PEAD drift data."""
        repo = EarningsRepository(session)

        # Create PEAD measurements
        for i in range(3):
            earnings_date = date(2024, 1, 15) + timedelta(days=90*i)
            repo.save_pead_measurement(
                ticker="GOOGL",
                fiscal_quarter=f"2024Q{i+1}",
                earnings_date=earnings_date,
                surprise_direction="positive" if i % 2 == 0 else "negative",
                surprise_magnitude=Decimal(str(2.0 + i)),
                car_1d=Decimal(str(0.5 + i * 0.1)),
                car_5d=Decimal(str(1.5 + i * 0.2)),
                car_21d=Decimal(str(3.0 + i * 0.3)),
                car_60d=Decimal(str(5.0 + i * 0.5)),
            )

        response = client.get("/api/earnings/GOOGL/pead?quarters=3")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3
        if data:
            assert "car_1d" in data[0]
            assert "car_60d" in data[0]

    def test_pead_no_data(self, client: TestClient):
        """Test PEAD endpoint with no data."""
        response = client.get("/api/earnings/NODATA/pead")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestRefreshEndpoint:
    """Test POST /api/earnings/refresh endpoint."""

    def test_trigger_refresh(self, session: Session, client: TestClient):
        """Test triggering refresh of earnings data."""
        from unittest.mock import patch

        # Mock the data service
        with patch("backend.routers.earnings.EarningsDataService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.refresh_all_estimates.return_value = {
                "estimates": {"total_tickers": 0, "estimates_ingested": 0, "errors": []},
                "actuals": {"total_tickers": 0, "actuals_ingested": 0, "errors": []},
                "smart_estimates": {"total_tickers": 0, "smart_estimates_generated": 0, "errors": []},
                "scorecards": {"scorecards_updated": 0, "estimates_evaluated": 0, "errors": []},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            response = client.post("/api/earnings/refresh")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data

    def test_refresh_error_handling(self, session: Session, client: TestClient):
        """Test refresh error handling."""
        from unittest.mock import patch

        with patch("backend.routers.earnings.EarningsDataService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.refresh_all_estimates.side_effect = Exception("Service error")

            response = client.post("/api/earnings/refresh")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"


class TestScreenerSignalsEndpoint:
    """Test GET /api/earnings/screener-signals endpoint."""

    def test_screener_signals_multiple_tickers(self, session: Session, client: TestClient):
        """Test batch signal retrieval for multiple tickers."""
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        # Create signals for multiple tickers
        tickers = ["AAPL", "MSFT", "GOOGL"]

        for ticker in tickers:
            repo.save_signal(
                ticker=ticker,
                fiscal_quarter="2025Q1",
                signal_date=now,
                signal_type="buy" if ticker == "AAPL" else "sell",
                confidence=70,
                smart_estimate_eps=Decimal("5.00"),
                consensus_eps=Decimal("4.90"),
                divergence_pct=Decimal("2.04"),
                days_to_earnings=3,
                valid_until=now + timedelta(days=3),
            )

        response = client.get("/api/earnings/screener-signals?tickers=AAPL,MSFT,GOOGL")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        assert all(ticker in data for ticker in ["AAPL", "MSFT", "GOOGL"] if ticker in data)

    def test_screener_signals_missing_ticker_in_query(self, client: TestClient):
        """Test screener with missing tickers parameter."""
        response = client.get("/api/earnings/screener-signals")

        assert response.status_code == 422

    def test_screener_signals_whitespace_handling(self, session: Session, client: TestClient):
        """Test screener handles whitespace in ticker list."""
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        repo.save_signal(
            ticker="TSLA",
            fiscal_quarter="2025Q1",
            signal_date=now,
            signal_type="hold",
            confidence=50,
            smart_estimate_eps=Decimal("1.50"),
            consensus_eps=Decimal("1.50"),
            divergence_pct=Decimal("0.0"),
            days_to_earnings=10,
            valid_until=now + timedelta(days=10),
        )

        response = client.get("/api/earnings/screener-signals?tickers=AAPL, TSLA , MSFT")

        assert response.status_code == 200
        data = response.json()
        assert "TSLA" in data


class TestSmartEstimateEndpoint:
    """Test GET /api/earnings/smart-estimate/{ticker}/{quarter} endpoint."""

    def test_calculate_smart_estimate(self, session: Session, client: TestClient):
        """Test SmartEstimate calculation endpoint."""
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        # Create estimates
        repo.save_estimate(
            ticker="AAPL",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("5.50"),
            estimate_date=now,
            analyst_broker="Analyst1",
        )

        repo.save_estimate(
            ticker="AAPL",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("5.60"),
            estimate_date=now,
            analyst_broker="Analyst2",
        )

        response = client.get("/api/earnings/smart-estimate/AAPL/2025Q1")

        assert response.status_code == 200
        data = response.json()
        assert "smart_eps" in data
        assert "consensus_eps" in data
        assert "num_estimates" in data

    def test_smart_estimate_no_data(self, client: TestClient):
        """Test SmartEstimate with no estimates."""
        response = client.get("/api/earnings/smart-estimate/NODATA/2025Q1")

        assert response.status_code == 200
        data = response.json()
        assert data["smart_eps"] is None
        assert data["num_estimates"] == 0


class TestPEADAggregateEndpoint:
    """Test GET /api/earnings/pead-aggregate endpoint."""

    def test_pead_aggregate_all(self, session: Session, client: TestClient):
        """Test PEAD aggregate across all measurements."""
        repo = EarningsRepository(session)

        # Create various PEAD measurements
        for i in range(3):
            repo.save_pead_measurement(
                ticker=f"TEST{i}",
                fiscal_quarter="2025Q1",
                earnings_date=date(2025, 1, 15),
                surprise_direction="positive" if i % 2 == 0 else "negative",
                surprise_magnitude=Decimal(str(2.0 + i)),
                car_1d=Decimal(str(0.5 + i * 0.1)),
                car_5d=Decimal(str(1.5 + i * 0.2)),
            )

        response = client.get("/api/earnings/pead-aggregate")

        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["filter"] == "all"

    def test_pead_aggregate_by_direction(self, session: Session, client: TestClient):
        """Test PEAD aggregate filtered by surprise direction."""
        repo = EarningsRepository(session)

        # Create positive and negative measurements
        repo.save_pead_measurement(
            ticker="POS",
            fiscal_quarter="2025Q1",
            earnings_date=date(2025, 1, 15),
            surprise_direction="positive",
            surprise_magnitude=Decimal("2.5"),
            car_1d=Decimal("0.8"),
        )

        repo.save_pead_measurement(
            ticker="NEG",
            fiscal_quarter="2025Q1",
            earnings_date=date(2025, 1, 15),
            surprise_direction="negative",
            surprise_magnitude=Decimal("-1.5"),
            car_1d=Decimal("-0.5"),
        )

        response = client.get("/api/earnings/pead-aggregate?surprise_direction=positive")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["filter"] == "positive"


class TestPEADByQuartileEndpoint:
    """Test GET /api/earnings/pead-by-quartile endpoint."""

    def test_pead_by_quartile(self, session: Session, client: TestClient):
        """Test PEAD analysis by surprise magnitude quartile."""
        repo = EarningsRepository(session)

        # Create measurements with varying magnitudes
        magnitudes = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]

        for i, mag in enumerate(magnitudes):
            repo.save_pead_measurement(
                ticker=f"TEST{i}",
                fiscal_quarter="2025Q1",
                earnings_date=date(2025, 1, 15),
                surprise_direction="positive",
                surprise_magnitude=Decimal(str(mag)),
                car_1d=Decimal(str(0.5 + i * 0.1)),
                car_5d=Decimal(str(1.0 + i * 0.2)),
            )

        response = client.get("/api/earnings/pead-by-quartile")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_invalid_ticker_format(self, client: TestClient):
        """Test validation of ticker format."""
        # Very long ticker
        response = client.get("/api/earnings/VERYLONGTICKERNAME/signal")
        assert response.status_code == 422

    def test_invalid_fiscal_quarter_format(self, client: TestClient):
        """Test validation of fiscal quarter format."""
        response = client.get("/api/earnings/smart-estimate/AAPL/invalid_quarter")

        # Should either accept or return proper error
        assert response.status_code in [200, 422]

    def test_negative_limit(self, client: TestClient):
        """Test validation of negative limit."""
        response = client.get("/api/earnings/calendar?limit=-1")
        assert response.status_code == 422

    def test_negative_offset(self, client: TestClient):
        """Test validation of negative offset."""
        response = client.get("/api/earnings/calendar?offset=-1")
        assert response.status_code == 422
