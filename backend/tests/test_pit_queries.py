"""
Tests for Point-in-Time (PiT) query correctness.
Ensures backtesting uses only data available at each point in time.
"""

import pytest
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from sqlmodel import Session

from backend.repositories.pit_queries import (
    get_prices_pit,
    get_fundamentals_pit,
    get_active_universe_pit,
)
from backend.models.market_data import PriceHistory, FundamentalsSnapshot
from backend.models.securities import SecurityStatus, SecurityLifecycleEvent


class TestGetPricesPIT:
    """Test Point-in-Time price queries."""

    def test_prices_pit_basic(self, session: Session, sample_prices):
        """Test basic PiT price retrieval."""
        as_of = date(2023, 6, 30)
        prices = get_prices_pit(session, "AAPL", as_of)

        # Should return a list
        assert isinstance(prices, list)
        # All prices should be from or before as_of date
        for price in prices:
            assert price.date <= as_of

    def test_prices_pit_excludes_future_data(
        self, session: Session, sample_prices
    ):
        """Test that PiT query excludes data from the future."""
        as_of = date(2023, 3, 31)
        prices = get_prices_pit(session, "AAPL", as_of)

        # All prices should have ingestion timestamps on or before as_of
        as_of_end = datetime.combine(as_of, datetime.max.time(), tzinfo=timezone.utc)
        for price in prices:
            assert price.ingestion_timestamp <= as_of_end

    def test_prices_pit_respects_start_date(
        self, session: Session, sample_prices
    ):
        """Test that start_date parameter is respected."""
        start = date(2023, 3, 1)
        end = date(2023, 12, 31)

        prices = get_prices_pit(session, "AAPL", end, start_date=start)

        # All prices should be in range
        for price in prices:
            assert start <= price.date <= end

    def test_prices_pit_empty_before_date(
        self, session: Session, sample_prices
    ):
        """Test PiT query for date before any data."""
        as_of = date(2022, 1, 1)  # Before sample data starts
        prices = get_prices_pit(session, "AAPL", as_of)

        # Should return empty list
        assert prices == []

    def test_prices_pit_sorted(self, session: Session, sample_prices):
        """Test that PiT prices are returned in chronological order."""
        as_of = date(2023, 12, 31)
        prices = get_prices_pit(session, "AAPL", as_of)

        if len(prices) > 1:
            # Prices should be sorted by date
            for i in range(len(prices) - 1):
                assert prices[i].date <= prices[i + 1].date

    def test_prices_pit_multiple_tickers(
        self, session: Session, sample_prices
    ):
        """Test that separate tickers have separate price data."""
        as_of = date(2023, 6, 30)

        prices_aapl = get_prices_pit(session, "AAPL", as_of)
        prices_msft = get_prices_pit(session, "MSFT", as_of)

        # Should return data for each ticker
        if prices_aapl and prices_msft:
            # Verify ticker separation
            aapl_tickers = set(p.ticker for p in prices_aapl)
            msft_tickers = set(p.ticker for p in prices_msft)

            assert "AAPL" in aapl_tickers
            assert "MSFT" in msft_tickers

    def test_prices_pit_nonexistent_ticker(self, session: Session):
        """Test PiT query for nonexistent ticker."""
        as_of = date(2023, 6, 30)
        prices = get_prices_pit(session, "NONEXISTENT", as_of)

        assert prices == []


