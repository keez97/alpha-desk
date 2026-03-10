"""
Signal Confluence Engine - Cross-signal synthesis system.

Detects when macro, RRG rotation, and sector performance data align
on the same thesis, generating confluence signals with conviction scoring.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from backend.services.rrg_calculator import calculate_rrg, SECTOR_ETFS
from backend.services.data_provider import get_macro_data, get_sector_data

logger = logging.getLogger(__name__)


def analyze_macro_regime(macro_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze macro data to determine market regime and sector implications.

    Returns:
        Dict with regime, vix_signal, yield_signal, dollar_signal
    """
    if not macro_data:
        return {"regime": "neutral", "signals": {}}

    # Extract key indicators
    vix = macro_data.get("^VIX", {})
    tnx = macro_data.get("^TNX", {})
    irx = macro_data.get("^IRX", {})
    dx = macro_data.get("DX-Y.NYB", {})
    spy = macro_data.get("SPY", {})

    vix_pct = vix.get("pct_change", 0)
    tnx_pct = tnx.get("pct_change", 0)
    dx_pct = dx.get("pct_change", 0)
    spy_pct = spy.get("pct_change", 0)

    # Determine risk-on/off
    # Risk-on: VIX down, equities up, yields up (growth), dollar down
    risk_on = vix_pct < -1 and spy_pct > 0.5
    risk_off = vix_pct > 1 and spy_pct < -0.5

    # Yield regime
    yield_rising = tnx_pct > 0.5
    yield_falling = tnx_pct < -0.5

    # Dollar regime
    dollar_strengthening = dx_pct > 0.5
    dollar_weakening = dx_pct < -0.5

    # Determine overall regime
    if risk_on:
        regime = "risk-on"
    elif risk_off:
        regime = "risk-off"
    else:
        regime = "neutral"

    return {
        "regime": regime,
        "risk_on": risk_on,
        "risk_off": risk_off,
        "vix_pct": vix_pct,
        "vix_signal": "bullish" if vix_pct < 0 else "bearish" if vix_pct > 0 else "neutral",
        "yield_pct": tnx_pct,
        "yield_rising": yield_rising,
        "dollar_pct": dx_pct,
        "dollar_weakening": dollar_weakening,
        "equity_pct": spy_pct,
    }


def get_sector_impact_from_regime(
    regime: Dict[str, Any],
    sector_ticker: str
) -> str:
    """Determine how macro regime impacts specific sector."""
    risk_on = regime.get("risk_on", False)
    risk_off = regime.get("risk_off", False)
    yield_rising = regime.get("yield_rising", False)
    dollar_weakening = regime.get("dollar_weakening", False)

    # Sector-specific macro impacts
    if sector_ticker == "XLE":  # Energy
        if dollar_weakening:
            return "Bullish (weak dollar favors commodities)"
        if yield_rising:
            return "Neutral (rising yields support demand)"
        return "Neutral"

    elif sector_ticker == "XLF":  # Financials
        if yield_rising:
            return "Bullish (rising yields expand net interest margins)"
        if risk_off:
            return "Bearish (risk-off hurts financial markets)"
        return "Neutral"

    elif sector_ticker == "XLK":  # Tech
        if risk_off:
            return "Bearish (risk-off rotation out of growth)"
        if yield_rising:
            return "Bearish (rising real rates pressure growth valuations)"
        if risk_on:
            return "Bullish (growth favored in risk-on environment)"
        return "Neutral"

    elif sector_ticker in ("XLY", "XLC"):  # Discretionary, Comms
        if risk_on:
            return "Bullish (growth/cyclical strength)"
        if risk_off:
            return "Bearish (defensive positioning)"
        return "Neutral"

    elif sector_ticker in ("XLP", "XLU"):  # Staples, Utilities
        if risk_off:
            return "Bullish (defensive safe havens)"
        if risk_on:
            return "Bearish (rotation out of defensives)"
        return "Neutral"

    elif sector_ticker == "XLV":  # Healthcare
        # Healthcare is relatively regime-agnostic
        return "Neutral (healthcare is defensive)"

    elif sector_ticker == "XLRE":  # Real Estate
        if yield_rising:
            return "Bearish (higher discount rates hurt RE valuations)"
        if risk_off:
            return "Bearish (rate-sensitive)"
        return "Neutral"

    elif sector_ticker == "XLI":  # Industrials
        if risk_on:
            return "Bullish (cyclical strength)"
        if risk_off:
            return "Bearish (cyclical weakness)"
        return "Neutral"

    return "Neutral"


