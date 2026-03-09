"""
Event Consumer Service for Phase 2 CEP - Layer 3 of Complex Event Processing.

Generates factor signals and screener badges from processed events:
- Convert events into backtestable factor signals
- Generate severity badges for screener display
- Analyze event type co-occurrences
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal

from sqlmodel import Session
from backend.repositories.event_repo import EventRepository
from backend.models.events import Event

logger = logging.getLogger(__name__)


class EventConsumerService:
    """Layer 3 of CEP: Factor signal generation and screener badge creation."""

    # Signal strength mapping: severity score (1-5) to normalized signal (-1 to +1)
    SEVERITY_TO_SIGNAL_STRENGTH = {
        1: Decimal("0.2"),
        2: Decimal("0.4"),
        3: Decimal("0.6"),
        4: Decimal("0.8"),
        5: Decimal("1.0"),
    }

    # Event type sentiment: positive (buy signal) or negative (sell signal)
    EVENT_TYPE_SENTIMENT = {
        # Insider activity - generally positive for buys
        "insider_trade_buy_large": Decimal("0.8"),
        "insider_trade_buy_small": Decimal("0.4"),
        "insider_trade_sell_large": Decimal("-0.6"),
        "insider_trade_sell_small": Decimal("-0.2"),
        # Beneficial ownership - activist 13D generally negative short-term
        "beneficial_ownership_13d": Decimal("-0.3"),
        "beneficial_ownership_13g": Decimal("0.1"),
        # Earnings - neutral until surprise known
        "earnings_announcement": Decimal("0.0"),
        # Dividends - generally positive
        "dividend_ex_date": Decimal("0.2"),
        "dividend_change_significant": Decimal("0.4"),
        # SEC filings - mixed sentiment
        "sec_filing_8k_item_1_01": Decimal("-1.0"),  # Bankruptcy - very negative
        "sec_filing_8k_item_2_01": Decimal("-1.0"),  # Bankruptcy/costs - very negative
        "sec_filing_8k_item_2_02": Decimal("-0.9"),
        "sec_filing_8k_item_2_03": Decimal("-0.7"),
        "sec_filing_8k_item_2_04": Decimal("-0.6"),
        "sec_filing_8k_item_2_05": Decimal("-0.5"),
        "sec_filing_8k_item_default": Decimal("0.0"),
        "sec_filing_10k": Decimal("0.0"),
        "sec_filing_10q": Decimal("0.0"),
    }

    # Signal value computation: (sentiment + severity_strength) / 2, clamped to [-1, +1]
    # Positive: bullish signals
    # Negative: bearish signals
    # Near 0: neutral/informational

    # Signal expiration: how long factor signal remains valid (in days)
    SIGNAL_EXPIRATION_DAYS = {
        "insider_trade": 30,
        "earnings_announcement": 7,
        "dividend_ex_date": 1,
        "beneficial_ownership_13d": 60,
        "sec_filing": 14,
    }

    # Factor definition IDs for common factors
    # These would come from the factor_definition table
    # For MVP, we'll use representative IDs
    FACTOR_IDS = {
        "insider_sentiment": 1,
        "earnings_surprise": 2,
        "activist_involvement": 3,
        "dividend_yield": 4,
        "corporate_action": 5,
    }

    def __init__(self):
        """Initialize EventConsumerService."""
        pass

    def generate_factor_signals(
        self,
        session: Session,
        event_id: int,
        event: Optional[Event] = None,
    ) -> List[Dict[str, Any]]:
        """
        Convert event into backtestable factor signals.

        Creates EventFactorBridge entries mapping event to relevant factors with signal values.
        Signal value: combination of sentiment (from event type) and severity strength.

        Args:
            session: SQLModel session
            event_id: Event ID to generate signals for
            event: Optional Event object (if not provided, will be fetched)

        Returns:
            List of created factor signal dictionaries with:
                - factor_id, signal_value, valid_until, bridge_id
        """
        repository = EventRepository(session)
        signals = []

        try:
            # Get event if not provided
            if not event:
                event = repository.get_event(event_id)
                if not event:
                    logger.error(f"Event {event_id} not found")
                    return signals

            # Determine relevant factors based on event type
            factor_assignments = self._get_factor_assignments(event.event_type, event.severity_score)

            for factor_id, factor_signal_value in factor_assignments:
                # Calculate signal expiration
                expiration_days = self._get_signal_expiration(event.event_type)
                valid_until = datetime.now(timezone.utc) + timedelta(days=expiration_days)

                # Create factor bridge
                bridge = repository.create_event_factor_bridge(
                    event_id=event_id,
                    factor_id=factor_id,
                    signal_value=factor_signal_value,
                    valid_until=valid_until,
                )

                signals.append({
                    "factor_id": factor_id,
                    "signal_value": float(factor_signal_value),
                    "valid_until": valid_until.isoformat(),
                    "bridge_id": bridge.bridge_id,
                })

                logger.info(
                    f"Created factor signal {bridge.bridge_id}: event={event_id} "
                    f"factor={factor_id} signal={float(factor_signal_value):.3f}"
                )

        except Exception as e:
            logger.error(f"Error generating factor signals for event {event_id}: {e}", exc_info=True)

        return signals

    def update_screener_badges(
        self,
        session: Session,
        ticker: str,
        lookback_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Generate severity badges for screener display.

        Retrieves recent events for a ticker and creates badge data showing:
        - Latest event types and severity
        - Max severity in lookback window
        - Count of events by type

        Args:
            session: SQLModel session
            ticker: Security ticker
            lookback_days: Days to look back for recent events (default 30)

        Returns:
            Dictionary with:
                - ticker
                - max_severity (1-5)
                - recent_events (list of event summaries)
                - event_count_by_type (dict)
        """
        repository = EventRepository(session)
        badges = {
            "ticker": ticker,
            "max_severity": 1,
            "recent_events": [],
            "event_count_by_type": {},
        }

        try:
            # Get recent events
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            events = repository.get_events_for_timeline(
                start_detected_at=cutoff_date,
                end_detected_at=datetime.now(timezone.utc),
                ticker=ticker,
            )

            if not events:
                return badges

            # Process events
            max_severity = 1
            event_type_counts = {}

            for event in events[:10]:  # Limit to 10 most recent for display
                # Update max severity
                if event.severity_score > max_severity:
                    max_severity = event.severity_score

                # Count by type
                if event.event_type not in event_type_counts:
                    event_type_counts[event.event_type] = 0
                event_type_counts[event.event_type] += 1

                # Add to recent events
                badges["recent_events"].append({
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "severity": event.severity_score,
                    "headline": event.headline,
                    "detected_at": event.detected_at.isoformat(),
                })

            badges["max_severity"] = max_severity
            badges["event_count_by_type"] = event_type_counts

        except Exception as e:
            logger.error(f"Error updating screener badges for {ticker}: {e}")

        return badges

    def get_event_correlations(
        self,
        session: Session,
        lookback_days: int = 90,
    ) -> List[Dict[str, Any]]:
        """
        Analyze co-occurrence of event types within time windows.

        Finds patterns of events that tend to occur together, e.g.,
        earnings announcements followed by insider trading.

        Args:
            session: SQLModel session
            lookback_days: Number of days to analyze (default 90)

        Returns:
            List of correlation dictionaries with:
                - event_type_1, event_type_2, co_occurrence_count, correlation_strength
        """
        repository = EventRepository(session)
        correlations = []

        try:
            # Get all events in lookback window
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            all_events = repository.get_events_for_timeline(
                start_detected_at=cutoff_date,
                end_detected_at=datetime.now(timezone.utc),
            )

            if len(all_events) < 2:
                return correlations

            # Build ticker -> events map
            ticker_events = {}
            for event in all_events:
                if event.ticker not in ticker_events:
                    ticker_events[event.ticker] = []
                ticker_events[event.ticker].append(event)

            # Analyze co-occurrences for each ticker
            correlation_map = {}  # (event_type_1, event_type_2, ticker) -> count

            for ticker, events in ticker_events.items():
                # Sort events by date
                events_by_date = sorted(events, key=lambda e: e.event_date)

                # Look for event pairs within time windows (default 7 days)
                for i, event1 in enumerate(events_by_date):
                    for event2 in events_by_date[i + 1:]:
                        days_apart = (event2.event_date - event1.event_date).days

                        # Only consider events within 14 days
                        if days_apart > 14:
                            continue

                        # Create ordered pair (alphabetical)
                        pair = tuple(sorted([event1.event_type, event2.event_type]))

                        if pair not in correlation_map:
                            correlation_map[pair] = {"count": 0, "total_pairs": 0}

                        if pair[0] == event1.event_type and pair[1] == event2.event_type:
                            # Direct occurrence
                            correlation_map[pair]["count"] += 1

            # Save significant correlations
            end_date = date.today()
            for (event_type_1, event_type_2), counts in correlation_map.items():
                if counts["count"] < 2:  # Only save if at least 2 co-occurrences
                    continue

                # Calculate correlation strength (0-1 scale)
                # Simple heuristic: count / max_possible_pairs
                correlation_strength = Decimal(min(counts["count"] / 10.0, 1.0))

                correlation = repository.save_event_correlation_analysis(
                    event_type_1=event_type_1,
                    event_type_2=event_type_2,
                    co_occurrence_count=counts["count"],
                    time_window_days=lookback_days,
                    correlation_strength=correlation_strength,
                    analyzed_period_end=end_date,
                )

                correlations.append({
                    "event_type_1": event_type_1,
                    "event_type_2": event_type_2,
                    "co_occurrence_count": counts["count"],
                    "correlation_strength": float(correlation_strength),
                })

                logger.info(
                    f"Correlation found: {event_type_1} + {event_type_2} "
                    f"(count={counts['count']}, strength={float(correlation_strength):.3f})"
                )

        except Exception as e:
            logger.error(f"Error analyzing event correlations: {e}", exc_info=True)

        return correlations

    def _get_factor_assignments(
        self,
        event_type: str,
        severity_score: int,
    ) -> List[Tuple[int, Decimal]]:
        """
        Determine which factors an event should be assigned to.

        Args:
            event_type: Classified event type
            severity_score: Severity score 1-5

        Returns:
            List of (factor_id, signal_value) tuples
        """
        assignments = []

        try:
            # Get base signal value from event type sentiment
            base_sentiment = self.EVENT_TYPE_SENTIMENT.get(event_type, Decimal("0.0"))

            # Get strength component from severity
            severity_strength = self.SEVERITY_TO_SIGNAL_STRENGTH.get(severity_score, Decimal("0.5"))

            # Combine: average of sentiment and severity strength
            combined_signal = (base_sentiment + severity_strength) / 2

            # Clamp to [-1, +1]
            signal_value = max(Decimal("-1"), min(Decimal("1"), combined_signal))

            # Assign to factors based on event type
            if "insider_trade" in event_type:
                assignments.append((self.FACTOR_IDS["insider_sentiment"], signal_value))

            if "earnings" in event_type:
                assignments.append((self.FACTOR_IDS["earnings_surprise"], signal_value))

            if "beneficial_ownership_13d" in event_type:
                assignments.append((self.FACTOR_IDS["activist_involvement"], signal_value))

            if "dividend" in event_type:
                assignments.append((self.FACTOR_IDS["dividend_yield"], signal_value))

            # All events map to corporate_action factor
            assignments.append((self.FACTOR_IDS["corporate_action"], signal_value))

        except Exception as e:
            logger.error(f"Error computing factor assignments for {event_type}: {e}")
            # Fallback: assign to corporate_action only
            assignments = [(self.FACTOR_IDS["corporate_action"], Decimal("0.5"))]

        return assignments

    def _get_signal_expiration(self, event_type: str) -> int:
        """
        Determine how long a factor signal should remain valid.

        Args:
            event_type: Classified event type

        Returns:
            Expiration time in days
        """
        if "insider_trade" in event_type:
            return self.SIGNAL_EXPIRATION_DAYS["insider_trade"]
        elif "earnings" in event_type:
            return self.SIGNAL_EXPIRATION_DAYS["earnings_announcement"]
        elif "dividend" in event_type:
            return self.SIGNAL_EXPIRATION_DAYS["dividend_ex_date"]
        elif "beneficial_ownership_13d" in event_type:
            return self.SIGNAL_EXPIRATION_DAYS["beneficial_ownership_13d"]
        else:
            return self.SIGNAL_EXPIRATION_DAYS["sec_filing"]
