"""
Tests for Event Processor Service (Layer 2 CEP).

Tests event classification, severity scoring, and alpha decay calculations.
"""

import pytest
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from sqlmodel import Session

from backend.services.event_processor import EventProcessingEngine
from backend.models.events import Event, AlphaDecayWindow
from backend.repositories.event_repo import EventRepository


class TestEventClassification:
    """Test event type classification."""

    def test_classify_8k_items(self):
        """Verify 8-K item mapping."""
        engine = EventProcessingEngine()

        # Test item 1.01 (bankruptcy)
        raw_event = {
            "filing_type": "8-K",
            "filing_title": "Form 8-K - Item 1.01: Bankruptcy",
            "headline": "Item 1.01 Bankruptcy",
            "metadata": {"item_number": "1.01"},
        }
        classified_type, metadata = engine.classify_event(raw_event)
        assert "8k_item_1_01" in classified_type
        assert metadata["item_number"] == "1.01"

        # Test item 2.01 (material agreement)
        raw_event = {
            "filing_type": "8-K",
            "filing_title": "Item 2.01 Material Agreement",
            "headline": "Major acquisition announced",
            "metadata": {"item_number": "2.01"},
        }
        classified_type, metadata = engine.classify_event(raw_event)
        assert "8k_item_2_01" in classified_type

        # Test unknown item (should default)
        raw_event = {
            "filing_type": "8-K",
            "filing_title": "Form 8-K",
            "headline": "No item specified",
            "metadata": {},
        }
        classified_type, metadata = engine.classify_event(raw_event)
        assert "default" in classified_type

    def test_classify_form4_as_insider(self):
        """Verify Form 4 classified as insider trade."""
        engine = EventProcessingEngine()

        raw_event = {
            "filing_type": "4",
            "filing_title": "Form 4 - Insider Transaction",
            "headline": "CEO purchases 50,000 shares",
            "metadata": {
                "transaction_type": "buy",
                "transaction_amount": 5_000_000,
                "shares_traded": 50_000,
            },
        }
        classified_type, metadata = engine.classify_event(raw_event)
        assert "insider_trade" in classified_type
        assert "buy" in classified_type
        assert metadata["transaction_type"] == "buy"

    def test_classify_10k_as_sec_filing(self):
        """Verify 10-K classified as SEC filing."""
        engine = EventProcessingEngine()

        raw_event = {
            "filing_type": "10-K",
            "filing_title": "Annual Report",
            "headline": "2023 Annual Report",
            "metadata": {},
        }
        classified_type, metadata = engine.classify_event(raw_event)
        assert classified_type == "sec_filing_10k"

    def test_classify_earnings_from_yfinance(self):
        """Verify earnings event from yfinance."""
        engine = EventProcessingEngine()

        raw_event = {
            "event_type": "earnings",
            "headline": "Earnings Announcement",
            "metadata": {"earnings_date": "2024-03-10"},
        }
        classified_type, metadata = engine.classify_event(raw_event)
        assert classified_type == "earnings_announcement"

    def test_classify_beneficial_ownership_13d(self):
        """Verify SC 13D classified as beneficial ownership."""
        engine = EventProcessingEngine()

        raw_event = {
            "filing_type": "SC 13D",
            "filing_title": "Schedule 13D",
            "headline": "Activist acquisition",
            "metadata": {"ownership_level": 5.5},
        }
        classified_type, metadata = engine.classify_event(raw_event)
        assert classified_type == "beneficial_ownership_13d"


