"""
Synthetic Estimation Engine.

When all live data sources fail, this module generates statistically-grounded
estimates instead of returning hardcoded mock values. Uses FRED macro data
and cross-asset statistical relationships to produce directionally-informed
estimates.

Key principle: Better to show an estimate labeled "estimated" with real macro
context than a static mock that could be directionally wrong.

Models:
  1. VIX-based overnight gap estimation (VIX → expected overnight volatility)
  2. VIX-regime-based options skew estimation
  3. FRED yield curve → cross-asset momentum estimation
  4. Breadth estimation from VIX regime + recent trend
"""

import logging
import math
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.services import fred_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Overnight Returns Estimation
# ---------------------------------------------------------------------------
def estimate_overnight_returns(tickers: Dict[str, str]) -> Dict[str, Any]:
    """
    Estimate overnight returns using VIX-implied volatility scaling.

    VIX represents annualized expected S&P 500 volatility.
    Daily volatility ≈ VIX / √252
    Overnight gap is typically 30-50% of daily vol.

    Uses FRED VIX to scale expected gaps, with realistic cross-sectional
    dispersion. Returns estimates labeled as "estimated".
    """
    vix = fred_service.get_vix()
    if vix is None:
        vix = 20.0  # Long-run average

    # Daily implied vol (annualized VIX / sqrt(252))
    daily_vol = vix / math.sqrt(252)

    # Overnight gap is ~35% of daily vol on average
    overnight_vol = daily_vol * 0.35

    # VIX regime shifts the mean
    # High VIX (>25): mean slightly negative (fear)
    # Low VIX (<15): mean slightly positive (complacency → drift up)
    if vix > 30:
        mean_shift = -0.15  # Stressed markets tend to gap down
    elif vix > 25:
        mean_shift = -0.08
    elif vix < 15:
        mean_shift = 0.05
    else:
        mean_shift = 0.02  # Slight upward drift in normal markets

    # Beta multipliers for different assets relative to SPY
    beta_map = {
        "SPY": 1.0, "QQQ": 1.25, "IWM": 1.3, "DIA": 0.85,
        "XLK": 1.2, "XLV": 0.7, "XLF": 1.1, "XLY": 1.15,
        "XLP": 0.55, "XLE": 1.4, "XLRE": 0.9, "XLI": 0.95,
        "XLU": 0.5, "XLC": 1.1,
    }

    # Generate correlated estimates using a common market factor
    # Use a seeded random based on date so estimates are stable within a day
    today_seed = int(datetime.now(timezone.utc).strftime("%Y%m%d"))
    rng = random.Random(today_seed)
    market_factor = rng.gauss(mean_shift, overnight_vol)

    indices_data = []
    gaps_up = 0
    gaps_down = 0

    for ticker, name in tickers.items():
        beta = beta_map.get(ticker, 1.0)

        # Correlated return = beta * market_factor + idiosyncratic noise
        idio_vol = overnight_vol * 0.3  # 30% idiosyncratic
        idio_shock = rng.gauss(0, idio_vol)
        overnight_return = beta * market_factor + idio_shock

        # Historical stats (scaled by VIX regime)
        avg_overnight = mean_shift * beta * 0.5
        std_overnight = overnight_vol * beta

        z_score = (overnight_return - avg_overnight) / std_overnight if std_overnight > 0 else 0
        is_outlier = abs(z_score) > 2.0
        direction = "up" if overnight_return > 0 else "down"

        if direction == "up":
            gaps_up += 1
        else:
            gaps_down += 1

        indices_data.append({
            "ticker": ticker,
            "name": name,
            "overnight_return_pct": round(overnight_return, 3),
            "avg_overnight": round(avg_overnight, 3),
            "std_overnight": round(std_overnight, 3),
            "z_score": round(z_score, 2),
            "is_outlier": is_outlier,
            "direction": direction,
        })

    notable_gaps = [
        {"ticker": d["ticker"], "overnight_return_pct": d["overnight_return_pct"],
         "z_score": d["z_score"], "direction": d["direction"]}
        for d in indices_data if d["is_outlier"]
    ]
    notable_gaps.sort(key=lambda x: abs(x["z_score"]), reverse=True)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "indices": indices_data,
        "summary": {
            "total_tracked": len(indices_data),
            "gaps_up": gaps_up,
            "gaps_down": gaps_down,
            "net_direction": "up" if gaps_up > gaps_down else ("down" if gaps_down > gaps_up else "neutral"),
            "notable_gaps": notable_gaps[:5],
        },
        "data_source": "estimated",
        "estimation_basis": f"VIX={vix:.1f}, daily_vol={daily_vol:.2f}%",
    }


