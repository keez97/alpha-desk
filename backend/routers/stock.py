from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from datetime import datetime
import json
from backend.database import get_session
from backend.models.cache import StockGradeCache
from backend.services.yfinance_service import (
    search_ticker,
    get_quote,
    get_stock_fundamentals
)
from backend.services.fds_service import (
    get_income_statements,
    get_balance_sheets,
    get_cash_flow_statements
)
from backend.services.claude_service import grade_stock

router = APIRouter(prefix="/api", tags=["stock"])


@router.get("/search")
def search(q: str):
    """Search for tickers matching query."""
    results = search_ticker(q)
    return {
        "query": q,
        "results": results
    }


@router.get("/stock/{ticker}/quote")
def get_stock_quote(ticker: str):
    """Get stock quote with price and market data."""
    quote = get_quote(ticker)
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "quote": quote
    }


@router.post("/stock/{ticker}/grade")
async def grade_stock_endpoint(ticker: str, session: Session = Depends(get_session)):
    """Grade a stock based on fundamental analysis."""

    # Check cache
    cached = session.exec(
        select(StockGradeCache).where(StockGradeCache.ticker == ticker)
    ).first()

    if cached:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cached": True,
            "grade": json.loads(cached.grade_json)
        }

    # Get fundamental data
    fundamentals = get_stock_fundamentals(ticker)

    # Get financial statements
    try:
        income_stmts = await get_income_statements(ticker, limit=8)
        balance_sheets = await get_balance_sheets(ticker, limit=8)
        cash_flows = await get_cash_flow_statements(ticker, limit=8)
    except Exception:
        income_stmts = []
        balance_sheets = []
        cash_flows = []

    # Combine data for analysis
    analysis_data = {
        **fundamentals,
        "income_statements": income_stmts[:2],
        "balance_sheets": balance_sheets[:2],
        "cash_flows": cash_flows[:2]
    }

    # Grade stock
    grade = await grade_stock(ticker, analysis_data)

    # Cache result
    cache_entry = StockGradeCache(
        ticker=ticker,
        grade_json=json.dumps(grade)
    )
    session.add(cache_entry)
    session.commit()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cached": False,
        "grade": grade
    }