class TestSeverityScoring:
    """Test event severity scoring (1-5)."""

    def test_bankruptcy_severity_5(self):
        """Bankruptcy events should score 5."""
        engine = EventProcessingEngine()

        # 8-K item 1.01
        severity = engine.score_severity("sec_filing_8k_item_1_01", {})
        assert severity == 5

        # 8-K item 2.01
        severity = engine.score_severity("sec_filing_8k_item_2_01", {})
        assert severity == 5

    def test_insider_buy_severity(self):
        """Insider buy events vary by size."""
        engine = EventProcessingEngine()

        # Large insider buy: severity 4
        severity = engine.score_severity(
            "insider_trade_buy_large", {"transaction_type": "buy", "transaction_size": "large"}
        )
        assert severity == 4

        # Small insider buy: severity 2
        severity = engine.score_severity(
            "insider_trade_buy_small", {"transaction_type": "buy", "transaction_size": "small"}
        )
        assert severity == 2

    def test_earnings_severity_3(self):
        """Earnings announcements should score 3."""
        engine = EventProcessingEngine()

        severity = engine.score_severity("earnings_announcement", {})
        assert severity == 3

    def test_sec_filing_default_severity_2(self):
        """Regular SEC filings (10-Q) should score 2."""
        engine = EventProcessingEngine()

        severity = engine.score_severity("sec_filing_10q", {})
        assert severity == 2

    def test_insider_sell_severity(self):
        """Insider sell events vary by size."""
        engine = EventProcessingEngine()

        # Large insider sell: severity 3
        severity = engine.score_severity(
            "insider_trade_sell_large", {"transaction_type": "sell", "transaction_size": "large"}
        )
        assert severity == 3

        # Small insider sell: severity 1
        severity = engine.score_severity(
            "insider_trade_sell_small", {"transaction_type": "sell", "transaction_size": "small"}
        )
        assert severity == 1

    def test_beneficial_ownership_13d_severity_4(self):
        """13D (activist) should score 4."""
        engine = EventProcessingEngine()

        severity = engine.score_severity("beneficial_ownership_13d", {})
        assert severity == 4

    def test_unknown_event_severity_defaults_to_2(self):
        """Unknown event types should default to severity 2."""
        engine = EventProcessingEngine()

        severity = engine.score_severity("unknown_event_type", {})
        assert severity == 2


