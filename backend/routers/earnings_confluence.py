"""
Earnings Confluence Router - REST endpoints for earnings-confluence integration.

Provides access to earnings catalysts and their confluence-adjusted conviction scores.
"""

from fastapi import APIRouter, Path
from datetime import datetime
from backend.services.earnings_confluence_engine import (
    calculate_earnings_confluence,
    get_sector_earnings_detail,
)

router = APIRouter(prefix="/api/earnings-confluence", tags=["earnings-confluence"])


@router.get("/")
def get_earnings_catalysts():
    """
    Get earnings catalysts for all sectors with confluence boost analysis.

    Returns a list of sectors with upcoming earnings, catalyst counts,
    and conviction boosts based on confluence signals.

    Response structure:
    - catalysts: List of EarningsCatalyst objects
      - sectorTicker: Sector ETF ticker (e.g., "XLK")
      - sectorName: Full sector name
      - upcomingEarnings: List of upcoming earnings
        - ticker: Stock ticker
        - name: Company name
        - date: ISO format earnings date
        - daysUntil: Days until earnings
      - catalystCount: Number of major holdings with earnings in 14 days
      - confluenceBoost: Boost level (HIGH/MEDIUM/NONE)
      - originalConviction: Confluence conviction before boost
      - combinedConviction: Confluence conviction after boost
    - timestamp: ISO timestamp
    """
    result = calculate_earnings_confluence()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "data": result,
    }


@router.get("/{sector_ticker}")
def get_sector_earnings(
    sector_ticker: str = Path(..., description="Sector ETF ticker (e.g., XLK)"),
):
    """
    Get detailed earnings information for a specific sector.

    Shows all upcoming earnings for major holdings in the sector,
    with extended lookhead (30 days) for planning purposes.

    Args:
        sector_ticker: Sector ETF ticker

    Returns:
        Dict with sector earnings detail including all holdings and their upcoming earnings
    """
    result = get_sector_earnings_detail(sector_ticker)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "data": result,
    }
