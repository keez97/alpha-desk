"""
Signal Confluence Router - REST endpoints for cross-signal synthesis.

Provides access to confluence signals and signal matrix visualization.
"""

from fastapi import APIRouter
from datetime import datetime
from backend.services.confluence_engine import calculate_confluence_signals

router = APIRouter(prefix="/api/confluence", tags=["confluence"])


@router.get("/signals")
def get_confluence_signals():
    """
    Get current cross-signal confluence analysis.

    Returns confluence signals where 2+ data sources align on the same thesis,
    with conviction scoring (HIGH/MEDIUM/LOW).
    """
    result = calculate_confluence_signals()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "signals": result.get("confluence_signals", []),
            "macro_regime": result.get("macro_regime", {}),
        }
    }


@router.get("/matrix")
def get_signal_matrix():
    """
    Get signal matrix data for visualization.

    Returns a matrix of all signals per sector with RRG, macro, performance,
    and sentiment columns, plus total confluence score.
    """
    result = calculate_confluence_signals()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "matrix": result.get("matrix_data", []),
            "macro_regime": result.get("macro_regime", {}),
        }
    }
