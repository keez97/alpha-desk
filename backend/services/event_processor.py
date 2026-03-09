"""
Event Processor Service for Phase 2 CEP - Layer 2 of Complex Event Processing.

Classifies and scores raw events:
- Match against classification rules (8-K items, Form 4, calendar events, etc.)
- Score severity 1-5 based on event type and metadata
- Calculate alpha decay windows using PiT price history
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
import re

from sqlmodel import Session
from backend.repositories.event_repo import EventRepository
from backend.repositories.pit_queries import get_prices_pit
from backend.models.events import Event

logger = logging.getLogger(__name__)


class EventProcessingEngine:
    """Layer 2 of CEP: Event classification and severity scoring."""

    # Event type classification mappings
    EVENT_TYPE_MAP = {
        "8-K": "sec_filing_8k",
        "10-K": "sec_filing_10k",
        "10-Q": "sec_filing_10q",
        "4": "insider_trade",
        "SC 13D": "beneficial_ownership_acquisition",
        "SC 13G": "beneficial_ownership_passive",
        "earnings": "earnings",
        "dividend_ex_date": "dividend_change",
    }

    # Severity scoring rules
    SEVERITY_RULES = {
        # SEC 8-K filings with specific items
        "8k_item_1_01": 5,  # Bankruptcy
        "8k_item_1_02": 4,  # Material agreement
        "8k_item_2_01": 5,  # Bankruptcy/costs
        "8k_item_2_02": 5,  # Bankruptcy/cost estimated
        "8k_item_2_03": 4,  # Bankruptcy/creation
        "8k_item_2_04": 4,  # Bankruptcy/arrangement
        "8k_item_2_05": 4,  # Bankruptcy/effect
        "8k_item_2_06": 3,  # Bankruptcy/backlog
        "8k_item_default": 2,  # Other 8-K items
        # 10-K and 10-Q filings
        "10k_filing": 2,
        "10q_filing": 2,
        # Form 4 insider trades (varies by transaction size)
        "insider_trade_buy_large": 4,  # Large insider buy
        "insider_trade_buy_small": 2,  # Small insider buy
        "insider_trade_sell_large": 3,  # Large insider sell
        "insider_trade_sell_small": 1,  # Small insider sell
        "insider_trade_default": 2,
        # Beneficial ownership (13D/13G)
        "beneficial_ownership_13d": 4,  # 13D (activist)
        "beneficial_ownership_13g": 2,  # 13G (passive)
        # Calendar events
        "earnings_announcement": 3,
        "dividend_ex_date": 1,
        "dividend_change_significant": 4,
    }

    # Alpha decay window definitions (in days)
    ALPHA_DECAY_WINDOWS = [
        ("1d", 1),
        ("5d", 5),
        ("21d", 21),
        ("63d", 63),
    ]

    # Benchmark ticker (default SPY)
    DEFAULT_BENCHMARK = "SPY"

    def __init__(self):
        """Initialize EventProcessingEngine."""
        pass

    def classify_event(self, raw_event: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Classify raw event into standardized event type.

        Uses filing forms, item numbers, and metadata to determine event classification.

        Args:
            raw_event: Raw event dictionary from producer with:
                - filing_type, filing_title, event_type, metadata, etc.

        Returns:
            Tuple of (event_type, classification_metadata)
        """
        filing_type = raw_event.get("filing_type", "").upper()
        event_type = raw_event.get("event_type", "").lower()
        headline = raw_event.get("filing_title") or raw_event.get("headline", "")
        metadata = raw_event.get("metadata", {})

        # Classify by raw event source
        if filing_type == "8-K":
            # Parse 8-K item numbers from headline or metadata
            item_number = self._extract_8k_item(headline, metadata)
            classified_type = f"sec_filing_8k_item_{item_number}"
            return classified_type, {"item_number": item_number, "source": "SEC_EDGAR"}

        elif filing_type == "10-K":
            return "sec_filing_10k", {"source": "SEC_EDGAR"}

        elif filing_type == "10-Q":
            return "sec_filing_10q", {"source": "SEC_EDGAR"}

        elif filing_type == "4":
            # Form 4: Insider trade
            # Classify by transaction type (buy/sell) and size
            transaction_type = self._extract_form4_transaction_type(headline, metadata)
            transaction_size = self._extract_form4_transaction_size(metadata)
            classified_type = f"insider_trade_{transaction_type}_{transaction_size}"
            return classified_type, {
                "transaction_type": transaction_type,
                "transaction_size": transaction_size,
                "source": "SEC_EDGAR",
            }

        elif filing_type in ["SC 13D", "SC 13G"]:
            classified_type = "beneficial_ownership_13d" if filing_type == "SC 13D" else "beneficial_ownership_13g"
            return classified_type, {"ownership_level": metadata.get("ownership_level"), "source": "SEC_EDGAR"}

        elif event_type == "earnings":
            return "earnings_announcement", {"source": "YFINANCE"}

        elif event_type == "dividend_ex_date":
            # Check if dividend yield changed significantly
            dividend_yield = metadata.get("dividend_yield", 0)
            if dividend_yield and float(dividend_yield) > 0.03:  # >3% yield
                return "dividend_change_significant", {"dividend_yield": dividend_yield, "source": "YFINANCE"}
            else:
                return "dividend_ex_date", {"dividend_yield": dividend_yield, "source": "YFINANCE"}

        else:
            return "other_event", {"source": raw_event.get("source", "UNKNOWN")}

    def score_severity(self, event_type: str, metadata: Dict[str, Any]) -> int:
        """
        Score event severity 1-5 based on type and metadata.

        Severity 5: Bankruptcy, M&A, significant insider activity
        Severity 4: Large insider trades, activist ownership
        Severity 3: Earnings announcements, regular insider trades
        Severity 2: Regular 10-K/10-Q filings, small insider trades
        Severity 1: Dividend dates, passive beneficial ownership

        Args:
            event_type: Classified event type from classify_event
            metadata: Metadata from classification

        Returns:
            Severity score 1-5
        """
        # Direct severity mapping
        if event_type in self.SEVERITY_RULES:
            return self.SEVERITY_RULES[event_type]

        # Pattern-based severity scoring
        if "8k_item" in event_type:
            item_number = metadata.get("item_number", "default")
            rule_key = f"8k_item_{item_number}"
            if rule_key in self.SEVERITY_RULES:
                return self.SEVERITY_RULES[rule_key]
            return self.SEVERITY_RULES.get("8k_item_default", 2)

        if "insider_trade" in event_type:
            transaction_type = metadata.get("transaction_type", "unknown")
            transaction_size = metadata.get("transaction_size", "small")

            if transaction_type == "buy":
                return 4 if transaction_size == "large" else 2
            elif transaction_type == "sell":
                return 3 if transaction_size == "large" else 1
            else:
                return self.SEVERITY_RULES.get("insider_trade_default", 2)

        # Default severity
        return 2

    def calculate_alpha_decay(
        self,
        session: Session,
        event_id: int,
        event: Event,
        benchmark_ticker: str = DEFAULT_BENCHMARK,
    ) -> List[Dict[str, Any]]:
        """
        Calculate abnormal returns in alpha decay windows post-event.

        For each window (1d, 5d, 21d, 63d), calculate:
        abnormal_return = (security_return_window - benchmark_return_window)

        Uses PiT (point-in-time) price queries to ensure data was available at event date.

        Args:
            session: SQLModel session
            event_id: Event ID to calculate decay for
            event: Event object with event_date
            benchmark_ticker: Benchmark ticker (default SPY)

        Returns:
            List of alpha decay window dictionaries
        """
        alpha_decays = []
        repository = EventRepository(session)

        try:
            # Get security and benchmark prices as of event date (PiT safe)
            security_prices = get_prices_pit(
                session,
                event.ticker,
                event.event_date,
                start_date=event.event_date - timedelta(days=10),  # Get 10 days before for context
            )

            benchmark_prices = get_prices_pit(
                session,
                benchmark_ticker,
                event.event_date,
                start_date=event.event_date - timedelta(days=10),
            )

            if not security_prices or not benchmark_prices:
                logger.warning(f"Insufficient price data for event {event_id} ({event.ticker})")
                return alpha_decays

            # Build price maps for quick lookup
            security_price_map = {p.date: float(p.close) for p in security_prices}
            benchmark_price_map = {p.date: float(p.close) for p in benchmark_prices}

            # Get event date price as baseline
            if event.event_date not in security_price_map or event.event_date not in benchmark_price_map:
                logger.warning(f"No price on event date {event.event_date} for event {event_id}")
                return alpha_decays

            event_date_security_price = security_price_map[event.event_date]
            event_date_benchmark_price = benchmark_price_map[event.event_date]

            # Calculate decay for each window
            for window_name, window_days in self.ALPHA_DECAY_WINDOWS:
                window_end_date = event.event_date + timedelta(days=window_days)

                # Find closest price on or before window end date
                security_window_price = None
                benchmark_window_price = None

                for p_date, p_price in sorted(security_price_map.items()):
                    if p_date > window_end_date:
                        break
                    security_window_price = p_price

                for p_date, p_price in sorted(benchmark_price_map.items()):
                    if p_date > window_end_date:
                        break
                    benchmark_window_price = p_price

                if not security_window_price or not benchmark_window_price:
                    logger.debug(f"Incomplete price data for window {window_name} (event {event_id})")
                    continue

                # Calculate returns (using Decimal for precision)
                security_return = Decimal(
                    (security_window_price - event_date_security_price) / event_date_security_price
                )
                benchmark_return = Decimal(
                    (benchmark_window_price - event_date_benchmark_price) / event_date_benchmark_price
                )
                abnormal_return = security_return - benchmark_return

                # Save to repository
                decay_window = repository.save_alpha_decay_window(
                    event_id=event_id,
                    window_type=window_name,
                    abnormal_return=abnormal_return,
                    benchmark_return=benchmark_return,
                    measured_at=datetime.now(timezone.utc),
                    confidence=Decimal("1.0"),  # High confidence from historical data
                    sample_size=1,
                )

                alpha_decays.append({
                    "window_type": window_name,
                    "abnormal_return": float(abnormal_return),
                    "benchmark_return": float(benchmark_return),
                    "window_id": decay_window.window_id,
                })

        except Exception as e:
            logger.error(f"Error calculating alpha decay for event {event_id}: {e}")

        return alpha_decays

    def process_events(
        self,
        session: Session,
        raw_events: List[Dict[str, Any]],
    ) -> Tuple[List[Event], List[Dict[str, Any]]]:
        """
        Full CEP Layer 2 pipeline: classify → score → save → calculate alpha decay.

        Args:
            session: SQLModel session
            raw_events: List of raw events from producer

        Returns:
            Tuple of (created_events, alpha_decay_results)
        """
        created_events = []
        alpha_decay_results = []
        repository = EventRepository(session)

        logger.info(f"Processing {len(raw_events)} raw events")

        for raw_event in raw_events:
            try:
                # Extract common fields
                ticker = raw_event.get("ticker", "").upper()
                event_date_str = raw_event.get("filing_date") or raw_event.get("event_date")

                if not ticker or not event_date_str:
                    logger.warning(f"Skipping event with missing ticker or date: {raw_event}")
                    continue

                # Parse event date
                try:
                    event_date = datetime.fromisoformat(event_date_str).date()
                except (ValueError, TypeError):
                    logger.warning(f"Invalid event date for {ticker}: {event_date_str}")
                    continue

                # Classify event
                classified_type, classification_metadata = self.classify_event(raw_event)

                # Score severity
                severity_score = self.score_severity(classified_type, classification_metadata)

                # Build event headline and description
                headline = raw_event.get("filing_title") or raw_event.get("headline", f"{ticker} Event")
                description = raw_event.get("description")

                # Create event in database
                event = repository.create_event(
                    ticker=ticker,
                    event_type=classified_type,
                    severity_score=severity_score,
                    detected_at=datetime.now(timezone.utc),
                    event_date=event_date,
                    source=raw_event.get("source", "UNKNOWN"),
                    headline=headline,
                    description=description,
                    metadata={
                        **classification_metadata,
                        **raw_event.get("metadata", {}),
                        "raw_filing_type": raw_event.get("filing_type"),
                    }
                )

                created_events.append(event)

                # Save source mapping
                source_url = raw_event.get("source_url")
                source_id = raw_event.get("accession_number") or raw_event.get("source_id", "")

                if source_id:
                    repository.save_event_source_mapping(
                        event_id=event.event_id,
                        source_type=raw_event.get("source", "UNKNOWN"),
                        source_id=source_id,
                        source_url=source_url,
                        extracted_data=raw_event.get("metadata"),
                    )

                # Calculate alpha decay windows
                decay_results = self.calculate_alpha_decay(session, event.event_id, event)
                alpha_decay_results.extend(decay_results)

                logger.info(
                    f"Created event {event.event_id}: {ticker} {classified_type} severity={severity_score} "
                    f"on {event_date}"
                )

            except Exception as e:
                logger.error(f"Error processing raw event {raw_event}: {e}", exc_info=True)
                continue

        logger.info(f"Successfully processed {len(created_events)} events with {len(alpha_decay_results)} decay windows")
        return created_events, alpha_decay_results

    def _extract_8k_item(self, headline: str, metadata: Dict[str, Any]) -> str:
        """
        Extract 8-K item number from headline or metadata.

        Args:
            headline: Filing headline/title
            metadata: Filing metadata

        Returns:
            Item number string (e.g., "1.01", "2.01", "default")
        """
        # Check metadata first
        if "item_number" in metadata:
            return str(metadata["item_number"])

        # Pattern match in headline for item numbers
        # Examples: "Item 1.01", "Item 2.01", "Item 5.02"
        pattern = r"Item\s+(\d+\.\d+)"
        match = re.search(pattern, headline, re.IGNORECASE)
        if match:
            return match.group(1)

        return "default"

    def _extract_form4_transaction_type(self, headline: str, metadata: Dict[str, Any]) -> str:
        """
        Extract Form 4 transaction type (buy/sell).

        Args:
            headline: Filing headline
            metadata: Filing metadata

        Returns:
            "buy", "sell", or "unknown"
        """
        # Check metadata
        if "transaction_type" in metadata:
            return str(metadata["transaction_type"]).lower()

        # Pattern match in headline
        headline_lower = headline.lower()
        if "buy" in headline_lower or "purchase" in headline_lower:
            return "buy"
        elif "sell" in headline_lower or "sale" in headline_lower:
            return "sell"

        return "unknown"

    def _extract_form4_transaction_size(self, metadata: Dict[str, Any]) -> str:
        """
        Extract Form 4 transaction size classification (large/small).

        Args:
            metadata: Filing metadata with transaction details

        Returns:
            "large" or "small"
        """
        # Check for transaction amount in metadata
        amount = metadata.get("transaction_amount", 0)
        shares = metadata.get("shares_traded", 0)

        # Heuristic: >$1M or >100k shares = large
        if isinstance(amount, (int, float)):
            if amount > 1_000_000:
                return "large"
        if isinstance(shares, (int, float)):
            if shares > 100_000:
                return "large"

        return "small"
