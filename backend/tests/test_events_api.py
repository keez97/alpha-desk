"""
Tests for Events API Router (REST endpoints).

Tests HTTP endpoints for event listing, detail retrieval, scanning, and badges.
"""

import pytest
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal

from backend.repositories.event_repo import EventRepository


class TestListEventsEndpoint:
    """Test GET /api/events endpoint."""

    def test_list_events_returns_paginated_list(self, test_client, session):
        """GET /api/events returns paginated list of events."""
        repository = EventRepository(session)

        # Create test events
        for i in range(3):
            repository.create_event(
                ticker=f"TICK{i}",
                event_type=f"type_{i}",
                severity_score=(i % 5) + 1,
                detected_at=datetime.now(timezone.utc) - timedelta(hours=i),
                event_date=date.today(),
                source="SEC_EDGAR",
                headline=f"Event {i}",
            )

        response = test_client.get("/api/events")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data
        assert len(data["items"]) <= 50  # Default limit

    def test_list_events_filter_by_ticker(self, test_client, session):
        """Filter events by ticker parameter."""
        repository = EventRepository(session)

        repository.create_event(
            ticker="AAPL",
            event_type="earnings",
            severity_score=3,
            detected_at=datetime.now(timezone.utc),
            event_date=date.today(),
            source="YFINANCE",
            headline="Apple Earnings",
        )

        repository.create_event(
            ticker="MSFT",
            event_type="earnings",
            severity_score=3,
            detected_at=datetime.now(timezone.utc),
            event_date=date.today(),
            source="YFINANCE",
            headline="Microsoft Earnings",
        )

        response = test_client.get("/api/events?ticker=AAPL")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["ticker"] == "AAPL"

    def test_list_events_filter_by_severity(self, test_client, session):
        """Filter events by severity range."""
        repository = EventRepository(session)

        for sev in [1, 3, 5]:
            repository.create_event(
                ticker="AAPL",
                event_type=f"type_sev_{sev}",
                severity_score=sev,
                detected_at=datetime.now(timezone.utc),
                event_date=date.today(),
                source="YFINANCE",
                headline=f"Event severity {sev}",
            )

        response = test_client.get("/api/events?severity_min=3")
        assert response.status_code == 200

        data = response.json()
        assert all(item["severity_score"] >= 3 for item in data["items"])

    def test_list_events_pagination_limit(self, test_client, session):
        """Test pagination limit parameter."""
        repository = EventRepository(session)

        # Create 10 events
        for i in range(10):
            repository.create_event(
                ticker="AAPL",
                event_type="type",
                severity_score=3,
                detected_at=datetime.now(timezone.utc) - timedelta(hours=i),
                event_date=date.today(),
                source="YFINANCE",
                headline=f"Event {i}",
            )

        response = test_client.get("/api/events?limit=5&offset=0")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 5
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert data["has_more"] is True

    def test_list_events_validates_limit_bounds(self, test_client):
        """Verify limit parameter validation (1-500)."""
        # Limit too low
        response = test_client.get("/api/events?limit=0")
        assert response.status_code == 422  # Validation error

        # Limit too high
        response = test_client.get("/api/events?limit=1000")
        assert response.status_code == 422


