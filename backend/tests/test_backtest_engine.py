"""
Integration tests for BacktestEngine.
Tests rebalancing logic, portfolio construction, turnover calculation, and PiT enforcement.
"""

import pytest
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from sqlmodel import Session

from backend.services.backtest_engine import BacktestEngine
from backend.models.backtests import BacktestFactorAllocation
from backend.repositories.backtest_repo import BacktestRepository


class TestGenerateRebalanceDates:
    """Test rebalance date generation."""

    def test_generate_monthly_dates(self):
        """Test monthly rebalance frequency."""
        engine = BacktestEngine()
        start = date(2023, 1, 1)
        end = date(2023, 12, 31)

        dates = engine._generate_rebalance_dates(start, end, "monthly")

        # Should have 12 monthly dates
        assert len(dates) == 12
        assert dates[0] == start
        assert dates[-1].month == 12

    def test_generate_quarterly_dates(self):
        """Test quarterly rebalance frequency."""
        engine = BacktestEngine()
        start = date(2023, 1, 1)
        end = date(2023, 12, 31)

        dates = engine._generate_rebalance_dates(start, end, "quarterly")

        # Should have approximately 4 quarterly dates
        assert len(dates) >= 4
        assert dates[0] == start

    def test_generate_weekly_dates(self):
        """Test weekly rebalance frequency."""
        engine = BacktestEngine()
        start = date(2023, 1, 1)
        end = date(2023, 1, 31)

        dates = engine._generate_rebalance_dates(start, end, "weekly")

        # Should have 4-5 weekly dates in a month
        assert len(dates) >= 4
        assert all(isinstance(d, date) for d in dates)

    def test_generate_daily_dates(self):
        """Test daily rebalance frequency."""
        engine = BacktestEngine()
        start = date(2023, 1, 1)
        end = date(2023, 1, 10)

        dates = engine._generate_rebalance_dates(start, end, "daily")

        # Should have 10 daily dates
        assert len(dates) == 10
        assert dates[0] == start
        assert dates[-1] == end

    def test_generate_annual_dates(self):
        """Test annual rebalance frequency."""
        engine = BacktestEngine()
        start = date(2020, 1, 1)
        end = date(2023, 12, 31)

        dates = engine._generate_rebalance_dates(start, end, "annual")

        # Should have approximately 4 annual dates
        assert len(dates) == 4
        assert dates[0] == start

    def test_dates_in_order(self):
        """Test that rebalance dates are in ascending order."""
        engine = BacktestEngine()
        start = date(2023, 1, 1)
        end = date(2023, 12, 31)

        dates = engine._generate_rebalance_dates(start, end, "monthly")

        # Dates should be sorted
        assert dates == sorted(dates)

    def test_dates_within_range(self):
        """Test that all dates are within the specified range."""
        engine = BacktestEngine()
        start = date(2023, 3, 15)
        end = date(2023, 11, 28)

        dates = engine._generate_rebalance_dates(start, end, "monthly")

        # All dates should be within range
        assert all(start <= d <= end for d in dates)


class TestConstructPortfolio:
    """Test portfolio construction logic."""

    def test_construct_top_quintile(self):
        """Test selecting top quintile of securities."""
        engine = BacktestEngine()

        # Create 100 scores
        scores = {f"STOCK{i:03d}": float(i) for i in range(100)}

        selected = engine._construct_portfolio(scores, n_quantiles=5)

        # Top quintile should have 20 stocks
        assert len(selected) == 20
        # Should be the highest scoring stocks
        top_20_scores = sorted(scores.values(), reverse=True)[:20]
        min_selected_score = min(scores[ticker] for ticker in selected)
        assert min_selected_score == min(top_20_scores)

    def test_construct_top_quartile(self):
        """Test selecting top quartile of securities."""
        engine = BacktestEngine()

        scores = {f"STOCK{i:03d}": float(i) for i in range(80)}

        selected = engine._construct_portfolio(scores, n_quantiles=4)

        # Top quartile should have 20 stocks
        assert len(selected) == 20

    def test_construct_single_quantile(self):
        """Test with single quantile (should select all)."""
        engine = BacktestEngine()

        scores = {f"STOCK{i:03d}": float(i) for i in range(50)}

        selected = engine._construct_portfolio(scores, n_quantiles=1)

        # Single quantile should select all
        assert len(selected) == 50

    def test_construct_empty_scores(self):
        """Test with empty scores dictionary."""
        engine = BacktestEngine()

        scores = {}

        selected = engine._construct_portfolio(scores, n_quantiles=5)

        assert selected == []

    def test_construct_small_universe(self):
        """Test with universe smaller than quantile."""
        engine = BacktestEngine()

        scores = {f"STOCK{i:03d}": float(i) for i in range(3)}

        selected = engine._construct_portfolio(scores, n_quantiles=5)

        # With 3 stocks and 5 quantiles, should select at least 1
        assert len(selected) >= 1


