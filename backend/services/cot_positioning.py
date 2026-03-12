"""
COT (Commitments of Traders) Positioning Module – Live CFTC Data.

Fetches both Disaggregated Combined (for physical commodities) and TFF Combined
(Traders in Financial Futures) reports from the CFTC via the cot_reports library.

Tracks 20 markets across 6 categories: Equities, Rates, Energy, Metals,
Agriculture, and FX.

Calculates positioning percentiles across the full year of data, detects extreme
positioning (>90th / <10th percentile), and identifies commercial-speculative
divergences.

Report types used:
  • Disaggregated Futures-and-Options Combined  (191 columns, 4 trader groups)
  • TFF Futures-and-Options Combined             (87 columns, 5 trader groups)
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import numpy as np

from backend.services.cache import TTLCache

logger = logging.getLogger(__name__)

# COT positioning cache – weekly data, long TTL
_cot_cache = TTLCache()
_CACHE_TTL = 3600 * 4  # 4 hours (CFTC publishes weekly on Fridays)

# ---------------------------------------------------------------------------
# Categories & defaults
# ---------------------------------------------------------------------------
CATEGORIES = ["Equities", "Rates", "Energy", "Metals", "Agriculture", "FX"]
DEFAULT_MARKETS = ["ES", "NQ", "ZB", "GC", "CL", "NG", "6E", "DX"]

# ---------------------------------------------------------------------------
# Market definitions – maps our internal ticker to the CFTC market name,
# report type, category, and display sort order within category.
# ---------------------------------------------------------------------------
MARKETS: Dict[str, Dict[str, Any]] = {
    # ── Equities (TFF) ──
    "ES": {
        "name": "S&P 500 E-mini",
        "cftc_search": "E-MINI S&P 500",
        "report": "tff",
        "category": "Equities",
        "sort_order": 1,
    },
    "NQ": {
        "name": "Nasdaq-100 E-mini",
        "cftc_search": "NASDAQ MINI",
        "report": "tff",
        "category": "Equities",
        "sort_order": 2,
    },
    "RTY": {
        "name": "Russell 2000 E-mini",
        "cftc_search": "RUSSELL E-MINI",
        "report": "tff",
        "category": "Equities",
        "sort_order": 3,
    },
    # ── Rates (TFF) ──
    "ZB": {
        "name": "10Y Treasury Note",
        "cftc_search": "UST 10Y NOTE",
        "report": "tff",
        "category": "Rates",
        "sort_order": 1,
    },
    "ZN": {
        "name": "5Y Treasury Note",
        "cftc_search": "UST 5Y NOTE",
        "report": "tff",
        "category": "Rates",
        "sort_order": 2,
    },
    "ZF": {
        "name": "2Y Treasury Note",
        "cftc_search": "UST 2Y NOTE",
        "report": "tff",
        "category": "Rates",
        "sort_order": 3,
    },
    "US": {
        "name": "U.S. Treasury Bond",
        "cftc_search": "UST BOND - CHICAGO",
        "report": "tff",
        "category": "Rates",
        "sort_order": 4,
    },
    # ── Energy (Disaggregated) ──
    "CL": {
        "name": "Crude Oil (WTI)",
        "cftc_search": "CRUDE OIL, LIGHT SWEET",
        "report": "disagg",
        "category": "Energy",
        "sort_order": 1,
    },
    "NG": {
        "name": "Natural Gas",
        "cftc_search": "NAT GAS NYME",
        "report": "disagg",
        "category": "Energy",
        "sort_order": 2,
    },
    # ── Metals (Disaggregated) ──
    "GC": {
        "name": "Gold",
        "cftc_search": "GOLD - COMMODITY EXCHANGE",
        "report": "disagg",
        "category": "Metals",
        "sort_order": 1,
    },
    "SI": {
        "name": "Silver",
        "cftc_search": "SILVER - COMMODITY EXCHANGE",
        "report": "disagg",
        "category": "Metals",
        "sort_order": 2,
    },
    "HG": {
        "name": "Copper",
        "cftc_search": "COPPER- #1",
        "report": "disagg",
        "category": "Metals",
        "sort_order": 3,
    },
    # ── Agriculture (Disaggregated) ──
    "ZC": {
        "name": "Corn",
        "cftc_search": "CORN - CHICAGO",
        "report": "disagg",
        "category": "Agriculture",
        "sort_order": 1,
    },
    "ZS": {
        "name": "Soybeans",
        "cftc_search": "SOYBEANS - CHICAGO",
        "report": "disagg",
        "category": "Agriculture",
        "sort_order": 2,
    },
    "ZW": {
        "name": "Wheat (SRW)",
        "cftc_search": "WHEAT-SRW - CHICAGO",
        "report": "disagg",
        "category": "Agriculture",
        "sort_order": 3,
    },
    # ── FX (TFF) ──
    "6E": {
        "name": "Euro FX",
        "cftc_search": "EURO FX - CHICAGO MERCANTILE",
        "report": "tff",
        "category": "FX",
        "sort_order": 1,
    },
    "6J": {
        "name": "Japanese Yen",
        "cftc_search": "JAPANESE YEN - CHICAGO",
        "report": "tff",
        "category": "FX",
        "sort_order": 2,
    },
    "6B": {
        "name": "British Pound",
        "cftc_search": "BRITISH POUND - CHICAGO",
        "report": "tff",
        "category": "FX",
        "sort_order": 3,
    },
    "6A": {
        "name": "Australian Dollar",
        "cftc_search": "AUSTRALIAN DOLLAR",
        "report": "tff",
        "category": "FX",
        "sort_order": 4,
    },
    "DX": {
        "name": "U.S. Dollar Index",
        "cftc_search": "USD INDEX",
        "report": "tff",
        "category": "FX",
        "sort_order": 5,
    },
}


def _safe_int(val) -> int:
    """Convert a CFTC field value to int, handling whitespace and '.' (suppressed)."""
    try:
        s = str(val).strip()
        if s in (".", "", "nan", "None"):
            return 0
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def _safe_float(val) -> float:
    """Convert a CFTC field value to float."""
    try:
        s = str(val).strip()
        if s in (".", "", "nan", "None"):
            return 0.0
        return float(s)
    except (ValueError, TypeError):
        return 0.0


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
def _fetch_cftc_data() -> Dict[str, Any]:
    """
    Fetch current-year Disaggregated Combined + TFF Combined from CFTC.

    Returns dict with keys 'tff' and 'disagg', each a pandas DataFrame.
    Falls back to empty DataFrames on error.
    """
    import pandas as pd

    result: Dict[str, Any] = {"tff": pd.DataFrame(), "disagg": pd.DataFrame()}

    try:
        import cot_reports as cot
        current_year = datetime.now(timezone.utc).year

        logger.info(f"Fetching TFF Combined COT data for {current_year}...")
        tff_df = cot.cot_year(current_year, cot_report_type="traders_in_financial_futures_futopt")
        if tff_df is not None and len(tff_df) > 0:
            result["tff"] = tff_df
            logger.info(f"TFF data: {len(tff_df)} rows, {len(tff_df.columns)} columns")

        logger.info(f"Fetching Disaggregated Combined COT data for {current_year}...")
        disagg_df = cot.cot_year(current_year, cot_report_type="disaggregated_futopt")
        if disagg_df is not None and len(disagg_df) > 0:
            result["disagg"] = disagg_df
            logger.info(f"Disaggregated data: {len(disagg_df)} rows, {len(disagg_df.columns)} columns")

    except Exception as e:
        logger.error(f"Error fetching CFTC COT data: {e}", exc_info=True)

    return result


def _extract_market_from_tff(df, search_term: str) -> Optional[Dict[str, Any]]:
    """
    Extract the latest report + historical percentiles for a TFF market.

    TFF trader groups:
      - Dealer (intermediary)
      - Asset Manager (institutional – our "commercial" equivalent)
      - Leveraged Money (hedge funds – our "speculative" equivalent)
      - Other Reportable
    """
    if df is None or len(df) == 0:
        return None

    mask = df["Market_and_Exchange_Names"].str.contains(search_term, case=False, na=False)
    market_df = df[mask].copy()
    if len(market_df) == 0:
        return None

    # Sort by date, take latest
    market_df = market_df.sort_values("Report_Date_as_YYYY-MM-DD")
    latest = market_df.iloc[-1]

    # Net positions: long - short
    asset_mgr_net = _safe_int(latest.get("Asset_Mgr_Positions_Long_All", 0)) - _safe_int(latest.get("Asset_Mgr_Positions_Short_All", 0))
    lev_money_net = _safe_int(latest.get("Lev_Money_Positions_Long_All", 0)) - _safe_int(latest.get("Lev_Money_Positions_Short_All", 0))
    dealer_net = _safe_int(latest.get("Dealer_Positions_Long_All", 0)) - _safe_int(latest.get("Dealer_Positions_Short_All", 0))

    # Compute historical net positions for percentile calculation
    hist_asset_mgr_net = (
        market_df["Asset_Mgr_Positions_Long_All"].apply(_safe_int)
        - market_df["Asset_Mgr_Positions_Short_All"].apply(_safe_int)
    )
    hist_lev_money_net = (
        market_df["Lev_Money_Positions_Long_All"].apply(_safe_int)
        - market_df["Lev_Money_Positions_Short_All"].apply(_safe_int)
    )

    # Percentile of current value vs all weeks this year
    def _percentile(current_val: int, hist_series) -> int:
        arr = hist_series.values.astype(float)
        if len(arr) < 2:
            return 50
        pct = (np.sum(arr < current_val) / len(arr)) * 100
        return int(min(100, max(0, pct)))

    asset_mgr_pct = _percentile(asset_mgr_net, hist_asset_mgr_net)
    lev_money_pct = _percentile(lev_money_net, hist_lev_money_net)

    # Weekly change
    asset_mgr_change = _safe_int(latest.get("Change_in_Asset_Mgr_Long_All", 0)) - _safe_int(latest.get("Change_in_Asset_Mgr_Short_All", 0))
    lev_money_change = _safe_int(latest.get("Change_in_Lev_Money_Long_All", 0)) - _safe_int(latest.get("Change_in_Lev_Money_Short_All", 0))

    return {
        "report_date": str(latest.get("Report_Date_as_YYYY-MM-DD", "")),
        "open_interest": _safe_int(latest.get("Open_Interest_All", 0)),
        "report_type": "TFF Combined",
        "trader_groups": {
            "dealer": {
                "net": dealer_net,
                "long": _safe_int(latest.get("Dealer_Positions_Long_All", 0)),
                "short": _safe_int(latest.get("Dealer_Positions_Short_All", 0)),
                "spread": _safe_int(latest.get("Dealer_Positions_Spread_All", 0)),
                "pct_of_oi_long": _safe_float(latest.get("Pct_of_OI_Dealer_Long_All", 0)),
                "pct_of_oi_short": _safe_float(latest.get("Pct_of_OI_Dealer_Short_All", 0)),
            },
            "asset_manager": {
                "net": asset_mgr_net,
                "long": _safe_int(latest.get("Asset_Mgr_Positions_Long_All", 0)),
                "short": _safe_int(latest.get("Asset_Mgr_Positions_Short_All", 0)),
                "spread": _safe_int(latest.get("Asset_Mgr_Positions_Spread_All", 0)),
                "pct_of_oi_long": _safe_float(latest.get("Pct_of_OI_Asset_Mgr_Long_All", 0)),
                "pct_of_oi_short": _safe_float(latest.get("Pct_of_OI_Asset_Mgr_Short_All", 0)),
                "weekly_change": asset_mgr_change,
                "percentile": asset_mgr_pct,
            },
            "leveraged_money": {
                "net": lev_money_net,
                "long": _safe_int(latest.get("Lev_Money_Positions_Long_All", 0)),
                "short": _safe_int(latest.get("Lev_Money_Positions_Short_All", 0)),
                "spread": _safe_int(latest.get("Lev_Money_Positions_Spread_All", 0)),
                "pct_of_oi_long": _safe_float(latest.get("Pct_of_OI_Lev_Money_Long_All", 0)),
                "pct_of_oi_short": _safe_float(latest.get("Pct_of_OI_Lev_Money_Short_All", 0)),
                "weekly_change": lev_money_change,
                "percentile": lev_money_pct,
            },
        },
        # For backwards compat with existing UI:
        "commercial_net": asset_mgr_net,
        "speculative_net": lev_money_net,
        "commercial_percentile": asset_mgr_pct,
        "speculative_percentile": lev_money_pct,
        "weeks_of_data": len(market_df),
    }


def _extract_market_from_disagg(df, search_term: str) -> Optional[Dict[str, Any]]:
    """
    Extract the latest report + historical percentiles for a Disaggregated market.

    Disaggregated trader groups:
      - Producer/Merchant/Processor/User  (our "commercial")
      - Swap Dealers
      - Managed Money                     (our "speculative")
      - Other Reportable
    """
    if df is None or len(df) == 0:
        return None

    mask = df["Market_and_Exchange_Names"].str.contains(search_term, case=False, na=False)
    market_df = df[mask].copy()
    if len(market_df) == 0:
        return None

    market_df = market_df.sort_values("Report_Date_as_YYYY-MM-DD")
    latest = market_df.iloc[-1]

    prod_merc_net = _safe_int(latest.get("Prod_Merc_Positions_Long_All", 0)) - _safe_int(latest.get("Prod_Merc_Positions_Short_All", 0))
    swap_net = _safe_int(latest.get("Swap_Positions_Long_All", 0)) - _safe_int(latest.get("Swap__Positions_Short_All", 0))
    m_money_net = _safe_int(latest.get("M_Money_Positions_Long_All", 0)) - _safe_int(latest.get("M_Money_Positions_Short_All", 0))

    # Historical series for percentiles
    hist_prod_merc_net = (
        market_df["Prod_Merc_Positions_Long_All"].apply(_safe_int)
        - market_df["Prod_Merc_Positions_Short_All"].apply(_safe_int)
    )
    hist_m_money_net = (
        market_df["M_Money_Positions_Long_All"].apply(_safe_int)
        - market_df["M_Money_Positions_Short_All"].apply(_safe_int)
    )

    def _percentile(current_val: int, hist_series) -> int:
        arr = hist_series.values.astype(float)
        if len(arr) < 2:
            return 50
        pct = (np.sum(arr < current_val) / len(arr)) * 100
        return int(min(100, max(0, pct)))

    prod_merc_pct = _percentile(prod_merc_net, hist_prod_merc_net)
    m_money_pct = _percentile(m_money_net, hist_m_money_net)

    # Weekly changes
    prod_merc_change = _safe_int(latest.get("Change_in_Prod_Merc_Long_All", 0)) - _safe_int(latest.get("Change_in_Prod_Merc_Short_All", 0))
    m_money_change = _safe_int(latest.get("Change_in_M_Money_Long_All", 0)) - _safe_int(latest.get("Change_in_M_Money_Short_All", 0))

    return {
        "report_date": str(latest.get("Report_Date_as_YYYY-MM-DD", "")),
        "open_interest": _safe_int(latest.get("Open_Interest_All", 0)),
        "report_type": "Disaggregated Combined",
        "trader_groups": {
            "producer_merchant": {
                "net": prod_merc_net,
                "long": _safe_int(latest.get("Prod_Merc_Positions_Long_All", 0)),
                "short": _safe_int(latest.get("Prod_Merc_Positions_Short_All", 0)),
                "pct_of_oi_long": _safe_float(latest.get("Pct_of_OI_Prod_Merc_Long_All", 0)),
                "pct_of_oi_short": _safe_float(latest.get("Pct_of_OI_Prod_Merc_Short_All", 0)),
                "weekly_change": prod_merc_change,
                "percentile": prod_merc_pct,
            },
            "swap_dealers": {
                "net": swap_net,
                "long": _safe_int(latest.get("Swap_Positions_Long_All", 0)),
                "short": _safe_int(latest.get("Swap__Positions_Short_All", 0)),
                "spread": _safe_int(latest.get("Swap__Positions_Spread_All", 0)),
                "pct_of_oi_long": _safe_float(latest.get("Pct_of_OI_Swap_Long_All", 0)),
                "pct_of_oi_short": _safe_float(latest.get("Pct_of_OI_Swap_Short_All", 0)),
            },
            "managed_money": {
                "net": m_money_net,
                "long": _safe_int(latest.get("M_Money_Positions_Long_All", 0)),
                "short": _safe_int(latest.get("M_Money_Positions_Short_All", 0)),
                "spread": _safe_int(latest.get("M_Money_Positions_Spread_All", 0)),
                "pct_of_oi_long": _safe_float(latest.get("Pct_of_OI_M_Money_Long_All", 0)),
                "pct_of_oi_short": _safe_float(latest.get("Pct_of_OI_M_Money_Short_All", 0)),
                "weekly_change": m_money_change,
                "percentile": m_money_pct,
            },
        },
        # Backwards compat:
        "commercial_net": prod_merc_net,
        "speculative_net": m_money_net,
        "commercial_percentile": prod_merc_pct,
        "speculative_percentile": m_money_pct,
        "weeks_of_data": len(market_df),
    }


# ---------------------------------------------------------------------------
# Alert generation
# ---------------------------------------------------------------------------
def cross_reference_windham(
    market_positioning: Dict[str, Any],
    regime_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Cross-reference COT positioning extremes with Windham systemic state.
    Most dangerous: speculative crowding + fragile market.
    Smartest money: commercial hedging + hidden risk.
    """
    if not regime_data or not market_positioning:
        return market_positioning

    result = dict(market_positioning)
    windham = regime_data.get("windham", {})
    systemic = regime_data.get("systemic_risk", {})
    windham_state = windham.get("state", "resilient-calm")
    windham_label = windham.get("label", "Normal Markets")
    ar_delta_warning = systemic.get("ar_delta_warning", False)
    persistence = systemic.get("windham_persistence", 0)

    markets = result.get("markets", [])
    windham_alerts = []

    for market in markets:
        if not isinstance(market, dict):
            continue

        # Look for the relevant percentile fields — read the actual field names from the file
        spec_pctile = market.get("speculative_percentile", 50)
        comm_pctile = market.get("commercial_percentile", 50)
        ticker = market.get("ticker", "")
        name = market.get("name", ticker)

        # DANGER: Spec crowding in fragile market
        if spec_pctile > 90 and windham_state in ("fragile-calm", "fragile-turbulent"):
            alert = {
                "type": "danger",
                "market": name,
                "ticker": ticker,
                "message": f"DANGER: {name} specs at {spec_pctile:.0f}th pctile (extreme long) while market in {windham_label}. Maximum unwind risk.",
                "severity": "critical" if windham_state == "fragile-turbulent" else "high",
            }
            if ar_delta_warning:
                alert["message"] += " AR rising — fragility intensifying."
            market["windham_alert"] = alert
            windham_alerts.append(alert)

        # Spec extreme short in crisis = squeeze risk
        elif spec_pctile < 10 and windham_state == "fragile-turbulent":
            alert = {
                "type": "squeeze_risk",
                "market": name,
                "ticker": ticker,
                "message": f"ALERT: {name} specs at {spec_pctile:.0f}th pctile (extreme short) in Crisis Mode — squeeze risk if regime shifts.",
                "severity": "high",
            }
            market["windham_alert"] = alert
            windham_alerts.append(alert)

        # Smart money: commercials hedging in hidden risk
        elif comm_pctile > 90 and windham_state == "fragile-calm":
            alert = {
                "type": "smart_money",
                "market": name,
                "ticker": ticker,
                "message": f"INSIGHT: {name} commercials at {comm_pctile:.0f}th pctile (extreme hedge) in Hidden Risk. Smart money defensive.",
                "severity": "medium",
            }
            if persistence and persistence > 4:
                alert["message"] += f" Fragile for {persistence} periods."
            market["windham_alert"] = alert
            windham_alerts.append(alert)

    result["windham_cross_reference"] = {
        "windham_state": windham_state,
        "windham_label": windham_label,
        "alerts": windham_alerts,
        "alert_count": len(windham_alerts),
    }
    return result


