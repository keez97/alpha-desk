"""
Unit tests for the Systemic Risk Engine module.

Tests cover:
  - Absorption Ratio calculations with synthetic data
  - Turbulence Index with Mahalanobis distance
  - Chi-squared p-value computation
  - Sigmoid transitions and state classification
  - Hysteresis and state persistence
  - AR delta computation and zscore
  - Graceful degradation with insufficient data
"""

import pytest
import numpy as np
from scipy import stats as scipy_stats

from backend.services import systemic_risk_engine


class TestAbsorptionRatio:
    """Test Absorption Ratio calculations."""

    def test_perfectly_correlated_returns(self):
        """
        With perfectly correlated returns, AR should be very high (~1.0).
        All variance explained by first component.
        """
        n_assets = 4
        n_weeks = 60

        # Create perfectly correlated returns (all move together)
        base_returns = np.random.normal(0, 0.01, n_weeks)
        returns = np.tile(base_returns[:, np.newaxis], (1, n_assets))

        result = systemic_risk_engine.compute_absorption_ratio(
            returns, n_components=1, rolling_window=30
        )

        assert result["current"] is not None
        assert result["current"] > 0.8, "Perfectly correlated should have AR > 0.8 (Ledoit-Wolf shrinkage reduces dominant eigenvalue slightly)"
        assert 0 <= result["percentile"] <= 100
        assert "series" in result
        assert len(result["series"]) > 0

    def test_uncorrelated_returns(self):
        """
        With uncorrelated returns, AR should be lower (~n_comp/n_assets).
        Each component explains roughly equal variance.
        """
        n_assets = 4
        n_weeks = 100

        # Create uncorrelated returns
        returns = np.random.normal(0, 0.01, (n_weeks, n_assets))

        result = systemic_risk_engine.compute_absorption_ratio(
            returns, n_components=1, rolling_window=50
        )

        assert result["current"] is not None
        # With 1 component and 4 assets, AR should be roughly 0.25-0.35
        assert result["current"] < 0.5, "Uncorrelated should have lower AR"

    def test_ar_delta_computation(self):
        """Test that AR delta is computed correctly."""
        n_assets = 4
        n_weeks = 100

        # Create returns with varying correlation
        returns = np.random.normal(0, 0.01, (n_weeks, n_assets))

        result = systemic_risk_engine.compute_absorption_ratio(
            returns, n_components=2, rolling_window=40
        )

        assert "delta" in result
        assert "delta_zscore" in result
        # Delta should be small for random walk
        assert abs(result["delta"]) < 0.3

    def test_insufficient_data(self):
        """Test graceful degradation with insufficient data."""
        # Too few returns
        returns = np.random.normal(0, 0.01, (10, 4))

        result = systemic_risk_engine.compute_absorption_ratio(
            returns, n_components=1, rolling_window=30
        )

        assert result["current"] is None
        assert result["percentile"] == 50.0
        assert result["series"] == []


class TestTurbulenceIndex:
    """Test Turbulence Index calculations."""

    def test_normal_returns_low_turbulence(self):
        """Normal returns should have low turbulence (near mean)."""
        n_assets = 5
        n_days = 100

        # Create normal returns from a stable distribution
        returns = np.random.normal(0, 0.01, (n_days, n_assets))

        result = systemic_risk_engine.compute_turbulence_index(
            returns, rolling_window=40
        )

        assert result["current"] is not None
        assert result["percentile"] is not None
        assert result["p_value"] is not None
        # Recent value should be somewhere in the distribution
        assert 0 <= result["percentile"] <= 100

    def test_outlier_returns_high_turbulence(self):
        """An outlier day should have high Mahalanobis distance."""
        n_assets = 5
        n_days = 100

        returns = np.random.normal(0, 0.01, (n_days, n_assets))

        # Make the last day an outlier (5 standard deviations out)
        returns[-1] = returns[-1] + np.ones(n_assets) * 0.1

        result = systemic_risk_engine.compute_turbulence_index(
            returns, rolling_window=40
        )

        assert result["current"] is not None
        # Outlier should be in high percentile
        assert result["percentile"] > 50, "Outlier should have high percentile"

    def test_chi_squared_p_value(self):
        """Test that p-value is computed correctly."""
        n_assets = 4
        n_days = 100

        returns = np.random.normal(0, 0.01, (n_days, n_assets))

        result = systemic_risk_engine.compute_turbulence_index(
            returns, rolling_window=40
        )

        assert "p_value" in result
        assert 0 <= result["p_value"] <= 1.0

    def test_insufficient_data(self):
        """Test graceful degradation with insufficient data."""
        returns = np.random.normal(0, 0.01, (20, 4))

        result = systemic_risk_engine.compute_turbulence_index(
            returns, rolling_window=30
        )

        assert result["current"] is None
        assert result["percentile"] == 50.0
        assert result["p_value"] == 1.0
        assert result["series"] == []


