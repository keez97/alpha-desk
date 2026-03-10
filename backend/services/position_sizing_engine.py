"""
Position Sizing Engine - Calculate position sizes based on multi-factor exposures.

Features:
- Composite factor scoring (Momentum, Volatility, Mean Reversion, Volume Profile)
- Position sizing categories (Full, Three-Quarter, Half, Quarter, Avoid)
- Kelly Criterion approximation for risk adjustment
- Stop loss recommendations based on volatility
"""

import logging
from typing import Dict, List, Any, Optional
import numpy as np

from backend.services.stock_factors import calculate_stock_factors, REFERENCE_RANGES

logger = logging.getLogger(__name__)


def calculate_position_sizing(
    ticker: str,
    portfolio_value: float = 100000.0
) -> Optional[Dict[str, Any]]:
    """
    Calculate position sizing recommendation for a ticker based on factor exposures.

    Args:
        ticker: Stock ticker symbol
        portfolio_value: Total portfolio value in dollars (default: $100,000)

    Returns:
        Dictionary with position sizing details or None if calculation fails
    """
    try:
        # Get factor exposures
        factors = calculate_stock_factors(ticker)
        if not factors or len(factors) < 4:
            logger.warning(f"Insufficient factor data for {ticker}")
            return None

        # Extract factor percentiles (0-100)
        factor_map = {f["name"]: f for f in factors}

        momentum_percentile = factor_map.get("Momentum (12-1)", {}).get("percentile", 50)
        volatility_percentile = factor_map.get("Volatility (30D Ann)", {}).get("percentile", 50)
        mean_reversion_percentile = factor_map.get("Mean Reversion (Price/SMA200)", {}).get("percentile", 50)
        volume_percentile = factor_map.get("Volume Profile (20D)", {}).get("percentile", 50)

        # Invert volatility (high volatility = lower score)
        volatility_score = 100 - volatility_percentile

        # Calculate composite score with weights
        # Momentum: 30%, Volatility (inverted): 20%, Mean Reversion: 25%, Volume: 25%
        composite_score = (
            momentum_percentile * 0.30 +
            volatility_score * 0.20 +
            mean_reversion_percentile * 0.25 +
            volume_percentile * 0.25
        )

        composite_score = max(0, min(100, composite_score))  # Clamp to 0-100

        # Map composite score to position size category
        size_category, size_pct = _get_position_size_category(composite_score)

        # Calculate position value
        position_value = (size_pct / 100.0) * portfolio_value

        # Calculate Kelly Criterion approximation
        # Edge = momentum as proxy for edge
        # Odds = volatility as proxy for odds (higher vol = worse odds)
        momentum_value = factor_map.get("Momentum (12-1)", {}).get("value", 0)
        volatility_value = factor_map.get("Volatility (30D Ann)", {}).get("value", 20)

        kelly_fraction = _calculate_kelly_fraction(
            edge=momentum_value,
            volatility=volatility_value
        )

        # Calculate stop loss based on volatility (2x ATR approximation)
        # ATR approximation: volatility_value * current_price / 100 (simplified)
        # For now, use volatility as basis
        stop_loss_pct = min(10.0, volatility_value * 2)  # Cap at 10%

        # Build factor breakdown
        factor_breakdown = [
            {
                "name": "Momentum",
                "value": factor_map.get("Momentum (12-1)", {}).get("value", 0),
                "percentile": momentum_percentile,
                "weight": 0.30,
                "contribution": momentum_percentile * 0.30
            },
            {
                "name": "Volatility",
                "value": factor_map.get("Volatility (30D Ann)", {}).get("value", 0),
                "percentile": volatility_percentile,
                "weight": 0.20,
                "contribution": volatility_score * 0.20
            },
            {
                "name": "Mean Reversion",
                "value": factor_map.get("Mean Reversion (Price/SMA200)", {}).get("value", 0),
                "percentile": mean_reversion_percentile,
                "weight": 0.25,
                "contribution": mean_reversion_percentile * 0.25
            },
            {
                "name": "Volume Profile",
                "value": factor_map.get("Volume Profile (20D)", {}).get("value", 0),
                "percentile": volume_percentile,
                "weight": 0.25,
                "contribution": volume_percentile * 0.25
            }
        ]

        # Generate risk notes
        risk_notes = _generate_risk_notes(
            momentum_percentile=momentum_percentile,
            volatility_percentile=volatility_percentile,
            mean_reversion_percentile=mean_reversion_percentile,
            volume_percentile=volume_percentile,
            composite_score=composite_score
        )

        return {
            "ticker": ticker,
            "compositeScore": round(composite_score, 1),
            "sizeCategory": size_category,
            "sizePct": size_pct,
            "positionValue": round(position_value, 2),
            "kellyFraction": round(kelly_fraction, 3),
            "stopLoss": round(stop_loss_pct, 2),
            "factorBreakdown": factor_breakdown,
            "riskNotes": risk_notes
        }

    except Exception as e:
        logger.error(f"Error calculating position sizing for {ticker}: {e}")
        return None