# ---------------------------------------------------------------------------
# 2. Options Flow Estimation
# ---------------------------------------------------------------------------
def estimate_options_flow() -> Dict[str, Any]:
    """
    Estimate options flow metrics from VIX regime.

    VIX regime strongly predicts:
    - IV skew (higher VIX → steeper put skew)
    - Put/call ratio (higher VIX → more put buying)
    - GEX (higher VIX → more negative GEX)

    Based on empirical relationships from CBOE published research.
    """
    vix = fred_service.get_vix()
    if vix is None:
        vix = 20.0

    vix_history = fred_service.get_vix_history(lookback_days=30)

    # VIX percentile determines regime
    if vix_history:
        vix_percentile = sum(1 for v in vix_history if v <= vix) / len(vix_history) * 100
    else:
        vix_percentile = 50

    # IV skew scales with VIX (empirical: skew ≈ 0.005 * VIX)
    # Normal markets: 0.10-0.15, Stressed: 0.25-0.40
    iv_skew = min(0.8, max(0.05, 0.005 * vix + 0.02))

    # Put-call ratio: normal ~0.9-1.1, fear ~1.3-1.8
    if vix > 30:
        put_call_ratio = 1.3 + (vix - 30) * 0.02
    elif vix > 20:
        put_call_ratio = 1.0 + (vix - 20) * 0.03
    else:
        put_call_ratio = 0.85 + vix * 0.005

    put_call_ratio = round(min(2.0, max(0.5, put_call_ratio)), 3)

    # Volume imbalance (inverse of put/call)
    volume_imbalance = round(1 / put_call_ratio, 3)

    # GEX estimation: high VIX → negative GEX
    if vix > 30:
        gex_value = -200 - (vix - 30) * 20
        gex_signal = "negative"
    elif vix > 22:
        gex_value = 50 - (vix - 22) * 30
        gex_signal = "negative" if gex_value < -100 else "neutral"
    else:
        gex_value = 150 + (22 - vix) * 10
        gex_signal = "positive"

    # Overall signal
    details = []
    score = 0

    if put_call_ratio > 1.2:
        score -= 1
        details.append(f"Elevated put volume estimated ({put_call_ratio:.2f}x)")
    elif put_call_ratio < 0.8:
        score += 1
        details.append(f"Call-heavy volume estimated ({1/put_call_ratio:.2f}x)")

    if iv_skew > 0.2:
        score -= 1
        details.append(f"Put skew elevated (est. {iv_skew:.2f} from VIX={vix:.0f})")

    if gex_signal == "positive":
        score += 1
        details.append(f"GEX estimated positive ({gex_value:.0f})")
    elif gex_signal == "negative":
        score -= 1
        details.append(f"GEX estimated negative ({gex_value:.0f})")

    signal = "bullish" if score > 1 else ("bearish" if score < -1 else "neutral")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ticker": "SPY",
        "spot_price": 0,  # Unknown without live price
        "iv_skew": round(iv_skew, 4),
        "put_call_ratio": put_call_ratio,
        "volume_imbalance": volume_imbalance,
        "gex_signal": gex_signal,
        "gex_value": round(gex_value, 1),
        "total_call_volume": 0,
        "total_put_volume": 0,
        "total_call_oi": 0,
        "total_put_oi": 0,
        "signal": signal,
        "details": details,
        "fred_vix": vix,
        "vix_percentile": round(vix_percentile, 1),
        "data_source": "estimated",
        "estimation_basis": f"VIX={vix:.1f} (P{vix_percentile:.0f})",
    }