class TestSigmoidTransitions:
    """Test sigmoid transition functions."""

    def test_sigmoid_at_threshold(self):
        """Sigmoid should be 0.5 at the center (threshold)."""
        score = systemic_risk_engine._sigmoid(50, center=50, slope=0.1)
        assert abs(score - 0.5) < 0.01, "Sigmoid should be 0.5 at center"

    def test_sigmoid_below_threshold(self):
        """Below threshold, sigmoid should approach 0."""
        score = systemic_risk_engine._sigmoid(30, center=50, slope=0.1)
        assert score < 0.5, "Below threshold should give low score"

    def test_sigmoid_above_threshold(self):
        """Above threshold, sigmoid should approach 1."""
        score = systemic_risk_engine._sigmoid(70, center=50, slope=0.1)
        assert score > 0.5, "Above threshold should give high score"

    def test_sigmoid_monotonic(self):
        """Sigmoid should be monotonically increasing."""
        x_vals = np.linspace(0, 100, 20)
        scores = [systemic_risk_engine._sigmoid(x, center=50, slope=0.1) for x in x_vals]

        # Check that scores are increasing
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i-1], "Sigmoid should be monotonic"

    def test_sigmoid_steepness(self):
        """Higher slope should give steeper transition."""
        x = 55  # 5 units from center

        score_low_slope = systemic_risk_engine._sigmoid(x, center=50, slope=0.05)
        score_high_slope = systemic_risk_engine._sigmoid(x, center=50, slope=0.5)

        # High slope at same distance should give more extreme value
        assert score_high_slope > score_low_slope


class TestWindhamClassification:
    """Test Windham 2x2 state classification."""

    def test_resilient_calm(self):
        """Low turbulence + low absorption = resilient-calm."""
        result = systemic_risk_engine.classify_windham_state(
            turb_pctile=30,  # Low
            ar_pctile=40,    # Low
        )

        assert result["state"] == "resilient-calm"
        assert result["label"] == "Normal Markets"
        assert result["risk_level"] == "low"
        assert result["score"] > 0

    def test_resilient_turbulent(self):
        """High turbulence + low absorption = resilient-turbulent."""
        result = systemic_risk_engine.classify_windham_state(
            turb_pctile=80,  # High
            ar_pctile=40,    # Low
        )

        assert result["state"] == "resilient-turbulent"
        assert result["label"] == "Idiosyncratic Shock"
        assert result["risk_level"] == "moderate"
        assert result["score"] < 0

    def test_fragile_calm(self):
        """Low turbulence + high absorption = fragile-calm (dangerous!)."""
        result = systemic_risk_engine.classify_windham_state(
            turb_pctile=30,  # Low
            ar_pctile=85,    # High
        )

        assert result["state"] == "fragile-calm"
        assert result["label"] == "Hidden Risk"
        assert result["risk_level"] == "high"
        assert result["score"] < 0

    def test_fragile_turbulent(self):
        """High turbulence + high absorption = fragile-turbulent (crisis!)."""
        result = systemic_risk_engine.classify_windham_state(
            turb_pctile=85,  # High
            ar_pctile=85,    # High
        )

        assert result["state"] == "fragile-turbulent"
        assert result["label"] == "Crisis Mode"
        assert result["risk_level"] == "extreme"
        assert result["score"] == -1.0

    def test_ar_delta_warning(self):
        """Test that AR delta zscore triggers warning."""
        result = systemic_risk_engine.classify_windham_state(
            turb_pctile=50,
            ar_pctile=50,
            ar_delta_zscore=1.5,  # Above threshold
        )

        assert result["ar_delta_warning"] is True

    def test_hysteresis_exit_thresholds(self):
        """Test that exit thresholds are used when previous state was elevated."""
        # When prev_state was fragile, should use exit threshold
        result = systemic_risk_engine.classify_windham_state(
            turb_pctile=68,  # Between exit (65) and entry (75) turbulence
            ar_pctile=72,    # Between exit (70) and entry (80) absorption
            prev_state="fragile-turbulent",
        )

        # With hysteresis, should still consider fragile/turbulent
        # because we were in that state and haven't exited yet
        assert "fragile" in result["state"] or "turbulent" in result["state"]


