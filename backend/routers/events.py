"""
API Router for Event Scanner Phase 2 - Complex Event Processing endpoints.

Endpoints:
- GET /api/events - List events (paginated, filterable)
- GET /api/events/{event_id} - Get event details with alpha decay
- GET /api/events/{event_id}/alpha-decay - Get alpha decay windows
- POST /api/events/scan - Trigger manual scan (background task)
- GET /api/events/polling-status - Get polling service status
- GET /api/events/timeline - Get event timeline for watchlist
- GET /api/events/screener-badges - Get event badges for screener
- DELETE /api/events/{event_id} - Delete an event
"""

import logging
from typing import List, Optional
from datetime import datetime, date, timezone
from fastapi import APIRouter, Depends, Query, Path, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from sqlmodel import Session
from backend.database import get_session
from backend.repositories.event_repo import EventRepository
from backend.models.events import Event, AlphaDecayWindow
from backend.services.event_polling import BackgroundPollingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])

# Pydantic models for API requests/responses

class AlphaDecayResponse(BaseModel):
    """Alpha decay window response."""
    window_id: int
    event_id: int
    window_type: str
    abnormal_return: float
    benchmark_return: float
    measured_at: str
    confidence: Optional[float] = None
    sample_size: Optional[int] = None

    class Config:
        from_attributes = True


class EventDetailResponse(BaseModel):
    """Event detail response."""
    event_id: int
    ticker: str
    event_type: str
    severity_score: int
    detected_at: str
    event_date: str
    source: str
    headline: str
    description: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: str
    alpha_decay_windows: List[AlphaDecayResponse] = []

    class Config:
        from_attributes = True


class EventListItemResponse(BaseModel):
    """Event list item response."""
    event_id: int
    ticker: str
    event_type: str
    severity_score: int
    detected_at: str
    event_date: str
    headline: str
    source: str

    class Config:
        from_attributes = True


