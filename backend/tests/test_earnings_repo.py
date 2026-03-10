"""
Tests for Earnings Repository.

Tests CRUD operations for estimates, actuals, weights, scorecards, PEAD, signals,
filtering, and unique constraint handling.
"""

import pytest
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from backend.repositories.earnings_repo import EarningsRepository
from backend.models.earnings import (
    EarningsEstimate,
    EarningsActual,
    SmartEstimateWeights,
    AnalystScorecard,
    PEADMeasurement,
    EarningsSignal,
)


class TestEarningsEstimateCRUD:
    """Test CRUD operations for earnings estimates."""

    def test_save_estimate(self, session: Session):
        """Test saving an earnings estimate."""
        repo = EarningsRepository(session)

        estimate = repo.save_estimate(
            ticker="AAPL",
            fiscal_quarter="2025Q1",
            estimate_type="consensus",
            eps_estimate=Decimal("5.50"),
            estimate_date=datetime.now(timezone.utc),
            analyst_broker=None,
        )

        assert estimate.id is not None
        assert estimate.ticker == "AAPL"
        assert estimate.fiscal_quarter == "2025Q1"
        assert estimate.estimate_type == "consensus"
        assert estimate.eps_estimate == Decimal("5.50")

    def test_save_multiple_estimates(self, session: Session):
        """Test saving multiple estimates for same quarter."""
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        est1 = repo.save_estimate(
            ticker="MSFT",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("2.50"),
            estimate_date=now,
            analyst_broker="Analyst1",
        )

        est2 = repo.save_estimate(
            ticker="MSFT",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("2.60"),
            estimate_date=now - timedelta(days=5),
            analyst_broker="Analyst2",
        )

        assert est1.id != est2.id

    def test_get_estimates(self, session: Session):
        """Test retrieving estimates."""
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        repo.save_estimate(
            ticker="GOOGL",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("1.80"),
            estimate_date=now,
            analyst_broker="Analyst",
        )

        estimates = repo.get_estimates("GOOGL", "2025Q1")

        assert len(estimates) == 1
        assert estimates[0].eps_estimate == Decimal("1.80")

    def test_get_estimates_filtered_by_type(self, session: Session):
        """Test filtering estimates by type."""
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        repo.save_estimate(
            ticker="TSLA",
            fiscal_quarter="2025Q1",
            estimate_type="consensus",
            eps_estimate=Decimal("0.75"),
            estimate_date=now,
        )

        repo.save_estimate(
            ticker="TSLA",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("0.80"),
            estimate_date=now,
            analyst_broker="Analyst",
        )

        consensus = repo.get_estimates("TSLA", "2025Q1", estimate_type="consensus")
        individual = repo.get_estimates("TSLA", "2025Q1", estimate_type="individual")

        assert len(consensus) == 1
        assert len(individual) == 1

    def test_get_latest_consensus(self, session: Session):
        """Test retrieving latest consensus estimate."""
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        # Old consensus
        repo.save_estimate(
            ticker="AMZN",
            fiscal_quarter="2025Q1",
            estimate_type="consensus",
            eps_estimate=Decimal("3.00"),
            estimate_date=now - timedelta(days=10),
        )

        # New consensus
        latest = repo.save_estimate(
            ticker="AMZN",
            fiscal_quarter="2025Q1",
            estimate_type="consensus",
            eps_estimate=Decimal("3.10"),
            estimate_date=now,
        )

        result = repo.get_latest_consensus("AMZN", "2025Q1")

        assert result.id == latest.id
        assert result.eps_estimate == Decimal("3.10")

    def test_estimate_unique_constraint(self, session: Session):
        """Test unique constraint on (ticker, quarter, type, broker, date)."""
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        # First estimate
        repo.save_estimate(
            ticker="META",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("5.00"),
            estimate_date=now,
            analyst_broker="Analyst1",
        )

        # Duplicate should fail (same date)
        with pytest.raises(IntegrityError):
            repo.save_estimate(
                ticker="META",
                fiscal_quarter="2025Q1",
                estimate_type="individual",
                eps_estimate=Decimal("5.10"),
                estimate_date=now,
                analyst_broker="Analyst1",
            )
            session.commit()