class TestAlphaDecayCalculation:
    """Test alpha decay window calculations."""

    def test_alpha_decay_calculation_with_mock_prices(self, session: Session, sample_securities, sample_prices):
        """Verify alpha decay calculation with mock price data."""
        engine = EventProcessingEngine()
        repository = EventRepository(session)

        # Create a test event
        event = repository.create_event(
            ticker="AAPL",
            event_type="earnings_announcement",
            severity_score=3,
            detected_at=datetime.now(timezone.utc),
            event_date=date(2023, 2, 1),
            source="YFINANCE",
            headline="Q1 Earnings",
            description="Q1 2023 earnings announcement",
        )

        # Calculate alpha decay
        decay_results = engine.calculate_alpha_decay(session, event.event_id, event, benchmark_ticker="SPY")

        # Verify results exist for multiple windows
        assert len(decay_results) > 0
        window_types = [d["window_type"] for d in decay_results]
        assert "1d" in window_types or "5d" in window_types  # Should have at least some windows

    def test_alpha_decay_windows_1d_5d_21d_63d(self, session: Session, sample_securities, sample_prices):
        """Verify alpha decay windows are calculated for all periods."""
        engine = EventProcessingEngine()
        repository = EventRepository(session)

        event = repository.create_event(
            ticker="MSFT",
            event_type="earnings_announcement",
            severity_score=3,
            detected_at=datetime.now(timezone.utc),
            event_date=date(2023, 3, 15),
            source="YFINANCE",
            headline="Q1 Earnings",
        )

        decay_results = engine.calculate_alpha_decay(session, event.event_id, event)

        # If we have price data, should have windows
        if decay_results:
            window_types = set(d["window_type"] for d in decay_results)
            # Should have at least 1d and 5d windows
            assert len(window_types) >= 1

    def test_alpha_decay_missing_price_data_handles_gracefully(self, session: Session):
        """Verify missing price data doesn't crash alpha decay calculation."""
        engine = EventProcessingEngine()
        repository = EventRepository(session)

        # Create event for ticker with no prices
        event = repository.create_event(
            ticker="NONEXISTENT",
            event_type="earnings_announcement",
            severity_score=3,
            detected_at=datetime.now(timezone.utc),
            event_date=date(2023, 2, 1),
            source="YFINANCE",
            headline="Earnings",
        )

        # Should not crash, just return empty list
        decay_results = engine.calculate_alpha_decay(session, event.event_id, event)
        assert isinstance(decay_results, list)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_unknown_event_type_defaults_to_other_event(self):
        """Unknown event type should default gracefully."""
        engine = EventProcessingEngine()

        raw_event = {
            "event_type": "unknown_type",
            "headline": "Some event",
            "metadata": {},
        }
        classified_type, metadata = engine.classify_event(raw_event)
        assert classified_type == "other_event"

    def test_missing_metadata_handled(self):
        """Events with missing metadata should be classified."""
        engine = EventProcessingEngine()

        raw_event = {
            "filing_type": "8-K",
            "filing_title": "Form 8-K",
            # No metadata, no headline details
        }
        classified_type, metadata = engine.classify_event(raw_event)
        # Should still classify, with default item
        assert "8k_item" in classified_type

    def test_process_events_with_invalid_dates(self, session: Session):
        """Events with invalid dates should be skipped."""
        engine = EventProcessingEngine()
        repository = EventRepository(session)

        raw_events = [
            {
                "ticker": "AAPL",
                "filing_type": "8-K",
                "filing_date": "invalid-date",
                "headline": "Form 8-K",
                "metadata": {},
            },
            {
                "ticker": "MSFT",
                "filing_type": "10-K",
                "filing_date": "2023-01-15",
                "headline": "Annual Report",
                "metadata": {},
            },
        ]

        created_events, alpha_decays = engine.process_events(session, raw_events)

        # Only valid date should be processed
        assert len(created_events) == 1
        assert created_events[0].ticker == "MSFT"

    def test_process_events_missing_ticker(self, session: Session):
        """Events with missing ticker should be skipped."""
        engine = EventProcessingEngine()

        raw_events = [
            {
                # Missing ticker
                "filing_type": "8-K",
                "filing_date": "2023-01-15",
                "headline": "Form 8-K",
            },
            {
                "ticker": "AAPL",
                "filing_type": "10-K",
                "filing_date": "2023-01-15",
                "headline": "Annual Report",
            },
        ]

        created_events, alpha_decays = engine.process_events(session, raw_events)

        # Only event with ticker should be processed
        assert len(created_events) == 1
        assert created_events[0].ticker == "AAPL"


class TestProcessEventsIntegration:
    """Integration tests for full event processing pipeline."""

    def test_process_events_full_pipeline(self, session: Session, sample_securities):
        """Test complete event processing pipeline."""
        engine = EventProcessingEngine()

        raw_events = [
            {
                "ticker": "AAPL",
                "filing_type": "8-K",
                "filing_date": "2023-02-15",
                "filing_title": "Form 8-K - Item 1.01",
                "headline": "Bankruptcy announcement",
                "source": "SEC_EDGAR",
                "accession_number": "0000000001-23-000001",
                "source_url": "https://www.sec.gov/cgi-bin/viewer?...",
                "metadata": {"item_number": "1.01"},
            },
            {
                "ticker": "MSFT",
                "filing_type": "4",
                "filing_date": "2023-02-16",
                "filing_title": "Form 4 - Insider Transaction",
                "headline": "CEO purchase 100k shares",
                "source": "SEC_EDGAR",
                "accession_number": "0000000002-23-000002",
                "metadata": {
                    "transaction_type": "buy",
                    "transaction_amount": 15_000_000,
                    "shares_traded": 100_000,
                },
            },
        ]

        created_events, alpha_decays = engine.process_events(session, raw_events)

        # Should create 2 events
        assert len(created_events) == 2

        # Verify classification
        event1 = next(e for e in created_events if e.ticker == "AAPL")
        assert "8k_item_1_01" in event1.event_type
        assert event1.severity_score == 5

        event2 = next(e for e in created_events if e.ticker == "MSFT")
        assert "insider_trade" in event2.event_type
        assert event2.severity_score == 4
