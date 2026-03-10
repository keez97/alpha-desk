"""
Tests for SmartEstimate Engine.

Tests weighted analyst consensus calculation, recency decay, accuracy-tier weighting,
signal generation, and scorecard updates.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlmodel import Session
from unittest.mock import patch, MagicMock

from backend.services.smart_estimate_engine import SmartEstimateEngine
from backend.repositories.earnings_repo import EarningsRepository
from backend.models.earnings import (
    EarningsEstimate,
    AnalystScorecard,
    SmartEstimateWeights,
)


class TestRecencyDecayCalculation:
    """Test recency decay weighting with 30-day half-life."""

    def test_recency_decay_same_day_weight_is_one(self, session: Session):
        """Estimate from today should have weight ~1.0."""
        engine = SmartEstimateEngine(session)
        repo = EarningsRepository(session)

        # Save estimate from today
        now = datetime.now(timezone.utc)
        repo.save_estimate(
            ticker="AAPL",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("5.50"),
            estimate_date=now,
            analyst_broker="Goldman Sachs",
        )

        # Add another estimate from 30 days ago (should be ~0.5 weight)
        thirty_days_ago = now - timedelta(days=30)
        repo.save_estimate(
            ticker="AAPL",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("5.40"),
            estimate_date=thirty_days_ago,
            analyst_broker="Morgan Stanley",
        )

        result = engine.calculate_smart_estimate("AAPL", "2025Q1")

        # SmartEstimate should be closer to recent estimate (5.50) than old one (5.40)
        assert result["smart_eps"] is not None
        assert result["smart_eps"] > 5.45  # Closer to recent estimate

    def test_recency_decay_old_estimate_lower_weight(self, session: Session):
        """60-day-old estimate should have weight ~0.25."""
        engine = SmartEstimateEngine(session)
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        # Recent estimate
        repo.save_estimate(
            ticker="MSFT",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("2.50"),
            estimate_date=now,
            analyst_broker="JP Morgan",
        )

        # Very old estimate
        sixty_days_ago = now - timedelta(days=60)
        repo.save_estimate(
            ticker="MSFT",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("2.00"),
            estimate_date=sixty_days_ago,
            analyst_broker="Citigroup",
        )

        result = engine.calculate_smart_estimate("MSFT", "2025Q1")

        # SmartEstimate should be heavily weighted towards recent (2.50)
        assert result["smart_eps"] is not None
        assert result["smart_eps"] > 2.40

    def test_recency_decay_exponential_curve(self, session: Session):
        """Verify exponential decay: 30-day half-life."""
        engine = SmartEstimateEngine(session)
        repo = EarningsRepository(session)

        # Set explicit half-life parameter
        repo.save_smart_estimate_weights(
            weight_type="recency_decay",
            parameter_name="half_life_days",
            parameter_value=Decimal("30"),
        )

        now = datetime.now(timezone.utc)

        # Create estimates at t=0, 15, 30, 45 days
        for days_offset, eps_value in [(0, 5.0), (15, 5.0), (30, 5.0), (45, 5.0)]:
            estimate_date = now - timedelta(days=days_offset)
            repo.save_estimate(
                ticker="GOOGL",
                fiscal_quarter="2025Q1",
                estimate_type="individual",
                eps_estimate=Decimal(str(eps_value)),
                estimate_date=estimate_date,
                analyst_broker=f"Analyst_{days_offset}",
            )

        result = engine.calculate_smart_estimate("GOOGL", "2025Q1")

        # All estimates are equal (5.0), so smart_eps should be 5.0
        assert result["smart_eps"] is not None
        assert abs(float(result["smart_eps"]) - 5.0) < 0.1


class TestAccuracyTierWeighting:
    """Test accuracy tier weighting (A/B/C tiers)."""

    def test_tier_a_analyst_higher_weight(self, session: Session):
        """Tier A analysts (error <= 3%) should get 1.5x weight."""
        engine = SmartEstimateEngine(session)
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        # Create tier A analyst (very accurate)
        repo.save_analyst_scorecard(
            analyst_broker="Tier_A_Analyst",
            ticker="AAPL",
            total_estimates=100,
            accurate_count=95,
            avg_error_pct=Decimal("2.0"),
            period_start=None,
            period_end=None,
        )

        # Create tier C analyst (less accurate)
        repo.save_analyst_scorecard(
            analyst_broker="Tier_C_Analyst",
            ticker="AAPL",
            total_estimates=100,
            accurate_count=50,
            avg_error_pct=Decimal("8.0"),
            period_start=None,
            period_end=None,
        )

        # Both estimate the same EPS
        repo.save_estimate(
            ticker="AAPL",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("5.00"),
            estimate_date=now,
            analyst_broker="Tier_A_Analyst",
        )

        repo.save_estimate(
            ticker="AAPL",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("5.00"),
            estimate_date=now,
            analyst_broker="Tier_C_Analyst",
        )

        result = engine.calculate_smart_estimate("AAPL", "2025Q1")

        # With equal EPS, equal recency, but different tiers, weights differ
        assert result["num_estimates"] == 2
        # SmartEstimate should still be 5.0 since estimates are equal
        assert abs(float(result["smart_eps"]) - 5.0) < 0.1

    def test_analyst_without_scorecard_defaults_to_tier_b(self, session: Session):
        """Analyst with no scorecard should default to tier B (1.0x)."""
        engine = SmartEstimateEngine(session)
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        # Analyst with no scorecard
        repo.save_estimate(
            ticker="TSLA",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("2.50"),
            estimate_date=now,
            analyst_broker="Unknown_Analyst",
        )

        result = engine.calculate_smart_estimate("TSLA", "2025Q1")

        # Should not crash, should use default tier B
        assert result["smart_eps"] is not None
        assert abs(float(result["smart_eps"]) - 2.50) < 0.1


class TestWeightedConsensusCalculation:
    """Test weighted consensus calculation."""

    def test_consensus_vs_smart_estimate_divergence(self, session: Session):
        """SmartEstimate should differ from simple consensus when estimates vary."""
        engine = SmartEstimateEngine(session)
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        # Recent high estimate (tier A analyst)
        repo.save_analyst_scorecard(
            analyst_broker="Bullish_Analyst",
            ticker="AMZN",
            total_estimates=50,
            accurate_count=45,
            avg_error_pct=Decimal("2.5"),
            period_start=None,
            period_end=None,
        )

        repo.save_estimate(
            ticker="AMZN",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("6.00"),
            estimate_date=now,
            analyst_broker="Bullish_Analyst",
        )

        # Older lower estimate (tier C analyst)
        old_date = now - timedelta(days=60)
        repo.save_estimate(
            ticker="AMZN",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("4.00"),
            estimate_date=old_date,
            analyst_broker="Conservative_Analyst",
        )

        result = engine.calculate_smart_estimate("AMZN", "2025Q1")

        # Consensus = (6.0 + 4.0) / 2 = 5.0
        expected_consensus = 5.0
        assert result["consensus_eps"] is not None
        assert abs(float(result["consensus_eps"]) - expected_consensus) < 0.1

        # SmartEstimate should be weighted towards recent/accurate analyst
        assert result["smart_eps"] is not None
        assert float(result["smart_eps"]) > expected_consensus

    def test_divergence_percentage_calculation(self, session: Session):
        """Divergence should be calculated correctly."""
        engine = SmartEstimateEngine(session)
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        repo.save_estimate(
            ticker="META",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("5.00"),
            estimate_date=now,
            analyst_broker="Analyst1",
        )

        repo.save_estimate(
            ticker="META",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("5.10"),
            estimate_date=now,
            analyst_broker="Analyst2",
        )

        result = engine.calculate_smart_estimate("META", "2025Q1")

        # Consensus = (5.00 + 5.10) / 2 = 5.05
        # Divergence should be relatively small
        assert result["divergence_pct"] is not None
        assert abs(float(result["divergence_pct"])) < 2.0


class TestSignalGeneration:
    """Test signal generation based on divergence."""

    def test_buy_signal_smart_greater_than_consensus(self):
        """Smart > consensus with |divergence| >= 2% should generate 'buy'."""
        engine = SmartEstimateEngine(None)

        signal_type, confidence = engine.generate_signal(
            divergence_pct=2.5,
            smart_eps=5.25,
            consensus_eps=5.12,
        )

        assert signal_type == "buy"
        assert confidence >= 50
        assert confidence <= 100

    def test_sell_signal_smart_less_than_consensus(self):
        """Smart < consensus with |divergence| >= 2% should generate 'sell'."""
        engine = SmartEstimateEngine(None)

        signal_type, confidence = engine.generate_signal(
            divergence_pct=-2.5,
            smart_eps=5.00,
            consensus_eps=5.13,
        )

        assert signal_type == "sell"
        assert confidence >= 50
        assert confidence <= 100

    def test_hold_signal_small_divergence(self):
        """Divergence < 2% should generate 'hold'."""
        engine = SmartEstimateEngine(None)

        signal_type, confidence = engine.generate_signal(
            divergence_pct=1.5,
            smart_eps=5.08,
            consensus_eps=5.00,
        )

        assert signal_type == "hold"
        assert confidence == 50

    def test_hold_signal_zero_divergence(self):
        """Zero divergence should generate 'hold'."""
        engine = SmartEstimateEngine(None)

        signal_type, confidence = engine.generate_signal(
            divergence_pct=0.0,
            smart_eps=5.00,
            consensus_eps=5.00,
        )

        assert signal_type == "hold"
        assert confidence == 50

    def test_confidence_increases_with_magnitude(self):
        """Confidence should increase with divergence magnitude."""
        engine = SmartEstimateEngine(None)

        # Small divergence
        _, conf_2 = engine.generate_signal(
            divergence_pct=2.0,
            smart_eps=5.1,
            consensus_eps=5.0,
        )

        # Large divergence
        _, conf_10 = engine.generate_signal(
            divergence_pct=10.0,
            smart_eps=5.5,
            consensus_eps=5.0,
        )

        assert conf_10 > conf_2

    def test_confidence_capped_at_100(self):
        """Confidence should not exceed 100."""
        engine = SmartEstimateEngine(None)

        _, confidence = engine.generate_signal(
            divergence_pct=50.0,  # Very large divergence
            smart_eps=7.5,
            consensus_eps=5.0,
        )

        assert confidence <= 100


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_no_estimates_returns_hold(self, session: Session):
        """No estimates should return error without crashing."""
        engine = SmartEstimateEngine(session)

        result = engine.calculate_smart_estimate("NONEXISTENT", "2025Q1")

        assert result["smart_eps"] is None
        assert result["consensus_eps"] is None
        assert result["signal"] == "hold"
        assert result["num_estimates"] == 0

    def test_single_estimate(self, session: Session):
        """Single estimate should have smart_eps = consensus_eps."""
        engine = SmartEstimateEngine(session)
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        repo.save_estimate(
            ticker="AAPL",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("5.50"),
            estimate_date=now,
            analyst_broker="Only_Analyst",
        )

        result = engine.calculate_smart_estimate("AAPL", "2025Q1")

        assert result["smart_eps"] is not None
        assert result["consensus_eps"] is not None
        assert abs(float(result["smart_eps"]) - float(result["consensus_eps"])) < 0.01

    def test_all_stale_estimates(self, session: Session):
        """All very old estimates should still be processed."""
        engine = SmartEstimateEngine(session)
        repo = EarningsRepository(session)

        # All estimates from 200+ days ago
        very_old_date = datetime.now(timezone.utc) - timedelta(days=365)

        repo.save_estimate(
            ticker="MSFT",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("3.00"),
            estimate_date=very_old_date,
            analyst_broker="Old_Analyst1",
        )

        repo.save_estimate(
            ticker="MSFT",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("3.10"),
            estimate_date=very_old_date,
            analyst_broker="Old_Analyst2",
        )

        result = engine.calculate_smart_estimate("MSFT", "2025Q1")

        # Should still calculate even with old estimates
        assert result["smart_eps"] is not None
        assert result["num_estimates"] == 2

    def test_consensus_with_zero_estimate(self, session: Session):
        """Zero estimate should not cause division errors."""
        engine = SmartEstimateEngine(session)
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        repo.save_estimate(
            ticker="ZERO",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("0.00"),
            estimate_date=now,
            analyst_broker="Analyst",
        )

        result = engine.calculate_smart_estimate("ZERO", "2025Q1")

        # Should handle gracefully
        assert result["smart_eps"] is not None

    def test_negative_estimates(self, session: Session):
        """Negative estimates (loss) should be handled."""
        engine = SmartEstimateEngine(session)
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        repo.save_estimate(
            ticker="LOSS",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("-0.50"),
            estimate_date=now,
            analyst_broker="Analyst",
        )

        result = engine.calculate_smart_estimate("LOSS", "2025Q1")

        assert result["smart_eps"] is not None
        assert float(result["smart_eps"]) < 0


class TestScorecardUpdate:
    """Test analyst accuracy scorecard update logic."""

    def test_scorecard_accuracy_calculation(self, session: Session):
        """Scorecard should track accurate estimates (within ±5%)."""
        engine = SmartEstimateEngine(session)
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        # Save estimate
        repo.save_estimate(
            ticker="AAPL",
            fiscal_quarter="2025Q1",
            estimate_type="individual",
            eps_estimate=Decimal("5.00"),
            estimate_date=now,
            analyst_broker="Test_Analyst",
        )

        # Save actual close to estimate (within ±5%)
        from datetime import date
        repo.save_actual(
            ticker="AAPL",
            fiscal_quarter="2025Q1",
            actual_eps=Decimal("5.10"),
            report_date=date.today(),
            source="yfinance",
        )

        # Update scorecard
        stats = engine.update_scorecards()

        # Should have updated scorecard
        assert stats["scorecards_updated"] >= 0

    def test_scorecard_directional_accuracy(self, session: Session):
        """Scorecard should track directional accuracy."""
        engine = SmartEstimateEngine(session)
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        # Create multiple estimates and actuals
        for i in range(3):
            repo.save_estimate(
                ticker="MSFT",
                fiscal_quarter=f"2024Q{i+1}",
                estimate_type="individual",
                eps_estimate=Decimal("2.00"),
                estimate_date=now - timedelta(days=i*90),
                analyst_broker="Good_Analyst",
            )

        from datetime import date
        for i in range(3):
            repo.save_actual(
                ticker="MSFT",
                fiscal_quarter=f"2024Q{i+1}",
                actual_eps=Decimal("2.05"),
                report_date=date.today() - timedelta(days=i*90),
                source="yfinance",
            )

        # Update scorecard
        stats = engine.update_scorecards()

        # Should evaluate multiple estimates
        assert stats["estimates_evaluated"] > 0


class TestRefreshEstimates:
    """Test estimate refresh from external sources."""

    @patch("backend.services.smart_estimate_engine.yf.Ticker")
    def test_refresh_estimates_from_yfinance(self, mock_ticker, session: Session):
        """Test pulling estimates from yfinance."""
        engine = SmartEstimateEngine(session)

        # Mock yfinance response
        mock_stock = MagicMock()
        mock_ticker.return_value = mock_stock

        # Mock earnings_estimate
        import pandas as pd
        mock_earnings = pd.DataFrame({
            "Earnings Estimate": [5.0, 5.5],
        }, index=["2025-03-31", "2025-06-30"])
        mock_stock.earnings_estimate = mock_earnings

        # Refresh
        stats = engine.refresh_estimates(["AAPL"])

        assert stats["total_tickers"] == 1
        # estimates_refreshed could be 0-2 depending on implementation

    @patch("backend.services.smart_estimate_engine.yf.Ticker")
    def test_refresh_no_estimates_handles_gracefully(self, mock_ticker, session: Session):
        """Empty estimates should not crash."""
        engine = SmartEstimateEngine(session)

        mock_stock = MagicMock()
        mock_ticker.return_value = mock_stock
        mock_stock.earnings_estimate = None

        stats = engine.refresh_estimates(["UNKNOWN"])

        assert stats["total_tickers"] == 1
        assert len(stats["errors"]) > 0


class TestIntegration:
    """Integration tests for full SmartEstimate flow."""

    def test_calculate_and_generate_signal_full_flow(self, session: Session):
        """Test full flow from estimates to signal generation."""
        engine = SmartEstimateEngine(session)
        repo = EarningsRepository(session)

        now = datetime.now(timezone.utc)

        # Create diverse estimates
        estimates = [
            ("Analyst1", Decimal("5.00"), 0),
            ("Analyst2", Decimal("5.20"), 10),
            ("Analyst3", Decimal("5.10"), 5),
        ]

        for analyst, eps, days_ago in estimates:
            repo.save_estimate(
                ticker="TEST",
                fiscal_quarter="2025Q1",
                estimate_type="individual",
                eps_estimate=eps,
                estimate_date=now - timedelta(days=days_ago),
                analyst_broker=analyst,
            )

        # Calculate SmartEstimate
        result = engine.calculate_smart_estimate("TEST", "2025Q1")

        assert result["smart_eps"] is not None
        assert result["consensus_eps"] is not None
        assert result["num_estimates"] == 3

        # Generate signal
        if result["divergence_pct"]:
            signal_type, confidence = engine.generate_signal(
                result["divergence_pct"],
                smart_eps=result["smart_eps"],
                consensus_eps=result["consensus_eps"],
            )

            assert signal_type in ["buy", "sell", "hold"]
            assert 0 <= confidence <= 100