class TestEarningsActualCRUD:
    """Test CRUD operations for actual earnings."""

    def test_save_actual(self, session: Session):
        """Test saving actual earnings."""
        repo = EarningsRepository(session)

        actual = repo.save_actual(
            ticker="AAPL",
            fiscal_quarter="2025Q1",
            actual_eps=Decimal("5.61"),
            report_date=date(2025, 1, 30),
            surprise_vs_consensus=Decimal("1.8"),
            source="yfinance",
        )

        assert actual.id is not None
        assert actual.ticker == "AAPL"
        assert actual.actual_eps == Decimal("5.61")

    def test_get_actual(self, session: Session):
        """Test retrieving actual earnings."""
        repo = EarningsRepository(session)

        repo.save_actual(
            ticker="MSFT",
            fiscal_quarter="2025Q1",
            actual_eps=Decimal("2.93"),
            report_date=date(2025, 1, 28),
            source="yfinance",
        )

        actual = repo.get_actual("MSFT", "2025Q1")

        assert actual is not None
        assert actual.actual_eps == Decimal("2.93")

    def test_get_actuals_history(self, session: Session):
        """Test retrieving historical actuals."""
        repo = EarningsRepository(session)

        # Create 4 quarters of actuals
        for i in range(4):
            repo.save_actual(
                ticker="GOOGL",
                fiscal_quarter=f"2024Q{i+1}",
                actual_eps=Decimal(str(1.80 + i * 0.1)),
                report_date=date(2024, 1, 15) + timedelta(days=90*i),
                source="yfinance",
            )

        history = repo.get_actuals_history("GOOGL", n_quarters=4)

        assert len(history) == 4
        # Should be ordered by report_date DESC
        assert history[0].report_date > history[-1].report_date

    def test_actual_unique_constraint(self, session: Session):
        """Test unique constraint on (ticker, quarter, report_date)."""
        repo = EarningsRepository(session)

        report_date = date(2025, 1, 30)

        # First actual
        repo.save_actual(
            ticker="TSLA",
            fiscal_quarter="2025Q1",
            actual_eps=Decimal("0.87"),
            report_date=report_date,
            source="yfinance",
        )

        # Duplicate should fail
        with pytest.raises(IntegrityError):
            repo.save_actual(
                ticker="TSLA",
                fiscal_quarter="2025Q1",
                actual_eps=Decimal("0.88"),
                report_date=report_date,
                source="yfinance",
            )
            session.commit()


class TestSmartEstimateWeightsCRUD:
    """Test CRUD operations for SmartEstimate weights."""

    def test_save_weights(self, session: Session):
        """Test saving weight configuration."""
        repo = EarningsRepository(session)

        weights = repo.save_smart_estimate_weights(
            weight_type="recency_decay",
            parameter_name="half_life_days",
            parameter_value=Decimal("30"),
            description="30-day half-life for recency decay",
        )

        assert weights.id is not None
        assert weights.weight_type == "recency_decay"
        assert weights.parameter_value == Decimal("30")

    def test_update_weights(self, session: Session):
        """Test updating existing weights."""
        repo = EarningsRepository(session)

        # Save initial
        repo.save_smart_estimate_weights(
            weight_type="accuracy_tier",
            parameter_name="tier_a_weight",
            parameter_value=Decimal("1.5"),
        )

        # Update
        updated = repo.save_smart_estimate_weights(
            weight_type="accuracy_tier",
            parameter_name="tier_a_weight",
            parameter_value=Decimal("2.0"),
        )

        assert updated.parameter_value == Decimal("2.0")

    def test_get_weights(self, session: Session):
        """Test retrieving weights."""
        repo = EarningsRepository(session)

        repo.save_smart_estimate_weights(
            weight_type="recency_decay",
            parameter_name="half_life_days",
            parameter_value=Decimal("30"),
        )

        weights = repo.get_weights(weight_type="recency_decay")

        assert len(weights) == 1
        assert weights[0].parameter_value == Decimal("30")


class TestAnalystScorecardCRUD:
    """Test CRUD operations for analyst scorecards."""

    def test_save_scorecard(self, session: Session):
        """Test saving analyst scorecard."""
        repo = EarningsRepository(session)

        scorecard = repo.save_analyst_scorecard(
            analyst_broker="Goldman Sachs",
            ticker="AAPL",
            total_estimates=100,
            accurate_count=95,
            avg_error_pct=Decimal("2.5"),
            directional_accuracy=Decimal("92.0"),
        )

        assert scorecard.id is not None
        assert scorecard.analyst_broker == "Goldman Sachs"
        assert scorecard.avg_error_pct == Decimal("2.5")

    def test_get_scorecards(self, session: Session):
        """Test retrieving scorecards."""
        repo = EarningsRepository(session)

        repo.save_analyst_scorecard(
            analyst_broker="JP Morgan",
            ticker="MSFT",
            total_estimates=50,
            accurate_count=45,
            avg_error_pct=Decimal("3.0"),
        )

        scorecards = repo.get_scorecards(broker="JP Morgan")

        assert len(scorecards) == 1
        assert scorecards[0].analyst_broker == "JP Morgan"

    def test_get_scorecards_by_ticker(self, session: Session):
        """Test filtering scorecards by ticker."""
        repo = EarningsRepository(session)

        repo.save_analyst_scorecard(
            analyst_broker="Analyst1",
            ticker="AAPL",
            total_estimates=20,
            accurate_count=18,
            avg_error_pct=Decimal("2.0"),
        )

        repo.save_analyst_scorecard(
            analyst_broker="Analyst1",
            ticker="MSFT",
            total_estimates=25,
            accurate_count=20,
            avg_error_pct=Decimal("3.5"),
        )

        aapl_scorecards = repo.get_scorecards(broker="Analyst1", ticker="AAPL")

        assert len(aapl_scorecards) == 1
        assert aapl_scorecards[0].ticker == "AAPL"


