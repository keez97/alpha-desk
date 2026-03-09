"""
Statistics calculator for backtesting results.
Computes institutional-grade performance metrics.
"""

from typing import List, Dict, Optional
import numpy as np
from datetime import datetime


class StatisticsCalculator:
    """Calculate institutional-grade portfolio statistics."""

    @staticmethod
    def sharpe_ratio(returns: List[float], risk_free_rate: float = 0.05) -> float:
        """
        Calculate Sharpe ratio.

        Args:
            returns: Daily returns as decimals (e.g., 0.01 for 1%)
            risk_free_rate: Annual risk-free rate (default 5%)

        Returns:
            Sharpe ratio (annualized)
        """
        if len(returns) < 2:
            return 0.0

        returns_array = np.array(returns, dtype=float)

        if np.std(returns_array) == 0:
            return 0.0

        # Convert annual risk-free rate to daily
        daily_rf = risk_free_rate / 252
        excess_returns = returns_array - daily_rf

        # Annualize: daily Sharpe * sqrt(252)
        daily_sharpe = np.mean(excess_returns) / np.std(excess_returns)
        return float(daily_sharpe * np.sqrt(252))

    @staticmethod
    def sortino_ratio(returns: List[float], risk_free_rate: float = 0.05) -> float:
        """
        Calculate Sortino ratio (penalizes only downside volatility).

        Args:
            returns: Daily returns as decimals
            risk_free_rate: Annual risk-free rate (default 5%)

        Returns:
            Sortino ratio (annualized)
        """
        if len(returns) < 2:
            return 0.0

        returns_array = np.array(returns, dtype=float)

        # Convert annual risk-free rate to daily
        daily_rf = risk_free_rate / 252
        excess_returns = returns_array - daily_rf

        # Downside deviation: only negative returns
        downside_returns = np.minimum(excess_returns, 0)
        downside_std = np.sqrt(np.mean(downside_returns ** 2))

        if downside_std == 0:
            return 0.0

        # Annualize
        daily_sortino = np.mean(excess_returns) / downside_std
        return float(daily_sortino * np.sqrt(252))

    @staticmethod
    def calmar_ratio(returns: List[float]) -> float:
        """
        Calculate Calmar ratio (return / max drawdown).

        Args:
            returns: Daily returns as decimals

        Returns:
            Calmar ratio
        """
        if len(returns) < 2:
            return 0.0

        annual_return = StatisticsCalculator.annualized_return(returns)
        max_dd = StatisticsCalculator.max_drawdown(returns)

        if max_dd == 0:
            return 0.0

        return float(annual_return / abs(max_dd))

    @staticmethod
    def max_drawdown(returns: List[float]) -> float:
        """
        Calculate maximum drawdown.

        Args:
            returns: Daily returns as decimals

        Returns:
            Maximum drawdown as decimal (negative value, e.g., -0.20 for 20%)
        """
        if len(returns) < 2:
            return 0.0

        returns_array = np.array(returns, dtype=float)

        # Compute cumulative returns
        cumulative = np.cumprod(1 + returns_array)

        # Running maximum
        running_max = np.maximum.accumulate(cumulative)

        # Drawdown at each point
        drawdown = (cumulative - running_max) / running_max

        return float(np.min(drawdown))

    @staticmethod
    def information_ratio(
        returns: List[float],
        benchmark_returns: List[float]
    ) -> float:
        """
        Calculate Information ratio (excess return / tracking error).

        Args:
            returns: Daily portfolio returns
            benchmark_returns: Daily benchmark returns

        Returns:
            Information ratio (annualized)
        """
        if len(returns) < 2 or len(benchmark_returns) < 2:
            return 0.0

        returns_array = np.array(returns, dtype=float)
        benchmark_array = np.array(benchmark_returns, dtype=float)

        # Ensure same length
        min_len = min(len(returns_array), len(benchmark_array))
        returns_array = returns_array[:min_len]
        benchmark_array = benchmark_array[:min_len]

        # Excess returns
        excess = returns_array - benchmark_array

        # Tracking error (volatility of excess returns)
        tracking_error = np.std(excess)

        if tracking_error == 0:
            return 0.0

        # Information ratio
        daily_ir = np.mean(excess) / tracking_error
        return float(daily_ir * np.sqrt(252))

    @staticmethod
    def hit_rate(returns: List[float]) -> float:
        """
        Calculate hit rate (percentage of positive daily returns).

        Args:
            returns: Daily returns

        Returns:
            Hit rate as decimal (0.0 to 1.0)
        """
        if len(returns) == 0:
            return 0.0

        returns_array = np.array(returns, dtype=float)
        positive = np.sum(returns_array > 0)
        return float(positive / len(returns_array))

    @staticmethod
    def annualized_return(returns: List[float]) -> float:
        """
        Calculate annualized return.

        Args:
            returns: Daily returns

        Returns:
            Annualized return as decimal
        """
        if len(returns) == 0:
            return 0.0

        returns_array = np.array(returns, dtype=float)
        cumulative_return = np.prod(1 + returns_array) - 1

        # Number of years
        num_days = len(returns_array)
        num_years = num_days / 252.0

        if num_years <= 0:
            return 0.0

        # Annualize
        annualized = (1 + cumulative_return) ** (1 / num_years) - 1
        return float(annualized)

    @staticmethod
    def annualized_volatility(returns: List[float]) -> float:
        """
        Calculate annualized volatility.

        Args:
            returns: Daily returns

        Returns:
            Annualized volatility as decimal
        """
        if len(returns) < 2:
            return 0.0

        returns_array = np.array(returns, dtype=float)
        daily_vol = np.std(returns_array)
        return float(daily_vol * np.sqrt(252))

    @staticmethod
    def calculate_all(
        daily_returns: List[float],
        benchmark_returns: List[float],
        risk_free_rate: float = 0.05
    ) -> Dict[str, float]:
        """
        Calculate all statistics at once.

        Args:
            daily_returns: Daily portfolio returns
            benchmark_returns: Daily benchmark returns
            risk_free_rate: Annual risk-free rate

        Returns:
            Dictionary with all metrics
        """
        return {
            "sharpe_ratio": StatisticsCalculator.sharpe_ratio(daily_returns, risk_free_rate),
            "sortino_ratio": StatisticsCalculator.sortino_ratio(daily_returns, risk_free_rate),
            "calmar_ratio": StatisticsCalculator.calmar_ratio(daily_returns),
            "max_drawdown": StatisticsCalculator.max_drawdown(daily_returns),
            "information_ratio": StatisticsCalculator.information_ratio(daily_returns, benchmark_returns),
            "hit_rate": StatisticsCalculator.hit_rate(daily_returns),
            "annualized_return": StatisticsCalculator.annualized_return(daily_returns),
            "annualized_volatility": StatisticsCalculator.annualized_volatility(daily_returns),
        }