class EventsListResponse(BaseModel):
    """Paginated events list response."""
    items: List[EventListItemResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class PollingStatusResponse(BaseModel):
    """Polling service status response."""
    status: str
    last_run: Optional[str] = None
    next_run_estimate: Optional[str] = None
    polling_interval_hours: int
    events_found: int
    errors: List[str] = []


class TimelineItemResponse(BaseModel):
    """Event timeline item."""
    event_id: int
    ticker: str
    event_type: str
    severity_score: int
    headline: str
    detected_at: str
    event_date: str


class TimelineResponse(BaseModel):
    """Event timeline response."""
    items: List[TimelineItemResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class ScreenerBadge(BaseModel):
    """Screener badge for a ticker."""
    ticker: str
    max_severity: int
    recent_event_count: int
    event_types: List[str]
    latest_event: Optional[str] = None


class ScreenerBadgesResponse(BaseModel):
    """Batch screener badges response."""
    badges: List[ScreenerBadge]
    timestamp: str


class ScanTriggerResponse(BaseModel):
    """Response to scan trigger request."""
    message: str
    task_id: Optional[str] = None
    status: str


# API Endpoints


@router.get("", response_model=EventsListResponse)
def list_events(
    session: Session = Depends(get_session),
    ticker: Optional[str] = Query(None, description="Filter by ticker (1-5 chars, alphanumeric)"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    severity_min: Optional[int] = Query(None, ge=1, le=5, description="Minimum severity"),
    severity_max: Optional[int] = Query(None, ge=1, le=5, description="Maximum severity"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    source: Optional[str] = Query(None, description="Filter by source (SEC_EDGAR, YFINANCE, etc.)"),
    limit: int = Query(50, ge=1, le=500, description="Results per page"),
    offset: int = Query(0, ge=0, description="Results to skip"),
):
    """
    List events with optional filtering.

    Query parameters:
    - ticker: Filter by stock ticker (1-5 alphanumeric chars)
    - event_type: Filter by event type
    - severity_min/max: Filter by severity range (1-5)
    - start_date/end_date: Filter by event date range
    - source: Filter by source (SEC_EDGAR, YFINANCE)
    - limit: Results per page (1-500, default 50)
    - offset: Results to skip (for pagination)

    Returns paginated list of events ordered by detected_at DESC.
    """
    try:
        from sqlmodel import func, select
        from backend.models.events import Event

        repository = EventRepository(session)

        # Build count query with same filters (efficient: single query)
        count_query = select(func.count(Event.event_id))

        if ticker:
            count_query = count_query.where(Event.ticker == ticker)
        if event_type:
            count_query = count_query.where(Event.event_type == event_type)
        if severity_min is not None:
            count_query = count_query.where(Event.severity_score >= severity_min)
        if severity_max is not None:
            count_query = count_query.where(Event.severity_score <= severity_max)
        if start_date:
            count_query = count_query.where(Event.event_date >= start_date)
        if end_date:
            count_query = count_query.where(Event.event_date <= end_date)
        if source:
            count_query = count_query.where(Event.source == source)

        total = session.exec(count_query).one()

        events = repository.list_events(
            ticker=ticker,
            event_type=event_type,
            severity_min=severity_min,
            severity_max=severity_max,
            start_date=start_date,
            end_date=end_date,
            source=source,
            limit=limit,
            offset=offset,
        )

        return EventsListResponse(
            items=[EventListItemResponse.from_orm(e) for e in events],
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        )
    except Exception as e:
        logger.error(f"Error listing events: {e}")
        return EventsListResponse(items=[], total=0, limit=limit, offset=offset, has_more=False)


@router.get("/{event_id}", response_model=EventDetailResponse)
def get_event_detail(
    event_id: int = Path(..., gt=0, description="Event ID (must be > 0)"),
    session: Session = Depends(get_session),
):
    """
    Get detailed information for a specific event.

    Includes:
    - Event metadata
    - All alpha decay windows
    - Source mappings
    - Factor signals
    """
    repository = EventRepository(session)

    event = repository.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Get alpha decay windows
    decay_windows = repository.get_alpha_decay_windows(event_id)

    return EventDetailResponse(
        event_id=event.event_id,
        ticker=event.ticker,
        event_type=event.event_type,
        severity_score=event.severity_score,
        detected_at=event.detected_at.isoformat(),
        event_date=event.event_date.isoformat(),
        source=event.source,
        headline=event.headline,
        description=event.description,
        metadata=event.metadata,
        created_at=event.created_at.isoformat(),
        alpha_decay_windows=[
            AlphaDecayResponse(
                window_id=w.window_id,
                event_id=w.event_id,
                window_type=w.window_type,
                abnormal_return=float(w.abnormal_return),
                benchmark_return=float(w.benchmark_return),
                measured_at=w.measured_at.isoformat(),
                confidence=float(w.confidence) if w.confidence else None,
                sample_size=w.sample_size,
            )
            for w in decay_windows
        ]
    )


@router.get("/{event_id}/alpha-decay", response_model=List[AlphaDecayResponse])
def get_alpha_decay(
    event_id: int = Path(..., gt=0, description="Event ID (must be > 0)"),
    window_type: Optional[str] = Query(None, description="Filter by window type (1d, 5d, 21d, 63d)"),
    session: Session = Depends(get_session),
):
    """
    Get alpha decay windows for an event.

    Returns abnormal returns and alpha metrics for each time window post-event.

    Query parameters:
    - window_type: Optional filter (1d, 5d, 21d, or 63d)
    """
    repository = EventRepository(session)

    # Verify event exists
    event = repository.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    decay_windows = repository.get_alpha_decay_windows(event_id, window_type=window_type)

    return [
        AlphaDecayResponse(
            window_id=w.window_id,
            event_id=w.event_id,
            window_type=w.window_type,
            abnormal_return=float(w.abnormal_return),
            benchmark_return=float(w.benchmark_return),
            measured_at=w.measured_at.isoformat(),
            confidence=float(w.confidence) if w.confidence else None,
            sample_size=w.sample_size,
        )
        for w in decay_windows
    ]


@router.post("/scan", response_model=ScanTriggerResponse)
def trigger_manual_scan(
    tickers: Optional[List[str]] = Query(None, description="Specific tickers to scan"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: Session = Depends(get_session),
):
    """
    Trigger a manual event scan cycle.

    Runs the full CEP pipeline in the background:
    1. Scan event sources (SEC EDGAR, yfinance)
    2. Classify and score events
    3. Calculate alpha decay windows
    4. Generate factor signals
    5. Update screener badges

    Query parameters:
    - tickers: Optional list of specific tickers (comma-separated or repeated param)

    Returns immediately with task status. Results are saved to database asynchronously.
    """
    try:
        polling_service = BackgroundPollingService()

        # Add background task
        background_tasks.add_task(
            polling_service.run_polling_cycle,
            session,
            tickers=tickers,
        )

        logger.info(f"Scheduled background scan for {len(tickers) if tickers else 'all'} tickers")

        return ScanTriggerResponse(
            message="Event scan triggered in background",
            status="queued",
        )
    except Exception as e:
        logger.error(f"Error triggering scan: {e}")
        return ScanTriggerResponse(
            message="Failed to trigger event scan",
            status="error",
        )


@router.get("/polling-status", response_model=PollingStatusResponse)
def get_polling_status():
    """
    Get current status of the background polling service.

    Returns:
    - last_run: Timestamp of last completed scan
    - next_run_estimate: Estimated time of next scheduled scan
    - events_found: Number of events found in last scan
    - errors: Any errors from last scan
    """
    try:
        polling_service = BackgroundPollingService()
        status = polling_service.get_polling_status()

        return PollingStatusResponse(
            status=status.get("status", "unknown"),
            last_run=status.get("last_run"),
            next_run_estimate=status.get("next_run_estimate"),
            polling_interval_hours=status.get("polling_interval_hours", 1),
            events_found=status.get("events_found", 0),
            errors=status.get("errors", []),
        )
    except Exception as e:
        logger.error(f"Error getting polling status: {e}")
        return PollingStatusResponse(
            status="unknown",
            polling_interval_hours=1,
            events_found=0,
            errors=[str(e)],
        )


@router.get("/timeline", response_model=TimelineResponse)
def get_event_timeline(
    days_back: int = Query(30, ge=1, le=365, description="Days to look back"),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    min_severity: int = Query(1, ge=1, le=5, description="Minimum severity"),
    limit: int = Query(100, ge=1, le=500, description="Results per page"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    session: Session = Depends(get_session),
):
    """
    Get event timeline for watchlist.

    Returns most recent events across all tickers in the watchlist,
    ordered by detected_at DESC.

    Query parameters:
    - days_back: Look back this many days (1-365)
    - ticker: Optional filter by specific ticker
    - event_type: Optional filter by event type
    - min_severity: Minimum severity to include (1-5)
    - limit: Results per page
    - offset: Results to skip
    """
    try:
        repository = EventRepository(session)

        start_date = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days_back)
        end_date = datetime.now(timezone.utc)

        events = repository.get_events_for_timeline(
            start_detected_at=start_date,
            end_detected_at=end_date,
            ticker=ticker,
            event_type=event_type,
            min_severity=min_severity,
        )

        # Apply pagination
        total = len(events)
        paginated_events = events[offset : offset + limit]

        return TimelineResponse(
            items=[
                TimelineItemResponse(
                    event_id=e.event_id,
                    ticker=e.ticker,
                    event_type=e.event_type,
                    severity_score=e.severity_score,
                    headline=e.headline,
                    detected_at=e.detected_at.isoformat(),
                    event_date=e.event_date.isoformat(),
                )
                for e in paginated_events
            ],
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        )
    except Exception as e:
        logger.error(f"Error getting event timeline: {e}")
        return TimelineResponse(items=[], total=0, limit=limit, offset=offset, has_more=False)


@router.get("/screener-badges", response_model=ScreenerBadgesResponse)
def get_screener_badges(
    tickers: List[str] = Query(..., description="Tickers to get badges for (can repeat)"),
    lookback_days: int = Query(30, ge=1, le=365, description="Days to look back for recent events"),
    session: Session = Depends(get_session),
):
    """
    Get event severity badges for screener display.

    Batch endpoint: returns event badge data for multiple tickers for use in
    screener UI (showing recent event indicators, severity levels, etc.).

    Uses batch query for efficiency (no N+1 problem).

    Query parameters:
    - tickers: List of tickers (repeat parameter: ?tickers=AAPL&tickers=MSFT)
    - lookback_days: Days to look back for recent events
    """
    from backend.services.event_consumer import EventConsumerService
    from backend.repositories.event_repo import EventRepository

    if not tickers:
        raise HTTPException(status_code=400, detail="At least one ticker required")

    consumer = EventConsumerService()
    repository = EventRepository(session)
    badges = []

    # Batch query: get all events for all tickers at once (no N+1)
    cutoff_date = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=lookback_days)
    all_events = repository.get_events_for_timeline(
        start_detected_at=cutoff_date,
        end_detected_at=datetime.now(timezone.utc),
    )

    # Build ticker -> events map
    ticker_events = {}
    for event in all_events:
        if event.ticker not in ticker_events:
            ticker_events[event.ticker] = []
        ticker_events[event.ticker].append(event)

    # Process each requested ticker
    for ticker in tickers[:100]:  # Limit to 100 tickers
        try:
            events = ticker_events.get(ticker, [])

            # Calculate badge data from events
            max_severity = 1
            event_types = set()
            recent_event_count = len(events)
            latest_event = None

            for event in events[:10]:  # Show top 10
                if event.severity_score > max_severity:
                    max_severity = event.severity_score
                event_types.add(event.event_type)

                if latest_event is None:
                    latest_event = f"{event.event_type} (severity {event.severity_score})"

            badges.append(
                ScreenerBadge(
                    ticker=ticker,
                    max_severity=max_severity,
                    recent_event_count=recent_event_count,
                    event_types=list(event_types),
                    latest_event=latest_event,
                )
            )
        except Exception as e:
            logger.error(f"Error getting badge for {ticker}: {e}", exc_info=True)
            # Still include ticker with default badge
            badges.append(
                ScreenerBadge(
                    ticker=ticker,
                    max_severity=1,
                    recent_event_count=0,
                    event_types=[],
                    latest_event=None,
                )
            )

    return ScreenerBadgesResponse(
        badges=badges,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.delete("/{event_id}")
def delete_event(
    event_id: int = Path(..., gt=0, description="Event ID (must be > 0)"),
    session: Session = Depends(get_session),
):
    """
    Delete an event from the database.

    Cascading deletes: alpha_decay_windows, factor_bridges, source_mappings.
    """
    repository = EventRepository(session)

    event = repository.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    try:
        session.delete(event)
        session.commit()
        logger.info(f"Deleted event {event_id}")
        return {"message": "Event deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting event {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