class TestPEADMeasurementCRUD:
    """Test CRUD operations for PEAD measurements."""

    def test_save_pead_measurement(self, session: Session):
        """Test saving PEAD measurement."""
        repo = EarningsRepository(session)

        pead = repo.save_pead_measurement(
            ticker="AAPL",
            fiscal_quarter="2025Q1",
            earnings_date=date(2025, 1, 30),
            surprise_direction="positive",
            surprise_magnitude=Decimal("2.5"),
            car_1d=Decimal("0.75"),
            car_5d=Decimal("1.50"),
            car_21d=Decimal("3.20"),
            car_60d=Decimal("5.10"),
        )

        assert pead.id is not None
        assert pead.surprise_direction == "positive"
        assert pead.car_1d == Decimal("0.75")

    def test_get_pead(self, session: Session):
        """Test retrieving PEAD measurement."""
        repo = EarningsRepository(session)

        repo.save_pead_measurement(
            ticker="MSFT",
            fiscal_quarter="2025Q1",
            earnings_date=date(2025, 1, 28),
            surprise_direction="negative",
            surprise_magnitude=Decimal("-1.5"),
            car_1d=Decimal("-0.50"),
        )

        pead = repo.get_pead("MSFT", "2025Q1")

        assert pead is not None
        assert pead.surprise_direction == "negative"

    def test_get_pead_aggregate(self, session: Session):
        """Test PEAD aggregation."""
        repo = EarningsRepository(session)

        # Create positive PEAD
        repo.save_pead_measurement(
            ticker="POS1",
            fiscal_quarter="2025Q1",
            earnings_date=date(2025, 1, 30),
            surprise_direction="positive",
            surprise_magnitude=Decimal("2.0"),
            car_1d=Decimal("0.5"),
            car_5d=Decimal("1.0"),
        )

        repo.save_pead_measurement(
            ticker="POS2",
            fiscal_quarter="2025Q1",
            earnings_date=date(2025, 1, 30),
            surprise_direction="positive",
            surprise_magnitude=Decimal("3.0"),
            car_1d=Decimal("1.0"),
            car_5d=Decimal("2.0"),
        )

        # Create negative PEAD
        repo.save_pead_measurement(
            ticker="NEG1",
            fiscal_quarter="2025Q1",
            earnings_date=date(2025, 1, 30),
            surprise_direction="negative",
            surprise_magnitude=Decimal("-1.5"),
            car_1d=Decimal("-0.5"),
            car_5d=Decimal("-1.0"),
        )

        # Aggregate all
        all_agg = repo.get_pead_aggregate()
        assert all_agg["count"] == 3

        # Aggregate positive only
        pos_agg = repo.get_pead_aggregate(surprise_direction="positive")
        assert pos_agg["count"] == 2

        # Aggregate negative only
        neg_agg = repo.get_pead_aggregate(surprise_direction="negative")
        assert neg_agg["count"] == 1


