"""
Tests for PEAD Analyzer.

Tests cumulative abnormal return calculations at multiple windows,
surprise direction handling, and PEAD aggregation.
"""

import pytest
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from sqlmodel import Session
from unittest.mock import patch, MagicMock

from backend.services.pead_analyzer import PEADAnalyzer
from backend.repositories.earnings_repo import EarningsRepository
from backend.models.earnings import EarningsActual, PEADMeasurement
from backend.models.market_data import PriceHistory


class TestCARCalculation:
    """Test cumulative abnormal return calculation at different windows."""

    def test_car_1d_calculation(self, session: Session):
        """Test 1-day CAR calculation."""
        analyzer = PEADAnalyzer(session)
        repo = EarningsRepository(session)

        earnings_date = date(2024, 1, 15)

        # Save actual earnings
        repo.save_actual(
            ticker="AAPL",
            fiscal_quarter="2024Q1",
            actual_eps=Decimal("5.61"),
            report_date=earnings_date,
            surprise_vs_consensus=Decimal("1.8"),
            source="yfinance",
        )

        # Create price history for 1 day after earnings
        prices_aapl = [
            PriceHistory(
                ticker="AAPL",
                date=earnings_date,
                open=Decimal("200.0"),
                high=Decimal("202.0"),
                low=Decimal("199.0"),
                close=Decimal("201.0"),
                adjusted_close=Decimal("201.0"),
                volume=50000000,
                ingestion_timestamp=datetime.combine(earnings_date, datetime.max.time(), timezone.utc),
            ),
            PriceHistory(
                ticker="AAPL",
                date=earnings_date + timedelta(days=1),
                open=Decimal("201.5"),
                high=Decimal("203.0"),
                low=Decimal("200.5"),
                close=Decimal("202.5"),
                adjusted_close=Decimal("202.5"),
                volume=45000000,
                ingestion_timestamp=datetime.combine(
                    earnings_date + timedelta(days=1), datetime.max.time(), timezone.utc
                ),
            ),
        ]

        prices_spy = [
            PriceHistory(
                ticker="SPY",
                date=earnings_date,
                open=Decimal("450.0"),
                high=Decimal("451.0"),
                low=Decimal("449.0"),
                close=Decimal("450.5"),
                adjusted_close=Decimal("450.5"),
                volume=100000000,
                ingestion_timestamp=datetime.combine(earnings_date, datetime.max.time(), timezone.utc),
            ),
            PriceHistory(
                ticker="SPY",
                date=earnings_date + timedelta(days=1),
                open=Decimal("450.8"),
                high=Decimal("451.5"),
                low=Decimal("450.0"),
                close=Decimal("451.0"),
                adjusted_close=Decimal("451.0"),
                volume=95000000,
                ingestion_timestamp=datetime.combine(
                    earnings_date + timedelta(days=1), datetime.max.time(), timezone.utc
                ),
            ),
        ]

        for p in prices_aapl + prices_spy:
            session.add(p)

        session.commit()

        # Mock the price retrieval
        with patch.object(analyzer, "_get_prices_for_measurement") as mock_prices:
            mock_prices.return_value = {
                "AAPL": prices_aapl,
                "SPY": prices_spy,
            }

            result = analyzer.measure_pead("AAPL", "2024Q1", benchmark_ticker="SPY")

        assert result["status"] == "success"
        assert result["car_1d"] is not None

    def test_car_5d_calculation(self, session: Session):
        """Test 5-day CAR calculation."""
        analyzer = PEADAnalyzer(session)
        repo = EarningsRepository(session)

        earnings_date = date(2024, 1, 15)

        repo.save_actual(
            ticker="MSFT",
            fiscal_quarter="2024Q1",
            actual_eps=Decimal("2.93"),
            report_date=earnings_date,
            surprise_vs_consensus=Decimal("2.1"),
            source="yfinance",
        )

        # Create 5 trading days of prices
        prices_msft = []
        prices_spy = []

        for i in range(6):  # 0 to 5 days
            current_date = earnings_date + timedelta(days=i)
            base_price_msft = 320.0 + i * 0.5
            base_price_spy = 450.0 + i * 0.3

            prices_msft.append(
                PriceHistory(
                    ticker="MSFT",
                    date=current_date,
                    open=Decimal(str(base_price_msft - 0.5)),
                    high=Decimal(str(base_price_msft + 1.0)),
                    low=Decimal(str(base_price_msft - 1.0)),
                    close=Decimal(str(base_price_msft)),
                    adjusted_close=Decimal(str(base_price_msft)),
                    volume=50000000,
                    ingestion_timestamp=datetime.combine(
                        current_date, datetime.max.time(), timezone.utc
                    ),
                )
            )

            prices_spy.append(
                PriceHistory(
                    ticker="SPY",
                    date=current_date,
                    open=Decimal(str(base_price_spy - 0.2)),
                    high=Decimal(str(base_price_spy + 0.5)),
                    low=Decimal(str(base_price_spy - 0.5)),
                    close=Decimal(str(base_price_spy)),
                    adjusted_close=Decimal(str(base_price_spy)),
                    volume=100000000,
                    ingestion_timestamp=datetime.combine(
                        current_date, datetime.max.time(), timezone.utc
                    ),
                )
            )

        for p in prices_msft + prices_spy:
            session.add(p)

        session.commit()

        with patch.object(analyzer, "_get_prices_for_measurement") as mock_prices:
            mock_prices.return_value = {
                "MSFT": prices_msft,
                "SPY": prices_spy,
            }

            result = analyzer.measure_pead("MSFT", "2024Q1", benchmark_ticker="SPY")

        assert result["status"] == "success"
        assert result["car_5d"] is not None

    def test_car_21d_calculation(self, session: Session):
        """Test 21-day CAR calculation."""
        analyzer = PEADAnalyzer(session)
        repo = EarningsRepository(session)

        earnings_date = date(2024, 1, 15)

        repo.save_actual(
            ticker="GOOGL",
            fiscal_quarter="2024Q1",
            actual_eps=Decimal("1.95"),
            report_date=earnings_date,
            surprise_vs_consensus=Decimal("-0.5"),
            source="yfinance",
        )

        # Create 21 trading days of prices
        prices_googl = []
        prices_spy = []

        for i in range(22):
            current_date = earnings_date + timedelta(days=i)
            base_price = 140.0 + i * 0.1
            spy_price = 450.0 + i * 0.2

            prices_googl.append(
                PriceHistory(
                    ticker="GOOGL",
                    date=current_date,
                    open=Decimal(str(base_price)),
                    high=Decimal(str(base_price + 1.0)),
                    low=Decimal(str(base_price - 1.0)),
                    close=Decimal(str(base_price)),
                    adjusted_close=Decimal(str(base_price)),
                    volume=40000000,
                    ingestion_timestamp=datetime.combine(
                        current_date, datetime.max.time(), timezone.utc
                    ),
                )
            )

            prices_spy.append(
                PriceHistory(
                    ticker="SPY",
                    date=current_date,
                    open=Decimal(str(spy_price)),
                    high=Decimal(str(spy_price + 0.5)),
                    low=Decimal(str(spy_price - 0.5)),
                    close=Decimal(str(spy_price)),
                    adjusted_close=Decimal(str(spy_price)),
                    volume=100000000,
                    ingestion_timestamp=datetime.combine(
                        current_date, datetime.max.time(), timezone.utc
                    ),
                )
            )

        for p in prices_googl + prices_spy:
            session.add(p)

        session.commit()

        with patch.object(analyzer, "_get_prices_for_measurement") as mock_prices:
            mock_prices.return_value = {
                "GOOGL": prices_googl,
                "SPY": prices_spy,
            }

            result = analyzer.measure_pead("GOOGL", "2024Q1", benchmark_ticker="SPY")

        assert result["status"] == "success"
        assert result["car_21d"] is not None

    def test_car_60d_calculation(self, session: Session):
        """Test 60-day CAR calculation."""
        analyzer = PEADAnalyzer(session)
        repo = EarningsRepository(session)

        earnings_date = date(2024, 1, 15)

        repo.save_actual(
            ticker="TSLA",
            fiscal_quarter="2024Q1",
            actual_eps=Decimal("0.87"),
            report_date=earnings_date,
            surprise_vs_consensus=Decimal("5.0"),
            source="yfinance",
        )

        # Create 60 trading days of prices
        prices_tsla = []
        prices_spy = []

        for i in range(61):
            current_date = earnings_date + timedelta(days=i)
            base_price = 200.0 + i * 0.2
            spy_price = 450.0 + i * 0.15

            prices_tsla.append(
                PriceHistory(
                    ticker="TSLA",
                    date=current_date,
                    open=Decimal(str(base_price)),
                    high=Decimal(str(base_price + 2.0)),
                    low=Decimal(str(base_price - 2.0)),
                    close=Decimal(str(base_price)),
                    adjusted_close=Decimal(str(base_price)),
                    volume=60000000,
                    ingestion_timestamp=datetime.combine(
                        current_date, datetime.max.time(), timezone.utc
                    ),
                )
            )

            prices_spy.append(
                PriceHistory(
                    ticker="SPY",
                    date=current_date,
                    open=Decimal(str(spy_price)),
                    high=Decimal(str(spy_price + 1.0)),
                    low=Decimal(str(spy_price - 1.0)),
                    close=Decimal(str(spy_price)),
                    adjusted_close=Decimal(str(spy_price)),
                    volume=100000000,
                    ingestion_timestamp=datetime.combine(
                        current_date, datetime.max.time(), timezone.utc
                    ),
                )
            )

        for p in prices_tsla + prices_spy:
            session.add(p)

        session.commit()

        with patch.object(analyzer, "_get_prices_for_measurement") as mock_prices:
            mock_prices.return_value = {
                "TSLA": prices_tsla,
                "SPY": prices_spy,
            }

            result = analyzer.measure_pead("TSLA", "2024Q1", benchmark_ticker="SPY")

        assert result["status"] == "success"
        assert result["car_60d"] is not None


