"""
Repository for Backtest CRUD operations and queries.
"""

from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any
from decimal import Decimal
from sqlmodel import Session, select
from backend.models.backtests import (
    Backtest,
    BacktestConfiguration,
    BacktestFactorAllocation,
    BacktestResult,
    BacktestStatistic,
    FactorCorrelation,
    AlphaDecayAnalysis,
)
from backend.models.factors import FactorDefinition


class BacktestRepository:
    """Repository for backtest-related database operations."""

    def __init__(self, session: Session):
        self.session = session

    def create_backtest(
        self,
        name: str,
        backtest_type: str = "factor_combination",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Backtest:
        """
        Create a new backtest in DRAFT status.

        Args:
            name: Human-readable name
            backtest_type: Type of backtest
            metadata: Optional metadata dict

        Returns:
            Created Backtest object
        """
        backtest = Backtest(
            name=name,
            backtest_type=backtest_type,
            status="DRAFT",
            metadata=metadata,
        )
        self.session.add(backtest)
        self.session.commit()
        self.session.refresh(backtest)
        return backtest

    def get_backtest(self, backtest_id: int) -> Optional[Backtest]:
        """Get a backtest by ID."""
        return self.session.exec(
            select(Backtest).where(Backtest.id == backtest_id)
        ).first()

    def get_backtest_by_name(self, name: str) -> Optional[Backtest]:
        """Get a backtest by name."""
        return self.session.exec(
            select(Backtest).where(Backtest.name == name)
        ).first()

    def list_backtests(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Backtest]:
        """
        List backtests with optional filtering.

        Args:
            status: Optional filter by status
            limit: Number of results to return
            offset: Number of results to skip

        Returns:
            List of Backtest objects
        """
        query = select(Backtest).order_by(Backtest.created_at.desc())

        if status:
            query = query.where(Backtest.status == status)

        query = query.limit(limit).offset(offset)
        return self.session.exec(query).all()

    def update_backtest_status(
        self,
        backtest_id: int,
        status: str,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ) -> Optional[Backtest]:
        """
        Update backtest status.

        Args:
            backtest_id: ID of backtest
            status: New status
            error_message: Optional error message
            completed_at: Optional completion timestamp

        Returns:
            Updated Backtest or None if not found
        """
        backtest = self.get_backtest(backtest_id)
        if not backtest:
            return None

        backtest.status = status
        backtest.updated_at = datetime.now(timezone.utc)

        if error_message:
            backtest.error_message = error_message

        if completed_at:
            backtest.completed_at = completed_at

        self.session.add(backtest)
        self.session.commit()
        self.session.refresh(backtest)
        return backtest

    def create_configuration(
        self,
        backtest_id: int,
        start_date: date,
        end_date: date,
        rebalance_frequency: str = "monthly",
        universe_selection: str = "sp500",
        commission_bps: Decimal = Decimal("5.0"),
        slippage_bps: Decimal = Decimal("2.0"),
        benchmark_ticker: str = "SPY",
        rolling_window_months: int = 60,
    ) -> BacktestConfiguration:
        """
        Create backtest configuration.

        Args:
            backtest_id: Parent backtest ID
            start_date: Start date of backtest
            end_date: End date of backtest
            rebalance_frequency: Rebalancing frequency
            universe_selection: Universe selection method
            commission_bps: Commission in basis points
            slippage_bps: Slippage in basis points
            benchmark_ticker: Benchmark ticker
            rolling_window_months: Rolling window size

        Returns:
            Created BacktestConfiguration
        """
        config = BacktestConfiguration(
            backtest_id=backtest_id,
            start_date=start_date,
            end_date=end_date,
            rebalance_frequency=rebalance_frequency,
            universe_selection=universe_selection,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            benchmark_ticker=benchmark_ticker,
            rolling_window_months=rolling_window_months,
        )
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    def get_configuration(self, backtest_id: int) -> Optional[BacktestConfiguration]:
        """Get configuration for a backtest."""
        return self.session.exec(
            select(BacktestConfiguration).where(
                BacktestConfiguration.backtest_id == backtest_id
            )
        ).first()

    def add_factor_allocation(
        self,
        backtest_id: int,
        factor_id: int,
        weight: Decimal,
    ) -> BacktestFactorAllocation:
        """
        Add a factor allocation to a backtest.

        Args:
            backtest_id: Parent backtest ID
            factor_id: Factor ID
            weight: Weight of factor (0-1)

        Returns:
            Created BacktestFactorAllocation
        """
        allocation = BacktestFactorAllocation(
            backtest_id=backtest_id,
            factor_id=factor_id,
            weight=weight,
        )
        self.session.add(allocation)
        self.session.commit()
        self.session.refresh(allocation)
        return allocation

    def get_factor_allocations(self, backtest_id: int) -> List[BacktestFactorAllocation]:
        """Get all factor allocations for a backtest."""
        return self.session.exec(
            select(BacktestFactorAllocation).where(
                BacktestFactorAllocation.backtest_id == backtest_id
            )
        ).all()

    def save_results(
        self,
        backtest_id: int,
        results: List[BacktestResult],
    ) -> None:
        """
        Save daily backtest results using bulk insert.

        Args:
            backtest_id: Parent backtest ID
            results: List of BacktestResult objects
        """
        if not results:
            return

        # Set backtest_id on all results
        for result in results:
            result.backtest_id = backtest_id

        # Use add_all for bulk insert instead of loop
        self.session.add_all(results)
        self.session.commit()

    def get_results(
        self,
        backtest_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[BacktestResult]:
        """
        Get backtest results for a date range.

        Args:
            backtest_id: Backtest ID
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            List of BacktestResult objects
        """
        query = select(BacktestResult).where(
            BacktestResult.backtest_id == backtest_id
        )

        if start_date:
            query = query.where(BacktestResult.date >= start_date)

        if end_date:
            query = query.where(BacktestResult.date <= end_date)

        query = query.order_by(BacktestResult.date.asc())
        return self.session.exec(query).all()

    def save_statistics(
        self,
        backtest_id: int,
        statistics: List[BacktestStatistic],
    ) -> None:
        """
        Save backtest statistics using bulk insert.

        Args:
            backtest_id: Parent backtest ID
            statistics: List of BacktestStatistic objects
        """
        if not statistics:
            return

        # Set backtest_id on all statistics
        for stat in statistics:
            stat.backtest_id = backtest_id

        # Use add_all for bulk insert
        self.session.add_all(statistics)
        self.session.commit()

    def get_statistics(
        self,
        backtest_id: int,
        metric_name: Optional[str] = None,
    ) -> List[BacktestStatistic]:
        """
        Get backtest statistics.

        Args:
            backtest_id: Backtest ID
            metric_name: Optional filter by metric name

        Returns:
            List of BacktestStatistic objects
        """
        query = select(BacktestStatistic).where(
            BacktestStatistic.backtest_id == backtest_id
        )

        if metric_name:
            query = query.where(BacktestStatistic.metric_name == metric_name)

        return self.session.exec(query).all()

    def get_statistic(
        self,
        backtest_id: int,
        metric_name: str,
    ) -> Optional[BacktestStatistic]:
        """Get a single statistic metric."""
        return self.session.exec(
            select(BacktestStatistic).where(
                BacktestStatistic.backtest_id == backtest_id,
                BacktestStatistic.metric_name == metric_name,
            )
        ).first()

    def save_factor_correlations(
        self,
        backtest_id: int,
        correlations: List[FactorCorrelation],
    ) -> None:
        """
        Save factor correlations using bulk insert.

        Args:
            backtest_id: Parent backtest ID
            correlations: List of FactorCorrelation objects
        """
        if not correlations:
            return

        # Set backtest_id on all correlations
        for corr in correlations:
            corr.backtest_id = backtest_id

        # Use add_all for bulk insert
        self.session.add_all(correlations)
        self.session.commit()

    def get_factor_correlations(
        self,
        backtest_id: int,
        as_of_date: Optional[date] = None,
    ) -> List[FactorCorrelation]:
        """
        Get factor correlations for a backtest.

        Args:
            backtest_id: Backtest ID
            as_of_date: Optional filter by date

        Returns:
            List of FactorCorrelation objects
        """
        query = select(FactorCorrelation).where(
            FactorCorrelation.backtest_id == backtest_id
        )

        if as_of_date:
            query = query.where(FactorCorrelation.as_of_date == as_of_date)

        return self.session.exec(query).all()

    def save_alpha_decay_analysis(
        self,
        analyses: List[AlphaDecayAnalysis],
    ) -> None:
        """
        Save alpha decay analysis results using bulk insert.

        Args:
            analyses: List of AlphaDecayAnalysis objects
        """
        if not analyses:
            return

        # Use add_all for bulk insert
        self.session.add_all(analyses)
        self.session.commit()

    def get_alpha_decay_analysis(
        self,
        factor_id: Optional[int] = None,
        backtest_id: Optional[int] = None,
    ) -> List[AlphaDecayAnalysis]:
        """
        Get alpha decay analysis.

        Args:
            factor_id: Optional filter by factor
            backtest_id: Optional filter by backtest

        Returns:
            List of AlphaDecayAnalysis objects
        """
        query = select(AlphaDecayAnalysis)

        if factor_id:
            query = query.where(AlphaDecayAnalysis.factor_id == factor_id)

        if backtest_id:
            query = query.where(AlphaDecayAnalysis.backtest_id == backtest_id)

        return self.session.exec(query).all()
