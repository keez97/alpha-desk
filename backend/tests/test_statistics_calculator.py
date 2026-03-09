"""
Unit tests for StatisticsCalculator.
Tests all performance metrics with known inputs and edge cases.
"""

import pytest
import numpy as np
from backend.services.statistics_calculator import StatisticsCalculator


class TestSharpeRatio:
    """Test Sharpe ratio calculations."""

    def test_sharpe_ratio_known_returns(self):
        """Test Sharpe ratio with known returns."""
        # Daily returns: [0.01, -0.005, 0.008, 0.002, -0.003]
        returns = [0.01, -0.005, 0.008, 0.002, -0.003]
        sharpe = StatisticsCalculator.sharpe_ratio(returns, risk_free_rate=0.05)

        # Should return a positive float
        assert isinstance(sharpe, float)
        # With these returns, Sharpe should be positive
        assert sharpe > 0

    def test_sharpe_ratio_empty_returns(self):
        """Test Sharpe ratio with empty returns list."""
        returns = []
        sharpe = StatisticsCalculator.sharpe_ratio(returns)
        assert sharpe == 0.0

    def test_sharpe_ratio_single_return(self):
        """Test Sharpe ratio with single return."""
        returns = [0.01]
        sharpe = StatisticsCalculator.sharpe_ratio(returns)
        assert sharpe == 0.0

    def test_sharpe_ratio_zero_volatility(self):
        """Test Sharpe ratio when all returns are identical."""
        returns = [0.01, 0.01, 0.01, 0.01]
        sharpe = StatisticsCalculator.sharpe_ratio(returns)
        # Zero volatility should return 0
        assert sharpe == 0.0

    def test_sharpe_ratio_custom_risk_free_rate(self):
        """Test Sharpe ratio with custom risk-free rate."""
        returns = [0.01, -0.005, 0.008, 0.002, -0.003]
        sharpe_5 = StatisticsCalculator.sharpe_ratio(returns, risk_free_rate=0.05)
        sharpe_2 = StatisticsCalculator.sharpe_ratio(returns, risk_free_rate=0.02)

        # With lower risk-free rate, Sharpe should be higher
        assert sharpe_2 > sharpe_5

    def test_sharpe_ratio_negative_returns(self):
        """Test Sharpe ratio with negative returns."""
        returns = [-0.01, -0.02, -0.01, -0.03]
        sharpe = StatisticsCalculator.sharpe_ratio(returns)
        # Should return a float (could be negative)
        assert isinstance(sharpe, float)


class TestSortinoRatio:
    """Test Sortino ratio calculations."""

    def test_sortino_ratio_known_returns(self):
        """Test Sortino ratio with known returns."""
        returns = [0.01, -0.005, 0.008, 0.002, -0.003]
        sortino = StatisticsCalculator.sortino_ratio(returns, risk_free_rate=0.05)

        assert isinstance(sortino, float)
        # Should be positive with mostly positive returns
        assert sortino > 0

    def test_sortino_ratio_no_downside(self):
        """Test Sortino ratio with only positive returns."""
        returns = [0.01, 0.02, 0.01, 0.03, 0.02]
        sortino = StatisticsCalculator.sortino_ratio(returns)

        # With no downside volatility, high Sortino
        assert sortino > 0

    def test_sortino_ratio_empty_returns(self):
        """Test Sortino ratio with empty returns."""
        returns = []
        sortino = StatisticsCalculator.sortino_ratio(returns)
        assert sortino == 0.0

    def test_sortino_ratio_only_downside(self):
        """Test Sortino ratio with only negative returns."""
        returns = [-0.01, -0.02, -0.01, -0.03]
        sortino = StatisticsCalculator.sortino_ratio(returns)

        # Should handle negative returns gracefully
        assert isinstance(sortino, float)

    def test_sortino_vs_sharpe(self):
        """Test that Sortino >= Sharpe when there's positive skew."""
        # Returns with upside skew
        returns = [0.02, 0.01, 0.015, -0.005, 0.01]

        sortino = StatisticsCalculator.sortino_ratio(returns)
        sharpe = StatisticsCalculator.sharpe_ratio(returns)

        # Sortino penalizes less downside volatility
        assert sortino >= sharpe