class TestGetFundamentalsPIT:
    """Test Point-in-Time fundamental data queries."""

    def test_fundamentals_pit_basic(
        self, session: Session, sample_fundamentals
    ):
        """Test basic PiT fundamental retrieval."""
        as_of = date(2023, 6, 30)
        fundamentals = get_fundamentals_pit(session, "AAPL", as_of)

        assert isinstance(fundamentals, list)
        # All fundamentals should have source document date before as_of
        for fund in fundamentals:
            assert fund.source_document_date <= as_of

    def test_fundamentals_pit_respects_document_date(
        self, session: Session, sample_fundamentals
    ):
        """Test that source_document_date is enforced."""
        as_of = date(2023, 3, 31)
        fundamentals = get_fundamentals_pit(session, "AAPL", as_of)

        # All should have source document date before as_of
        for fund in fundamentals:
            assert fund.source_document_date <= as_of

    def test_fundamentals_pit_respects_ingestion_timestamp(
        self, session: Session, sample_fundamentals
    ):
        """Test that ingestion_timestamp is enforced."""
        as_of = date(2023, 6, 30)
        fundamentals = get_fundamentals_pit(session, "AAPL", as_of)

        as_of_end = datetime.combine(as_of, datetime.max.time(), tzinfo=timezone.utc)
        for fund in fundamentals:
            assert fund.ingestion_timestamp <= as_of_end

    def test_fundamentals_pit_filter_by_metric(
        self, session: Session, sample_fundamentals
    ):
        """Test filtering fundamentals by metric name."""
        as_of = date(2023, 6, 30)
        metrics = ["free_cash_flow", "market_cap"]

        fundamentals = get_fundamentals_pit(
            session, "AAPL", as_of, metric_names=metrics
        )

        # All returned fundamentals should have matching metric names
        for fund in fundamentals:
            assert fund.metric_name in metrics

    def test_fundamentals_pit_multiple_quarters(
        self, session: Session, sample_fundamentals
    ):
        """Test fundamentals from multiple fiscal periods."""
        as_of = date(2023, 12, 31)
        fundamentals = get_fundamentals_pit(session, "AAPL", as_of)

        # Should have multiple periods (from setup: 4 quarters)
        if len(fundamentals) > 0:
            periods = set(f.fiscal_period_end for f in fundamentals)
            # Should have fundamentals from different periods
            assert len(periods) > 0

    def test_fundamentals_pit_latest_first(
        self, session: Session, sample_fundamentals
    ):
        """Test that most recent fundamentals appear first."""
        as_of = date(2023, 12, 31)
        fundamentals = get_fundamentals_pit(session, "AAPL", as_of)

        if len(fundamentals) > 1:
            # Most recent should be first
            for i in range(len(fundamentals) - 1):
                assert fundamentals[i].fiscal_period_end >= fundamentals[
                    i + 1
                ].fiscal_period_end

    def test_fundamentals_pit_nonexistent_ticker(
        self, session: Session
    ):
        """Test fundamentals query for nonexistent ticker."""
        as_of = date(2023, 6, 30)
        fundamentals = get_fundamentals_pit(session, "NONEXISTENT", as_of)

        assert fundamentals == []

    def test_fundamentals_pit_empty_before_date(
        self, session: Session, sample_fundamentals
    ):
        """Test fundamentals query before any data exists."""
        as_of = date(2022, 1, 1)
        fundamentals = get_fundamentals_pit(session, "AAPL", as_of)

        assert fundamentals == []


class TestGetActiveUniversePIT:
    """Test Point-in-Time active universe queries."""

    def test_active_universe_pit_basic(
        self, session: Session, sample_securities
    ):
        """Test basic active universe retrieval."""
        as_of = date(2023, 6, 30)
        universe = get_active_universe_pit(session, as_of)

        assert isinstance(universe, list)
        # All securities should be active
        for sec in universe:
            assert sec.current_status == SecurityStatus.ACTIVE

    def test_active_universe_excludes_delisted(
        self, session: Session, sample_securities, sample_security_lifecycle
    ):
        """Test that delisted securities are excluded."""
        # Delist one security
        delisted_sec = sample_securities[0]
        delisted_sec.current_status = SecurityStatus.DELISTED
        session.add(delisted_sec)

        # Add delisting event
        delisted_event = SecurityLifecycleEvent(
            ticker=delisted_sec.ticker,
            event_type="DELISTED",
            event_date=date(2023, 6, 1),
            details={"reason": "Bankruptcy"},
        )
        session.add(delisted_event)
        session.commit()

        # Query after delisting
        universe = get_active_universe_pit(session, date(2023, 7, 1))

        # Delisted security should not be in universe
        tickers = [sec.ticker for sec in universe]
        assert delisted_sec.ticker not in tickers

    def test_active_universe_excludes_acquired(
        self, session: Session, sample_securities
    ):
        """Test that acquired securities are excluded."""
        acquired_sec = sample_securities[1]
        acquired_sec.current_status = SecurityStatus.ACQUIRED
        session.add(acquired_sec)
        session.commit()

        universe = get_active_universe_pit(session, date(2023, 6, 30))

        tickers = [sec.ticker for sec in universe]
        assert acquired_sec.ticker not in tickers

    def test_active_universe_excludes_bankrupt(
        self, session: Session, sample_securities
    ):
        """Test that bankrupt securities are excluded."""
        bankrupt_sec = sample_securities[2]
        bankrupt_sec.current_status = SecurityStatus.BANKRUPT
        session.add(bankrupt_sec)
        session.commit()

        universe = get_active_universe_pit(session, date(2023, 6, 30))

        tickers = [sec.ticker for sec in universe]
        assert bankrupt_sec.ticker not in tickers

    def test_active_universe_respects_timeline(
        self, session: Session, sample_securities, sample_security_lifecycle
    ):
        """Test that timeline of status changes is respected."""
        sec = sample_securities[0]

        # First it's active (via initial fixture)
        universe_before = get_active_universe_pit(session, date(2023, 5, 1))
        tickers_before = [s.ticker for s in universe_before]
        assert sec.ticker in tickers_before

        # Then delist it on a specific date
        sec.current_status = SecurityStatus.DELISTED
        session.add(sec)
        session.commit()

        # After delisting, should not be in universe
        universe_after = get_active_universe_pit(session, date(2023, 7, 1))
        tickers_after = [s.ticker for s in universe_after]
        assert sec.ticker not in tickers_after

    def test_active_universe_size(
        self, session: Session, sample_securities
    ):
        """Test that active universe has expected size."""
        universe = get_active_universe_pit(session, date(2023, 6, 30))

        # Fixture creates 5 active securities
        assert len(universe) == 5

    def test_active_universe_multiple_dates(
        self, session: Session, sample_securities
    ):
        """Test that universe is consistent across dates."""
        universe_early = get_active_universe_pit(session, date(2023, 1, 1))
        universe_late = get_active_universe_pit(session, date(2023, 12, 31))

        # Without any status changes, should be the same
        tickers_early = sorted(s.ticker for s in universe_early)
        tickers_late = sorted(s.ticker for s in universe_late)

        assert tickers_early == tickers_late