class TestCalculateTurnover:
    """Test turnover calculation logic."""

    def test_turnover_full_rebalance(self):
        """Test turnover with complete portfolio change."""
        engine = BacktestEngine()

        old = ["AAPL", "MSFT", "GOOGL"]
        new = ["TSLA", "AMZN", "NVDA"]

        turnover = engine._calculate_turnover(old, new, Decimal("1000000"))

        # Complete rebalance: 3 sold, 3 bought
        assert turnover > 0

    def test_turnover_no_change(self):
        """Test turnover when holdings don't change."""
        engine = BacktestEngine()

        holdings = ["AAPL", "MSFT", "GOOGL"]

        turnover = engine._calculate_turnover(holdings, holdings, Decimal("1000000"))

        assert turnover == 0.0

    def test_turnover_partial_overlap(self):
        """Test turnover with partial portfolio overlap."""
        engine = BacktestEngine()

        old = ["AAPL", "MSFT", "GOOGL", "TSLA"]
        new = ["AAPL", "MSFT", "AMZN", "NVDA"]

        turnover = engine._calculate_turnover(old, new, Decimal("1000000"))

        # 2 positions sold, 2 bought
        assert 0 < turnover < 1

    def test_turnover_empty_old(self):
        """Test turnover when starting from empty portfolio."""
        engine = BacktestEngine()

        old = []
        new = ["AAPL", "MSFT", "GOOGL"]

        turnover = engine._calculate_turnover(old, new, Decimal("1000000"))

        assert turnover > 0

    def test_turnover_empty_new(self):
        """Test turnover when liquidating portfolio."""
        engine = BacktestEngine()

        old = ["AAPL", "MSFT", "GOOGL"]
        new = []

        turnover = engine._calculate_turnover(old, new, Decimal("1000000"))

        assert turnover > 0

    def test_turnover_both_empty(self):
        """Test turnover when both portfolios are empty."""
        engine = BacktestEngine()

        turnover = engine._calculate_turnover([], [], Decimal("1000000"))

        assert turnover == 0.0


class TestPitEnforcement:
    """Test Point-in-Time data enforcement."""

    def test_prices_pit_excludes_future_data(self, session: Session, sample_prices):
        """Test that price queries don't include data from the future."""
        from backend.repositories.pit_queries import get_prices_pit

        # Query for prices as of mid-year
        as_of = date(2023, 6, 30)

        prices = get_prices_pit(session, "AAPL", as_of)

        # Should only have prices ingested by as_of_date
        for price in prices:
            assert price.ingestion_timestamp <= datetime.combine(
                as_of, datetime.max.time(), tzinfo=timezone.utc
            )

    def test_prices_pit_respects_date_range(
        self, session: Session, sample_prices
    ):
        """Test that prices are returned in the correct date range."""
        from backend.repositories.pit_queries import get_prices_pit

        as_of = date(2023, 12, 31)
        start = date(2023, 6, 1)

        prices = get_prices_pit(session, "AAPL", as_of, start_date=start)

        # All prices should be in the range
        for price in prices:
            assert start <= price.date <= as_of

    def test_universe_excludes_delisted(
        self, session: Session, sample_securities, sample_security_lifecycle
    ):
        """Test that active universe query excludes delisted securities."""
        from backend.repositories.pit_queries import get_active_universe_pit
        from backend.models.securities import SecurityStatus, SecurityLifecycleEvent

        # Manually delist one security
        delisted_sec = sample_securities[0]
        delisted_sec.current_status = SecurityStatus.DELISTED
        session.add(delisted_sec)

        delisted_event = SecurityLifecycleEvent(
            ticker=delisted_sec.ticker,
            event_type="DELISTED",
            event_date=date(2023, 6, 1),
            details={"reason": "Test delisting"},
        )
        session.add(delisted_event)
        session.commit()

        # Query active universe after delisting
        universe = get_active_universe_pit(session, date(2023, 7, 1))

        # Delisted security should not be in universe
        tickers = [sec.ticker for sec in universe]
        assert delisted_sec.ticker not in tickers
        assert len(tickers) == 4  # 5 - 1 delisted