class TestMaxDrawdown:
    """Test maximum drawdown calculations."""

    def test_max_drawdown_known_sequence(self):
        """Test max drawdown with known peak-to-trough sequence."""
        # Returns: [10%, -5%, -8%, 3%]
        # Cumulative: [1.10, 1.045, 0.9614, 0.99]
        # Running max: [1.10, 1.10, 1.10, 1.10]
        # Drawdown: [0, -5%, -12.5%, -10%]
        returns = [0.10, -0.05, -0.08, 0.03]
        max_dd = StatisticsCalculator.max_drawdown(returns)

        # Should be negative
        assert max_dd < 0
        # Should be around -12.5%
        assert max_dd > -0.15
        assert max_dd < -0.10

    def test_max_drawdown_no_loss(self):
        """Test max drawdown with only positive returns."""
        returns = [0.01, 0.02, 0.03, 0.01]
        max_dd = StatisticsCalculator.max_drawdown(returns)
        # No drawdown
        assert max_dd == 0.0

    def test_max_drawdown_total_loss(self):
        """Test max drawdown with complete loss."""
        returns = [0.5, -1.0]  # 50% gain then 100% loss
        max_dd = StatisticsCalculator.max_drawdown(returns)

        # Should be close to -100%
        assert max_dd < -0.9

    def test_max_drawdown_empty_returns(self):
        """Test max drawdown with empty returns."""
        returns = []
        max_dd = StatisticsCalculator.max_drawdown(returns)
        assert max_dd == 0.0

    def test_max_drawdown_single_return(self):
        """Test max drawdown with single return."""
        returns = [0.05]
        max_dd = StatisticsCalculator.max_drawdown(returns)
        assert max_dd == 0.0


class TestCalmarRatio:
    """Test Calmar ratio (return/max drawdown) calculations."""

    def test_calmar_ratio_known_values(self):
        """Test Calmar ratio with known return and drawdown."""
        # Create returns with positive annual return and known drawdown
        returns = [0.001] * 200 + [-0.05, -0.05] + [0.001] * 50
        calmar = StatisticsCalculator.calmar_ratio(returns)

        assert isinstance(calmar, float)
        assert calmar > 0  # Should be positive

    def test_calmar_ratio_zero_drawdown(self):
        """Test Calmar ratio with no drawdown (only positive returns)."""
        returns = [0.01] * 252
        calmar = StatisticsCalculator.calmar_ratio(returns)

        # No drawdown: should return 0
        assert calmar == 0.0

    def test_calmar_ratio_empty_returns(self):
        """Test Calmar ratio with empty returns."""
        returns = []
        calmar = StatisticsCalculator.calmar_ratio(returns)
        assert calmar == 0.0


class TestInformationRatio:
    """Test Information ratio calculations."""

    def test_information_ratio_known_returns(self):
        """Test Information ratio with known portfolio and benchmark returns."""
        # Portfolio outperforms benchmark
        portfolio = [0.01, 0.015, 0.008, 0.012, 0.010]
        benchmark = [0.008, 0.010, 0.007, 0.009, 0.008]

        ir = StatisticsCalculator.information_ratio(portfolio, benchmark)

        assert isinstance(ir, float)
        assert ir > 0  # Should be positive (outperformance)

    def test_information_ratio_equal_returns(self):
        """Test Information ratio when portfolio equals benchmark."""
        returns = [0.01, 0.015, 0.008, 0.012, 0.010]
        ir = StatisticsCalculator.information_ratio(returns, returns)

        # No tracking error
        assert ir == 0.0

    def test_information_ratio_mismatched_lengths(self):
        """Test Information ratio with different-length return series."""
        portfolio = [0.01, 0.015, 0.008, 0.012, 0.010]
        benchmark = [0.008, 0.010, 0.007]

        ir = StatisticsCalculator.information_ratio(portfolio, benchmark)

        # Should handle gracefully by truncating
        assert isinstance(ir, float)

    def test_information_ratio_underperformance(self):
        """Test Information ratio when portfolio underperforms."""
        portfolio = [0.005, 0.008, 0.003, 0.006, 0.004]
        benchmark = [0.01, 0.015, 0.008, 0.012, 0.010]

        ir = StatisticsCalculator.information_ratio(portfolio, benchmark)

        assert isinstance(ir, float)
        assert ir < 0  # Should be negative (underperformance)


