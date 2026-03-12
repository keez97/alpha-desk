"""
COT (Commitments of Traders) Positioning API Router - REST endpoints for futures market positioning analysis.

Provides access to commercial and speculative positioning data,
positioning percentiles, extreme positioning alerts, and divergence signals.
Tracks 20 markets across 6 categories.
"""

from fastapi import APIRouter, Path, Query
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from backend.services.cot_positioning import (
    get_cot_positioning, get_market_positioning,
    MARKETS, CATEGORIES, DEFAULT_MARKETS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cot-positioning", tags=["cot-positioning"])


# ==================== Pydantic Response Models ====================


class MarketPositioning(BaseModel):
    """Positioning data for a single futures market."""

    name: str = Field(..., description="Market name (e.g., 'S&P 500 E-mini')")
    ticker: str = Field(..., description="Futures ticker (e.g., 'ES')")
    category: str = Field("Other", description="Asset class category")
    sort_order: int = Field(99, description="Display sort order within category")
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
        description="commercial_extreme_long|short or speculative_extreme_long|short",
    )
    divergence: bool = Field(..., description="Commercial-speculative positioning divergence flag")
    weekly_change: Optional[int] = Field(None, description="Weekly net change in commercial contracts")
    insight: Optional[str] = Field(None, description="AI-generated positioning interpretation")
    bias: Optional[str] = Field(None, description="bullish|bearish|neutral")


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
        ..., description="Positioning data for all tracked futures"
    )
    alerts: List[Alert] = Field(..., description="Reversal and divergence alerts")
    summary: Optional[str] = Field(None, description="Overall market positioning summary")


class MarketMeta(BaseModel):
    """Metadata for a single market available in COT."""
    ticker: str
    name: str
    category: str
    sort_order: int


class COTMetaResponse(BaseModel):
    """Available markets, categories, and defaults for UI configuration."""
    markets: List[MarketMeta]
    categories: List[str]
    defaults: List[str]


# ==================== API Endpoints ====================


@router.get("/meta", response_model=COTMetaResponse)
def get_cot_meta():
    """
    Get available COT markets, categories, and default selection.
    Used by the frontend settings panel to show what markets can be tracked.
    """
    market_list = [
        MarketMeta(
            ticker=ticker,
            name=config["name"],
            category=config.get("category", "Other"),
            sort_order=config.get("sort_order", 99),
        )
        for ticker, config in MARKETS.items()
    ]
    return COTMetaResponse(
        markets=market_list,
        categories=CATEGORIES,
        defaults=DEFAULT_MARKETS,
    )


@router.get("", response_model=COTPositioningResponse)
def get_cot_positioning_data():
    """
    Get COT positioning for all tracked futures markets (20 markets across 6 categories).

    Returns commercial and speculative net positions, percentiles,
    extreme positioning alerts, and divergence signals.
    """
    try:
        result = get_cot_positioning()

        markets = [
            MarketPositioning(
                name=m["name"],
                ticker=m["ticker"],
                category=m.get("category", "Other"),
                sort_order=m.get("sort_order", 99),
                commercial_net=m["commercial_net"],
                speculative_net=m["speculative_net"],
                commercial_percentile=m["commercial_percentile"],
                speculative_percentile=m["speculative_percentile"],
                extreme_flag=m.get("extreme_flag"),
                divergence=m.get("divergence", False),
                weekly_change=m.get("weekly_change"),
                insight=m.get("insight"),
                bias=m.get("bias"),
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
            summary=result.get("summary"),
        )

    except Exception as e:
        logger.error(f"Error fetching COT positioning: {e}", exc_info=True)
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
            category=market_data.get("category", "Other"),
            sort_order=market_data.get("sort_order", 99),
            commercial_net=market_data["commercial_net"],
            speculative_net=market_data["speculative_net"],
            commercial_percentile=market_data["commercial_percentile"],
            speculative_percentile=market_data["speculative_percentile"],
            extreme_flag=market_data.get("extreme_flag"),
            divergence=market_data.get("divergence", False),
            weekly_change=market_data.get("weekly_change"),
            insight=market_data.get("insight"),
            bias=market_data.get("bias"),
        )

    except ValueError as e:
        logger.error(f"Invalid ticker request: {e}")
        raise
    except Exception as e:
        logger.error(f"Error fetching COT data for {ticker_upper}: {e}", exc_info=True)
        raise
