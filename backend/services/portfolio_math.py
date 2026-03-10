import pandas as pd
import numpy as np
from scipy.optimize import minimize
from typing import Dict, List, Any
import logging
from backend.services.data_provider import get_history

logger = logging.getLogger(__name__)


def compute_correlation_matrix(tickers: List[str], period: str = "1y") -> Dict[str, Any]:
    """Compute correlation matrix for given tickers."""
    try:
        # Fetch historical data for all tickers
        price_data = {}
        for ticker in tickers:
            history = get_history(ticker, period=period)
            if not history:
                logger.warning(f"No data for {ticker}")
                continue

            dates = [h["date"] for h in history]
            closes = [h["close"] for h in history]
            price_data[ticker] = pd.Series(closes, index=pd.to_datetime(dates))

        if not price_data:
            return {"tickers": tickers, "matrix": []}

        # Create DataFrame and compute returns
        df = pd.DataFrame(price_data)
        returns = df.pct_change().dropna()

        # Compute correlation matrix
        corr_matrix = returns.corr()

        return {
            "tickers": list(corr_matrix.columns),
            "matrix": corr_matrix.values.tolist()
        }
    except Exception as e:
        logger.error(f"Error computing correlation matrix: {e}")
        return {"tickers": tickers, "matrix": [], "error": str(e)}


def optimize_max_sharpe(returns: pd.DataFrame, risk_free_rate: float = 0.05) -> Dict[str, Any]:
    """Optimize for maximum Sharpe ratio."""
    try:
        n_assets = len(returns.columns)

        # Expected returns and covariance
        mean_returns = returns.mean() * 252  # Annualize
        cov_matrix = returns.cov() * 252

        def negative_sharpe(weights):
            portfolio_return = np.sum(mean_returns * weights)
            portfolio_std = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
            sharpe = (portfolio_return - risk_free_rate) / portfolio_std
            return -sharpe

        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(n_assets))
        initial_guess = np.array([1/n_assets] * n_assets)

        result = minimize(
            negative_sharpe,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        optimal_weights = result.x
        portfolio_return = np.sum(mean_returns * optimal_weights)
        portfolio_std = np.sqrt(np.dot(optimal_weights, np.dot(cov_matrix, optimal_weights)))
        sharpe = (portfolio_return - risk_free_rate) / portfolio_std

        return {
            "weights": dict(zip(returns.columns, optimal_weights.tolist())),
            "expected_return": float(portfolio_return),
            "volatility": float(portfolio_std),
            "sharpe_ratio": float(sharpe)
        }
    except Exception as e:
        logger.error(f"Error optimizing max Sharpe: {e}")
        return {
            "weights": {},
            "expected_return": 0.0,
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "error": str(e)
        }


def optimize_max_variance(returns: pd.DataFrame) -> Dict[str, Any]:
    """Optimize for maximum portfolio variance (risk)."""
    try:
        n_assets = len(returns.columns)
        cov_matrix = returns.cov() * 252

        def negative_variance(weights):
            return -np.dot(weights, np.dot(cov_matrix, weights))

        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(n_assets))
        initial_guess = np.array([1/n_assets] * n_assets)

        result = minimize(
            negative_variance,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        optimal_weights = result.x
        portfolio_variance = np.dot(optimal_weights, np.dot(cov_matrix, optimal_weights))
        portfolio_std = np.sqrt(portfolio_variance)

        mean_returns = returns.mean() * 252
        portfolio_return = np.sum(mean_returns * optimal_weights)

        return {
            "weights": dict(zip(returns.columns, optimal_weights.tolist())),
            "expected_return": float(portfolio_return),
            "volatility": float(portfolio_std),
            "variance": float(portfolio_variance)
        }
    except Exception as e:
        logger.error(f"Error optimizing max variance: {e}")
        return {
            "weights": {},
            "expected_return": 0.0,
            "volatility": 0.0,
            "variance": 0.0,
            "error": str(e)
        }


def monte_carlo_simulation(
    weights: Dict[str, float],
    returns: pd.DataFrame,
    capital: float,
    n_simulations: int = 1000,
    n_days: int = 252
) -> Dict[str, Any]:
    """Run Monte Carlo simulation on portfolio."""
    try:
        # Align weights with returns columns
        weight_array = np.array([weights.get(col, 0) for col in returns.columns])

        # Portfolio daily returns
        daily_returns = returns.sum(axis=1)
        mean_return = daily_returns.mean()
        std_return = daily_returns.std()

        # Run simulations
        simulation_results = np.zeros((n_simulations, n_days))

        for sim in range(n_simulations):
            portfolio_value = capital
            for day in range(n_days):
                daily_return = np.random.normal(mean_return, std_return)
                portfolio_value *= (1 + daily_return)
            simulation_results[sim, -1] = portfolio_value

        # Compute percentiles
        final_values = simulation_results[:, -1]
        percentiles = {
            "p5": float(np.percentile(final_values, 5)),
            "p25": float(np.percentile(final_values, 25)),
            "p50": float(np.percentile(final_values, 50)),
            "p75": float(np.percentile(final_values, 75)),
            "p95": float(np.percentile(final_values, 95)),
        }

        return {
            "initial_capital": capital,
            "percentiles": percentiles,
            "mean_final_value": float(np.mean(final_values)),
            "std_final_value": float(np.std(final_values)),
            "min_value": float(np.min(final_values)),
            "max_value": float(np.max(final_values)),
            "n_simulations": n_simulations,
            "n_days": n_days,
        }
    except Exception as e:
        logger.error(f"Error running Monte Carlo: {e}")
        return {
            "error": str(e),
            "initial_capital": capital,
            "percentiles": {},
        }
