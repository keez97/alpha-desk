"""
Confluence Backtest Router - Historical validation of confluence signals.

Provides endpoints to backtest how often confluence signals (3+ aligned signals)
produced positive returns over various time horizons.
"""

from fastapi import APIRouter, Query
from datetime import datetime
import logging

from backend.services.confluence_backtest_engine import run_confluence_backtest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/confluence-backtest", tags=["confluence-backtest"])


@router.get("/run")
def run_confluence_backtest_endpoint(
    lookback_months: int = Query(12, ge=1, le=24, description="Historical lookback period in months")
):
    """
    Run a full confluence backtest.

    Tests historical periods to see how often confluence signals
    (RRG + Macro + Performance alignment) produced positive returns.

    Args:
        lookback_months: Number of months to backtest (1-24, default 12)

    Returns:
        Dict with:
        - summary: Conviction and direction statistics
        - equityCurve: Time series of cumulative PnL from HIGH confluence bullish signals
        - signalsAnalyzed: Number of signals tested
        - period: Description of backtest period
        - timestamp: When backtest was run
    """
    try:
        logger.info(f"Running confluence backtest with {lookback_months} month lookback")
        result = run_confluence_backtest(lookback_months=lookback_months)
        return result
    except Exception as e:
        logger.error(f"Error in confluence backtest: {e}")
        return {
            "error": str(e),
            "summary": {"convictionStats": [], "directionStats": []},
            "equityCurve": [],
            "signalsAnalyzed": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/summary")
def get_confluence_backtest_summary(
    lookback_months: int = Query(12, ge=1, le=24, description="Historical lookback period in months")
):
    """
    Get summary statistics only (without equity curve).

    Faster endpoint for just viewing the conviction and direction stats.

    Args:
        lookback_months: Number of months to backtest (1-24, default 12)

    Returns:
        Dict with summary stats only (no equity curve)
    """
    try:
        logger.info(f"Running confluence backtest summary with {lookback_months} month lookback")
        result = run_confluence_backtest(lookback_months=lookback_months)

        # Strip equity curve to reduce response size
        return {
            "summary": result.get("summary", {}),
            "signalsAnalyzed": result.get("signalsAnalyzed", 0),
            "period": result.get("period", ""),
            "timestamp": result.get("timestamp", datetime.utcnow().isoformat()),
        }
    except Exception as e:
        logger.error(f"Error in confluence backtest summary: {e}")
        return {
            "error": str(e),
            "summary": {"convictionStats": [], "directionStats": []},
            "signalsAnalyzed": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }
