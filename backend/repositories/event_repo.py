"""
Repository for Event Scanner CRUD operations and queries.

Provides database access layer for events, classifications, alpha decay windows,
factor bridges, and related entities.
"""

from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any
from decimal import Decimal
from sqlmodel import Session, select
from backend.models.events import (
    Event,
    EventClassificationRule,
    AlphaDecayWindow,
    EventFactorBridge,
    EventSourceMapping,
    EventAlertConfiguration,
    EventCorrelationAnalysis,
)


class EventRepository:
    """Repository for event-related database operations."""

    def __init__(self, session: Session):
        self.session = session

    # ==================== Event CRUD ====================

    def create_event(
        self,
        ticker: str,
        event_type: str,
        severity_score: int,
        detected_at: datetime,
        event_date: date,
        source: str,
        headline: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Event:
        """
        Create a new event record.

        Args:
            ticker: Security ticker symbol
            event_type: Type of event (earnings, m_and_a, insider_trade, etc.)
            severity_score: Severity rating 1-5
            detected_at: Point-in-time when event was detected
            event_date: Date when event occurred
            source: Source of event (SEC_EDGAR, YFINANCE, MANUAL)
            headline: Short headline of event
            description: Optional longer description
            metadata: Optional JSON metadata

        Returns:
            Created Event object
        """
        event = Event(
            ticker=ticker,
            event_type=event_type,
            severity_score=severity_score,
            detected_at=detected_at,
            event_date=event_date,
            source=source,
            headline=headline,
            description=description,
            metadata=metadata,
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def get_event(self, event_id: int) -> Optional[Event]:
        """Get an event by ID."""
        return self.session.exec(
            select(Event).where(Event.event_id == event_id)
        ).first()

    def list_events(
        self,
        ticker: Optional[str] = None,
        event_type: Optional[str] = None,
        severity_min: Optional[int] = None,
        severity_max: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Event]:
        """
        List events with optional filtering.

        Args:
            ticker: Optional ticker filter
            event_type: Optional event type filter
            severity_min: Optional minimum severity (1-5)
            severity_max: Optional maximum severity (1-5)
            start_date: Optional start date filter
            end_date: Optional end date filter
            source: Optional source filter
            limit: Number of results to return
            offset: Number of results to skip

        Returns:
            List of Event objects, ordered by detected_at DESC
        """
        query = select(Event).order_by(Event.detected_at.desc())

        if ticker:
            query = query.where(Event.ticker == ticker)

        if event_type:
            query = query.where(Event.event_type == event_type)

        if severity_min is not None:
            query = query.where(Event.severity_score >= severity_min)

        if severity_max is not None:
            query = query.where(Event.severity_score <= severity_max)

        if start_date:
            query = query.where(Event.event_date >= start_date)

        if end_date:
            query = query.where(Event.event_date <= end_date)

        if source:
            query = query.where(Event.source == source)

        query = query.limit(limit).offset(offset)
        return self.session.exec(query).all()

    def get_events_for_timeline(
        self,
        start_detected_at: datetime,
        end_detected_at: datetime,
        ticker: Optional[str] = None,
        event_type: Optional[str] = None,
        min_severity: int = 1,
    ) -> List[Event]:
        """
        Get events for timeline display, ordered by detected_at DESC.

        Args:
            start_detected_at: Start of detection time window
            end_detected_at: End of detection time window
            ticker: Optional ticker filter
            event_type: Optional event type filter
            min_severity: Minimum severity to include (default 1)

        Returns:
            List of Event objects ordered by detected_at DESC
        """
        query = select(Event).where(
            Event.detected_at >= start_detected_at,
            Event.detected_at <= end_detected_at,
            Event.severity_score >= min_severity,
        ).order_by(Event.detected_at.desc())

        if ticker:
            query = query.where(Event.ticker == ticker)

        if event_type:
            query = query.where(Event.event_type == event_type)

        return self.session.exec(query).all()

    def get_events_by_ticker(
        self,
        ticker: str,
        limit: int = 50,
    ) -> List[Event]:
        """
        Get recent events for a ticker (for screener badge generation).

        Args:
            ticker: Security ticker
            limit: Number of recent events to return

        Returns:
            List of Event objects ordered by detected_at DESC
        """
        query = select(Event).where(
            Event.ticker == ticker
        ).order_by(Event.detected_at.desc()).limit(limit)

        return self.session.exec(query).all()

    # ==================== Alpha Decay Window ====================

    def save_alpha_decay_window(
        self,
        event_id: int,
        window_type: str,
        abnormal_return: Decimal,
        benchmark_return: Decimal,
        measured_at: datetime,
        confidence: Optional[Decimal] = None,
        sample_size: Optional[int] = None,
    ) -> AlphaDecayWindow:
        """
        Save an alpha decay window measurement.

        Args:
            event_id: Parent event ID
            window_type: Window duration (1d, 5d, 21d, 63d)
            abnormal_return: Abnormal return in this window
            benchmark_return: Benchmark return in window
            measured_at: Point-in-time when measured
            confidence: Optional confidence score (0-1)
            sample_size: Optional number of observations

        Returns:
            Created AlphaDecayWindow object
        """
        window = AlphaDecayWindow(
            event_id=event_id,
            window_type=window_type,
            abnormal_return=abnormal_return,
            benchmark_return=benchmark_return,
            measured_at=measured_at,
            confidence=confidence,
            sample_size=sample_size,
        )
        self.session.add(window)
        self.session.commit()
        self.session.refresh(window)
        return window

    def get_alpha_decay_windows(
        self,
        event_id: int,
        window_type: Optional[str] = None,
    ) -> List[AlphaDecayWindow]:
        """
        Get alpha decay windows for an event.

        Args:
            event_id: Event ID
            window_type: Optional filter by window type (1d, 5d, 21d, 63d)

        Returns:
            List of AlphaDecayWindow objects
        """
        query = select(AlphaDecayWindow).where(
            AlphaDecayWindow.event_id == event_id
        ).order_by(AlphaDecayWindow.measured_at.desc())

        if window_type:
            query = query.where(AlphaDecayWindow.window_type == window_type)

        return self.session.exec(query).all()

    # ==================== Event Factor Bridge ====================

    def create_event_factor_bridge(
        self,
        event_id: int,
        factor_id: int,
        signal_value: Decimal,
        valid_until: Optional[datetime] = None,
    ) -> EventFactorBridge:
        """
        Create a bridge linking an event to a factor signal.

        Args:
            event_id: Parent event ID
            factor_id: Factor definition ID
            signal_value: Signal strength (-1 to +1)
            valid_until: Optional expiration datetime

        Returns:
            Created EventFactorBridge object
        """
        bridge = EventFactorBridge(
            event_id=event_id,
            factor_id=factor_id,
            signal_value=signal_value,
            valid_until=valid_until,
        )
        self.session.add(bridge)
        self.session.commit()
        self.session.refresh(bridge)
        return bridge

    def get_active_factor_signals(
        self,
        event_id: int,
        as_of_date: Optional[datetime] = None,
    ) -> List[EventFactorBridge]:
        """
        Get active factor signals for an event (for backtester integration).

        Args:
            event_id: Event ID
            as_of_date: Optional point-in-time check (default: now)

        Returns:
            List of EventFactorBridge objects with unexpired signals
        """
        as_of = as_of_date or datetime.now(timezone.utc)

        query = select(EventFactorBridge).where(
            EventFactorBridge.event_id == event_id,
        )

        # Filter for valid signals (either no expiration or not expired)
        from sqlalchemy import or_
        query = query.where(
            or_(
                EventFactorBridge.valid_until.is_(None),
                EventFactorBridge.valid_until >= as_of,
            )
        )

        return self.session.exec(query).all()

    # ==================== Event Source Mapping ====================

    def save_event_source_mapping(
        self,
        event_id: int,
        source_type: str,
        source_id: str,
        source_url: Optional[str] = None,
        extracted_data: Optional[Dict[str, Any]] = None,
    ) -> EventSourceMapping:
        """
        Map an event to its source.

        Args:
            event_id: Parent event ID
            source_type: Type of source (SEC_EDGAR, YFINANCE, etc.)
            source_id: ID from source (accession number, filing ID, etc.)
            source_url: Optional URL to source
            extracted_data: Optional JSON extracted from source

        Returns:
            Created EventSourceMapping object
        """
        mapping = EventSourceMapping(
            event_id=event_id,
            source_type=source_type,
            source_id=source_id,
            source_url=source_url,
            extracted_data=extracted_data,
        )
        self.session.add(mapping)
        self.session.commit()
        self.session.refresh(mapping)
        return mapping

    def get_event_source_mappings(
        self,
        event_id: int,
    ) -> List[EventSourceMapping]:
        """Get all source mappings for an event."""
        return self.session.exec(
            select(EventSourceMapping).where(
                EventSourceMapping.event_id == event_id
            )
        ).all()

    # ==================== Classification Rules ====================

    def create_classification_rule(
        self,
        classification: str,
        pattern_type: str,
        pattern_value: Dict[str, Any],
        confidence_score: int,
        enabled: bool = True,
        description: Optional[str] = None,
    ) -> EventClassificationRule:
        """
        Create an event classification rule.

        Args:
            classification: Event type or category name
            pattern_type: Type of pattern (keyword, filing_form, calendar_event)
            pattern_value: JSON pattern definition
            confidence_score: Confidence 0-100
            enabled: Whether rule is active
            description: Optional description

        Returns:
            Created EventClassificationRule object
        """
        rule = EventClassificationRule(
            classification=classification,
            pattern_type=pattern_type,
            pattern_value=pattern_value,
            confidence_score=confidence_score,
            enabled=enabled,
            description=description,
        )
        self.session.add(rule)
        self.session.commit()
        self.session.refresh(rule)
        return rule

    def get_classification_rules(
        self,
        enabled_only: bool = True,
    ) -> List[EventClassificationRule]:
        """
        Get classification rules.

        Args:
            enabled_only: If True, only return enabled rules

        Returns:
            List of EventClassificationRule objects
        """
        query = select(EventClassificationRule)

        if enabled_only:
            query = query.where(EventClassificationRule.enabled == True)

        query = query.order_by(EventClassificationRule.confidence_score.desc())
        return self.session.exec(query).all()

    # ==================== Alert Configuration ====================

    def create_alert_configuration(
        self,
        event_type_filter: List[str],
        severity_threshold: int = 1,
        enabled: bool = True,
        tickers_filter: Optional[List[str]] = None,
    ) -> EventAlertConfiguration:
        """
        Create alert configuration.

        Args:
            event_type_filter: List of event types to alert on
            severity_threshold: Minimum severity (1-5)
            enabled: Whether alerts are active
            tickers_filter: Optional list of tickers to alert on (null = all)

        Returns:
            Created EventAlertConfiguration object
        """
        config = EventAlertConfiguration(
            event_type_filter=event_type_filter,
            severity_threshold=severity_threshold,
            enabled=enabled,
            tickers_filter=tickers_filter,
        )
        self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config

    def get_active_alert_configuration(self) -> Optional[EventAlertConfiguration]:
        """Get the currently active alert configuration."""
        return self.session.exec(
            select(EventAlertConfiguration).where(
                EventAlertConfiguration.enabled == True
            )
        ).first()

    # ==================== Correlation Analysis ====================

    def save_event_correlation_analysis(
        self,
        event_type_1: str,
        event_type_2: str,
        co_occurrence_count: int,
        time_window_days: int,
        correlation_strength: Decimal,
        analyzed_period_end: date,
    ) -> EventCorrelationAnalysis:
        """
        Save event correlation analysis.

        Args:
            event_type_1: First event type
            event_type_2: Second event type
            co_occurrence_count: Number of co-occurrences
            time_window_days: Analysis window in days
            correlation_strength: Correlation 0-1
            analyzed_period_end: End date of analysis period

        Returns:
            Created EventCorrelationAnalysis object
        """
        analysis = EventCorrelationAnalysis(
            event_type_1=event_type_1,
            event_type_2=event_type_2,
            co_occurrence_count=co_occurrence_count,
            time_window_days=time_window_days,
            correlation_strength=correlation_strength,
            analyzed_period_end=analyzed_period_end,
        )
        self.session.add(analysis)
        self.session.commit()
        self.session.refresh(analysis)
        return analysis

    def get_event_correlations(
        self,
        event_type: Optional[str] = None,
    ) -> List[EventCorrelationAnalysis]:
        """
        Get event correlation analyses.

        Args:
            event_type: Optional filter by event type

        Returns:
            List of EventCorrelationAnalysis objects
        """
        query = select(EventCorrelationAnalysis).order_by(
            EventCorrelationAnalysis.correlation_strength.desc()
        )

        if event_type:
            from sqlalchemy import or_
            query = query.where(
                or_(
                    EventCorrelationAnalysis.event_type_1 == event_type,
                    EventCorrelationAnalysis.event_type_2 == event_type,
                )
            )

        return self.session.exec(query).all()
