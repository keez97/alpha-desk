from fastapi import APIRouter, Query
from datetime import datetime
from backend.services.correlation_engine import (
    calculate_correlation_matrix,
    get_pair_details,
)

router = APIRouter(prefix="/api/correlation", tags=["correlation"])


@router.get("/matrix")
def get_correlation_matrix(lookback: int = Query(90, ge=30, le=365)):
    """
    Get correlation matrix for all sector ETFs.

    Query Parameters:
    - lookback: Number of days to look back (default 90, range 30-365)

    Returns:
    {
        timestamp: ISO datetime,
        matrix: [[float]],
        tickers: [str],
        sectors: [str],
        pairs_trades: [...],
        hedging_pairs: [...],
        lookback_days: int
    }
    """
    result = calculate_correlation_matrix(lookback_days=lookback)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "lookback_days": lookback,
        **result,
    }


@router.get("/pairs")
def get_pairs_trades(lookback: int = Query(90, ge=30, le=365)):
    """
    Get identified pairs trade opportunities only.

    Query Parameters:
    - lookback: Number of days to look back (default 90, range 30-365)

    Returns pairs_trades array with mean-reversion opportunities.
    """
    result = calculate_correlation_matrix(lookback_days=lookback)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "lookback_days": lookback,
        "pairs_trades": result.get("pairs_trades", []),
    }


@router.get("/pair/{ticker1}/{ticker2}")
def get_pair_analysis(
    ticker1: str,
    ticker2: str,
    lookback: int = Query(90, ge=30, le=365)
):
    """
    Get detailed pair analysis: spread, z-score, rolling correlation.

    Path Parameters:
    - ticker1: First ETF ticker (e.g., XLK)
    - ticker2: Second ETF ticker (e.g., XLV)

    Query Parameters:
    - lookback: Number of days to look back (default 90, range 30-365)

    Returns detailed spread analysis and correlation metrics.
    """
    result = get_pair_details(ticker1, ticker2, lookback_days=lookback)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "lookback_days": lookback,
        **result,
    }
