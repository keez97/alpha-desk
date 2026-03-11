"""
COT (Commitments of Traders) Positioning API Router - REST endpoints for futures market positioning analysis.

Provides access to commercial and speculative positioning data,
positioning percentiles, extreme positioning alerts, and divergence signals.
"""

from fastapi import APIRouter, Path, Query
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from backend.services.cot_positioning import get_cot_positioning, get_market_positioning

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cot-positioning", tags=["cot-positioning"])


# ==================== Pydantic Response Models ====================


class MarketPositioning(BaseModel):
    """Positioning data for a single futures market."""

    name: str = Field(..., description="Market name (e.g., 'S&P 500 E-mini')")
    ticker: str = Field(..., description="Futures ticker (e.g., 'ES')")
    commercial_net: int = Field(..., description="Net commercial position (contracts)")
    speculative_net: int = Field(..., description="Net speculative position (contracts)")
    commercial_percentile: int = Field(
        ...,
        ge=0,
        le=100,
        description="Commercial position percentile vs 1-year range",
    )
    speculative_percentile: int = Field(
        ...,
        ge=0,
        le=100,
        description="Speculative position percentile vs 1-year range",
    )
    extreme_flag: Optional[str] = Field(
        None,
        description="commercial_extreme_long|commercial_extreme_short|speculative_extreme_long|speculative_extreme_short|null",
    )
    divergence: bool = Field(..., description="Commercial-speculative positioning divergence flag")


class Alert(BaseModel):
    """COT-based positioning alert."""

    ticker: str = Field(..., description="Futures ticker")
    market_name: str = Field(..., description="Market name")
    type: str = Field(..., description="extreme_positioning|divergence")
    severity: str = Field(..., description="high|medium")
    message: str = Field(..., description="Alert description")
    bias: str = Field(..., description="bullish|bearish|neutral")


class COTPositioningResponse(BaseModel):
    """Complete COT positioning snapshot."""

    timestamp: str = Field(..., description="Report timestamp")
    markets: List[MarketPositioning] = Field(
        ..., description="Positioning data for all major futures"
    )
    alerts: List[Alert] = Field(..., description="Reversal and divergence alerts")


# ==================== API Endpoints ====================


@router.get("", response_model=COTPositioningResponse)
def get_cot_positioning_data():
    """
    Get COT positioning for all major futures markets.

    Returns:
    - Commercial and speculative net positions for key futures:
      - S&P 500 E-mini (ES)
      - Gold (GC)
      - Crude Oil (CL)
      - 10-Year Treasury (ZB)
      - Euro FX (6E)
    - Positioning percentiles (0-100) vs 1-year range
    - Extreme positioning alerts (top/bottom 10th percentile)
    - Divergence signals (commercials vs speculators)

    Endpoint:
    GET /api/cot-positioning
    """
    try:
        result = get_cot_positioning()

        # Convert to response format
        markets = [
            MarketPositioning(
                name=m["name"],
                ticker=m["ticker"],
                commercial_net=m["commercial_net"],
                speculative_net=m["speculative_net"],
                commercial_percentile=m["commercial_percentile"],
                speculative_percentile=m["speculative_percentile"],
                extreme_flag=m.get("extreme_flag"),
                divergence=m.get("divergence", False),
            )
            for m in result.get("markets", [])
        ]

        alerts = [
            Alert(
                ticker=a["ticker"],
                market_name=a["market_name"],
                type=a["type"],
                severity=a["severity"],
                message=a["message"],
                bias=a["bias"],
            )
            for a in result.get("alerts", [])
        ]

        return COTPositioningResponse(
            timestamp=result["timestamp"],
            markets=markets,
            alerts=alerts,
        )

    except Exception as e:
        logger.error(f"Error fetching COT positioning: {e}", exc_info=True)
        # Return empty response on error
        return COTPositioningResponse(
            timestamp=datetime.utcnow().isoformat(),
            markets=[],
            alerts=[],
        )


@router.get("/{ticker}", response_model=MarketPositioning)
def get_market_positioning_data(
    ticker: str = Path(..., min_length=1, max_length=3, description="Futures ticker (e.g., ES, GC, CL)"),
):
    """
    Get COT positioning for a specific futures market.

    Path parameters:
    - ticker: Futures ticker symbol (ES, GC, CL, ZB, 6E)

    Returns:
    - Detailed positioning data for the requested market
    - Commercial and speculative net positions
    - Positioning percentiles vs 1-year range
    - Extreme positioning flags if applicable
    """
    ticker_upper = ticker.upper()

    try:
        market_data = get_market_positioning(ticker_upper)

        if not market_data:
            logger.warning(f"Unknown ticker: {ticker_upper}")
            raise ValueError(f"Unknown futures ticker: {ticker_upper}")

        return MarketPositioning(
            name=market_data["name"],
            ticker=market_data["ticker"],
            commercial_net=market_data["commercial_net"],
            speculative_net=market_data["speculative_net"],
            commercial_percentile=market_data["commercial_percentile"],
            speculative_percentile=market_data["speculative_percentile"],
            extreme_flag=market_data.get("extreme_flag"),
            divergence=market_data.get("divergence", False),
        )

    except ValueError as e:
        logger.error(f"Invalid ticker request: {e}")
        raise
    except Exception as e:
        logger.error(f"Error fetching COT data for {ticker_upper}: {e}", exc_info=True)
        raise
