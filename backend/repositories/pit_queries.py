"""
Point-in-Time (PiT) safe query helpers for the Factor Backtester.

These functions ensure that all historical queries return data as it was known
at a specific point in time, which is critical for backtesting accuracy.
"""

from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from backend.models.securities import Security, SecurityLifecycleEvent
from backend.models.market_data import PriceHistory, FundamentalsSnapshot
from backend.models.factors import CustomFactorScore
from backend.models.events import Event


def get_prices_pit(
    session: Session,
    ticker: str,
    as_of_date: date,
    start_date: Optional[date] = None,
) -> List[PriceHistory]:
    """
    Get historical prices as they were known on a specific date.

    This implements point-in-time semantics: returns only price data that
    had been ingested (as_of the as_of_date), ensuring backtests use only
    data that would have been available at that time.

    Args:
        session: SQLModel session
        ticker: Security ticker
        as_of_date: The date to treat as "now" - only returns data ingested by this date
        start_date: Optional start date for the price history window

    Returns:
        List of PriceHistory records, ordered by date ascending
    """
    query = select(PriceHistory).where(
        PriceHistory.ticker == ticker,
        PriceHistory.ingestion_timestamp <= datetime.combine(
            as_of_date, datetime.max.time(), tzinfo=timezone.utc
        ),
    )

    if start_date:
        query = query.where(PriceHistory.date >= start_date)

    query = query.order_by(PriceHistory.date.asc())
    return session.exec(query).all()


def get_fundamentals_pit(
    session: Session,
    ticker: str,
    as_of_date: date,
    metric_names: Optional[List[str]] = None,
    start_date: Optional[date] = None,
) -> List[FundamentalsSnapshot]:
    """
    Get fundamental metrics as they were known on a specific date.

    Returns fundamentals where the source_document_date is before as_of_date,
    and ingestion_timestamp confirms the data was available at as_of_date.

    Args:
        session: SQLModel session
        ticker: Security ticker
        as_of_date: The date to treat as "now"
        metric_names: Optional list of specific metric names to retrieve
        start_date: Optional start date for the fundamentals window

    Returns:
        List of FundamentalsSnapshot records
    """
    query = select(FundamentalsSnapshot).where(
        FundamentalsSnapshot.ticker == ticker,
        FundamentalsSnapshot.source_document_date <= as_of_date,
        FundamentalsSnapshot.ingestion_timestamp <= datetime.combine(
            as_of_date, datetime.max.time(), tzinfo=timezone.utc
        ),
    )

    if metric_names:
        query = query.where(FundamentalsSnapshot.metric_name.in_(metric_names))

    if start_date:
        query = query.where(FundamentalsSnapshot.fiscal_period_end >= start_date)

    query = query.order_by(FundamentalsSnapshot.fiscal_period_end.desc())
    return session.exec(query).all()


def get_active_universe_pit(
    session: Session,
    as_of_date: date,
) -> List[Security]:
    """
    Get the universe of active securities as of a specific date.

    Returns only securities that were ACTIVE (not delisted, bankrupt, or acquired)
    as of the as_of_date. Uses SecurityLifecycleEvent to determine status changes.
    Uses a single LEFT JOIN query instead of N+1.

    Args:
        session: SQLModel session
        as_of_date: The date to check for active status

    Returns:
        List of active Security records
    """
    # Single query with LEFT JOIN: get all securities and left join to lifecycle events
    # Filter for securities that have no deactivating events before as_of_date
    query = select(Security).where(
        ~Security.ticker.in_(
            select(SecurityLifecycleEvent.ticker).where(
                SecurityLifecycleEvent.effective_date <= as_of_date,
                SecurityLifecycleEvent.event_type.in_(
                    ["DELISTED", "BANKRUPT", "ACQUIRED"]
                ),
            )
        )
    )

    return session.exec(query).all()


def get_latest_fundamentals_pit(
    session: Session,
    ticker: str,
    as_of_date: date,
    metric_name: str,
) -> Optional[FundamentalsSnapshot]:
    """
    Get the most recent fundamental metric value as of a date.

    Useful for single-point lookups of a metric (e.g., latest EPS before a date).

    Args:
        session: SQLModel session
        ticker: Security ticker
        as_of_date: The date to check
        metric_name: Name of the metric

    Returns:
        The most recent FundamentalsSnapshot matching criteria, or None
    """
    query = select(FundamentalsSnapshot).where(
        FundamentalsSnapshot.ticker == ticker,
        FundamentalsSnapshot.metric_name == metric_name,
        FundamentalsSnapshot.source_document_date <= as_of_date,
        FundamentalsSnapshot.ingestion_timestamp <= datetime.combine(
            as_of_date, datetime.max.time(), tzinfo=timezone.utc
        ),
    ).order_by(FundamentalsSnapshot.source_document_date.desc())

    return session.exec(query).first()