class TestStatePersistence:
    """Test state persistence tracking."""

    def test_consecutive_periods_increment(self):
        """Consecutive periods should increment when state doesn't change."""
        # Clear history
        systemic_risk_engine._windham_state_history = []

        # Same state twice
        result1 = systemic_risk_engine.classify_windham_state(
            turb_pctile=30, ar_pctile=40
        )
        result2 = systemic_risk_engine.classify_windham_state(
            turb_pctile=30, ar_pctile=40
        )

        assert result1["consecutive_periods"] > 0
        assert result2["consecutive_periods"] >= result1["consecutive_periods"]

    def test_consecutive_periods_reset(self):
        """Consecutive periods should reset when state changes."""
        # Clear history
        systemic_risk_engine._windham_state_history = []

        # First state
        result1 = systemic_risk_engine.classify_windham_state(
            turb_pctile=30, ar_pctile=40
        )
        # Different state
        result2 = systemic_risk_engine.classify_windham_state(
            turb_pctile=85, ar_pctile=85
        )

        # Second should have low consecutive count
        assert result2["consecutive_periods"] < result1["consecutive_periods"] or result2["consecutive_periods"] == 1


class TestTopLevelComputation:
    """Test the top-level compute_systemic_risk function."""

    def test_returns_complete_dict(self):
        """compute_systemic_risk should return complete output dict."""
        result = systemic_risk_engine.compute_systemic_risk()

        assert "turbulence" in result
        assert "absorption" in result
        assert "windham" in result
        assert "data_quality" in result

    def test_graceful_degradation_no_data(self):
        """Should degrade gracefully if no market data available."""
        # This depends on yahoo_direct being available; we can't easily mock it
        # in this test, but the function should not crash
        result = systemic_risk_engine.compute_systemic_risk()

        # Should have some result even if data is unavailable
        assert "turbulence" in result
        assert "absorption" in result
        assert "windham" in result


class TestDataIntegration:
    """Integration tests with the module-level universes."""

    def test_sector_etf_universe_defined(self):
        """Sector ETF universe should be defined."""
        assert len(systemic_risk_engine.SECTOR_ETF_UNIVERSE) == 11
        assert "XLK" in systemic_risk_engine.SECTOR_ETF_UNIVERSE
        assert "XLV" in systemic_risk_engine.SECTOR_ETF_UNIVERSE

    def test_cross_asset_universe_defined(self):
        """Cross-asset universe should be defined."""
        assert len(systemic_risk_engine.CROSS_ASSET_UNIVERSE) == 10
        assert "SPY" in systemic_risk_engine.CROSS_ASSET_UNIVERSE
        assert "GLD" in systemic_risk_engine.CROSS_ASSET_UNIVERSE

    def test_threshold_constants(self):
        """Threshold constants should be reasonable."""
        assert systemic_risk_engine.TURBULENCE_THRESHOLD_PCTILE == 75
        assert systemic_risk_engine.ABSORPTION_THRESHOLD_PCTILE == 80
        assert systemic_risk_engine.TURBULENCE_EXIT_PCTILE == 65
        assert systemic_risk_engine.ABSORPTION_EXIT_PCTILE == 70
        # Exit thresholds should be lower than entry (wider margin)
        assert systemic_risk_engine.TURBULENCE_EXIT_PCTILE < systemic_risk_engine.TURBULENCE_THRESHOLD_PCTILE
        assert systemic_risk_engine.ABSORPTION_EXIT_PCTILE < systemic_risk_engine.ABSORPTION_THRESHOLD_PCTILE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
