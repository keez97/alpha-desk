"""
PEAD Analyzer - Post-Earnings Announcement Drift measurement and aggregation.

Measures cumulative abnormal returns at multiple time windows after earnings
to quantify the market's delayed reaction to earnings surprises.
"""

from datetime import datetime, timezone, date, timedelta
from typing import Dict, Any, Optional, List
from decimal import Decimal
import logging
import math
from sqlmodel import Session

from backend.repositories.earnings_repo import EarningsRepository
from backend.repositories.pit_queries import get_prices_pit_batch
from backend.models.market_data import PriceHistory

logger = logging.getLogger(__name__)


class PEADAnalyzer:
    """Post-Earnings Announcement Drift analyzer."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = EarningsRepository(session)

    def measure_pead(
        self,
        ticker: str,
        fiscal_quarter: str,
        benchmark_ticker: str = "SPY",
    ) -> Dict[str, Any]:
        """
        Measure post-earnings announcement drift.

        After earnings are reported:
        1. Get earnings date from earnings_actual
        2. Get price_history for ticker and benchmark from earnings date to +60 days
        3. Calculate cumulative abnormal return (CAR) at 1d, 5d, 21d, 60d
        4. CAR = cumulative(stock_return - benchmark_return) over window
        5. Save to pead_measurement table

        Args:
            ticker: Security ticker
            fiscal_quarter: Fiscal quarter in format YYYYQ#
            benchmark_ticker: Benchmark for abnormal returns (default SPY)

        Returns:
            Dictionary with PEAD measurements and statistics
        """
        # Get actual earnings
        actual = self.repo.get_actual(ticker, fiscal_quarter)
        if not actual:
            logger.warning(f"No actual earnings found for {ticker} {fiscal_quarter}")
            return {
                "error": "No actual earnings found",
                "ticker": ticker,
                "fiscal_quarter": fiscal_quarter,
            }

        earnings_date = actual.report_date
        today = date.today()

        # If earnings haven't happened yet, skip measurement
        if earnings_date > today:
            return {
                "status": "pending",
                "ticker": ticker,
                "fiscal_quarter": fiscal_quarter,
                "earnings_date": earnings_date.isoformat(),
            }

        # Get price history for stock and benchmark
        end_date = min(earnings_date + timedelta(days=60), today)
        start_date = earnings_date

        prices = self._get_prices_for_measurement(
            [ticker, benchmark_ticker],
            start_date,
            end_date,
        )

        if ticker not in prices or benchmark_ticker not in prices:
            logger.warning(f"Missing price data for {ticker} or {benchmark_ticker}")
            return {
                "error": "Missing price data",
                "ticker": ticker,
                "fiscal_quarter": fiscal_quarter,
            }

        # Calculate returns
        stock_prices = prices[ticker]
        benchmark_prices = prices[benchmark_ticker]

        # Build price maps by date
        stock_price_map = {p.date: float(p.close_price) for p in stock_prices}
        bench_price_map = {p.date: float(p.close_price) for p in benchmark_prices}

        # Get trading days
        common_dates = sorted(set(stock_price_map.keys()) & set(bench_price_map.keys()))

        if len(common_dates) < 2:
            logger.warning(f"Insufficient price data for PEAD calculation: {ticker}")
            return {
                "error": "Insufficient price data",
                "ticker": ticker,
                "fiscal_quarter": fiscal_quarter,
            }

        # Calculate CAR at different windows
        car_1d = self._calculate_car(common_dates, stock_price_map, bench_price_map, 1)
        car_5d = self._calculate_car(common_dates, stock_price_map, bench_price_map, 5)
        car_21d = self._calculate_car(common_dates, stock_price_map, bench_price_map, 21)
        car_60d = self._calculate_car(common_dates, stock_price_map, bench_price_map, 60)

        # Determine surprise direction
        surprise_direction = "inline"
        if actual.surprise_vs_consensus:
            if actual.surprise_vs_consensus > 0:
                surprise_direction = "positive"
            elif actual.surprise_vs_consensus < 0:
                surprise_direction = "negative"

        surprise_magnitude = actual.surprise_vs_consensus or Decimal("0")

        # Save measurement
        self.repo.save_pead_measurement(
            ticker=ticker,
            fiscal_quarter=fiscal_quarter,
            earnings_date=earnings_date,
            surprise_direction=surprise_direction,
            surprise_magnitude=surprise_magnitude,
            car_1d=car_1d,
            car_5d=car_5d,
            car_21d=car_21d,
            car_60d=car_60d,
            benchmark_ticker=benchmark_ticker,
            measured_at=datetime.now(timezone.utc),
        )

        return {
            "status": "success",
            "ticker": ticker,
            "fiscal_quarter": fiscal_quarter,
            "earnings_date": earnings_date.isoformat(),
            "surprise_direction": surprise_direction,
            "surprise_magnitude": float(surprise_magnitude),
            "car_1d": float(car_1d) if car_1d else None,
            "car_5d": float(car_5d) if car_5d else None,
            "car_21d": float(car_21d) if car_21d else None,
            "car_60d": float(car_60d) if car_60d else None,
            "common_dates": len(common_dates),
        }

    def aggregate_pead(
        self,
        surprise_direction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Aggregate PEAD statistics across all measurements.

        Groups by surprise direction (positive/negative/inline) and returns
        average CAR at each window.

        Args:
            surprise_direction: Optional filter ('positive', 'negative', 'inline')

        Returns:
            Dictionary with aggregated PEAD statistics
        """
        stats = self.repo.get_pead_aggregate(surprise_direction)

        # Add direction filter info
        if surprise_direction:
            stats["filter"] = surprise_direction
        else:
            stats["filter"] = "all"

        return stats

    # ==================== Private Helpers ====================

    def _get_prices_for_measurement(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date,
    ) -> Dict[str, List[PriceHistory]]:
        """
        Get price history for multiple tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date for price range
            end_date: End date for price range

        Returns:
            Dictionary mapping ticker -> list of PriceHistory objects
        """
        # Use PiT query to get prices as they were known
        today = date.today()
        prices = get_prices_pit_batch(
            self.session,
            tickers,
            start_date,
            end_date,
            today,
        )

        return prices

    def _calculate_car(
        self,
        common_dates: List[date],
        stock_price_map: Dict[date, float],
        bench_price_map: Dict[date, float],
        window_days: int,
    ) -> Optional[Decimal]:
        """
        Calculate cumulative abnormal return over a window.

        CAR = sum(daily_abnormal_returns) where:
        daily_abnormal_return = daily_stock_return - daily_benchmark_return

        Args:
            common_dates: List of common trading dates
            stock_price_map: Dictionary of date -> stock price
            bench_price_map: Dictionary of date -> benchmark price
            window_days: Number of trading days for window (approximately)

        Returns:
            CAR as Decimal percentage or None if insufficient data
        """
        if len(common_dates) < 2:
            return None

        # Start from first date (earnings date)
        start_idx = 0
        end_idx = min(start_idx + window_days, len(common_dates) - 1)

        if end_idx <= start_idx:
            return None

        # Get start and end prices
        start_date = common_dates[start_idx]
        end_date = common_dates[end_idx]

        stock_start = stock_price_map.get(start_date)
        stock_end = stock_price_map.get(end_date)
        bench_start = bench_price_map.get(start_date)
        bench_end = bench_price_map.get(end_date)

        if not all([stock_start, stock_end, bench_start, bench_end]):
            return None

        # Calculate returns
        if stock_start == 0 or bench_start == 0:
            return None

        stock_return = (stock_end - stock_start) / stock_start
        bench_return = (bench_end - bench_start) / bench_start

        # CAR is the difference (abnormal return)
        car = (stock_return - bench_return) * 100

        return Decimal(str(car))

    def analyze_pead_by_surprise_quartile(self) -> Dict[str, Any]:
        """
        Analyze PEAD patterns grouped by surprise magnitude quartile.

        Groups earnings by surprise magnitude and measures average PEAD
        for each quartile to identify whether larger surprises have
        stronger drift effects.

        Returns:
            Dictionary with PEAD analysis by surprise quartile
        """
        from sqlmodel import select
        from backend.models.earnings import PEADMeasurement

        # Get all PEAD measurements
        measurements = self.session.exec(select(PEADMeasurement)).all()

        if not measurements:
            return {
                "error": "No PEAD measurements found",
            }

        # Sort by surprise magnitude
        sorted_meas = sorted(
            measurements,
            key=lambda x: float(x.surprise_magnitude),
        )

        # Split into quartiles
        n = len(sorted_meas)
        q_size = n // 4

        quartiles = {
            "q1_smallest": sorted_meas[:q_size],
            "q2_small_medium": sorted_meas[q_size : 2 * q_size],
            "q3_medium_large": sorted_meas[2 * q_size : 3 * q_size],
            "q4_largest": sorted_meas[3 * q_size :],
        }

        result = {}

        for q_name, q_data in quartiles.items():
            if not q_data:
                continue

            car_1d_values = [m.car_1d for m in q_data if m.car_1d is not None]
            car_5d_values = [m.car_5d for m in q_data if m.car_5d is not None]
            car_21d_values = [m.car_21d for m in q_data if m.car_21d is not None]
            car_60d_values = [m.car_60d for m in q_data if m.car_60d is not None]

            magnitude_values = [float(m.surprise_magnitude) for m in q_data]

            result[q_name] = {
                "count": len(q_data),
                "avg_surprise_magnitude": sum(magnitude_values) / len(magnitude_values),
                "car_1d_avg": sum(car_1d_values) / len(car_1d_values) if car_1d_values else None,
                "car_5d_avg": sum(car_5d_values) / len(car_5d_values) if car_5d_values else None,
                "car_21d_avg": sum(car_21d_values) / len(car_21d_values) if car_21d_values else None,
                "car_60d_avg": sum(car_60d_values) / len(car_60d_values) if car_60d_values else None,
            }

        return result