def get_custom_factor_scores_pit(
    session: Session,
    factor_id: int,
    ticker: str,
    as_of_date: date,
) -> Optional[CustomFactorScore]:
    """
    Get the most recent custom factor score as of a date.

    Args:
        session: SQLModel session
        factor_id: ID of the factor definition
        ticker: Security ticker
        as_of_date: The date to check

    Returns:
        The most recent CustomFactorScore, or None
    """
    query = select(CustomFactorScore).where(
        CustomFactorScore.factor_id == factor_id,
        CustomFactorScore.ticker == ticker,
        CustomFactorScore.calculation_date <= as_of_date,
        CustomFactorScore.ingestion_timestamp <= datetime.combine(
            as_of_date, datetime.max.time(), tzinfo=timezone.utc
        ),
    ).order_by(CustomFactorScore.calculation_date.desc())

    return session.exec(query).first()


def get_factor_scores_pit_batch(
    session: Session,
    factor_ids: List[int],
    tickers: List[str],
    as_of_date: date
) -> Dict[tuple, float]:
    """
    Batch query: get all factor scores for multiple factors and tickers in ONE query.

    Replaces N+1 loop pattern with single IN clause query.

    Args:
        session: SQLModel session
        factor_ids: List of factor IDs
        tickers: List of security tickers
        as_of_date: The date to check

    Returns:
        Dictionary mapping (factor_id, ticker) -> factor_score value
    """
    if not factor_ids or not tickers:
        return {}

    # Single query with IN clauses
    query = select(CustomFactorScore).where(
        CustomFactorScore.factor_id.in_(factor_ids),
        CustomFactorScore.ticker.in_(tickers),
        CustomFactorScore.calculation_date <= as_of_date,
        CustomFactorScore.ingestion_timestamp <= datetime.combine(
            as_of_date, datetime.max.time(), tzinfo=timezone.utc
        ),
    )

    results = session.exec(query).all()

    # Build result dictionary, taking most recent for each (factor_id, ticker) pair
    scores_dict = {}
    for score in results:
        key = (score.factor_id, score.ticker)
        # Keep only if we haven't seen this pair or this one is more recent
        if key not in scores_dict or score.calculation_date > scores_dict[key][1]:
            scores_dict[key] = (float(score.factor_value), score.calculation_date)

    # Return just the float values
    return {k: v[0] for k, v in scores_dict.items()}


def get_prices_pit_batch(
    session: Session,
    tickers: List[str],
    start_date: date,
    end_date: date,
    as_of_date: date
) -> Dict[str, List[PriceHistory]]:
    """
    Batch query: get prices for multiple tickers in ONE query.

    Replaces N+1 loop pattern with single IN clause query.

    Args:
        session: SQLModel session
        tickers: List of security tickers
        start_date: Start of price window
        end_date: End of price window
        as_of_date: The date to treat as "now" - only returns data ingested by this date

    Returns:
        Dictionary mapping ticker -> list of PriceHistory records
    """
    if not tickers:
        return {}

    # Single query with IN clause
    query = select(PriceHistory).where(
        PriceHistory.ticker.in_(tickers),
        PriceHistory.date >= start_date,
        PriceHistory.date <= end_date,
        PriceHistory.ingestion_timestamp <= datetime.combine(
            as_of_date, datetime.max.time(), tzinfo=timezone.utc
        ),
    ).order_by(PriceHistory.ticker.asc(), PriceHistory.date.asc())

    results = session.exec(query).all()

    # Organize results by ticker
    prices_by_ticker = {ticker: [] for ticker in tickers}
    for price in results:
        prices_by_ticker[price.ticker].append(price)

    return prices_by_ticker


def get_events_pit(
    session: Session,
    ticker: str,
    as_of_date: date,
) -> List[Event]:
    """
    Get events as they were known on a specific date (Point-in-Time safe).

    Returns only events where detected_at <= as_of_date, ensuring backtests
    use only events that would have been detected at that point in time.

    Args:
        session: SQLModel session
        ticker: Security ticker
        as_of_date: The date to treat as "now" - only returns events detected by this date

    Returns:
        List of Event records, ordered by detected_at DESC
    """
    query = select(Event).where(
        Event.ticker == ticker,
        Event.detected_at <= datetime.combine(
            as_of_date, datetime.max.time(), tzinfo=timezone.utc
        ),
    ).order_by(Event.detected_at.desc())

    return session.exec(query).all()
