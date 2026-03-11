import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
import logging
from datetime import datetime, timedelta
from backend.services.data_provider import get_history
from backend.services.rrg_calculator import calculate_rrg, SECTOR_ETFS
from backend.services import fds_client

logger = logging.getLogger(__name__)

# Sector ETFs for correlation analysis
SECTOR_TICKERS = list(SECTOR_ETFS.keys())


def _get_history_cascade(ticker: str, days: int = 365) -> list:
    """
    Fetch price history: FDS (Tier 1) → data_provider (Tier 2).

    Args:
        ticker: Stock ticker symbol
        days: Number of days to look back

    Returns:
        List of price records with at least 20 data points, or empty list on failure
    """
    if fds_client.is_available():
        try:
            end_date = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
            start_date = (datetime.utcnow().date() - timedelta(days=days)).isoformat()
            records = fds_client.get_historical_prices(ticker, start_date, end_date)
            if records and len(records) >= 20:
                # Normalize: FDS uses 'date' field (which is what we need)
                return records
        except Exception as e:
            logger.debug(f"FDS history {ticker}: {e}")
    # Fallback to data_provider
    return get_history(ticker, period="1y")


def calculate_correlation_matrix(
    lookback_days: int = 90,
) -> Dict[str, Any]:
    """
    Calculate correlation matrix for sector ETFs.

    Args:
        lookback_days: Number of days to look back (default 90)

    Returns:
        {
            matrix: [[float]],  # NxN correlation matrix
            tickers: [str],      # Sorted sector ETF tickers
            sectors: [str],      # Sector names corresponding to tickers
            pairs_trades: [...], # Mean-reversion pairs
            hedging_pairs: [...],# Diversification/hedging pairs
            lookback_days: int
        }
    """
    try:
        # Fetch price data for all sector ETFs
        price_data = {}
        valid_tickers = []

        for ticker in SECTOR_TICKERS:
            try:
                history = _get_history_cascade(ticker)
                if not history or len(history) < 20:
                    logger.warning(f"Insufficient data for {ticker}")
                    continue

                # Extract close prices and reverse to oldest first
                prices = [h["close"] for h in history]
                prices.reverse()

                # Take only the lookback period
                prices = prices[-lookback_days:]

                if len(prices) >= lookback_days:
                    price_data[ticker] = prices
                    valid_tickers.append(ticker)
            except Exception as e:
                logger.error(f"Error fetching data for {ticker}: {e}")
                continue

        if not valid_tickers:
            return {
                "error": "No valid ticker data available",
                "matrix": [],
                "tickers": [],
                "sectors": [],
                "pairs_trades": [],
                "hedging_pairs": [],
                "lookback_days": lookback_days,
            }

        # Sort tickers for consistency
        valid_tickers.sort()

        # Create price dataframe
        df_prices = pd.DataFrame(price_data)

        # Calculate daily returns
        df_returns = df_prices.pct_change().dropna()

        # Calculate correlation matrix
        corr_matrix = df_returns.corr().values.tolist()

        # Get sector names
        sectors = [SECTOR_ETFS.get(ticker, ticker) for ticker in valid_tickers]

        # Find pairs trade opportunities (highly correlated pairs that diverge in RRG)
        pairs_trades = _identify_pairs_trades(valid_tickers, sectors, corr_matrix)

        # Find hedging opportunities (low/negative correlation)
        hedging_pairs = _identify_hedging_pairs(valid_tickers, sectors, corr_matrix)

        return {
            "matrix": corr_matrix,
            "tickers": valid_tickers,
            "sectors": sectors,
            "pairs_trades": pairs_trades,
            "hedging_pairs": hedging_pairs,
            "lookback_days": lookback_days,
        }
    except Exception as e:
        logger.error(f"Error calculating correlation matrix: {e}")
        return {
            "error": str(e),
            "matrix": [],
            "tickers": [],
            "sectors": [],
            "pairs_trades": [],
            "hedging_pairs": [],
            "lookback_days": lookback_days,
        }