def _generate_alerts(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate reversal and divergence alerts based on positioning extremes."""
    alerts = []

    for market in markets:
        ticker = market["ticker"]
        name = market["name"]
        comm_pct = market.get("commercial_percentile", 50)
        spec_pct = market.get("speculative_percentile", 50)
        comm_net = market.get("commercial_net", 0)
        spec_net = market.get("speculative_net", 0)

        # Extreme positioning alerts
        if comm_pct >= 90:
            alerts.append({
                "ticker": ticker,
                "market_name": name,
                "type": "extreme_positioning",
                "severity": "high",
                "message": f"{name}: Commercials at extreme long (P{comm_pct}) – potential reversal risk",
                "bias": "bearish",
            })
        elif comm_pct <= 10:
            alerts.append({
                "ticker": ticker,
                "market_name": name,
                "type": "extreme_positioning",
                "severity": "high",
                "message": f"{name}: Commercials at extreme short (P{comm_pct}) – potential reversal risk",
                "bias": "bullish",
            })

        if spec_pct >= 90:
            alerts.append({
                "ticker": ticker,
                "market_name": name,
                "type": "extreme_positioning",
                "severity": "high",
                "message": f"{name}: Speculators at extreme long (P{spec_pct}) – crowded trade warning",
                "bias": "bearish",
            })
        elif spec_pct <= 10:
            alerts.append({
                "ticker": ticker,
                "market_name": name,
                "type": "extreme_positioning",
                "severity": "high",
                "message": f"{name}: Speculators at extreme short (P{spec_pct}) – contrarian buy signal",
                "bias": "bullish",
            })

        # Divergence: commercials and speculators on opposite sides
        if (comm_net > 0 and spec_net < 0) or (comm_net < 0 and spec_net > 0):
            # Check if positions are far apart (at least 30 pctile difference)
            if abs(comm_pct - spec_pct) > 30:
                alerts.append({
                    "ticker": ticker,
                    "market_name": name,
                    "type": "divergence",
                    "severity": "medium",
                    "message": f"{name}: Commercial/Speculative divergence – commercials P{comm_pct} vs speculators P{spec_pct}",
                    "bias": "neutral",
                })

    return alerts


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------
class COTPositioningEngine:
    """Fetch and analyze live CFTC COT positioning data."""

    def __init__(self):
        self.cache = _cot_cache

    def get_cot_positioning(self) -> Dict[str, Any]:
        """
        Get COT positioning for all tracked markets.

        Returns dict with timestamp, markets list, alerts list,
        and data_source indicator.
        """
        cache_key = "cot_positioning:live_v4"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result

        try:
            # Fetch raw CFTC data
            raw = _fetch_cftc_data()
            tff_df = raw.get("tff")
            disagg_df = raw.get("disagg")

            markets_out: List[Dict[str, Any]] = []

            for ticker, config in MARKETS.items():
                report_type = config["report"]
                search = config["cftc_search"]

                if report_type == "tff":
                    data = _extract_market_from_tff(tff_df, search)
                else:
                    data = _extract_market_from_disagg(disagg_df, search)

                if data:
                    # Detect extreme flags
                    extreme_flag = None
                    if data["commercial_percentile"] >= 90:
                        extreme_flag = "commercial_extreme_long"
                    elif data["commercial_percentile"] <= 10:
                        extreme_flag = "commercial_extreme_short"
                    elif data["speculative_percentile"] >= 90:
                        extreme_flag = "speculative_extreme_long"
                    elif data["speculative_percentile"] <= 10:
                        extreme_flag = "speculative_extreme_short"

                    # Divergence check
                    divergence = False
                    comm_net = data["commercial_net"]
                    spec_net = data["speculative_net"]
                    if (comm_net > 0 and spec_net < 0) or (comm_net < 0 and spec_net > 0):
                        if abs(data["commercial_percentile"] - data["speculative_percentile"]) > 30:
                            divergence = True

                    # Extract weekly change from the appropriate trader group
                    tg = data.get("trader_groups", {})
                    if config["report"] == "tff":
                        weekly_change = tg.get("asset_manager", {}).get("weekly_change")
                    else:
                        weekly_change = tg.get("producer_merchant", {}).get("weekly_change")

                    markets_out.append({
                        "ticker": ticker,
                        "name": config["name"],
                        "category": config.get("category", "Other"),
                        "sort_order": config.get("sort_order", 99),
                        "report_date": data.get("report_date"),
                        "open_interest": data.get("open_interest", 0),
                        "report_type": data.get("report_type"),
                        "commercial_net": data["commercial_net"],
                        "speculative_net": data["speculative_net"],
                        "commercial_percentile": data["commercial_percentile"],
                        "speculative_percentile": data["speculative_percentile"],
                        "extreme_flag": extreme_flag,
                        "divergence": divergence,
                        "trader_groups": data.get("trader_groups", {}),
                        "weeks_of_data": data.get("weeks_of_data", 0),
                        "weekly_change": weekly_change,
                    })
                else:
                    logger.warning(f"No CFTC data found for {ticker} ({search})")

            # Generate insight text per market
            for market in markets_out:
                comm_pct = market.get("commercial_percentile", 50)
                spec_pct = market.get("speculative_percentile", 50)
                name = market["name"]

                if comm_pct >= 80 and spec_pct <= 30:
                    market["insight"] = f"Commercials heavily long while speculators are short — historically bullish signal for {name}"
                    market["bias"] = "bullish"
                elif comm_pct <= 20 and spec_pct >= 70:
                    market["insight"] = f"Commercials short while speculators heavily long — historically bearish signal for {name}"
                    market["bias"] = "bearish"
                elif comm_pct >= 70:
                    market["insight"] = f"Commercial positioning at P{comm_pct} — strong hands accumulating {name}"
                    market["bias"] = "bullish"
                elif spec_pct >= 80:
                    market["insight"] = f"Speculative positioning at P{spec_pct} — crowded long trade in {name}"
                    market["bias"] = "bearish"
                elif spec_pct <= 20:
                    market["insight"] = f"Speculative positioning at P{spec_pct} — potential contrarian buy opportunity in {name}"
                    market["bias"] = "bullish"
                elif market.get("divergence"):
                    market["insight"] = f"Commercial/Speculative divergence detected — watch for reversal in {name}"
                    market["bias"] = "neutral"
                else:
                    market["insight"] = f"Positioning neutral — no extreme signals in {name}"
                    market["bias"] = "neutral"

            # Generate alerts
            alerts = _generate_alerts(markets_out)

            # Generate overall summary
            bullish_markets = [m["name"] for m in markets_out if m.get("bias") == "bullish"]
            bearish_markets = [m["name"] for m in markets_out if m.get("bias") == "bearish"]

            summary_parts = []
            if bullish_markets:
                summary_parts.append(f"Bullish signals in {', '.join(bullish_markets)}")
            if bearish_markets:
                summary_parts.append(f"Bearish signals in {', '.join(bearish_markets)}")
            if not summary_parts:
                summary_parts.append("No extreme positioning signals across tracked markets")
            summary = ". ".join(summary_parts) + "."

            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data_source": "CFTC Disaggregated Combined + TFF Combined",
                "markets": markets_out,
                "alerts": alerts,
                "summary": summary,
            }

            self.cache.set(cache_key, result, _CACHE_TTL)
            return result

        except Exception as e:
            logger.error(f"Error in COT positioning engine: {e}", exc_info=True)
            return self._empty_result()

    def get_market_positioning(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get positioning for a specific market from the cached full result."""
        full = self.get_cot_positioning()
        for m in full.get("markets", []):
            if m["ticker"] == ticker:
                return m
        return None

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_source": "unavailable",
            "markets": [],
            "alerts": [],
        }


# Module-level singleton
_cot_engine = COTPositioningEngine()


def get_cot_positioning() -> Dict[str, Any]:
    """Get COT positioning data for all markets."""
    return _cot_engine.get_cot_positioning()


def get_market_positioning(ticker: str) -> Optional[Dict[str, Any]]:
    """Get COT positioning for a specific market."""
    return _cot_engine.get_market_positioning(ticker)