# ---------------------------------------------------------------------------
# 3. Cross-Asset Momentum Estimation
# ---------------------------------------------------------------------------
def estimate_momentum() -> Dict[str, Any]:
    """
    Estimate cross-asset momentum from FRED macro indicators.

    Uses:
    - Yield curve slope → bond/equity momentum direction
    - VIX level → equity volatility regime
    - Credit spreads → risk appetite
    - Dollar index → dollar momentum
    - Oil prices → commodity momentum

    These macro factors explain ~40-60% of monthly asset class returns.
    """
    fred_data = fred_service.get_all_latest()

    vix = _get_fred_val(fred_data, "VIXCLS", 20.0)
    yield_curve = _get_fred_val(fred_data, "T10Y2Y", 0.5)
    credit_spread = _get_fred_val(fred_data, "BAMLH0A0HYM2", 3.5)
    dxy = _get_fred_val(fred_data, "DTWEXBGS", 105.0)
    oil = _get_fred_val(fred_data, "DCOILWTICO", 70.0)

    # Get historical for trend
    vix_hist = fred_service.get_values_only("VIXCLS", 60)
    dxy_hist = fred_service.get_values_only("DTWEXBGS", 60)
    oil_hist = fred_service.get_values_only("DCOILWTICO", 60)

    assets = []

    # SPY: VIX falling = positive momentum, credit tight = positive
    spy_score = 0
    if vix < 18:
        spy_score += 0.04
    elif vix < 25:
        spy_score += 0.01
    else:
        spy_score -= 0.03
    if credit_spread < 3.5:
        spy_score += 0.02
    elif credit_spread > 5:
        spy_score -= 0.04
    if yield_curve > 0:
        spy_score += 0.01

    assets.append(_momentum_entry("SPY", "S&P 500", "Equities", spy_score, spy_score * 2.5))

    # TLT: Inverted yield curve = bond buying, high VIX = flight to quality
    tlt_score = 0
    if yield_curve < 0:
        tlt_score += 0.03
    elif yield_curve < 0.5:
        tlt_score += 0.01
    if vix > 25:
        tlt_score += 0.02

    assets.append(_momentum_entry("TLT", "US Bonds (7-10yr)", "Fixed Income", tlt_score, tlt_score * 2))

    # GLD: High VIX + negative real rates = gold positive
    gld_score = 0
    if vix > 25:
        gld_score += 0.02
    if yield_curve < 0:
        gld_score += 0.015

    assets.append(_momentum_entry("GLD", "Gold", "Commodities", gld_score, gld_score * 2.5))

    # USO: Oil price trend
    if oil_hist and len(oil_hist) >= 20:
        oil_1m = (oil - oil_hist[-min(21, len(oil_hist))]) / oil_hist[-min(21, len(oil_hist))] if oil_hist[-min(21, len(oil_hist))] else 0
        oil_3m = (oil - oil_hist[0]) / oil_hist[0] if oil_hist[0] else 0
    else:
        oil_1m, oil_3m = 0.01, 0.02

    assets.append(_momentum_entry("USO", "Oil", "Commodities", oil_1m, oil_3m))

    # UUP: Dollar trend from FRED
    if dxy_hist and len(dxy_hist) >= 20:
        dxy_1m = (dxy - dxy_hist[-min(21, len(dxy_hist))]) / dxy_hist[-min(21, len(dxy_hist))] if dxy_hist[-min(21, len(dxy_hist))] else 0
        dxy_3m = (dxy - dxy_hist[0]) / dxy_hist[0] if dxy_hist[0] else 0
    else:
        dxy_1m, dxy_3m = 0, 0

    assets.append(_momentum_entry("UUP", "US Dollar", "Currencies", dxy_1m, dxy_3m))

    # BTC: Risk-on proxy — correlated with SPY in recent years
    btc_score = spy_score * 1.5  # Higher beta
    assets.append(_momentum_entry("BTC-USD", "Bitcoin", "Crypto", btc_score, btc_score * 3))

    # Generate signals
    from backend.services.cross_asset_momentum import _generate_signals
    try:
        signals = _generate_signals(assets)
    except Exception:
        signals = []

    positive_count = sum(1 for a in assets if a["state"] == "positive")
    negative_count = sum(1 for a in assets if a["state"] == "negative")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "assets": assets,
        "signals": signals,
        "matrix": {
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": len(assets) - positive_count - negative_count,
        },
        "data_source": "estimated",
        "estimation_basis": f"VIX={vix:.1f}, YC={yield_curve:.2f}, HY={credit_spread:.2f}",
    }