def score_conviction(signal_count: int, signal_strength: float = 1.0) -> str:
    """
    Score conviction based on number of aligned signals and their strength.

    Args:
        signal_count: Number of aligned signals (0-3)
        signal_strength: Average strength/magnitude of signals (0-1, where 1 is strongest)
    """
    # Adjust conviction based on signal strength
    adjusted_count = signal_count * (0.5 + signal_strength * 0.5)

    if adjusted_count >= 2.5:
        return "HIGH"
    elif adjusted_count >= 1.5:
        return "MEDIUM"
    else:
        return "LOW"


def _calculate_signal_strength(perf_pct: float, rs_momentum: float, macro_impact: str) -> float:
    """Calculate normalized signal strength (0-1) based on magnitude."""
    # Performance strength: 0-1 based on absolute daily move
    perf_strength = min(abs(perf_pct) / 2.0, 1.0)  # Normalize to 2% daily move

    # RS momentum strength: 0-1 based on magnitude
    rs_strength = min(abs(rs_momentum) / 20.0, 1.0)  # Normalize to 20% momentum

    # Macro impact strength: 0.5 = neutral, 1.0 = strong signal
    macro_strength = 1.0 if "strong" in macro_impact.lower() or "bullish" in macro_impact.lower() or "bearish" in macro_impact.lower() else 0.5

    # Average strength
    return (perf_strength + rs_strength + macro_strength) / 3.0