def _identify_pairs_trades(
    tickers: List[str],
    sectors: List[str],
    corr_matrix: List[List[float]],
) -> List[Dict[str, Any]]:
    """
    Identify pairs trade opportunities: highly correlated pairs where RRG quadrants diverge.
    Mean-reversion pairs occur when correlated assets diverge (one strengthening, other weakening).
    """
    pairs_trades = []

    try:
        # Get RRG data to check quadrants
        try:
            rrg_data = calculate_rrg(tickers)
        except Exception as e:
            logger.warning(f"RRG calculation failed for pairs analysis: {e}")
            return pairs_trades

        if "error" in rrg_data or not rrg_data.get("sectors"):
            logger.warning("Could not fetch RRG data for pairs analysis")
            return pairs_trades

        # Build RRG quadrant lookup
        rrg_quadrants = {}
        for sector in rrg_data["sectors"]:
            rrg_quadrants[sector["ticker"]] = sector["quadrant"]

        # Find highly correlated pairs with diverging quadrants
        for i, ticker1 in enumerate(tickers):
            for j, ticker2 in enumerate(tickers):
                if i >= j:  # Avoid duplicates and diagonal
                    continue

                corr = corr_matrix[i][j]

                # High correlation threshold for pairs trades
                if corr > 0.7:
                    quad1 = rrg_quadrants.get(ticker1)
                    quad2 = rrg_quadrants.get(ticker2)

                    if not quad1 or not quad2:
                        continue

                    # Check for divergence: one strengthening/recovering, other weakening/deteriorating
                    strengthening_set = {"Strengthening", "Recovering"}
                    weakening_set = {"Weakening", "Deteriorating"}

                    if (quad1 in strengthening_set and quad2 in weakening_set) or \
                       (quad1 in weakening_set and quad2 in strengthening_set):

                        # Determine trade direction
                        if quad1 in strengthening_set:
                            long_ticker = ticker1
                            short_ticker = ticker2
                        else:
                            long_ticker = ticker2
                            short_ticker = ticker1

                        pairs_trades.append({
                            "ticker1": long_ticker,
                            "ticker2": short_ticker,
                            "sector1": sectors[tickers.index(long_ticker)],
                            "sector2": sectors[tickers.index(short_ticker)],
                            "correlation": round(corr, 4),
                            "quadrant1": rrg_quadrants[long_ticker],
                            "quadrant2": rrg_quadrants[short_ticker],
                            "trade_type": "Long / Short",
                            "conviction": round(min(abs(corr - 0.7) + 0.3, 1.0), 2),  # Higher corr = higher conviction
                        })

        # Sort by conviction descending
        pairs_trades.sort(key=lambda x: x["conviction"], reverse=True)

    except Exception as e:
        logger.error(f"Error identifying pairs trades: {e}")

    return pairs_trades


def _identify_hedging_pairs(
    tickers: List[str],
    sectors: List[str],
    corr_matrix: List[List[float]],
) -> List[Dict[str, Any]]:
    """
    Identify hedging opportunities: low or negative correlation pairs for diversification.
    """
    hedging_pairs = []

    try:
        for i, ticker1 in enumerate(tickers):
            for j, ticker2 in enumerate(tickers):
                if i >= j:  # Avoid duplicates and diagonal
                    continue

                corr = corr_matrix[i][j]

                # Hedging criteria: correlation < -0.3 (negative) or near 0 (low)
                if corr < -0.3 or (corr > -0.2 and corr < 0.2):
                    hedging_pairs.append({
                        "ticker1": ticker1,
                        "ticker2": ticker2,
                        "sector1": sectors[i],
                        "sector2": sectors[j],
                        "correlation": round(corr, 4),
                        "hedge_type": "Negative" if corr < -0.3 else "Low",
                    })

        # Sort by absolute correlation descending (strongest hedges first)
        hedging_pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    except Exception as e:
        logger.error(f"Error identifying hedging pairs: {e}")

    return hedging_pairs


def get_pair_details(
    ticker1: str,
    ticker2: str,
    lookback_days: int = 90,
) -> Dict[str, Any]:
    """
    Get detailed pair analysis: spread, z-score, rolling correlation.
    """
    try:
        # Fetch price data
        history1 = _get_history_cascade(ticker1)
        history2 = _get_history_cascade(ticker2)

        if not history1 or not history2:
            return {"error": f"Could not fetch data for {ticker1} or {ticker2}"}

        # Extract prices (oldest first)
        prices1 = [h["close"] for h in history1]
        prices2 = [h["close"] for h in history2]

        prices1.reverse()
        prices2.reverse()

        # Take lookback period
        prices1 = prices1[-lookback_days:]
        prices2 = prices2[-lookback_days:]

        if len(prices1) < lookback_days or len(prices2) < lookback_days:
            return {"error": "Insufficient data"}

        # Create series
        s1 = pd.Series(prices1)
        s2 = pd.Series(prices2)

        # Normalize to 100
        s1_norm = (s1 / s1.iloc[0]) * 100
        s2_norm = (s2 / s2.iloc[0]) * 100

        # Calculate spread
        spread = s1_norm - s2_norm

        # Z-score of spread
        spread_mean = spread.mean()
        spread_std = spread.std()
        z_score = (spread.iloc[-1] - spread_mean) / spread_std if spread_std > 0 else 0

        # Rolling correlation (20-day window)
        returns1 = s1.pct_change().dropna()
        returns2 = s2.pct_change().dropna()

        rolling_corr = returns1.rolling(window=20).corr(returns2)
        current_rolling_corr = rolling_corr.iloc[-1]

        # Overall correlation
        overall_corr = returns1.corr(returns2)

        return {
            "ticker1": ticker1,
            "ticker2": ticker2,
            "current_spread": round(spread.iloc[-1], 4),
            "spread_mean": round(spread_mean, 4),
            "spread_std": round(spread_std, 4),
            "z_score": round(z_score, 4),
            "rolling_correlation_20d": round(current_rolling_corr, 4),
            "overall_correlation": round(overall_corr, 4),
            "spread_history": spread.tail(30).tolist(),  # Last 30 days
        }
    except Exception as e:
        logger.error(f"Error getting pair details for {ticker1}/{ticker2}: {e}")
        return {"error": str(e)}