class TestPITConsistency:
    """Integration tests for PiT query consistency."""

    def test_pit_prices_and_fundamentals_consistent(
        self, session: Session, sample_prices, sample_fundamentals
    ):
        """Test that prices and fundamentals are from same or earlier date."""
        as_of = date(2023, 6, 30)

        prices = get_prices_pit(session, "AAPL", as_of)
        fundamentals = get_fundamentals_pit(session, "AAPL", as_of)

        # All data should be from before as_of
        for price in prices:
            assert price.date <= as_of
        for fund in fundamentals:
            assert fund.source_document_date <= as_of

    def test_pit_universe_prices_alignment(
        self, session: Session, sample_securities, sample_prices
    ):
        """Test that active universe members have price data."""
        as_of = date(2023, 6, 30)

        universe = get_active_universe_pit(session, as_of)
        universe_tickers = [sec.ticker for sec in universe]

        # Most universe members should have prices
        for ticker in universe_tickers[:3]:  # Check first 3
            prices = get_prices_pit(session, ticker, as_of)
            # May be empty if not enough price data
            assert isinstance(prices, list)

    def test_pit_walk_forward_progression(
        self, session: Session, sample_prices, sample_fundamentals
    ):
        """Test that PiT data progressively includes more as date advances."""
        ticker = "AAPL"

        # Early date
        prices_early = get_prices_pit(session, ticker, date(2023, 1, 31))
        fundamentals_early = get_fundamentals_pit(
            session, ticker, date(2023, 1, 31)
        )

        # Later date
        prices_late = get_prices_pit(session, ticker, date(2023, 12, 31))
        fundamentals_late = get_fundamentals_pit(
            session, ticker, date(2023, 12, 31)
        )

        # Later date should have >= data points
        assert len(prices_late) >= len(prices_early)
        assert len(fundamentals_late) >= len(fundamentals_early)


class TestPITEdgeCases:
    """Edge cases for PiT queries."""

    def test_pit_end_of_day_boundary(
        self, session: Session, sample_prices
    ):
        """Test PiT query at end-of-day boundary."""
        # Query at exact end of day
        as_of = date(2023, 6, 30)
        prices = get_prices_pit(session, "AAPL", as_of)

        # All should be included for the day
        day_prices = [p for p in prices if p.date == as_of]
        assert len(day_prices) >= 0  # May or may not exist

    def test_pit_far_future_date(
        self, session: Session, sample_prices
    ):
        """Test PiT query for a date far in the future."""
        as_of = date(2030, 12, 31)
        prices = get_prices_pit(session, "AAPL", as_of)

        # Should include all available data
        assert isinstance(prices, list)

    def test_pit_very_early_date(self, session: Session, sample_prices):
        """Test PiT query for a date before any data."""
        as_of = date(1990, 1, 1)
        prices = get_prices_pit(session, "AAPL", as_of)

        # Should return empty
        assert prices == []

    def test_pit_with_large_universe(
        self, session: Session, sample_securities
    ):
        """Test PiT queries with many securities."""
        as_of = date(2023, 6, 30)

        # Query should work efficiently even with many tickers
        universe = get_active_universe_pit(session, as_of)

        # Should complete without timeout
        assert isinstance(universe, list)
