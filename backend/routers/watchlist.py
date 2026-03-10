from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime
from pydantic import BaseModel
import logging
from backend.database import get_session
from backend.models.watchlist import Watchlist
from backend.services.data_provider import get_quote

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class WatchlistItem(BaseModel):
    ticker: str


class WatchlistResponse(BaseModel):
    ticker: str
    added_at: str
    price: float
    change: float
    pct_change: float
    last_grade: str = None
    last_grade_at: str = None


@router.get("/")
def list_watchlist(session: Session = Depends(get_session)):
    """List all watchlist items with current prices."""
    try:
        items = session.exec(select(Watchlist)).all()

        response = []
        for item in items:
            try:
                quote = get_quote(item.ticker)
            except Exception as quote_err:
                logger.error(f"Error getting quote for {item.ticker}: {quote_err}")
                quote = {"price": 0, "change": 0, "pct_change": 0}

            response.append({
                "ticker": item.ticker,
                "added_at": item.added_at.isoformat(),
                "price": quote.get("price", 0),
                "change": quote.get("change", 0),
                "pct_change": quote.get("pct_change", 0),
                "last_grade": item.last_grade,
                "last_grade_at": item.last_grade_at.isoformat() if item.last_grade_at else None
            })

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "items": response
        }
    except Exception as e:
        logger.error(f"Error listing watchlist: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "items": []
        }


@router.post("/")
def add_to_watchlist(data: WatchlistItem, session: Session = Depends(get_session)):
    """Add ticker to watchlist."""
    ticker = data.ticker.upper()

    # Check if already exists
    existing = session.exec(
        select(Watchlist).where(Watchlist.ticker == ticker)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Ticker already in watchlist")

    # Add to watchlist
    watchlist_item = Watchlist(ticker=ticker)
    session.add(watchlist_item)
    session.commit()
    session.refresh(watchlist_item)

    quote = get_quote(ticker)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "ticker": ticker,
        "added_at": watchlist_item.added_at.isoformat(),
        "price": quote.get("price", 0),
        "change": quote.get("change", 0),
        "pct_change": quote.get("pct_change", 0)
    }


@router.delete("/{ticker}")
def remove_from_watchlist(ticker: str, session: Session = Depends(get_session)):
    """Remove ticker from watchlist."""
    ticker = ticker.upper()

    watchlist_item = session.exec(
        select(Watchlist).where(Watchlist.ticker == ticker)
    ).first()

    if not watchlist_item:
        raise HTTPException(status_code=404, detail="Ticker not in watchlist")

    session.delete(watchlist_item)
    session.commit()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "removed": ticker
    }