class TestEarningsSignalCRUD:
    """Test CRUD operations for earnings signals."""

    def test_save_signal(self, session: Session):
        """Test saving earnings signal."""
        repo = EarningsRepository(session)

        signal = repo.save_signal(
            ticker="AAPL",
            fiscal_quarter="2025Q1",
            signal_date=datetime.now(timezone.utc),
            signal_type="buy",
            confidence=75,
            smart_estimate_eps=Decimal("5.60"),
            consensus_eps=Decimal("5.50"),
            divergence_pct=Decimal("1.82"),
            days_to_earnings=5,
            valid_until=datetime.now(timezone.utc) + timedelta(days=5),
        )

        assert signal.id is not None
        assert signal.signal_type == "buy"
        assert signal.confidence == 75

    def test_get_signal(self, session: Session):
        """Test retrieving signal."""
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        repo.save_signal(
            ticker="MSFT",
            fiscal_quarter="2025Q1",
            signal_date=now,
            signal_type="sell",
            confidence=60,
            smart_estimate_eps=Decimal("2.80"),
            consensus_eps=Decimal("2.90"),
            divergence_pct=Decimal("-3.45"),
            days_to_earnings=3,
            valid_until=now + timedelta(days=3),
        )

        signal = repo.get_signal("MSFT", "2025Q1")

        assert signal is not None
        assert signal.signal_type == "sell"

    def test_get_active_signals(self, session: Session):
        """Test retrieving active signals."""
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        # Active signal (2 days to earnings)
        repo.save_signal(
            ticker="GOOGL",
            fiscal_quarter="2025Q1",
            signal_date=now,
            signal_type="hold",
            confidence=50,
            smart_estimate_eps=Decimal("1.95"),
            consensus_eps=Decimal("1.95"),
            divergence_pct=Decimal("0.0"),
            days_to_earnings=2,
            valid_until=now + timedelta(days=2),
        )

        # Future signal (20 days to earnings - not active)
        repo.save_signal(
            ticker="TSLA",
            fiscal_quarter="2025Q2",
            signal_date=now,
            signal_type="buy",
            confidence=70,
            smart_estimate_eps=Decimal("1.50"),
            consensus_eps=Decimal("1.40"),
            divergence_pct=Decimal("7.14"),
            days_to_earnings=20,
            valid_until=now + timedelta(days=20),
        )

        active = repo.get_active_signals(days_to_earnings_max=5)

        assert len(active) == 1
        assert active[0].ticker == "GOOGL"

    def test_signal_unique_constraint(self, session: Session):
        """Test unique constraint on (ticker, quarter, date)."""
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        # First signal
        repo.save_signal(
            ticker="META",
            fiscal_quarter="2025Q1",
            signal_date=now,
            signal_type="buy",
            confidence=75,
            smart_estimate_eps=Decimal("5.60"),
            consensus_eps=Decimal("5.50"),
            divergence_pct=Decimal("1.82"),
            days_to_earnings=5,
            valid_until=now + timedelta(days=5),
        )

        # Duplicate should fail (same date)
        with pytest.raises(IntegrityError):
            repo.save_signal(
                ticker="META",
                fiscal_quarter="2025Q1",
                signal_date=now,
                signal_type="sell",
                confidence=60,
                smart_estimate_eps=Decimal("5.50"),
                consensus_eps=Decimal("5.50"),
                divergence_pct=Decimal("0.0"),
                days_to_earnings=5,
                valid_until=now + timedelta(days=5),
            )
            session.commit()


class TestEarningsCalendar:
    """Test earnings calendar retrieval."""

    def test_get_earnings_calendar(self, session: Session):
        """Test retrieving earnings calendar."""
        repo = EarningsRepository(session)

        today = date.today()

        # Add future earnings
        repo.save_actual(
            ticker="AAPL",
            fiscal_quarter="2025Q1",
            actual_eps=Decimal("5.50"),
            report_date=today + timedelta(days=5),
            source="yfinance",
        )

        # Add past earnings (should not appear in calendar)
        repo.save_actual(
            ticker="MSFT",
            fiscal_quarter="2024Q4",
            actual_eps=Decimal("2.90"),
            report_date=today - timedelta(days=10),
            source="yfinance",
        )

        calendar = repo.get_earnings_calendar(days_ahead=30, limit=10)

        # Only AAPL should be in calendar
        assert len(calendar) >= 1
        assert any(item["ticker"] == "AAPL" for item in calendar)

    def test_earnings_calendar_with_signals(self, session: Session):
        """Test earnings calendar includes signal data."""
        repo = EarningsRepository(session)

        today = date.today()
        future_date = today + timedelta(days=10)
        now = datetime.now(timezone.utc)

        # Save actual
        repo.save_actual(
            ticker="GOOGL",
            fiscal_quarter="2025Q1",
            actual_eps=Decimal("1.95"),
            report_date=future_date,
            source="yfinance",
        )

        # Save consensus estimate
        repo.save_estimate(
            ticker="GOOGL",
            fiscal_quarter="2025Q1",
            estimate_type="consensus",
            eps_estimate=Decimal("1.90"),
            estimate_date=now,
        )

        # Save signal
        repo.save_signal(
            ticker="GOOGL",
            fiscal_quarter="2025Q1",
            signal_date=now,
            signal_type="buy",
            confidence=75,
            smart_estimate_eps=Decimal("1.98"),
            consensus_eps=Decimal("1.90"),
            divergence_pct=Decimal("4.21"),
            days_to_earnings=10,
            valid_until=now + timedelta(days=10),
        )

        calendar = repo.get_earnings_calendar(days_ahead=30)

        # Should have GOOGL with signal
        googl_entry = next((item for item in calendar if item["ticker"] == "GOOGL"), None)
        assert googl_entry is not None
        assert googl_entry["signal"] == "buy"