class TestHitRate:
    """Test hit rate (percentage of positive returns) calculations."""

    def test_hit_rate_known_returns(self):
        """Test hit rate with known returns."""
        # 3 positive, 2 negative out of 5
        returns = [0.01, -0.005, 0.008, 0.002, -0.003]
        hit_rate = StatisticsCalculator.hit_rate(returns)

        # 3/5 = 0.6
        assert hit_rate == 0.6

    def test_hit_rate_all_positive(self):
        """Test hit rate with all positive returns."""
        returns = [0.01, 0.02, 0.03, 0.01]
        hit_rate = StatisticsCalculator.hit_rate(returns)

        assert hit_rate == 1.0

    def test_hit_rate_all_negative(self):
        """Test hit rate with all negative returns."""
        returns = [-0.01, -0.02, -0.03, -0.01]
        hit_rate = StatisticsCalculator.hit_rate(returns)

        assert hit_rate == 0.0

    def test_hit_rate_with_zeros(self):
        """Test hit rate with zero returns."""
        returns = [0.01, 0.0, 0.02, 0.0, -0.01]
        hit_rate = StatisticsCalculator.hit_rate(returns)

        # Only positive (not zero) count as hits: 2/5 = 0.4
        assert hit_rate == 0.4

    def test_hit_rate_empty(self):
        """Test hit rate with empty returns."""
        returns = []
        hit_rate = StatisticsCalculator.hit_rate(returns)

        assert hit_rate == 0.0


class TestAnnualizedReturn:
    """Test annualized return calculations."""

    def test_annualized_return_known_returns(self):
        """Test annualized return with known daily returns."""
        # 0.1% daily for 252 days: (1.001)^252 - 1 ≈ 28.5%
        returns = [0.001] * 252
        annual_return = StatisticsCalculator.annualized_return(returns)

        # Should be positive and reasonable
        assert annual_return > 0.25
        assert annual_return < 0.35

    def test_annualized_return_zero_returns(self):
        """Test annualized return with zero returns."""
        returns = [0.0] * 252
        annual_return = StatisticsCalculator.annualized_return(returns)

        assert annual_return == 0.0

    def test_annualized_return_negative_returns(self):
        """Test annualized return with negative returns."""
        returns = [-0.001] * 252
        annual_return = StatisticsCalculator.annualized_return(returns)

        # Should be negative
        assert annual_return < 0

    def test_annualized_return_partial_year(self):
        """Test annualized return with less than a year of data."""
        returns = [0.01] * 100  # ~4 months
        annual_return = StatisticsCalculator.annualized_return(returns)

        # Should be higher than average daily return when annualized
        avg_daily = np.mean(returns)
        assert annual_return > avg_daily

    def test_annualized_return_empty(self):
        """Test annualized return with empty returns."""
        returns = []
        annual_return = StatisticsCalculator.annualized_return(returns)

        assert annual_return == 0.0


class TestAnnualizedVolatility:
    """Test annualized volatility calculations."""

    def test_annualized_volatility_known_returns(self):
        """Test annualized volatility with known returns."""
        # Volatility should be consistent across calculations
        returns = [0.01, -0.005, 0.008, 0.002, -0.003] * 50
        vol = StatisticsCalculator.annualized_volatility(returns)

        # Should be positive
        assert vol > 0
        # Should be annualized (roughly sqrt(252) ≈ 15.87x daily volatility)
        daily_vol = np.std(returns)
        assert vol > daily_vol * 10

    def test_annualized_volatility_no_volatility(self):
        """Test annualized volatility with no volatility."""
        returns = [0.01] * 252
        vol = StatisticsCalculator.annualized_volatility(returns)

        assert vol == 0.0

    def test_annualized_volatility_single_return(self):
        """Test annualized volatility with single return."""
        returns = [0.01]
        vol = StatisticsCalculator.annualized_volatility(returns)

        assert vol == 0.0

    def test_annualized_volatility_empty(self):
        """Test annualized volatility with empty returns."""
        returns = []
        vol = StatisticsCalculator.annualized_volatility(returns)

        assert vol == 0.0


