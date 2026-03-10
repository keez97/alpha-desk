"""Quantitative screener engine for composable filtering and screening."""

import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from backend.services.rrg_calculator import calculate_rrg, SECTOR_ETFS
from backend.services.data_provider import get_sector_data

logger = logging.getLogger(__name__)


def run_quant_screen(
    rrg_quadrant: Optional[List[str]] = None,
    rrg_momentum_min: Optional[float] = None,
    rrg_momentum_max: Optional[float] = None,
    rrg_ratio_min: Optional[float] = None,
    rrg_ratio_max: Optional[float] = None,
    change_1d_min: Optional[float] = None,
    change_1d_max: Optional[float] = None,
    sector: Optional[str] = None,
    sort_by: str = "rs_momentum",
    sort_desc: bool = True,
) -> Dict[str, Any]:
    """
    Run quantitative screening on sector ETFs with composable filters.

    Args:
        rrg_quadrant: Filter by RRG quadrant (Strengthening, Weakening, Recovering, Deteriorating)
        rrg_momentum_min/max: RS-Momentum range
        rrg_ratio_min/max: RS-Ratio range
        change_1d_min/max: 1-day percent change range
        sector: Filter by sector name
        sort_by: Sort key (rs_momentum, rs_ratio, change_1d)
        sort_desc: Sort descending

    Returns:
        Dict with filtered results and metadata
    """
    try:
        # Fetch RRG data for all sector ETFs
        tickers = list(SECTOR_ETFS.keys())
        rrg_data = calculate_rrg(tickers, benchmark="SPY", weeks=10)

        if not rrg_data.get("sectors"):
            return {
                "error": "Could not fetch RRG data",
                "results": [],
                "total": 0,
            }

        # Fetch sector performance data
        sector_perf = get_sector_data(period="1D")
        if not sector_perf:
            sector_perf = []

        # Create lookup for sector performance by ticker
        perf_map = {s["ticker"]: s for s in sector_perf}

        # Merge RRG data with sector performance
        merged = []
        for rrg_item in rrg_data["sectors"]:
            ticker = rrg_item["ticker"]
            perf = perf_map.get(ticker, {})

            merged.append({
                "ticker": ticker,
                "name": rrg_item["sector"],
                "price": perf.get("price", 0),
                "change_1d": perf.get("daily_change", 0),
                "change_1d_pct": perf.get("daily_pct_change", 0),
                "rs_ratio": rrg_item["rs_ratio"],
                "rs_momentum": rrg_item["rs_momentum"],
                "quadrant": rrg_item["quadrant"],
            })

        # Apply filters
        filtered = apply_filters(
            merged,
            rrg_quadrant=rrg_quadrant,
            rrg_momentum_min=rrg_momentum_min,
            rrg_momentum_max=rrg_momentum_max,
            rrg_ratio_min=rrg_ratio_min,
            rrg_ratio_max=rrg_ratio_max,
            change_1d_min=change_1d_min,
            change_1d_max=change_1d_max,
            sector=sector,
        )

        # Sort results
        sorted_results = sort_results(filtered, sort_by=sort_by, sort_desc=sort_desc)

        return {
            "results": sorted_results,
            "total": len(sorted_results),
            "filters_applied": {
                "rrg_quadrant": rrg_quadrant,
                "rrg_momentum_min": rrg_momentum_min,
                "rrg_momentum_max": rrg_momentum_max,
                "rrg_ratio_min": rrg_ratio_min,
                "rrg_ratio_max": rrg_ratio_max,
                "change_1d_min": change_1d_min,
                "change_1d_max": change_1d_max,
                "sector": sector,
            },
        }
    except Exception as e:
        logger.error(f"Error running quant screen: {e}")
        return {
            "error": str(e),
            "results": [],
            "total": 0,
        }


def apply_filters(
    data: List[Dict[str, Any]],
    rrg_quadrant: Optional[List[str]] = None,
    rrg_momentum_min: Optional[float] = None,
    rrg_momentum_max: Optional[float] = None,
    rrg_ratio_min: Optional[float] = None,
    rrg_ratio_max: Optional[float] = None,
    change_1d_min: Optional[float] = None,
    change_1d_max: Optional[float] = None,
    sector: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Apply composable filters to screening data."""
    result = data

    # Filter by RRG quadrant
    if rrg_quadrant:
        result = [r for r in result if r["quadrant"] in rrg_quadrant]

    # Filter by RS-Momentum range
    if rrg_momentum_min is not None:
        result = [r for r in result if r["rs_momentum"] >= rrg_momentum_min]
    if rrg_momentum_max is not None:
        result = [r for r in result if r["rs_momentum"] <= rrg_momentum_max]

    # Filter by RS-Ratio range
    if rrg_ratio_min is not None:
        result = [r for r in result if r["rs_ratio"] >= rrg_ratio_min]
    if rrg_ratio_max is not None:
        result = [r for r in result if r["rs_ratio"] <= rrg_ratio_max]

    # Filter by 1-day change range
    if change_1d_min is not None:
        result = [r for r in result if r["change_1d_pct"] >= change_1d_min]
    if change_1d_max is not None:
        result = [r for r in result if r["change_1d_pct"] <= change_1d_max]

    # Filter by sector
    if sector:
        result = [r for r in result if r["name"].lower() == sector.lower()]

    return result


def sort_results(
    data: List[Dict[str, Any]],
    sort_by: str = "rs_momentum",
    sort_desc: bool = True,
) -> List[Dict[str, Any]]:
    """Sort screening results by specified column."""
    key_map = {
        "rs_momentum": "rs_momentum",
        "rs_ratio": "rs_ratio",
        "change_1d": "change_1d_pct",
        "price": "price",
        "ticker": "ticker",
    }

    sort_key = key_map.get(sort_by, "rs_momentum")
    return sorted(data, key=lambda x: x[sort_key], reverse=sort_desc)


def get_screen_presets() -> List[Dict[str, Any]]:
    """Return pre-built screening strategy presets."""
    return [
        {
            "id": "rrg_leaders",
            "name": "RRG Leaders",
            "description": "Sectors in Strengthening quadrant with positive momentum",
            "filters": {
                "rrg_quadrant": ["Strengthening"],
                "rrg_momentum_min": 0,
            },
        },
        {
            "id": "rotation_candidates",
            "name": "Rotation Candidates",
            "description": "Sectors in Recovering quadrant with positive momentum",
            "filters": {
                "rrg_quadrant": ["Recovering"],
                "rrg_momentum_min": 0,
            },
        },
        {
            "id": "avoid_list",
            "name": "Avoid List",
            "description": "Sectors in Deteriorating quadrant with negative momentum",
            "filters": {
                "rrg_quadrant": ["Deteriorating"],
                "rrg_momentum_max": -2,
            },
        },
        {
            "id": "momentum_leaders",
            "name": "Momentum Leaders",
            "description": "Sectors with strongest RS-Momentum",
            "filters": {
                "rrg_momentum_min": 2,
            },
        },
        {
            "id": "relative_strength",
            "name": "Relative Strength",
            "description": "Sectors outperforming benchmark (RS-Ratio > 100)",
            "filters": {
                "rrg_ratio_min": 100,
            },
        },
    ]
