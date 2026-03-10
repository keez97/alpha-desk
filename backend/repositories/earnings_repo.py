"""
Repository for Earnings Surprise Predictor CRUD operations and queries.

Provides database access layer for earnings estimates, actuals, SmartEstimate weights,
analyst scorecards, PEAD measurements, and earnings signals.
"""

from datetime import datetime, date, timezone, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal
from sqlmodel import Session, select
from backend.models.earnings import (
    EarningsEstimate,
    EarningsActual,
    SmartEstimateWeights,
    AnalystScorecard,
    PEADMeasurement,
    EarningsSignal,
)


class EarningsRepository:
    """Repository for earnings-related database operations."""

    def __init__(self, session: Session):
        self.session = session

    # ==================== Earnings Estimate CRUD ====================

    def save_estimate(
        self,
        ticker: str,
        fiscal_quarter: str,
        estimate_type: str,
        eps_estimate: Decimal,
        estimate_date: datetime,
        analyst_broker: Optional[str] = None,
        revision_number: int = 0,
    ) -> EarningsEstimate:
        """
        Save an earnings estimate.

        Args:
            ticker: Security ticker
            fiscal_quarter: Format 'YYYYQ#' (e.g., '2025Q4')
            estimate_type: 'consensus', 'smart_estimate', or 'individual'
            eps_estimate: EPS estimate value
            estimate_date: When estimate was published (PiT timestamp)
            analyst_broker: Analyst/broker name (null for consensus/smart_estimate)
            revision_number: Revision count

        Returns:
            Created EarningsEstimate object
        """
        estimate = EarningsEstimate(
            ticker=ticker,
            fiscal_quarter=fiscal_quarter,
            estimate_type=estimate_type,
            eps_estimate=eps_estimate,
            estimate_date=estimate_date,
            analyst_broker=analyst_broker,
            revision_number=revision_number,
        )
        self.session.add(estimate)
        self.session.commit()
        self.session.refresh(estimate)
        return estimate

    def get_estimates(
        self,
        ticker: str,
        fiscal_quarter: str,
        estimate_type: Optional[str] = None,
    ) -> List[EarningsEstimate]:
        """
        Get all estimates for a ticker and quarter.

        Args:
            ticker: Security ticker
            fiscal_quarter: Format 'YYYYQ#'
            estimate_type: Optional filter ('consensus', 'smart_estimate', 'individual')

        Returns:
            List of EarningsEstimate objects, ordered by estimate_date DESC
        """
        query = select(EarningsEstimate).where(
            EarningsEstimate.ticker == ticker,
            EarningsEstimate.fiscal_quarter == fiscal_quarter,
        ).order_by(EarningsEstimate.estimate_date.desc())

        if estimate_type:
            query = query.where(EarningsEstimate.estimate_type == estimate_type)

        return self.session.exec(query).all()

    def get_latest_consensus(self, ticker: str, fiscal_quarter: str) -> Optional[EarningsEstimate]:
        """
        Get the most recent consensus estimate for a ticker and quarter.

        Args:
            ticker: Security ticker
            fiscal_quarter: Format 'YYYYQ#'

        Returns:
            Most recent consensus EarningsEstimate or None
        """
        query = select(EarningsEstimate).where(
            EarningsEstimate.ticker == ticker,
            EarningsEstimate.fiscal_quarter == fiscal_quarter,
            EarningsEstimate.estimate_type == "consensus",
        ).order_by(EarningsEstimate.estimate_date.desc())

        return self.session.exec(query).first()

    # ==================== Earnings Actual CRUD ====================

    def save_actual(
        self,
        ticker: str,
        fiscal_quarter: str,
        actual_eps: Decimal,
        report_date: date,
        report_time: Optional[str] = None,
        surprise_vs_consensus: Optional[Decimal] = None,
        surprise_vs_smart: Optional[Decimal] = None,
        source: str = "yfinance",
    ) -> EarningsActual:
        """
        Save actual reported earnings.

        Args:
            ticker: Security ticker
            fiscal_quarter: Format 'YYYYQ#'
            actual_eps: Actual reported EPS
            report_date: Date of earnings announcement
            report_time: 'pre_market', 'post_market', or 'during'
            surprise_vs_consensus: Surprise % vs consensus
            surprise_vs_smart: Surprise % vs smart estimate
            source: Data source ('yfinance' or 'sec_edgar')

        Returns:
            Created EarningsActual object
        """
        actual = EarningsActual(
            ticker=ticker,
            fiscal_quarter=fiscal_quarter,
            actual_eps=actual_eps,
            report_date=report_date,
            report_time=report_time,
            surprise_vs_consensus=surprise_vs_consensus,
            surprise_vs_smart=surprise_vs_smart,
            source=source,
        )
        self.session.add(actual)
        self.session.commit()
        self.session.refresh(actual)
        return actual

    def get_actual(
        self,
        ticker: str,
        fiscal_quarter: str,
    ) -> Optional[EarningsActual]:
        """
        Get actual earnings for a ticker and quarter.

        Args:
            ticker: Security ticker
            fiscal_quarter: Format 'YYYYQ#'

        Returns:
            EarningsActual object or None
        """
        query = select(EarningsActual).where(
            EarningsActual.ticker == ticker,
            EarningsActual.fiscal_quarter == fiscal_quarter,
        )
        return self.session.exec(query).first()

    def get_actuals_history(
        self,
        ticker: str,
        n_quarters: int = 8,
    ) -> List[EarningsActual]:
        """
        Get historical actuals for a ticker (last N quarters).

        Args:
            ticker: Security ticker
            n_quarters: Number of quarters to retrieve (default 8)

        Returns:
            List of EarningsActual objects ordered by report_date DESC
        """
        query = select(EarningsActual).where(
            EarningsActual.ticker == ticker,
        ).order_by(EarningsActual.report_date.desc()).limit(n_quarters)

        return self.session.exec(query).all()

    # ==================== SmartEstimate Weights CRUD ====================

    def save_smart_estimate_weights(
        self,
        weight_type: str,
        parameter_name: str,
        parameter_value: Decimal,
        description: Optional[str] = None,
    ) -> SmartEstimateWeights:
        """
        Save or update SmartEstimate weight configuration.

        Args:
            weight_type: 'recency_decay', 'accuracy_tier', or 'broker_size'
            parameter_name: Parameter name (e.g., 'half_life_days')
            parameter_value: Decimal value
            description: Human-readable description

        Returns:
            Created/Updated SmartEstimateWeights object
        """
        # Try to find existing
        existing = self.session.exec(
            select(SmartEstimateWeights).where(
                SmartEstimateWeights.weight_type == weight_type,
                SmartEstimateWeights.parameter_name == parameter_name,
            )
        ).first()

        if existing:
            existing.parameter_value = parameter_value
            existing.description = description
            existing.updated_at = datetime.now(timezone.utc)
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return existing

        weights = SmartEstimateWeights(
            weight_type=weight_type,
            parameter_name=parameter_name,
            parameter_value=parameter_value,
            description=description,
        )
        self.session.add(weights)
        self.session.commit()
        self.session.refresh(weights)
        return weights

    def get_weights(self, weight_type: Optional[str] = None) -> List[SmartEstimateWeights]:
        """
        Get SmartEstimate weight configurations.

        Args:
            weight_type: Optional filter by weight type

        Returns:
            List of SmartEstimateWeights objects
        """
        query = select(SmartEstimateWeights)

        if weight_type:
            query = query.where(SmartEstimateWeights.weight_type == weight_type)

        return self.session.exec(query).all()

    # ==================== Analyst Scorecard CRUD ====================

    def save_analyst_scorecard(
        self,
        analyst_broker: str,
        total_estimates: int,
        accurate_count: int,
        directional_accuracy: Optional[Decimal] = None,
        avg_error_pct: Optional[Decimal] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        ticker: Optional[str] = None,
    ) -> AnalystScorecard:
        """
        Save analyst accuracy scorecard.

        Args:
            analyst_broker: Analyst/broker name
            total_estimates: Total estimates evaluated
            accurate_count: Count within ±5% of actual
            directional_accuracy: Percentage correct direction (0-100)
            avg_error_pct: Average absolute error %
            period_start: Start date of evaluation period
            period_end: End date of evaluation period
            ticker: Specific ticker (null for aggregate)

        Returns:
            Created AnalystScorecard object
        """
        if period_start is None:
            period_start = date.today() - timedelta(days=365)
        if period_end is None:
            period_end = date.today()

        scorecard = AnalystScorecard(
            analyst_broker=analyst_broker,
            ticker=ticker,
            total_estimates=total_estimates,
            accurate_count=accurate_count,
            directional_accuracy=directional_accuracy,
            avg_error_pct=avg_error_pct,
            last_evaluated=datetime.now(timezone.utc),
            period_start=period_start,
            period_end=period_end,
        )
        self.session.add(scorecard)
        self.session.commit()
        self.session.refresh(scorecard)
        return scorecard

    def get_scorecards(
        self,
        broker: Optional[str] = None,
        ticker: Optional[str] = None,
    ) -> List[AnalystScorecard]:
        """
        Get analyst scorecards.

        Args:
            broker: Optional filter by broker name
            ticker: Optional filter by ticker

        Returns:
            List of AnalystScorecard objects ordered by avg_error_pct ASC
        """
        query = select(AnalystScorecard).order_by(AnalystScorecard.avg_error_pct.asc())

        if broker:
            query = query.where(AnalystScorecard.analyst_broker == broker)

        if ticker:
            query = query.where(AnalystScorecard.ticker == ticker)

        return self.session.exec(query).all()

    # ==================== PEAD Measurement CRUD ====================

    def save_pead_measurement(
        self,
        ticker: str,
        fiscal_quarter: str,
        earnings_date: date,
        surprise_direction: str,
        surprise_magnitude: Decimal,
        car_1d: Optional[Decimal] = None,
        car_5d: Optional[Decimal] = None,
        car_21d: Optional[Decimal] = None,
        car_60d: Optional[Decimal] = None,
        benchmark_ticker: Optional[str] = None,
        measured_at: Optional[datetime] = None,
    ) -> PEADMeasurement:
        """
        Save PEAD measurement.

        Args:
            ticker: Security ticker
            fiscal_quarter: Format 'YYYYQ#'
            earnings_date: Date of earnings announcement
            surprise_direction: 'positive', 'negative', or 'inline'
            surprise_magnitude: Magnitude of surprise %
            car_1d: Cumulative abnormal return at 1 day
            car_5d: CAR at 5 trading days
            car_21d: CAR at 21 trading days
            car_60d: CAR at 60 trading days
            benchmark_ticker: Benchmark ticker (default SPY)
            measured_at: When measured (default now)

        Returns:
            Created PEADMeasurement object
        """
        if measured_at is None:
            measured_at = datetime.now(timezone.utc)

        if benchmark_ticker is None:
            benchmark_ticker = "SPY"

        pead = PEADMeasurement(
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
            measured_at=measured_at,
        )
        self.session.add(pead)
        self.session.commit()
        self.session.refresh(pead)
        return pead

    def get_pead(
        self,
        ticker: str,
        fiscal_quarter: str,
    ) -> Optional[PEADMeasurement]:
        """
        Get PEAD measurement for a ticker and quarter.

        Args:
            ticker: Security ticker
            fiscal_quarter: Format 'YYYYQ#'

        Returns:
            PEADMeasurement object or None
        """
        query = select(PEADMeasurement).where(
            PEADMeasurement.ticker == ticker,
            PEADMeasurement.fiscal_quarter == fiscal_quarter,
        ).order_by(PEADMeasurement.measured_at.desc())

        return self.session.exec(query).first()

    def get_pead_aggregate(
        self,
        surprise_direction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Aggregate PEAD statistics across all measurements.

        Args:
            surprise_direction: Optional filter ('positive', 'negative', 'inline')

        Returns:
            Dictionary with aggregated PEAD statistics
        """
        query = select(PEADMeasurement)

        if surprise_direction:
            query = query.where(PEADMeasurement.surprise_direction == surprise_direction)

        measurements = self.session.exec(query).all()

        if not measurements:
            return {
                "count": 0,
                "car_1d_avg": None,
                "car_5d_avg": None,
                "car_21d_avg": None,
                "car_60d_avg": None,
            }

        car_1d_values = [m.car_1d for m in measurements if m.car_1d is not None]
        car_5d_values = [m.car_5d for m in measurements if m.car_5d is not None]
        car_21d_values = [m.car_21d for m in measurements if m.car_21d is not None]
        car_60d_values = [m.car_60d for m in measurements if m.car_60d is not None]

        return {
            "count": len(measurements),
            "car_1d_avg": sum(car_1d_values) / len(car_1d_values) if car_1d_values else None,
            "car_5d_avg": sum(car_5d_values) / len(car_5d_values) if car_5d_values else None,
            "car_21d_avg": sum(car_21d_values) / len(car_21d_values) if car_21d_values else None,
            "car_60d_avg": sum(car_60d_values) / len(car_60d_values) if car_60d_values else None,
        }

    # ==================== Earnings Signal CRUD ====================

    def save_signal(
        self,
        ticker: str,
        fiscal_quarter: str,
        signal_date: datetime,
        signal_type: str,
        confidence: int,
        smart_estimate_eps: Decimal,
        consensus_eps: Decimal,
        divergence_pct: Decimal,
        days_to_earnings: int,
        valid_until: datetime,
    ) -> EarningsSignal:
        """
        Save an earnings signal.

        Args:
            ticker: Security ticker
            fiscal_quarter: Format 'YYYYQ#'
            signal_date: When signal was generated (PiT timestamp)
            signal_type: 'buy', 'sell', or 'hold'
            confidence: Confidence level (0-100)
            smart_estimate_eps: SmartEstimate EPS
            consensus_eps: Consensus EPS
            divergence_pct: Divergence %
            days_to_earnings: Days until earnings
            valid_until: Signal validity window end

        Returns:
            Created EarningsSignal object
        """
        signal = EarningsSignal(
            ticker=ticker,
            fiscal_quarter=fiscal_quarter,
            signal_date=signal_date,
            signal_type=signal_type,
            confidence=confidence,
            smart_estimate_eps=smart_estimate_eps,
            consensus_eps=consensus_eps,
            divergence_pct=divergence_pct,
            days_to_earnings=days_to_earnings,
            valid_until=valid_until,
        )
        self.session.add(signal)
        self.session.commit()
        self.session.refresh(signal)
        return signal

    def get_signal(self, ticker: str, fiscal_quarter: str) -> Optional[EarningsSignal]:
        """
        Get the most recent signal for a ticker and quarter.

        Args:
            ticker: Security ticker
            fiscal_quarter: Format 'YYYYQ#'

        Returns:
            EarningsSignal object or None
        """
        query = select(EarningsSignal).where(
            EarningsSignal.ticker == ticker,
            EarningsSignal.fiscal_quarter == fiscal_quarter,
        ).order_by(EarningsSignal.signal_date.desc())

        return self.session.exec(query).first()

    def get_active_signals(
        self,
        days_to_earnings_max: int = 5,
    ) -> List[EarningsSignal]:
        """
        Get active signals (upcoming earnings within N days).

        Args:
            days_to_earnings_max: Maximum days to earnings (default 5)

        Returns:
            List of EarningsSignal objects ordered by days_to_earnings ASC
        """
        query = select(EarningsSignal).where(
            EarningsSignal.days_to_earnings <= days_to_earnings_max,
            EarningsSignal.days_to_earnings >= 0,
        ).order_by(EarningsSignal.days_to_earnings.asc())

        return self.session.exec(query).all()

    # ==================== Earnings Calendar ====================

    def get_earnings_calendar(
        self,
        days_ahead: int = 30,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming earnings with latest estimates.

        Args:
            days_ahead: Days ahead to look (default 30)
            limit: Number of results
            offset: Pagination offset

        Returns:
            List of dicts with earnings calendar data
        """
        # Get upcoming actuals (not reported yet)
        from datetime import date
        today = date.today()
        future_date = today + timedelta(days=days_ahead)

        # Get unique tickers with upcoming earnings
        query = select(EarningsActual).where(
            EarningsActual.report_date >= today,
            EarningsActual.report_date <= future_date,
        ).order_by(EarningsActual.report_date.asc()).limit(limit).offset(offset)

        actuals = self.session.exec(query).all()

        result = []
        for actual in actuals:
            # Get latest estimates for this quarter
            consensus = self.get_latest_consensus(actual.ticker, actual.fiscal_quarter)
            signal = self.get_signal(actual.ticker, actual.fiscal_quarter)

            days_to_earnings = (actual.report_date - today).days

            result.append({
                "ticker": actual.ticker,
                "earnings_date": actual.report_date.isoformat(),
                "fiscal_quarter": actual.fiscal_quarter,
                "consensus_eps": float(consensus.eps_estimate) if consensus else None,
                "smart_estimate_eps": float(signal.smart_estimate_eps) if signal else None,
                "divergence_pct": float(signal.divergence_pct) if signal else None,
                "signal": signal.signal_type if signal else None,
                "confidence": signal.confidence if signal else None,
                "days_to_earnings": days_to_earnings,
            })

        return result
