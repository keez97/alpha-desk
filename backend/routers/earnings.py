"""
Earnings API Router - REST endpoints for earnings surprise predictions.

Provides access to earnings calendar, signals, historical data, and PEAD analysis.
"""

from fastapi import APIRouter, Depends, Query, Path, HTTPException
import logging
import re

logger = logging.getLogger(__name__)
from sqlmodel import Session
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field
from decimal import Decimal

from backend.database import get_session
from backend.repositories.earnings_repo import EarningsRepository
from backend.services.smart_estimate_engine import SmartEstimateEngine
from backend.services.pead_analyzer import PEADAnalyzer
from backend.services.earnings_data import EarningsDataService

router = APIRouter(prefix="/api/earnings", tags=["earnings"])


# ==================== Pydantic Models ====================


class EarningsEstimateResponse(BaseModel):
    """Earnings estimate response."""
    ticker: str
    fiscal_quarter: str
    estimate_type: str
    eps_estimate: float
    estimate_date: datetime
    analyst_broker: Optional[str] = None
    revision_number: int = 0


class EarningsActualResponse(BaseModel):
    """Actual earnings response."""
    ticker: str
    fiscal_quarter: str
    actual_eps: float
    report_date: date
    report_time: Optional[str] = None
    surprise_vs_consensus: Optional[float] = None
    surprise_vs_smart: Optional[float] = None
    source: str


class SmartEstimateResponse(BaseModel):
    """SmartEstimate response."""
    smart_eps: Optional[float] = None
    consensus_eps: Optional[float] = None
    divergence_pct: Optional[float] = None
    signal: str = "hold"
    num_estimates: int = 0
    details: List[dict] = []


class EarningsSignalResponse(BaseModel):
    """Earnings signal response."""
    ticker: str
    fiscal_quarter: str
    signal_date: datetime
    signal_type: str
    confidence: int
    smart_estimate_eps: float
    consensus_eps: float
    divergence_pct: float
    days_to_earnings: int
    valid_until: datetime


class EarningsCalendarItem(BaseModel):
    """Earnings calendar item."""
    ticker: str
    earnings_date: str
    fiscal_quarter: str
    consensus_eps: Optional[float] = None
    smart_estimate_eps: Optional[float] = None
    divergence_pct: Optional[float] = None
    signal: Optional[str] = None
    confidence: Optional[int] = None
    days_to_earnings: int


class PEADResponse(BaseModel):
    """PEAD measurement response."""
    ticker: str
    fiscal_quarter: str
    earnings_date: date
    surprise_direction: str
    surprise_magnitude: float
    car_1d: Optional[float] = None
    car_5d: Optional[float] = None
    car_21d: Optional[float] = None
    car_60d: Optional[float] = None


class HistoryResponse(BaseModel):
    """Historical earnings response."""
    ticker: str
    fiscal_quarter: str
    actual_eps: Optional[float] = None
    consensus_eps: Optional[float] = None
    smart_estimate_eps: Optional[float] = None
    surprise_pct: Optional[float] = None
    report_date: Optional[date] = None
    pead_data: Optional[dict] = None


# ==================== API Endpoints ====================