class TestGetAllTradingDates:
    """Test trading dates extraction from price data."""

    def test_get_all_trading_dates(self, session: Session, sample_prices):
        """Test that all trading dates are retrieved correctly."""
        engine = BacktestEngine()
        start = date(2023, 1, 1)
        end = date(2023, 3, 31)

        dates = engine._get_all_trading_dates(start, end, session)

        # Should have some dates
        assert len(dates) > 0
        # All dates should be in range
        assert all(start <= d <= end for d in dates)
        # Dates should be unique and sorted
        assert dates == sorted(dates)
        assert len(dates) == len(set(dates))

    def test_trading_dates_sorted(self, session: Session, sample_prices):
        """Test that trading dates are sorted."""
        engine = BacktestEngine()
        start = date(2023, 1, 1)
        end = date(2023, 12, 31)

        dates = engine._get_all_trading_dates(start, end, session)

        # Check ordering
        for i in range(len(dates) - 1):
            assert dates[i] <= dates[i + 1]


class TestComputeFactorScores:
    """Test factor score computation."""

    def test_compute_factor_scores_basic(
        self, session: Session, sample_securities, sample_factors, sample_backtest
    ):
        """Test basic factor score computation."""
        engine = BacktestEngine()
        tickers = [sec.ticker for sec in sample_securities]
        as_of = date(2023, 3, 1)

        allocations = session.query(BacktestFactorAllocation).filter(
            BacktestFactorAllocation.backtest_id == sample_backtest.id
        ).all()

        scores = engine._compute_factor_scores(
            session, tickers, allocations, as_of
        )

        # Should return a dictionary
        assert isinstance(scores, dict)

    def test_compute_factor_scores_empty_universe(
        self, session: Session, sample_factors, sample_backtest
    ):
        """Test factor score computation with empty universe."""
        engine = BacktestEngine()
        tickers = []
        as_of = date(2023, 3, 1)

        allocations = session.query(BacktestFactorAllocation).filter(
            BacktestFactorAllocation.backtest_id == sample_backtest.id
        ).all()

        scores = engine._compute_factor_scores(
            session, tickers, allocations, as_of
        )

        assert scores == {}


class TestCalculateDailyReturns:
    """Test daily return calculation."""

    def test_calculate_daily_returns_basic(
        self, session: Session, sample_securities, sample_prices
    ):
        """Test basic daily return calculation."""
        engine = BacktestEngine()
        holdings = ["AAPL", "MSFT"]
        date1 = date(2023, 1, 2)
        date2 = date(2023, 1, 3)

        ret, exposures, count = engine._calculate_daily_returns(
            session, holdings, date2, date1
        )

        # Should return a valid return or None
        if ret is not None:
            assert isinstance(ret, float)
            assert -1 <= ret <= 1  # Reasonable return bounds
        assert isinstance(count, int)
        assert count >= 0

    def test_calculate_daily_returns_empty_holdings(self, session: Session):
        """Test daily return calculation with empty holdings."""
        engine = BacktestEngine()
        holdings = []
        date1 = date(2023, 1, 2)
        date2 = date(2023, 1, 3)

        ret, exposures, count = engine._calculate_daily_returns(
            session, holdings, date2, date1
        )

        assert ret is None
        assert count == 0

    def test_calculate_daily_returns_missing_data(
        self, session: Session
    ):
        """Test daily return calculation when price data is missing."""
        engine = BacktestEngine()
        holdings = ["NONEXISTENT"]
        date1 = date(2023, 1, 2)
        date2 = date(2023, 1, 3)

        ret, exposures, count = engine._calculate_daily_returns(
            session, holdings, date2, date1
        )

        # Should handle gracefully
        assert ret is None or isinstance(ret, float)


class TestGetBenchmarkReturn:
    """Test benchmark return retrieval."""

    def test_get_benchmark_return_basic(
        self, session: Session, sample_prices
    ):
        """Test basic benchmark return retrieval."""
        engine = BacktestEngine()
        date1 = date(2023, 1, 2)
        date2 = date(2023, 1, 3)

        ret = engine._get_benchmark_return(session, "AAPL", date2, date1)

        # Should return a float or None
        if ret is not None:
            assert isinstance(ret, float)
            assert -1 <= ret <= 1

    def test_get_benchmark_return_nonexistent(
        self, session: Session
    ):
        """Test benchmark return for nonexistent ticker."""
        engine = BacktestEngine()
        date1 = date(2023, 1, 2)
        date2 = date(2023, 1, 3)

        ret = engine._get_benchmark_return(
            session, "NONEXISTENT", date2, date1
        )

        assert ret is None
