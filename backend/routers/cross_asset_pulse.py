"""
Cross-Asset Pulse — SPY, TLT, GLD, DXY, HYG with 5-day sparklines.
"""
from fastapi import APIRouter
import logging
import traceback

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["cross-asset-pulse"])

PULSE_ASSETS = [
    {"ticker": "SPY", "name": "S&P 500"},
    {"ticker": "TLT", "name": "20+ Year Treasury"},
    {"ticker": "GLD", "name": "Gold"},
    {"ticker": "UUP", "name": "US Dollar"},
    {"ticker": "HYG", "name": "High Yield Corp"},
]


@router.get("/cross-asset-pulse")
async def get_cross_asset_pulse():
    """Return current price, daily change, and 5-day sparkline for key cross-asset ETFs."""
    try:
        from backend.services.yahoo_direct import batch_quotes, get_history

        tickers = [a["ticker"] for a in PULSE_ASSETS]

        # Get current quotes
        quotes = batch_quotes(tickers)

        assets = []
        for asset_def in PULSE_ASSETS:
            ticker = asset_def["ticker"]
            quote = quotes.get(ticker, {})

            # Get 5-day sparkline from history
            sparkline = []
            try:
                history = get_history(ticker, range_str="5d", interval="1d")
                sparkline = [bar["close"] for bar in history if bar.get("close") is not None]
            except Exception:
                pass

            price = quote.get("price", 0)
            prev_close = quote.get("previousClose", quote.get("prev_close", price))
            change = price - prev_close if prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0

            assets.append({
                "ticker": ticker,
                "name": asset_def["name"],
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "sparkline": [round(s, 2) for s in sparkline] if sparkline else [],
            })

        return {"data": {"assets": assets}}

    except Exception as e:
        logger.error(f"Cross-asset pulse error: {e}\n{traceback.format_exc()}")
        return {"data": {"assets": [], "error": str(e)}}