class TestSurpriseDirection:
    """Test surprise direction classification."""

    def test_positive_surprise_direction(self, session: Session):
        """Positive surprise should be classified correctly."""
        analyzer = PEADAnalyzer(session)
        repo = EarningsRepository(session)

        earnings_date = date(2024, 1, 15)

        repo.save_actual(
            ticker="AAPL",
            fiscal_quarter="2024Q1",
            actual_eps=Decimal("5.61"),
            report_date=earnings_date,
            surprise_vs_consensus=Decimal("2.5"),
            source="yfinance",
        )

        # Create price data
        prices = []
        for i in range(3):
            current_date = earnings_date + timedelta(days=i)
            prices.append(
                PriceHistory(
                    ticker="AAPL",
                    date=current_date,
                    open=Decimal("200.0"),
                    high=Decimal("202.0"),
                    low=Decimal("199.0"),
                    close=Decimal(str(200.0 + i * 0.5)),
                    adjusted_close=Decimal(str(200.0 + i * 0.5)),
                    volume=50000000,
                    ingestion_timestamp=datetime.combine(
                        current_date, datetime.max.time(), timezone.utc
                    ),
                )
            )
            prices.append(
                PriceHistory(
                    ticker="SPY",
                    date=current_date,
                    open=Decimal("450.0"),
                    high=Decimal("451.0"),
                    low=Decimal("449.0"),
                    close=Decimal(str(450.0 + i * 0.2)),
                    adjusted_close=Decimal(str(450.0 + i * 0.2)),
                    volume=100000000,
                    ingestion_timestamp=datetime.combine(
                        current_date, datetime.max.time(), timezone.utc
                    ),
                )
            )

        for p in prices:
            session.add(p)

        session.commit()

        with patch.object(analyzer, "_get_prices_for_measurement") as mock_prices:
            mock_prices.return_value = {
                "AAPL": [p for p in prices if p.ticker == "AAPL"],
                "SPY": [p for p in prices if p.ticker == "SPY"],
            }

            result = analyzer.measure_pead("AAPL", "2024Q1")

        assert result["status"] == "success"
        assert result["surprise_direction"] == "positive"

    def test_negative_surprise_direction(self, session: Session):
        """Negative surprise should be classified correctly."""
        analyzer = PEADAnalyzer(session)
        repo = EarningsRepository(session)

        earnings_date = date(2024, 1, 15)

        repo.save_actual(
            ticker="MSFT",
            fiscal_quarter="2024Q1",
            actual_eps=Decimal("2.80"),
            report_date=earnings_date,
            surprise_vs_consensus=Decimal("-1.5"),
            source="yfinance",
        )

        prices = []
        for i in range(3):
            current_date = earnings_date + timedelta(days=i)
            prices.append(
                PriceHistory(
                    ticker="MSFT",
                    date=current_date,
                    open=Decimal("320.0"),
                    high=Decimal("321.0"),
                    low=Decimal("319.0"),
                    close=Decimal(str(320.0 - i * 0.5)),
                    adjusted_close=Decimal(str(320.0 - i * 0.5)),
                    volume=50000000,
                    ingestion_timestamp=datetime.combine(
                        current_date, datetime.max.time(), timezone.utc
                    ),
                )
            )
            prices.append(
                PriceHistory(
                    ticker="SPY",
                    date=current_date,
                    open=Decimal("450.0"),
                    high=Decimal("451.0"),
                    low=Decimal("449.0"),
                    close=Decimal(str(450.0 + i * 0.3)),
                    adjusted_close=Decimal(str(450.0 + i * 0.3)),
                    volume=100000000,
                    ingestion_timestamp=datetime.combine(
                        current_date, datetime.max.time(), timezone.utc
                    ),
                )
            )

        for p in prices:
            session.add(p)

        session.commit()

        with patch.object(analyzer, "_get_prices_for_measurement") as mock_prices:
            mock_prices.return_value = {
                "MSFT": [p for p in prices if p.ticker == "MSFT"],
                "SPY": [p for p in prices if p.ticker == "SPY"],
            }

            result = analyzer.measure_pead("MSFT", "2024Q1")

        assert result["status"] == "success"
        assert result["surprise_direction"] == "negative"

    def test_inline_surprise_direction(self, session: Session):
        """Inline (zero) surprise should be classified correctly."""
        analyzer = PEADAnalyzer(session)
        repo = EarningsRepository(session)

        earnings_date = date(2024, 1, 15)

        repo.save_actual(
            ticker="GOOGL",
            fiscal_quarter="2024Q1",
            actual_eps=Decimal("1.95"),
            report_date=earnings_date,
            surprise_vs_consensus=Decimal("0.0"),
            source="yfinance",
        )

        prices = []
        for i in range(3):
            current_date = earnings_date + timedelta(days=i)
            prices.append(
                PriceHistory(
                    ticker="GOOGL",
                    date=current_date,
                    open=Decimal("140.0"),
                    high=Decimal("141.0"),
                    low=Decimal("139.0"),
                    close=Decimal("140.0"),
                    adjusted_close=Decimal("140.0"),
                    volume=40000000,
                    ingestion_timestamp=datetime.combine(
                        current_date, datetime.max.time(), timezone.utc
                    ),
                )
            )
            prices.append(
                PriceHistory(
                    ticker="SPY",
                    date=current_date,
                    open=Decimal("450.0"),
                    high=Decimal("451.0"),
                    low=Decimal("449.0"),
                    close=Decimal("450.0"),
                    adjusted_close=Decimal("450.0"),
                    volume=100000000,
                    ingestion_timestamp=datetime.combine(
                        current_date, datetime.max.time(), timezone.utc
                    ),
                )
            )

        for p in prices:
            session.add(p)

        session.commit()

        with patch.object(analyzer, "_get_prices_for_measurement") as mock_prices:
            mock_prices.return_value = {
                "GOOGL": [p for p in prices if p.ticker == "GOOGL"],
                "SPY": [p for p in prices if p.ticker == "SPY"],
            }

            result = analyzer.measure_pead("GOOGL", "2024Q1")

        assert result["status"] == "success"
        assert result["surprise_direction"] == "inline"