def _momentum_entry(ticker, name, asset_class, m1m, m3m):
    if m1m > 0.02 or m3m > 0.02:
        state = "positive"
    elif m1m < -0.02 or m3m < -0.02:
        state = "negative"
    else:
        state = "neutral"

    return {
        "ticker": ticker,
        "name": name,
        "asset_class": asset_class,
        "momentum_1m": round(m1m, 5),
        "momentum_3m": round(m3m, 5),
        "state": state,
    }


# ---------------------------------------------------------------------------
# 4. Market Breadth Estimation
# ---------------------------------------------------------------------------
def estimate_breadth() -> Dict[str, Any]:
    """
    Estimate market breadth from VIX + credit spread regime.

    Empirical relationships:
    - VIX < 15: ~62% advancing (strong breadth)
    - VIX 15-20: ~55% advancing (healthy)
    - VIX 20-25: ~48% advancing (mixed)
    - VIX 25-30: ~42% advancing (weak)
    - VIX > 30: ~35% advancing (very weak)

    Credit spreads modify: tight spreads (+5%), wide spreads (-5%)
    """
    vix = fred_service.get_vix()
    if vix is None:
        vix = 20.0

    credit_spread = fred_service.get_credit_spread()
    if credit_spread is None:
        credit_spread = 3.5

    # Base advancing pct from VIX
    if vix < 15:
        pct_adv = 62
    elif vix < 20:
        pct_adv = 55 + (20 - vix) * 1.4
    elif vix < 25:
        pct_adv = 48 + (25 - vix) * 1.4
    elif vix < 30:
        pct_adv = 42 + (30 - vix) * 1.2
    else:
        pct_adv = max(25, 42 - (vix - 30) * 0.7)

    # Credit spread modifier
    if credit_spread < 3.0:
        pct_adv += 3
    elif credit_spread > 5.0:
        pct_adv -= 5
    elif credit_spread > 4.0:
        pct_adv -= 2

    pct_adv = max(15, min(80, pct_adv))

    # Simulate from pct
    total = 100
    advances = int(total * pct_adv / 100)
    declines = total - advances - 3  # ~3 unchanged
    unchanged = 3
    net_advances = advances - declines

    ad_ratio = round(advances / max(declines, 1), 2)
    breadth_thrust = pct_adv > 61.5
    mcclellan = round(net_advances * 0.6, 1)

    if ad_ratio > 2.0:
        signal = "strongly_bullish"
    elif ad_ratio > 1.5:
        signal = "bullish"
    elif ad_ratio > 0.67:
        signal = "neutral"
    elif ad_ratio > 0.5:
        signal = "bearish"
    else:
        signal = "strongly_bearish"

    return {
        "advances": advances,
        "declines": declines,
        "unchanged": unchanged,
        "total": total,
        "ad_ratio": ad_ratio,
        "pct_advancing": round(pct_adv, 1),
        "pct_declining": round(declines / total * 100, 1),
        "breadth_thrust": breadth_thrust,
        "mcclellan": mcclellan,
        "net_advances": net_advances,
        "signal": signal,
        "sample_size": total,
        "data_source": "estimated",
        "estimation_basis": f"VIX={vix:.1f}, HY_OAS={credit_spread:.2f}",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_fred_val(fred_data: Dict, series_id: str, default: float) -> float:
    entry = fred_data.get(series_id)
    if isinstance(entry, dict) and entry.get("value") is not None:
        return entry["value"]
    return default
