"""
Walk-forward backtesting engine with Point-in-Time enforcement.
Core engine for backtesting factor combinations.
"""

from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import numpy as np
from sqlmodel import Session, select

from backend.models.backtests import (
    Backtest,
    BacktestConfiguration,
    BacktestFactorAllocation,
    BacktestResult,
    BacktestStatistic,
)
from backend.models.factors import FactorDefinition, CustomFactorScore
from backend.models.market_data import PriceHistory
from backend.repositories.pit_queries import (
    get_prices_pit,
    get_prices_pit_batch,
    get_active_universe_pit,
    get_custom_factor_scores_pit,
    get_factor_scores_pit_batch,
)
from backend.repositories.backtest_repo import BacktestRepository
from backend.repositories.factor_repo import FactorRepository
from backend.services.statistics_calculator import StatisticsCalculator
from backend.services.factor_calculator import FactorCalculator


class BacktestEngine:
    """Walk-forward backtesting engine with PiT enforcement."""

    def __init__(self):
        pass

    async def run_backtest(self, backtest_id: int, session: Session) -> None:
        """
        Main entry point. Runs the full backtest:
        1. Load configuration (dates, factors, weights, costs)
        2. Generate rebalance dates based on frequency
        3. At each rebalance date:
           a. Query PiT-safe factor scores for active universe
           b. Rank securities by composite factor score
           c. Construct quantile portfolios (top quintile = long)
           d. Calculate turnover from previous holdings
           e. Apply transaction costs
        4. Between rebalances: compute daily P&L from price returns
        5. After all dates: calculate statistics
        6. Save results to database

        Args:
            backtest_id: ID of backtest to run
            session: Database session
        """
        try:
            repo = BacktestRepository(session)
            backtest = repo.get_backtest(backtest_id)

            if not backtest:
                return

            # Update status to RUNNING
            repo.update_backtest_status(backtest_id, "RUNNING")

            # Load configuration
            config = repo.get_configuration(backtest_id)
            if not config:
                repo.update_backtest_status(
                    backtest_id,
                    "FAILED",
                    error_message="No configuration found"
                )
                return

            # Load factor allocations
            allocations = repo.get_factor_allocations(backtest_id)
            if not allocations:
                repo.update_backtest_status(
                    backtest_id,
                    "FAILED",
                    error_message="No factor allocations found"
                )
                return

            # Generate rebalance dates
            rebalance_dates = self._generate_rebalance_dates(
                config.start_date,
                config.end_date,
                config.rebalance_frequency
            )

            if not rebalance_dates:
                repo.update_backtest_status(
                    backtest_id,
                    "FAILED",
                    error_message="No valid rebalance dates"
                )
                return

            # Initialize portfolio tracking
            daily_returns = []
            benchmark_returns = []
            portfolio_values = []
            current_holdings = []
            current_value = Decimal("1000000")  # Start with $1M

            # Get all trading dates in the backtest period
            all_dates = self._get_all_trading_dates(
                config.start_date,
                config.end_date,
                session
            )

            if not all_dates:
                repo.update_backtest_status(
                    backtest_id,
                    "FAILED",
                    error_message="No trading dates found"
                )
                return

            # Walk-forward loop
            results = []
            rebalance_idx = 0

            for i, current_date in enumerate(all_dates):
                # Check if this is a rebalance date
                if rebalance_idx < len(rebalance_dates) and current_date == rebalance_dates[rebalance_idx]:
                    # Rebalance logic
                    universe = get_active_universe_pit(session, current_date)

                    if not universe:
                        rebalance_idx += 1
                        continue

                    tickers = [sec.ticker for sec in universe]

                    # Compute composite factor scores
                    composite_scores = self._compute_factor_scores(
                        session,
                        tickers,
                        allocations,
                        current_date
                    )

                    # Construct portfolio (top quintile)
                    new_holdings = self._construct_portfolio(
                        composite_scores,
                        n_quantiles=5
                    )

                    # Calculate turnover
                    turnover = self._calculate_turnover(
                        current_holdings,
                        new_holdings,
                        current_value
                    )

                    # Apply transaction costs
                    transaction_cost = turnover * (
                        float(config.commission_bps) + float(config.slippage_bps)
                    ) / 10000

                    current_value -= Decimal(str(transaction_cost))

                    current_holdings = new_holdings
                    rebalance_idx += 1

                # Calculate daily return
                if i > 0 and current_holdings:
                    prev_date = all_dates[i - 1]
                    daily_return, factor_exposures, holdings_count = self._calculate_daily_returns(
                        session,
                        current_holdings,
                        current_date,
                        prev_date
                    )

                    if daily_return is not None:
                        daily_returns.append(daily_return)
                        current_value = current_value * Decimal(str(1 + daily_return))

                        # Get benchmark return
                        benchmark_ret = self._get_benchmark_return(
                            session,
                            config.benchmark_ticker,
                            current_date,
                            prev_date
                        )

                        if benchmark_ret is not None:
                            benchmark_returns.append(benchmark_ret)

                        portfolio_values.append(current_value)

                        # Save daily result
                        result = BacktestResult(
                            backtest_id=backtest_id,
                            date=current_date,
                            portfolio_value=current_value,
                            daily_return=Decimal(str(daily_return)),
                            benchmark_return=Decimal(str(benchmark_ret)) if benchmark_ret else None,
                            turnover=Decimal(str(turnover if i > 0 else 0)),
                            factor_exposures=factor_exposures,
                            holdings_count=holdings_count,
                        )
                        results.append(result)

            # Save results to database
            repo.save_results(backtest_id, results)

            # Calculate statistics
            statistics_dict = StatisticsCalculator.calculate_all(
                daily_returns,
                benchmark_returns if benchmark_returns else daily_returns,
                risk_free_rate=0.05
            )

            # Convert to BacktestStatistic objects
            statistics = []
            for metric_name, metric_value in statistics_dict.items():
                stat = BacktestStatistic(
                    backtest_id=backtest_id,
                    metric_name=metric_name,
                    metric_value=Decimal(str(metric_value)),
                    period_start=config.start_date,
                    period_end=config.end_date,
                )
                statistics.append(stat)

            repo.save_statistics(backtest_id, statistics)

            # Update status to COMPLETED
            repo.update_backtest_status(
                backtest_id,
                "COMPLETED",
                completed_at=datetime.now(timezone.utc)
            )

        except Exception as e:
            repo = BacktestRepository(session)
            repo.update_backtest_status(
                backtest_id,
                "FAILED",
                error_message=str(e)
            )
            raise

    def _generate_rebalance_dates(
        self,
        start: date,
        end: date,
        freq: str
    ) -> List[date]:
        """
        Generate rebalance dates based on frequency.

        Args:
            start: Start date
            end: End date
            freq: Frequency ("daily", "weekly", "monthly", "quarterly", "annual")

        Returns:
            List of rebalance dates
        """
        dates = []
        current = start

        if freq == "daily":
            while current <= end:
                dates.append(current)
                current += timedelta(days=1)

        elif freq == "weekly":
            while current <= end:
                dates.append(current)
                current += timedelta(weeks=1)

        elif freq == "monthly":
            while current <= end:
                # Move to last business day of month (simplified: use day 1 of next month - 1)
                dates.append(current)
                # Add one month
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)

        elif freq == "quarterly":
            while current <= end:
                dates.append(current)
                current += timedelta(days=90)  # Simplified

        elif freq == "annual":
            while current <= end:
                dates.append(current)
                current = current.replace(year=current.year + 1)

        return [d for d in dates if d <= end]

    def _get_all_trading_dates(
        self,
        start: date,
        end: date,
        session: Session
    ) -> List[date]:
        """
        Get all trading dates in the period from price data.

        Args:
            start: Start date
            end: End date
            session: Database session

        Returns:
            List of trading dates
        """
        query = select(PriceHistory.date).where(
            PriceHistory.date >= start,
            PriceHistory.date <= end,
        ).distinct().order_by(PriceHistory.date.asc())

        results = session.exec(query).all()
        return sorted(list(set(results)))

    def _compute_factor_scores(
        self,
        session: Session,
        tickers: List[str],
        factor_allocations: List[BacktestFactorAllocation],
        as_of_date: date
    ) -> Dict[str, float]:
        """
        Compute weighted composite factor score for each ticker using PiT data.

        Uses batch queries instead of N+1 pattern.

        Args:
            session: Database session
            tickers: List of tickers
            factor_allocations: Factor weights
            as_of_date: Date as of which to compute scores

        Returns:
            Dictionary mapping ticker to composite score
        """
        if not tickers or not factor_allocations:
            return {}

        # Batch query: get all factor scores in ONE query
        factor_ids = [alloc.factor_id for alloc in factor_allocations]
        batch_scores = get_factor_scores_pit_batch(
            session,
            factor_ids,
            tickers,
            as_of_date
        )

        # Compute composite scores
        scores = {}
        for ticker in tickers:
            composite_score = 0.0
            total_weight = 0.0

            for allocation in factor_allocations:
                key = (allocation.factor_id, ticker)
                if key in batch_scores:
                    composite_score += batch_scores[key] * float(allocation.weight)
                    total_weight += float(allocation.weight)

            if total_weight > 0:
                scores[ticker] = composite_score / total_weight

        return scores

    def _construct_portfolio(
        self,
        scores: Dict[str, float],
        n_quantiles: int = 5
    ) -> List[str]:
        """
        Select top quantile securities (equal-weight within quantile).

        Args:
            scores: Dictionary of ticker -> score
            n_quantiles: Number of quantiles (default 5 for quintiles)

        Returns:
            List of selected tickers (top quantile)
        """
        if not scores:
            return []

        # Sort by score descending
        sorted_tickers = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Select top quantile
        quantile_size = max(1, len(sorted_tickers) // n_quantiles)
        top_tickers = [ticker for ticker, _ in sorted_tickers[:quantile_size]]

        return top_tickers

    def _calculate_turnover(
        self,
        old_holdings: List[str],
        new_holdings: List[str],
        portfolio_value: Decimal
    ) -> float:
        """
        Calculate turnover as percentage of portfolio value.

        Args:
            old_holdings: Previous holdings
            new_holdings: New holdings
            portfolio_value: Current portfolio value

        Returns:
            Turnover as decimal (e.g., 0.20 for 20%)
        """
        if not old_holdings and not new_holdings:
            return 0.0

        # Calculate bought and sold
        old_set = set(old_holdings)
        new_set = set(new_holdings)

        sold = old_set - new_set
        bought = new_set - old_set

        # Simple turnover: (sold + bought) / 2 / num_holdings
        # Approximate as percentage of portfolio
        turnover_amount = (len(sold) + len(bought)) / max(1, len(new_set))

        return turnover_amount

    def _calculate_daily_returns(
        self,
        session: Session,
        holdings: List[str],
        date: date,
        prev_date: date
    ) -> Tuple[Optional[float], Optional[Dict], Optional[int]]:
        """
        Calculate portfolio return between two dates using price data.

        Uses batch price queries instead of N+1 pattern.

        Args:
            session: Database session
            holdings: List of holdings
            date: Current date
            prev_date: Previous date

        Returns:
            Tuple of (daily_return, factor_exposures, holdings_count)
        """
        if not holdings:
            return None, None, 0

        # Batch query: get all prices for all holdings in two queries
        prev_prices_batch = get_prices_pit_batch(
            session,
            holdings,
            prev_date,
            prev_date,
            prev_date
        )
        curr_prices_batch = get_prices_pit_batch(
            session,
            holdings,
            date,
            date,
            date
        )

        returns = []

        for ticker in holdings:
            prev_prices = prev_prices_batch.get(ticker, [])
            curr_prices = curr_prices_batch.get(ticker, [])

            if not prev_prices or not curr_prices:
                continue

            # Find prices on exact dates (should be only one from batch)
            prev_price = None
            curr_price = None

            for p in prev_prices:
                if p.date == prev_date:
                    prev_price = p
                    break

            for p in curr_prices:
                if p.date == date:
                    curr_price = p
                    break

            if prev_price and curr_price and float(prev_price.adjusted_close) > 0:
                ret = (
                    (float(curr_price.adjusted_close) - float(prev_price.adjusted_close))
                    / float(prev_price.adjusted_close)
                )
                returns.append(ret)

        if not returns:
            return None, None, len(holdings)

        # Equal-weight portfolio return
        portfolio_return = float(np.mean(returns))

        return portfolio_return, {}, len(holdings)

    def _get_benchmark_return(
        self,
        session: Session,
        benchmark_ticker: str,
        current_date: date,
        prev_date: date
    ) -> Optional[float]:
        """
        Get benchmark return between two dates.

        Args:
            session: Database session
            benchmark_ticker: Benchmark ticker (e.g., SPY)
            current_date: Current date
            prev_date: Previous date

        Returns:
            Benchmark return or None
        """
        try:
            prev_prices = get_prices_pit(session, benchmark_ticker, prev_date)
            curr_prices = get_prices_pit(session, benchmark_ticker, current_date)

            if not prev_prices or not curr_prices:
                return None

            prev_price = None
            curr_price = None

            for p in prev_prices:
                if p.date == prev_date:
                    prev_price = p
                    break

            for p in curr_prices:
                if p.date == current_date:
                    curr_price = p
                    break

            if prev_price and curr_price and float(prev_price.adjusted_close) > 0:
                ret = (
                    (float(curr_price.adjusted_close) - float(prev_price.adjusted_close))
                    / float(prev_price.adjusted_close)
                )
                return ret

        except Exception:
            pass

        return None