class TestAggregatePEAD:
    """Test PEAD aggregation by surprise direction."""

    def test_aggregate_all_measurements(self, session: Session):
        """Aggregate should work across all measurements."""
        analyzer = PEADAnalyzer(session)
        repo = EarningsRepository(session)

        # Create multiple PEAD measurements
        for i in range(3):
            repo.save_pead_measurement(
                ticker=f"TEST{i}",
                fiscal_quarter="2024Q1",
                earnings_date=date(2024, 1, 15),
                surprise_direction="positive" if i % 2 == 0 else "negative",
                surprise_magnitude=Decimal(str(2.0 + i)),
                car_1d=Decimal(str(0.5 + i * 0.1)),
                car_5d=Decimal(str(1.5 + i * 0.2)),
                car_21d=Decimal(str(3.0 + i * 0.3)),
                car_60d=Decimal(str(5.0 + i * 0.5)),
            )

        result = analyzer.aggregate_pead()

        assert result["count"] == 3
        assert result["car_1d_avg"] is not None
        assert result["car_5d_avg"] is not None
        assert result["car_21d_avg"] is not None
        assert result["car_60d_avg"] is not None

    def test_aggregate_filter_positive_surprise(self, session: Session):
        """Aggregate should filter by positive surprise direction."""
        analyzer = PEADAnalyzer(session)
        repo = EarningsRepository(session)

        # Create positive and negative measurements
        repo.save_pead_measurement(
            ticker="POS",
            fiscal_quarter="2024Q1",
            earnings_date=date(2024, 1, 15),
            surprise_direction="positive",
            surprise_magnitude=Decimal("2.5"),
            car_1d=Decimal("0.8"),
            car_5d=Decimal("2.0"),
        )

        repo.save_pead_measurement(
            ticker="NEG",
            fiscal_quarter="2024Q1",
            earnings_date=date(2024, 1, 15),
            surprise_direction="negative",
            surprise_magnitude=Decimal("-1.5"),
            car_1d=Decimal("-0.5"),
            car_5d=Decimal("-1.0"),
        )

        result = analyzer.aggregate_pead(surprise_direction="positive")

        assert result["count"] == 1
        assert result["filter"] == "positive"

    def test_aggregate_filter_negative_surprise(self, session: Session):
        """Aggregate should filter by negative surprise direction."""
        analyzer = PEADAnalyzer(session)
        repo = EarningsRepository(session)

        # Create positive and negative measurements
        repo.save_pead_measurement(
            ticker="POS",
            fiscal_quarter="2024Q1",
            earnings_date=date(2024, 1, 15),
            surprise_direction="positive",
            surprise_magnitude=Decimal("2.5"),
            car_1d=Decimal("0.8"),
        )

        repo.save_pead_measurement(
            ticker="NEG",
            fiscal_quarter="2024Q1",
            earnings_date=date(2024, 1, 15),
            surprise_direction="negative",
            surprise_magnitude=Decimal("-1.5"),
            car_1d=Decimal("-0.5"),
        )

        result = analyzer.aggregate_pead(surprise_direction="negative")

        assert result["count"] == 1
        assert result["filter"] == "negative"

    def test_aggregate_empty_results(self, session: Session):
        """Aggregate should handle empty results gracefully."""
        analyzer = PEADAnalyzer(session)

        result = analyzer.aggregate_pead()

        assert result["count"] == 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_actual_earnings(self, session: Session):
        """Missing actual earnings should return error."""
        analyzer = PEADAnalyzer(session)

        result = analyzer.measure_pead("NONEXISTENT", "2025Q1")

        assert result["error"] == "No actual earnings found"

    def test_future_earnings_not_measured(self, session: Session):
        """Future earnings should return pending status."""
        analyzer = PEADAnalyzer(session)
        repo = EarningsRepository(session)

        future_date = date.today() + timedelta(days=30)

        repo.save_actual(
            ticker="FUTURE",
            fiscal_quarter="2025Q4",
            actual_eps=Decimal("5.00"),
            report_date=future_date,
            source="yfinance",
        )

        result = analyzer.measure_pead("FUTURE", "2025Q4")

        assert result["status"] == "pending"
        assert result["earnings_date"] == future_date.isoformat()

    def test_missing_price_data(self, session: Session):
        """Missing price data should return error."""
        analyzer = PEADAnalyzer(session)
        repo = EarningsRepository(session)

        earnings_date = date(2024, 1, 15)

        repo.save_actual(
            ticker="NOPRICES",
            fiscal_quarter="2024Q1",
            actual_eps=Decimal("5.00"),
            report_date=earnings_date,
            source="yfinance",
        )

        with patch.object(analyzer, "_get_prices_for_measurement") as mock_prices:
            mock_prices.return_value = {}

            result = analyzer.measure_pead("NOPRICES", "2024Q1")

        assert result["error"] == "Missing price data"

    def test_insufficient_price_data(self, session: Session):
        """Insufficient price data should return error."""
        analyzer = PEADAnalyzer(session)
        repo = EarningsRepository(session)

        earnings_date = date(2024, 1, 15)

        repo.save_actual(
            ticker="LOWDATA",
            fiscal_quarter="2024Q1",
            actual_eps=Decimal("5.00"),
            report_date=earnings_date,
            source="yfinance",
        )

        # Only 1 price point, need at least 2
        prices = [
            PriceHistory(
                ticker="LOWDATA",
                date=earnings_date,
                open=Decimal("200.0"),
                high=Decimal("202.0"),
                low=Decimal("199.0"),
                close=Decimal("201.0"),
                adjusted_close=Decimal("201.0"),
                volume=50000000,
                ingestion_timestamp=datetime.combine(earnings_date, datetime.max.time(), timezone.utc),
            ),
        ]

        with patch.object(analyzer, "_get_prices_for_measurement") as mock_prices:
            mock_prices.return_value = {
                "LOWDATA": prices,
                "SPY": prices,
            }

            result = analyzer.measure_pead("LOWDATA", "2024Q1")

        assert result["error"] == "Insufficient price data"


class TestPEADByQuartile:
    """Test PEAD analysis by surprise magnitude quartile."""

    def test_analyze_pead_by_quartile(self, session: Session):
        """Test PEAD quartile analysis."""
        analyzer = PEADAnalyzer(session)
        repo = EarningsRepository(session)

        # Create measurements with varying surprise magnitudes
        magnitudes = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]

        for i, mag in enumerate(magnitudes):
            repo.save_pead_measurement(
                ticker=f"TEST{i}",
                fiscal_quarter="2024Q1",
                earnings_date=date(2024, 1, 15),
                surprise_direction="positive",
                surprise_magnitude=Decimal(str(mag)),
                car_1d=Decimal(str(0.5 + i * 0.1)),
                car_5d=Decimal(str(1.0 + i * 0.2)),
                car_21d=Decimal(str(2.0 + i * 0.3)),
                car_60d=Decimal(str(3.0 + i * 0.5)),
            )

        result = analyzer.analyze_pead_by_surprise_quartile()

        # Should have quartile data
        assert "q1_smallest" in result or "q2_small_medium" in result
        assert len(result) > 0