def generate_confluence_signals(
    rrg_data: Dict[str, Any],
    sector_data: List[Dict[str, Any]],
    macro_regime: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Generate confluence signals by cross-referencing RRG, sector performance, and macro.

    Returns:
        List of confluence signals with thesis, direction, conviction, and supporting signals
    """
    signals = []

    # Build sector data map for quick lookup
    sector_map = {s["ticker"]: s for s in sector_data}

    # Build RRG data map
    rrg_map = {s["ticker"]: s for s in rrg_data.get("sectors", [])}

    # Analyze each sector
    for sector_ticker, sector_name in SECTOR_ETFS.items():
        sector_perf = sector_map.get(sector_ticker, {})
        rrg_sector = rrg_map.get(sector_ticker, {})

        if not sector_perf or not rrg_sector:
            continue

        # Collect signals
        supporting_signals = []
        direction_votes = {"bullish": 0, "bearish": 0, "neutral": 0}

        # --- RRG Signal ---
        quadrant = rrg_sector.get("quadrant", "Unknown")
        rs_momentum = rrg_sector.get("rs_momentum", 0)
        rs_ratio = rrg_sector.get("rs_ratio", 100)

        rrg_direction = "neutral"
        if quadrant == "Strengthening":
            rrg_direction = "bullish"
            supporting_signals.append({
                "source": "RRG",
                "detail": f"Strengthening quadrant (RS Ratio: {rs_ratio:.1f}, Momentum: {rs_momentum:.1f})",
                "sentiment": "bullish"
            })
            direction_votes["bullish"] += 1
        elif quadrant == "Weakening":
            rrg_direction = "bearish"
            supporting_signals.append({
                "source": "RRG",
                "detail": f"Weakening quadrant (RS Ratio: {rs_ratio:.1f}, Momentum: {rs_momentum:.1f})",
                "sentiment": "bearish"
            })
            direction_votes["bearish"] += 1
        elif quadrant == "Recovering":
            rrg_direction = "bullish"
            supporting_signals.append({
                "source": "RRG",
                "detail": f"Recovering quadrant (RS Ratio: {rs_ratio:.1f}, Momentum: {rs_momentum:.1f})",
                "sentiment": "bullish"
            })
            direction_votes["bullish"] += 1
        elif quadrant == "Deteriorating":
            rrg_direction = "bearish"
            supporting_signals.append({
                "source": "RRG",
                "detail": f"Deteriorating quadrant (RS Ratio: {rs_ratio:.1f}, Momentum: {rs_momentum:.1f})",
                "sentiment": "bearish"
            })
            direction_votes["bearish"] += 1

        # --- Sector Performance Signal ---
        daily_pct = sector_perf.get("daily_pct_change", 0)
        perf_direction = "neutral"
        if daily_pct > 0.5:
            perf_direction = "bullish"
            supporting_signals.append({
                "source": "Performance",
                "detail": f"{sector_ticker} up {daily_pct:.2f}% today",
                "sentiment": "bullish"
            })
            direction_votes["bullish"] += 1
        elif daily_pct < -0.5:
            perf_direction = "bearish"
            supporting_signals.append({
                "source": "Performance",
                "detail": f"{sector_ticker} down {daily_pct:.2f}% today",
                "sentiment": "bearish"
            })
            direction_votes["bearish"] += 1

        # --- Macro Regime Signal ---
        sector_impact = get_sector_impact_from_regime(macro_regime, sector_ticker)
        macro_direction = "neutral"
        if "Bullish" in sector_impact:
            macro_direction = "bullish"
            supporting_signals.append({
                "source": "Macro",
                "detail": sector_impact,
                "sentiment": "bullish"
            })
            direction_votes["bullish"] += 1
        elif "Bearish" in sector_impact:
            macro_direction = "bearish"
            supporting_signals.append({
                "source": "Macro",
                "detail": sector_impact,
                "sentiment": "bearish"
            })
            direction_votes["bearish"] += 1

        # Determine overall direction
        overall_direction = "neutral"
        if direction_votes["bullish"] > direction_votes["bearish"]:
            overall_direction = "bullish"
        elif direction_votes["bearish"] > direction_votes["bullish"]:
            overall_direction = "bearish"

        # Only include if we have at least 2 signals
        if len(supporting_signals) >= 2:
            # ENHANCED: Calculate signal strength to differentiate between stocks
            signal_strength = _calculate_signal_strength(
                daily_pct,
                rs_momentum,
                sector_impact
            )
            conviction = score_conviction(len(supporting_signals), signal_strength)

            # Generate thesis statement with specific rationale
            if overall_direction == "bullish":
                thesis = f"Overweight {sector_name} — {signal_strength*100:.0f}% confluence strength"
            elif overall_direction == "bearish":
                thesis = f"Underweight {sector_name} — {signal_strength*100:.0f}% confluence strength"
            else:
                thesis = f"Neutral {sector_name}"

            # ENHANCED: More specific suggested action based on signal strength
            if conviction == "HIGH":
                if signal_strength > 0.8:
                    suggested_action = f"Very Strong {overall_direction} — Consider significant {overall_direction} positioning"
                else:
                    suggested_action = f"Strong {overall_direction} signal — Consider increasing {overall_direction} exposure"
            elif conviction == "MEDIUM":
                suggested_action = f"Moderate {overall_direction} signal — Consider modest {overall_direction} positioning"
            else:
                suggested_action = f"Weak signal — Wait for stronger confirmation before trading"

            signals.append({
                "thesis": thesis,
                "direction": overall_direction,
                "conviction": conviction,
                "strength": signal_strength,  # NEW: explicit strength metric
                "sector": sector_name,
                "sectorTicker": sector_ticker,
                "signals": supporting_signals,
                "suggestedAction": suggested_action,
                "timeframe": "1-5 days",
                "confidence": f"{signal_strength*100:.0f}%"  # NEW: human-readable confidence
            })

    return signals


def get_signal_matrix_data(
    rrg_data: Dict[str, Any],
    sector_data: List[Dict[str, Any]],
    macro_regime: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Generate signal matrix data for the matrix view.

    Returns:
        List of rows with ticker, name, RRG quadrant, macro impact, performance, and confluence
    """
    matrix_rows = []

    sector_map = {s["ticker"]: s for s in sector_data}
    rrg_map = {s["ticker"]: s for s in rrg_data.get("sectors", [])}

    for sector_ticker, sector_name in SECTOR_ETFS.items():
        sector_perf = sector_map.get(sector_ticker, {})
        rrg_sector = rrg_map.get(sector_ticker, {})

        if not sector_perf or not rrg_sector:
            continue

        # RRG metrics
        quadrant = rrg_sector.get("quadrant", "Unknown")
        rs_momentum = rrg_sector.get("rs_momentum", 0)

        # Macro impact
        sector_impact = get_sector_impact_from_regime(macro_regime, sector_ticker)
        macro_sentiment = "bullish" if "Bullish" in sector_impact else "bearish" if "Bearish" in sector_impact else "neutral"

        # Performance
        daily_pct = sector_perf.get("daily_pct_change", 0)

        # Determine confluence direction and count
        direction_votes = {"bullish": 0, "bearish": 0}

        # RRG vote
        if quadrant in ("Strengthening", "Recovering"):
            direction_votes["bullish"] += 1
        elif quadrant in ("Weakening", "Deteriorating"):
            direction_votes["bearish"] += 1

        # Performance vote
        if daily_pct > 0.5:
            direction_votes["bullish"] += 1
        elif daily_pct < -0.5:
            direction_votes["bearish"] += 1

        # Macro vote
        if macro_sentiment == "bullish":
            direction_votes["bullish"] += 1
        elif macro_sentiment == "bearish":
            direction_votes["bearish"] += 1

        # Overall confluence
        signal_count = max(direction_votes["bullish"], direction_votes["bearish"])
        if direction_votes["bullish"] > direction_votes["bearish"]:
            confluence = "bullish"
        elif direction_votes["bearish"] > direction_votes["bullish"]:
            confluence = "bearish"
        else:
            confluence = "neutral"

        # ENHANCED: Calculate strength for matrix display
        signal_strength = _calculate_signal_strength(daily_pct, rs_momentum, sector_impact)
        conviction = score_conviction(signal_count, signal_strength)

        matrix_rows.append({
            "ticker": sector_ticker,
            "name": sector_name,
            "rrg": {
                "quadrant": quadrant,
                "momentum": rs_momentum,
            },
            "macro": {
                "regime": macro_regime.get("regime", "neutral"),
                "sectorImpact": sector_impact,
            },
            "performance": {
                "change1d": daily_pct,
                "change1m": 0,
            },
            "confluence": confluence,
            "signalCount": signal_count,
            "strength": signal_strength,  # NEW
            "conviction": conviction,  # NEW
            "confidence": f"{signal_strength*100:.0f}%"  # NEW
        })

    return matrix_rows


def calculate_confluence_signals() -> Dict[str, Any]:
    """
    Main entry point: fetch all data and generate confluence analysis.

    Returns:
        Dict with confluence_signals and matrix_data, with diagnostics if empty
    """
    try:
        # Fetch data from all sources
        macro_data = get_macro_data()
        sector_data = get_sector_data(period="1D")
        rrg_result = calculate_rrg(list(SECTOR_ETFS.keys()), benchmark="SPY", weeks=10)
        rrg_data = rrg_result if "error" not in rrg_result else {"sectors": []}

        if not macro_data or not sector_data or not rrg_data.get("sectors"):
            logger.warning("Missing data for confluence analysis")
            return {
                "confluence_signals": [],
                "matrix_data": [],
                "timestamp": datetime.utcnow().isoformat(),
                "macro_regime": {},
                "diagnostic": {
                    "issue": "Missing data sources",
                    "details": f"macro_data: {bool(macro_data)}, sector_data: {bool(sector_data)}, rrg_data: {bool(rrg_data.get('sectors'))}"
                }
            }

        # Analyze macro regime
        macro_regime = analyze_macro_regime(macro_data)

        # Generate confluence signals
        confluence_signals = generate_confluence_signals(
            rrg_data, sector_data, macro_regime
        )

        # Generate matrix data
        matrix_data = get_signal_matrix_data(rrg_data, sector_data, macro_regime)

        # ENHANCED: Provide diagnostic if no high-conviction signals found
        result = {
            "confluence_signals": confluence_signals,
            "matrix_data": matrix_data,
            "macro_regime": macro_regime,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if not confluence_signals or len(confluence_signals) == 0:
            # Generate diagnostic message
            high_conviction_count = sum(1 for s in confluence_signals if s.get("conviction") == "HIGH")
            medium_conviction_count = sum(1 for s in confluence_signals if s.get("conviction") == "MEDIUM")

            result["diagnostic"] = {
                "note": "No high-conviction confluence signals detected in current market environment",
                "matrix_available": len(matrix_data) > 0,
                "high_conviction_signals": high_conviction_count,
                "medium_conviction_signals": medium_conviction_count,
                "recommendation": "Review the signal matrix for MEDIUM conviction opportunities. High-conviction signals are rare — wait for multiple confirmations before trading."
            }
        else:
            # Count by conviction
            high_conv = sum(1 for s in confluence_signals if s.get("conviction") == "HIGH")
            med_conv = sum(1 for s in confluence_signals if s.get("conviction") == "MEDIUM")
            low_conv = len(confluence_signals) - high_conv - med_conv

            result["summary"] = {
                "total_signals": len(confluence_signals),
                "high_conviction": high_conv,
                "medium_conviction": med_conv,
                "low_conviction": low_conv,
            }

        return result

    except Exception as e:
        logger.error(f"Error calculating confluence signals: {e}")
        return {
            "confluence_signals": [],
            "matrix_data": [],
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "diagnostic": {
                "issue": "Error calculating confluence",
                "details": str(e)
            }
        }