class TestCalculateAll:
    """Test the calculate_all method that computes all statistics at once."""

    def test_calculate_all_returns_dict(self):
        """Test that calculate_all returns a dictionary with all metrics."""
        returns = [0.01, -0.005, 0.008, 0.002, -0.003] * 50
        benchmark_returns = [0.008, 0.0, 0.005, 0.001, 0.0] * 50

        stats = StatisticsCalculator.calculate_all(returns, benchmark_returns)

        # Check all expected keys exist
        expected_keys = [
            "sharpe_ratio",
            "sortino_ratio",
            "calmar_ratio",
            "max_drawdown",
            "information_ratio",
            "hit_rate",
            "annualized_return",
            "annualized_volatility",
        ]

        for key in expected_keys:
            assert key in stats
            assert isinstance(stats[key], float)

    def test_calculate_all_reasonable_values(self):
        """Test that all calculated metrics have reasonable values."""
        returns = [0.001] * 252
        benchmark_returns = [0.0008] * 252

        stats = StatisticsCalculator.calculate_all(returns, benchmark_returns)

        # With positive returns, most stats should be positive or reasonable
        assert stats["annualized_return"] > 0
        assert stats["annualized_volatility"] >= 0
        assert 0 <= stats["hit_rate"] <= 1
        assert stats["max_drawdown"] <= 0  # Drawdown is always <= 0

    def test_calculate_all_custom_risk_free_rate(self):
        """Test calculate_all with custom risk-free rate."""
        returns = [0.01, -0.005, 0.008, 0.002, -0.003] * 50
        benchmark_returns = returns

        stats_5 = StatisticsCalculator.calculate_all(
            returns, benchmark_returns, risk_free_rate=0.05
        )
        stats_2 = StatisticsCalculator.calculate_all(
            returns, benchmark_returns, risk_free_rate=0.02
        )

        # Sharpe ratio should be higher with lower risk-free rate
        assert stats_2["sharpe_ratio"] > stats_5["sharpe_ratio"]
        assert stats_2["sortino_ratio"] > stats_5["sortino_ratio"]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_large_returns_list(self):
        """Test with large returns list (10 years of daily data)."""
        returns = [0.0005 * (i % 10 + 1) for i in range(2520)]  # 10 * 252 days

        stats = StatisticsCalculator.calculate_all(returns, returns)

        # All statistics should compute without error
        assert all(isinstance(v, float) for v in stats.values())

    def test_extreme_positive_returns(self):
        """Test with extreme positive returns."""
        returns = [10.0] * 10  # 1000% daily returns
        max_dd = StatisticsCalculator.max_drawdown(returns)

        # Should handle extreme values
        assert isinstance(max_dd, float)

    def test_extreme_negative_returns(self):
        """Test with extreme negative returns."""
        returns = [-0.99] * 10  # -99% daily returns
        sharpe = StatisticsCalculator.sharpe_ratio(returns)

        # Should handle extreme values
        assert isinstance(sharpe, float)

    def test_nan_handling(self):
        """Test that NaN values don't crash the system."""
        # This should not crash, though behavior with NaN may vary
        returns = [0.01, float("nan"), 0.02, 0.01]

        try:
            sharpe = StatisticsCalculator.sharpe_ratio(returns)
            # If it doesn't raise, that's fine - just make sure it returns a float
            assert isinstance(sharpe, float)
        except (ValueError, TypeError):
            # Also acceptable to raise error on NaN
            pass