@router.get("/calendar", response_model=List[EarningsCalendarItem])
def get_earnings_calendar(
    days_ahead: int = Query(30, ge=1, le=180),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    """
    Get upcoming earnings with SmartEstimate signals.

    Query parameters:
    - days_ahead: Days ahead to look (1-180, default 30)
    - limit: Number of results (1-500, default 100)
    - offset: Pagination offset (default 0)

    Returns list of upcoming earnings with consensus, SmartEstimate, signals, etc.
    """
    repo = EarningsRepository(session)
    calendar = repo.get_earnings_calendar(
        days_ahead=days_ahead,
        limit=limit,
        offset=offset,
    )
    return calendar


@router.get("/{ticker}/history", response_model=List[HistoryResponse])
def get_earnings_history(
    ticker: str = Path(..., min_length=1, max_length=10, description="Stock ticker (e.g., AAPL)"),
    quarters: int = Query(8, ge=1, le=20, description="Number of quarters to return"),
    session: Session = Depends(get_session),
):
    """
    Get historical earnings for past N quarters.

    Returns actual EPS, consensus, SmartEstimate, surprise %, and PEAD data.
    """
    repo = EarningsRepository(session)
    analyzer = PEADAnalyzer(session)

    actuals = repo.get_actuals_history(ticker, n_quarters=quarters)

    result = []
    for actual in actuals:
        # Get estimates for this quarter
        consensus = repo.get_latest_consensus(ticker, actual.fiscal_quarter)
        smart_estimate = repo.get_estimates(
            ticker,
            actual.fiscal_quarter,
            estimate_type="smart_estimate",
        )

        # Get PEAD if available
        pead = repo.get_pead(ticker, actual.fiscal_quarter)

        result.append(
            HistoryResponse(
                ticker=ticker,
                fiscal_quarter=actual.fiscal_quarter,
                actual_eps=float(actual.actual_eps),
                consensus_eps=float(consensus.eps_estimate) if consensus else None,
                smart_estimate_eps=float(smart_estimate[0].eps_estimate) if smart_estimate else None,
                surprise_pct=float(actual.surprise_vs_consensus) if actual.surprise_vs_consensus else None,
                report_date=actual.report_date,
                pead_data={
                    "surprise_direction": pead.surprise_direction,
                    "car_1d": float(pead.car_1d) if pead.car_1d else None,
                    "car_5d": float(pead.car_5d) if pead.car_5d else None,
                    "car_21d": float(pead.car_21d) if pead.car_21d else None,
                    "car_60d": float(pead.car_60d) if pead.car_60d else None,
                } if pead else None,
            )
        )

    return result


@router.get("/{ticker}/signal", response_model=Optional[EarningsSignalResponse])
def get_earnings_signal(
    ticker: str = Path(..., min_length=1, max_length=10),
    session: Session = Depends(get_session),
):
    """
    Get current pre-earnings signal for a ticker.

    Returns the most recent signal with confidence and reasoning.
    Only returns active signals (days_to_earnings >= 0).
    """
    repo = EarningsRepository(session)

    # Get active signals for this ticker
    active_signals = repo.get_active_signals(days_to_earnings_max=30)
    ticker_signals = [s for s in active_signals if s.ticker == ticker]

    if not ticker_signals:
        return None

    # Return most recent
    signal = ticker_signals[0]
    return EarningsSignalResponse(
        ticker=signal.ticker,
        fiscal_quarter=signal.fiscal_quarter,
        signal_date=signal.signal_date,
        signal_type=signal.signal_type,
        confidence=signal.confidence,
        smart_estimate_eps=float(signal.smart_estimate_eps),
        consensus_eps=float(signal.consensus_eps),
        divergence_pct=float(signal.divergence_pct),
        days_to_earnings=signal.days_to_earnings,
        valid_until=signal.valid_until,
    )


@router.get("/{ticker}/pead", response_model=List[PEADResponse])
def get_pead_data(
    ticker: str = Path(..., min_length=1, max_length=10),
    quarters: int = Query(8, ge=1, le=20),
    session: Session = Depends(get_session),
):
    """
    Get PEAD drift data for past N quarters.

    Returns cumulative abnormal returns at 1d, 5d, 21d, and 60d windows
    for each reported earnings.
    """
    repo = EarningsRepository(session)

    # Get actuals for this ticker
    actuals = repo.get_actuals_history(ticker, n_quarters=quarters)

    result = []
    for actual in actuals:
        pead = repo.get_pead(ticker, actual.fiscal_quarter)
        if pead:
            result.append(
                PEADResponse(
                    ticker=pead.ticker,
                    fiscal_quarter=pead.fiscal_quarter,
                    earnings_date=pead.earnings_date,
                    surprise_direction=pead.surprise_direction,
                    surprise_magnitude=float(pead.surprise_magnitude),
                    car_1d=float(pead.car_1d) if pead.car_1d else None,
                    car_5d=float(pead.car_5d) if pead.car_5d else None,
                    car_21d=float(pead.car_21d) if pead.car_21d else None,
                    car_60d=float(pead.car_60d) if pead.car_60d else None,
                )
            )

    return result


@router.get("/screener-signals", response_model=dict)
def get_screener_signals(
    tickers: str = Query(..., description="Comma-separated ticker list (e.g., 'AAPL,MSFT,TSLA')"),
    session: Session = Depends(get_session),
):
    """
    Batch get signals for screener integration.

    Returns active signals for all specified tickers in a single call.
    Useful for scanning large watchlists.
    """
    repo = EarningsRepository(session)

    # Parse and validate tickers
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if len(ticker_list) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 tickers allowed")
    if not all(t.isalnum() and len(t) <= 10 for t in ticker_list):
        raise HTTPException(status_code=400, detail="Invalid ticker format")

    # Get active signals
    active_signals = repo.get_active_signals(days_to_earnings_max=30)

    result = {}
    for ticker in ticker_list:
        ticker_signals = [s for s in active_signals if s.ticker == ticker]
        if ticker_signals:
            signal = ticker_signals[0]
            result[ticker] = {
                "signal": signal.signal_type,
                "confidence": signal.confidence,
                "days_to_earnings": signal.days_to_earnings,
                "smart_eps": float(signal.smart_estimate_eps),
                "consensus_eps": float(signal.consensus_eps),
                "divergence_pct": float(signal.divergence_pct),
            }

    return result


@router.post("/refresh")
def trigger_refresh(
    session: Session = Depends(get_session),
):
    """
    Trigger background refresh of earnings data.

    Pulls latest estimates and actuals from yfinance and recalculates
    SmartEstimates and signals. This is a blocking call - consider
    moving to background task in production.
    """
    service = EarningsDataService(session)

    try:
        result = service.refresh_all_estimates()
        return {
            "status": "success",
            "data": result,
        }
    except Exception as e:
        logger.error(f"Earnings refresh error: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": "Refresh operation failed. Please try again later.",
        }


@router.get("/smart-estimate/{ticker}/{quarter}", response_model=SmartEstimateResponse)
def calculate_smart_estimate(
    ticker: str = Path(..., min_length=1, max_length=10),
    quarter: str = Path(..., description="Fiscal quarter (e.g., 2025Q4)"),
    session: Session = Depends(get_session),
):
    """
    Calculate SmartEstimate for a specific ticker and quarter.

    Applies recency decay and analyst accuracy weighting to produce
    a weighted consensus estimate with signal recommendation.
    """
    engine = SmartEstimateEngine(session)

    result = engine.calculate_smart_estimate(ticker, quarter)

    # Generate signal
    if result.get("divergence_pct"):
        signal_type, confidence = engine.generate_signal(
            result["divergence_pct"],
            smart_eps=result.get("smart_eps"),
            consensus_eps=result.get("consensus_eps"),
        )
        result["signal"] = signal_type

    return result


@router.get("/pead-aggregate")
def get_pead_aggregate(
    surprise_direction: Optional[str] = Query(None, description="Filter by surprise direction (positive/negative/inline)"),
    session: Session = Depends(get_session),
):
    """
    Get aggregate PEAD statistics across all measurements.

    Groups by surprise direction and returns average CAR at each window.
    Useful for understanding the market's typical reaction patterns.
    """
    analyzer = PEADAnalyzer(session)

    aggregate = analyzer.aggregate_pead(surprise_direction=surprise_direction)

    return aggregate


@router.get("/pead-by-quartile")
def get_pead_by_quartile(
    session: Session = Depends(get_session),
):
    """
    Analyze PEAD patterns by surprise magnitude quartile.

    Groups earnings by surprise size and shows how large surprises
    correlate with stronger PEAD effects.
    """
    analyzer = PEADAnalyzer(session)

    result = analyzer.analyze_pead_by_surprise_quartile()

    return result
