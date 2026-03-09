"""
Background Polling Service for Phase 2 CEP.

Scheduled polling coordinator that executes full event scanning cycles:
- Get watchlist tickers
- Scan all event sources (SEC EDGAR, yfinance)
- Process events (classify, score, save)
- Generate factor signals
- Analyze correlations
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from threading import Lock

from sqlmodel import Session

from backend.services.event_producer import EventProducerService
from backend.services.event_processor import EventProcessingEngine
from backend.services.event_consumer import EventConsumerService
from backend.repositories.event_repo import EventRepository

logger = logging.getLogger(__name__)

# Global polling state
_polling_lock = Lock()
_last_poll_time: Optional[datetime] = None
_last_poll_status: Dict[str, Any] = {
    "status": "never_run",
    "last_run": None,
    "next_run": None,
    "events_found": 0,
    "errors": [],
}


class BackgroundPollingService:
    """Scheduled polling coordinator for the event scanning CEP pipeline."""

    def __init__(self):
        """Initialize BackgroundPollingService."""
        self.producer = EventProducerService()
        self.processor = EventProcessingEngine()
        self.consumer = EventConsumerService()

    def run_polling_cycle(self, session: Session, tickers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Execute full scan cycle: scan → process → signal generation → correlations.

        This is the main entry point for background polling. It coordinates all three
        CEP layers to produce a complete event processing result.

        Args:
            session: SQLModel session
            tickers: Optional list of specific tickers to scan. If None, uses all watchlist tickers.

        Returns:
            Polling result dictionary with:
                - status, events_found, errors, start_time, end_time
        """
        global _last_poll_time, _last_poll_status

        result = {
            "status": "in_progress",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "events_found": 0,
            "signals_generated": 0,
            "correlations_found": 0,
            "errors": [],
            "end_time": None,
        }

        with _polling_lock:
            try:
                logger.info(f"Starting polling cycle for {len(tickers) if tickers else '?'} tickers")

                # Get tickers if not provided
                if not tickers:
                    tickers = self._get_watchlist_tickers(session)
                    if not tickers:
                        logger.warning("No tickers in watchlist")
                        result["status"] = "completed_no_tickers"
                        return result

                logger.info(f"Scanning {len(tickers)} tickers")

                # Layer 1: Scan all event sources
                try:
                    logger.info("Layer 1: Running event producer (scanners)")
                    raw_events = self.producer.scan_all(tickers)
                    result["raw_events_found"] = len(raw_events)
                    logger.info(f"Layer 1: Found {len(raw_events)} raw events")
                except Exception as e:
                    error_msg = f"Error in event producer: {e}"
                    logger.error(error_msg, exc_info=True)
                    result["errors"].append(error_msg)
                    raw_events = []

                if not raw_events:
                    result["status"] = "completed_no_events"
                    result["end_time"] = datetime.now(timezone.utc).isoformat()
                    _last_poll_time = datetime.now(timezone.utc)
                    _last_poll_status = result
                    return result

                # Layer 2: Process events (classify, score, save)
                try:
                    logger.info("Layer 2: Running event processor (classify, score, save)")
                    created_events, alpha_decays = self.processor.process_events(session, raw_events)
                    result["events_found"] = len(created_events)
                    result["alpha_decay_windows"] = len(alpha_decays)
                    logger.info(
                        f"Layer 2: Created {len(created_events)} events "
                        f"with {len(alpha_decays)} alpha decay windows"
                    )
                except Exception as e:
                    error_msg = f"Error in event processor: {e}"
                    logger.error(error_msg, exc_info=True)
                    result["errors"].append(error_msg)
                    created_events = []

                if not created_events:
                    result["status"] = "completed_no_valid_events"
                    result["end_time"] = datetime.now(timezone.utc).isoformat()
                    _last_poll_time = datetime.now(timezone.utc)
                    _last_poll_status = result
                    return result

                # Layer 3: Generate factor signals and screener badges
                try:
                    logger.info("Layer 3: Running event consumer (signals, badges)")
                    signals_generated = 0
                    for event in created_events:
                        signals = self.consumer.generate_factor_signals(session, event.event_id, event)
                        signals_generated += len(signals)

                    result["signals_generated"] = signals_generated
                    logger.info(f"Layer 3: Generated {signals_generated} factor signals")

                    # Update screener badges for all affected tickers
                    tickers_with_events = set(e.ticker for e in created_events)
                    for ticker in tickers_with_events:
                        try:
                            badge = self.consumer.update_screener_badges(session, ticker)
                            logger.debug(f"Updated screener badge for {ticker}")
                        except Exception as e:
                            logger.error(f"Error updating badge for {ticker}: {e}")

                except Exception as e:
                    error_msg = f"Error in event consumer: {e}"
                    logger.error(error_msg, exc_info=True)
                    result["errors"].append(error_msg)

                # Analyze event correlations
                try:
                    logger.info("Analyzing event correlations")
                    correlations = self.consumer.get_event_correlations(session, lookback_days=90)
                    result["correlations_found"] = len(correlations)
                    logger.info(f"Found {len(correlations)} event type correlations")
                except Exception as e:
                    error_msg = f"Error analyzing correlations: {e}"
                    logger.error(error_msg, exc_info=True)
                    result["errors"].append(error_msg)

                result["status"] = "completed_success"

            except Exception as e:
                error_msg = f"Unexpected error in polling cycle: {e}"
                logger.error(error_msg, exc_info=True)
                result["errors"].append(error_msg)
                result["status"] = "completed_error"

            finally:
                result["end_time"] = datetime.now(timezone.utc).isoformat()
                _last_poll_time = datetime.now(timezone.utc)
                _last_poll_status = result
                logger.info(f"Polling cycle completed: {result['status']}")

        return result

    def get_polling_status(self) -> Dict[str, Any]:
        """
        Get current polling service status.

        Returns status from last poll and estimates for next scheduled poll.

        Returns:
            Dictionary with:
                - last_run, last_run_status, events_found, errors
                - next_run_estimate, polling_interval_hours
        """
        global _last_poll_time, _last_poll_status

        status = dict(_last_poll_status)  # Copy latest status
        status["last_run"] = _last_poll_time.isoformat() if _last_poll_time else None

        # Estimate next run (would be set by scheduler, but for now just add interval)
        if _last_poll_time:
            next_run = _last_poll_time + timedelta(hours=1)  # Default 1-hour interval
            status["next_run_estimate"] = next_run.isoformat()
        else:
            status["next_run_estimate"] = datetime.now(timezone.utc).isoformat()

        status["polling_interval_hours"] = 1
        return status

    def _get_watchlist_tickers(self, session: Session) -> List[str]:
        """
        Get list of tickers from user's watchlist.

        For MVP, returns hardcoded list. In production, would query
        watchlist from database.

        Args:
            session: SQLModel session

        Returns:
            List of ticker symbols
        """
        # TODO: Query from watchlist table in database
        # For now, return hardcoded list for testing
        return [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
            "META", "NVDA", "JPM", "V", "WMT",
        ]
