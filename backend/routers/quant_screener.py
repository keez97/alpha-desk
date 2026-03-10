"""API router for quantitative screening endpoints."""

from fastapi import APIRouter, Query
from typing import Optional, List
from datetime import datetime
from backend.services.quant_screener_engine import run_quant_screen, get_screen_presets

router = APIRouter(prefix="/api/quant-screener", tags=["quant-screener"])


@router.get("/screen")
def run_quant_screen_endpoint(
    rrg_quadrant: Optional[List[str]] = Query(None),
    rrg_momentum_min: Optional[float] = None,
    rrg_momentum_max: Optional[float] = None,
    rrg_ratio_min: Optional[float] = None,
    rrg_ratio_max: Optional[float] = None,
    change_1d_min: Optional[float] = None,
    change_1d_max: Optional[float] = None,
    sector: Optional[str] = None,
    sort_by: str = "rs_momentum",
    sort_desc: bool = True,
):
    """
    Run quantitative screen with composable filters.

    Query Parameters:
        rrg_quadrant: List of quadrants to include (Strengthening, Weakening, Recovering, Deteriorating)
        rrg_momentum_min/max: RS-Momentum range
        rrg_ratio_min/max: RS-Ratio range
        change_1d_min/max: 1-day percent change range
        sector: Filter by sector name
        sort_by: Sort column (rs_momentum, rs_ratio, change_1d, price, ticker)
        sort_desc: Sort descending (true/false)
    """
    result = run_quant_screen(
        rrg_quadrant=rrg_quadrant,
        rrg_momentum_min=rrg_momentum_min,
        rrg_momentum_max=rrg_momentum_max,
        rrg_ratio_min=rrg_ratio_min,
        rrg_ratio_max=rrg_ratio_max,
        change_1d_min=change_1d_min,
        change_1d_max=change_1d_max,
        sector=sector,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "data": result,
    }


@router.get("/presets")
def get_screen_presets_endpoint():
    """Return pre-built screening strategy presets."""
    presets = get_screen_presets()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "presets": presets,
    }
