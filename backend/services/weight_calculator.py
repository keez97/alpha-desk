"""
Regime-adaptive factor weight calculator for stock grading.

Base weights derived from academic factor literature:
- Fama-French Five-Factor Model (1993, 2015): HML, RMW, CMA premiums
- Sloan (1996): Accruals anomaly (~4% annual spread)
- Jegadeesh & Titman (1993): Momentum premium (~7% but high crash risk)
- Asness et al. (2019): Quality factor robustness

Regime detection uses VIX and yield curve spread to shift weights
toward factors that matter most in the current market environment.
"""

import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Static base weights derived from long-run factor premium magnitudes
# and Sharpe ratios. A higher base weight = more reliably predicts returns.
BASE_WEIGHTS: Dict[str, float] = {
    "valuation": 0.20,        # HML premium: ~3.5% annualized (1963-2023)
    "growth_quality": 0.12,   # Growth is priced in efficiently; lower base weight
    "profitability": 0.18,    # RMW premium: ~3.1% annualized; very robust
    "balance_sheet": 0.10,    # CMA/investment factor: ~2.5% annualized
    "earnings_quality": 0.13, # Sloan accruals anomaly: ~4% spread
    "momentum": 0.12,         # UMD premium: ~7% but high crash risk, discounted
    "positioning": 0.07,      # Short interest predicts returns but data is noisy
    "catalysts": 0.08,        # Event-driven; hard to backtest systematically
}

# How weights shift in different market regimes
REGIME_ADJUSTMENTS: Dict[str, Dict[str, float]] = {
    "risk_off": {
        # In risk-off: balance sheet strength, earnings quality, and valuation
        # discipline matter more. Momentum and growth get punished.
        "valuation": +0.03,
        "growth_quality": -0.04,
        "profitability": +0.02,
        "balance_sheet": +0.05,
        "earnings_quality": +0.04,
        "momentum": -0.05,
        "positioning": +0.00,
        "catalysts": -0.03,
    },
    "risk_on": {
        # In risk-on: growth and momentum get rewarded, balance sheet
        # concerns fade (cheap capital), valuation discipline loosens.
        "valuation": -0.04,
        "growth_quality": +0.04,
        "profitability": -0.01,
        "balance_sheet": -0.03,
        "earnings_quality": -0.03,
        "momentum": +0.04,
        "positioning": +0.01,
        "catalysts": +0.02,
    },
    "neutral": {},  # Use base weights as-is
}

# Regime detection thresholds
VIX_HIGH_THRESHOLD = 25.0   # Above this = elevated fear
VIX_LOW_THRESHOLD = 18.0    # Below this = complacency
YIELD_SPREAD_INVERSION = 0.0  # 10Y-2Y spread below 0 = inverted
YIELD_SPREAD_STEEP = 0.5      # Above this = steepening curve


def detect_regime(vix: float = None, yield_10y: float = None, yield_2y: float = None) -> str:
    """
    Detect current market regime from macro indicators.

    Returns: "risk_off", "risk_on", or "neutral"
    """
    if vix is None:
        return "neutral"

    yield_spread = None
    if yield_10y is not None and yield_2y is not None:
        yield_spread = yield_10y - yield_2y

    # Risk-off: high VIX + inverted/flat curve
    if vix > VIX_HIGH_THRESHOLD:
        if yield_spread is not None and yield_spread < YIELD_SPREAD_INVERSION:
            return "risk_off"
        # High VIX alone still leans risk-off
        return "risk_off"

    # Risk-on: low VIX + steepening curve
    if vix < VIX_LOW_THRESHOLD:
        if yield_spread is not None and yield_spread > YIELD_SPREAD_STEEP:
            return "risk_on"
        # Low VIX alone still leans risk-on
        return "risk_on"

    return "neutral"


def get_weights(vix: float = None, yield_10y: float = None, yield_2y: float = None) -> Tuple[Dict[str, float], str]:
    """
    Calculate regime-adaptive dimension weights.

    Returns: (weights_dict, regime_name)
    """
    regime = detect_regime(vix, yield_10y, yield_2y)
    weights = BASE_WEIGHTS.copy()

    adjustments = REGIME_ADJUSTMENTS.get(regime, {})
    for dim, adj in adjustments.items():
        weights[dim] = max(0.03, weights[dim] + adj)  # Floor at 3% — no dimension is ever zero

    # Renormalize to sum to 1.0
    total = sum(weights.values())
    weights = {k: round(v / total, 4) for k, v in weights.items()}

    logger.info(f"Regime: {regime} | VIX: {vix} | Yield spread: {(yield_10y or 0) - (yield_2y or 0):.2f}")
    logger.info(f"Weights: {weights}")

    return weights, regime
