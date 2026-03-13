"""
Sector Seasonality — Monthly average returns for 11 SPDR sector ETFs.
Uses 10 years of historical monthly data to compute seasonal patterns.
"""
from fastapi import APIRouter
import logging
import traceback

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["sector-seasonality"])

SECTOR_ETFS = [
    {"ticker": "XLB", "name": "Materials"},
    {"ticker": "XLC", "name": "Communication"},
    {"ticker": "XLE", "name": "Energy"},
    {"ticker": "XLF", "name": "Financials"},
    {"ticker": "XLI", "name": "Industrials"},
    {"ticker": "XLK", "name": "Technology"},
    {"ticker": "XLP", "name": "Cons. Staples"},
    {"ticker": "XLRE", "name": "Real Estate"},
    {"ticker": "XLU", "name": "Utilities"},
    {"ticker": "XLV", "name": "Healthcare"},
    {"ticker": "XLY", "name": "Cons. Disc."},
]

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@router.get("/sector-seasonality")
async def get_sector_seasonality():
    """Return average monthly returns for sector ETFs based on historical data."""
    try:
        from backend.services.yahoo_direct import get_history
        from collections import defaultdict
        from datetime import datetime as dt_class

        sectors = []
        for etf in SECTOR_ETFS:
            monthly_returns = {}
            try:
                # Get 10 years of monthly data
                history = get_history(etf["ticker"], range_str="10y", interval="1mo")
                if history and len(history) > 1:
                    # Calculate monthly returns and group by month
                    month_groups: dict[int, list[float]] = defaultdict(list)

                    for i in range(1, len(history)):
                        prev_close = history[i - 1].get("close")
                        curr_close = history[i].get("close")
                        date_str = history[i].get("date", "")

                        if prev_close and curr_close and prev_close != 0:
                            ret = ((curr_close - prev_close) / prev_close) * 100
                            try:
                                parsed = dt_class.strptime(date_str, "%Y-%m-%d")
                                month_groups[parsed.month].append(ret)
                            except Exception:
                                continue

                    # Average returns by month
                    for month_num in range(1, 13):
                        month_name = MONTH_NAMES[month_num - 1]
                        vals = month_groups.get(month_num, [])
                        monthly_returns[month_name] = round(sum(vals) / len(vals), 1) if vals else 0.0
                else:
                    for m in MONTH_NAMES:
                        monthly_returns[m] = 0.0

            except Exception as e:
                logger.warning(f"Failed to get seasonality for {etf['ticker']}: {e}")
                for m in MONTH_NAMES:
                    monthly_returns[m] = 0.0

            sectors.append({
                "ticker": etf["ticker"],
                "name": etf["name"],
                "monthly_returns": monthly_returns,
            })

        return {"data": {"sectors": sectors}}

    except Exception as e:
        logger.error(f"Sector seasonality error: {e}\n{traceback.format_exc()}")
        return {"data": {"sectors": [], "error": str(e)}}