def _get_position_size_category(score: float) -> tuple[str, float]:
    """
    Map composite score to position size category and percentage.

    Score ranges:
    - 80-100: Full Size (5% of portfolio)
    - 60-79: Three-Quarter (3.75%)
    - 40-59: Half Size (2.5%)
    - 20-39: Quarter Size (1.25%)
    - 0-19: Avoid (0%)

    Args:
        score: Composite factor score (0-100)

    Returns:
        Tuple of (category_name, size_percentage)
    """
    if score >= 80:
        return ("Full Size", 5.0)
    elif score >= 60:
        return ("Three-Quarter", 3.75)
    elif score >= 40:
        return ("Half Size", 2.5)
    elif score >= 20:
        return ("Quarter Size", 1.25)
    else:
        return ("Avoid", 0.0)


def _calculate_kelly_fraction(edge: float, volatility: float) -> float:
    """
    Calculate Kelly Criterion fraction for position sizing.

    Simplified Kelly: f* = edge / odds

    Edge proxy: momentum value
    Odds proxy: volatility (inverse relationship)

    Args:
        edge: Momentum value as edge proxy
        volatility: Volatility as odds proxy

    Returns:
        Kelly fraction (should typically be < 0.25 for practical use)
    """
    # Clamp volatility to avoid division issues
    if volatility <= 0:
        volatility = 10.0

    # Normalize edge to probability-like range (-1 to 1)
    edge_normalized = edge / 100.0

    # Basic Kelly: f* = edge / odds
    # Since momentum can be negative, we add 100 to work in positive range
    kelly = ((edge + 100) / 200.0) / (1 + volatility / 100.0)

    # Clamp Kelly to reasonable range
    kelly = max(0.01, min(0.25, kelly))

    return kelly


def _generate_risk_notes(
    momentum_percentile: float,
    volatility_percentile: float,
    mean_reversion_percentile: float,
    volume_percentile: float,
    composite_score: float
) -> List[str]:
    """
    Generate risk notes based on factor exposures.

    Args:
        momentum_percentile: Momentum percentile (0-100)
        volatility_percentile: Volatility percentile (0-100)
        mean_reversion_percentile: Mean reversion percentile (0-100)
        volume_percentile: Volume profile percentile (0-100)
        composite_score: Composite score (0-100)

    Returns:
        List of risk note strings
    """
    notes = []

    # Volatility warnings
    if volatility_percentile > 75:
        notes.append("High volatility - consider tighter stops")

    # Volume warnings
    if volume_percentile < 25:
        notes.append("Low volume profile - liquidity risk")
    elif volume_percentile < 50:
        notes.append("Below-average volume - monitor liquidity")

    # Mean reversion warnings
    if mean_reversion_percentile > 80:
        notes.append("Price well above 200-day SMA - mean reversion risk")
    elif mean_reversion_percentile < 20:
        notes.append("Price well below 200-day SMA - potential support test")

    # Momentum warnings
    if momentum_percentile > 80:
        notes.append("Strong momentum - vulnerable to pullbacks")
    elif momentum_percentile < 20:
        notes.append("Weak momentum - trending lower")

    # Composite score warnings
    if composite_score < 30 and volume_percentile > 60:
        notes.append("Weak factors despite good volume - pass or reduce size")

    # Conflicting signals
    if momentum_percentile > 70 and mean_reversion_percentile > 70:
        notes.append("Strong momentum but price extended - divergent signals")

    if not notes:
        notes.append("Factors appear balanced")

    return notes


def batch_position_sizing(
    tickers: List[str],
    portfolio_value: float = 100000.0
) -> Dict[str, Any]:
    """
    Calculate position sizing for multiple tickers.

    Args:
        tickers: List of ticker symbols
        portfolio_value: Total portfolio value in dollars

    Returns:
        Dictionary with results and summary
    """
    results = []
    total_allocation = 0.0

    for ticker in tickers:
        sizing = calculate_position_sizing(ticker, portfolio_value)
        if sizing:
            results.append(sizing)
            total_allocation += sizing["sizePct"]

    # Calculate utilization
    utilization_pct = (total_allocation / 100.0) * 100.0 if results else 0.0

    return {
        "results": results,
        "count": len(results),
        "totalAllocation": round(total_allocation, 2),
        "utilizationPct": round(min(100.0, utilization_pct), 2),
        "portfolioValue": portfolio_value
    }