class TestGetEventDetailEndpoint:
    """Test GET /api/events/{event_id} endpoint."""

    def test_get_event_detail(self, test_client, session):
        """Get detailed information for a specific event."""
        repository = EventRepository(session)

        event = repository.create_event(
            ticker="AAPL",
            event_type="earnings_announcement",
            severity_score=3,
            detected_at=datetime.now(timezone.utc),
            event_date=date.today(),
            source="YFINANCE",
            headline="Q1 Earnings",
            description="Apple earnings announcement",
            metadata={"earnings_date": "2024-03-10"},
        )

        response = test_client.get(f"/api/events/{event.event_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["event_id"] == event.event_id
        assert data["ticker"] == "AAPL"
        assert data["event_type"] == "earnings_announcement"
        assert data["severity_score"] == 3
        assert data["headline"] == "Q1 Earnings"

    def test_get_event_detail_with_alpha_decay(self, test_client, session):
        """Event detail response includes alpha decay windows."""
        repository = EventRepository(session)

        event = repository.create_event(
            ticker="AAPL",
            event_type="earnings",
            severity_score=3,
            detected_at=datetime.now(timezone.utc),
            event_date=date.today(),
            source="YFINANCE",
            headline="Earnings",
        )

        # Add alpha decay window
        repository.save_alpha_decay_window(
            event_id=event.event_id,
            window_type="1d",
            abnormal_return=Decimal("0.025"),
            benchmark_return=Decimal("0.010"),
            measured_at=datetime.now(timezone.utc),
        )

        response = test_client.get(f"/api/events/{event.event_id}")
        assert response.status_code == 200

        data = response.json()
        assert "alpha_decay_windows" in data
        assert len(data["alpha_decay_windows"]) == 1
        assert data["alpha_decay_windows"][0]["window_type"] == "1d"

    def test_get_event_detail_nonexistent_returns_404(self, test_client):
        """Getting nonexistent event returns 404."""
        response = test_client.get("/api/events/99999")
        assert response.status_code == 404

    def test_get_event_detail_validates_event_id(self, test_client):
        """Event ID must be valid integer."""
        response = test_client.get("/api/events/invalid")
        assert response.status_code == 422  # Validation error


class TestTriggerScanEndpoint:
    """Test POST /api/events/scan endpoint."""

    def test_trigger_manual_scan(self, test_client):
        """POST /api/events/scan returns 202 and queues background task."""
        response = test_client.post("/api/events/scan")
        assert response.status_code == 202

        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "queued"

    def test_trigger_scan_with_specific_tickers(self, test_client):
        """POST /api/events/scan with tickers parameter."""
        response = test_client.post("/api/events/scan?tickers=AAPL&tickers=MSFT")
        assert response.status_code == 202

        data = response.json()
        assert data["status"] == "queued"


class TestScreenerBadgesEndpoint:
    """Test GET /api/events/screener-badges endpoint."""

    def test_screener_badges_single_ticker(self, test_client, session):
        """Get screener badge for single ticker."""
        repository = EventRepository(session)

        # Create recent events
        now = datetime.now(timezone.utc)
        for i in range(2):
            repository.create_event(
                ticker="AAPL",
                event_type=f"type_{i}",
                severity_score=(i + 1),
                detected_at=now - timedelta(days=i),
                event_date=date.today(),
                source="YFINANCE",
                headline=f"Event {i}",
            )

        response = test_client.get("/api/events/screener-badges?tickers=AAPL")
        assert response.status_code == 200

        data = response.json()
        assert "badges" in data
        assert "timestamp" in data
        assert len(data["badges"]) == 1
        badge = data["badges"][0]
        assert badge["ticker"] == "AAPL"
        assert badge["max_severity"] >= 1
        assert "recent_event_count" in badge
        assert "event_types" in badge

    def test_screener_badges_multiple_tickers(self, test_client, session):
        """Get screener badges for multiple tickers."""
        repository = EventRepository(session)

        # Create events for different tickers
        for ticker in ["AAPL", "MSFT"]:
            repository.create_event(
                ticker=ticker,
                event_type="earnings",
                severity_score=3,
                detected_at=datetime.now(timezone.utc),
                event_date=date.today(),
                source="YFINANCE",
                headline=f"{ticker} Earnings",
            )

        response = test_client.get("/api/events/screener-badges?tickers=AAPL&tickers=MSFT")
        assert response.status_code == 200

        data = response.json()
        assert len(data["badges"]) == 2
        tickers = set(b["ticker"] for b in data["badges"])
        assert tickers == {"AAPL", "MSFT"}

    def test_screener_badges_requires_tickers(self, test_client):
        """screener-badges endpoint requires at least one ticker."""
        response = test_client.get("/api/events/screener-badges")
        assert response.status_code == 422  # Missing required parameter

    def test_screener_badges_lookback_days_validation(self, test_client):
        """lookback_days parameter must be 1-365."""
        response = test_client.get("/api/events/screener-badges?tickers=AAPL&lookback_days=0")
        assert response.status_code == 422

        response = test_client.get("/api/events/screener-badges?tickers=AAPL&lookback_days=400")
        assert response.status_code == 422


class TestTimelineEndpoint:
    """Test GET /api/events/timeline endpoint."""

    def test_event_timeline_returns_recent_events(self, test_client, session):
        """Get event timeline for recent events."""
        repository = EventRepository(session)

        now = datetime.now(timezone.utc)
        for i in range(3):
            repository.create_event(
                ticker=f"TICK{i}",
                event_type="earnings",
                severity_score=3,
                detected_at=now - timedelta(days=i),
                event_date=date.today() - timedelta(days=i),
                source="YFINANCE",
                headline=f"Event {i}",
            )

        response = test_client.get("/api/events/timeline")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1

    def test_timeline_respects_days_back_parameter(self, test_client, session):
        """Timeline filters by days_back parameter."""
        repository = EventRepository(session)

        now = datetime.now(timezone.utc)
        # Old event (40 days ago)
        repository.create_event(
            ticker="OLD",
            event_type="earnings",
            severity_score=1,
            detected_at=now - timedelta(days=40),
            event_date=date.today() - timedelta(days=40),
            source="YFINANCE",
            headline="Old Event",
        )

        # Recent event (5 days ago)
        repository.create_event(
            ticker="RECENT",
            event_type="earnings",
            severity_score=3,
            detected_at=now - timedelta(days=5),
            event_date=date.today() - timedelta(days=5),
            source="YFINANCE",
            headline="Recent Event",
        )

        # Get last 30 days
        response = test_client.get("/api/events/timeline?days_back=30")
        assert response.status_code == 200

        data = response.json()
        # Should only get recent event
        assert len(data["items"]) == 1
        assert data["items"][0]["ticker"] == "RECENT"


class TestPollingStatusEndpoint:
    """Test GET /api/events/polling-status endpoint."""

    def test_polling_status_returns_status(self, test_client):
        """Get polling service status."""
        response = test_client.get("/api/events/polling-status")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "polling_interval_hours" in data
        assert "events_found" in data
        assert "errors" in data
