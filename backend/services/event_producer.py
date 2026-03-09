"""
Event Producer Service for Phase 2 CEP - Layer 1 of Complex Event Processing.

Detects raw events from external sources:
- SEC EDGAR filings (8-K, 10-K, 10-Q, Form 4, SC 13D/G)
- yfinance calendar events (earnings dates, ex-dividend dates)

Rate limiting: max 10 requests/sec from SEC EDGAR.
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
import time
from functools import wraps

logger = logging.getLogger(__name__)

# Rate limiting: track last request times to ensure max 10 req/sec
_request_times = []
_rate_limit_per_sec = 10


def _rate_limit_sec():
    """Rate limiter for SEC EDGAR requests (max 10/sec)."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            global _request_times
            now = time.time()
            # Remove timestamps older than 1 second
            _request_times = [t for t in _request_times if now - t < 1.0]

            if len(_request_times) >= _rate_limit_per_sec:
                # Wait until oldest request is outside 1-second window
                sleep_time = 1.0 - (now - _request_times[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)

            _request_times.append(time.time())
            return func(*args, **kwargs)
        return wrapper
    return decorator


class EventProducerService:
    """Layer 1 of CEP: Raw event detection from external sources."""

    # SEC EDGAR filing type codes
    FILING_TYPES = {
        "8-K": "current_report",
        "10-K": "annual_report",
        "10-Q": "quarterly_report",
        "4": "insider_trade",
        "SC 13D": "beneficial_ownership_acquisition",
        "SC 13G": "beneficial_ownership_passive",
    }

    # User-Agent for SEC EDGAR (required by SEC)
    SEC_USER_AGENT = "AlphaDesk/1.0 atarikarim@hotmail.com"

    # 8-K Item numbers for event classification
    _8K_ITEMS = {
        "1.01": "bankruptcy",
        "1.02": "material_agreement",
        "1.03": "material_agreement",
        "2.01": "bankruptcy",
        "2.02": "bankruptcy",
        "2.03": "bankruptcy",
        "2.04": "bankruptcy",
        "2.05": "bankruptcy",
        "2.06": "bankruptcy",
        "3.01": "other",
        "3.02": "other",
        "3.03": "other",
        "4.01": "other",
        "4.02": "other",
        "5.01": "other",
        "5.02": "other",
        "5.03": "other",
        "5.04": "other",
        "5.05": "other",
        "5.06": "other",
        "5.07": "other",
        "5.08": "other",
        "6.01": "other",
        "7.01": "other",
        "8.01": "other",
        "9.01": "other",
    }

    def __init__(self):
        """Initialize EventProducerService."""
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.SEC_USER_AGENT})

    @_rate_limit_sec()
    def _fetch_edgar_url(self, url: str, params: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Fetch content from SEC EDGAR with rate limiting.

        Args:
            url: URL to fetch
            params: Optional query parameters

        Returns:
            Response content or None if failed
        """
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching SEC EDGAR URL {url}: {e}")
            return None

    def scan_sec_edgar(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """
        Parse SEC EDGAR RSS for recent filings.

        Uses the SEC full-text search API to find filings for each ticker.
        Returns raw events for 8-K, 10-K, 10-Q, Form 4, SC 13D/G filings.

        Args:
            tickers: List of stock tickers to scan

        Returns:
            List of raw event dictionaries with:
                - ticker, filing_type, accession_number, filing_date,
                  filing_title, company_name, source_url, metadata
        """
        raw_events = []

        for ticker in tickers:
            try:
                # SEC full-text search API for recent filings
                # Format: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type={type}&dateb=&owner=&count=100
                base_url = "https://www.sec.gov/cgi-bin/browse-edgar"

                # Get CIK first (we'll use ticker as fallback for CIK lookup)
                # In a real implementation, maintain a ticker->CIK mapping
                cik = self._ticker_to_cik(ticker)
                if not cik:
                    logger.warning(f"Could not find CIK for ticker {ticker}")
                    continue

                for filing_type in ["8-K", "10-K", "10-Q", "4", "SC 13D", "SC 13G"]:
                    params = {
                        "action": "getcompany",
                        "CIK": cik,
                        "type": filing_type,
                        "dateb": "",
                        "owner": "include" if filing_type == "4" else "exclude",
                        "count": "10",  # Get last 10 filings
                    }

                    html_content = self._fetch_edgar_url(base_url, params)
                    if not html_content:
                        continue

                    # Parse HTML table for filings
                    events = self._parse_edgar_html(html_content, ticker, filing_type)
                    raw_events.extend(events)

            except Exception as e:
                logger.error(f"Error scanning SEC EDGAR for {ticker}: {e}")
                continue

        return raw_events

    def _ticker_to_cik(self, ticker: str) -> Optional[str]:
        """
        Convert ticker to SEC CIK.

        For MVP, returns ticker as-is. In production, maintain a ticker->CIK mapping.

        Args:
            ticker: Stock ticker symbol

        Returns:
            CIK string or None
        """
        # Simple mapping for common tickers
        # In production, query SEC Edgar index or maintain a database
        ticker_to_cik = {
            "AAPL": "0000320193",
            "MSFT": "0000789019",
            "GOOGL": "0001652044",
            "AMZN": "0001018724",
            "TSLA": "0001318605",
            "META": "0001326801",
            "NVDA": "0001045810",
            "JPM": "0000064397",
            "V": "0001403161",
            "WMT": "0000104169",
        }
        return ticker_to_cik.get(ticker.upper(), ticker.upper())

    def _parse_edgar_html(self, html: str, ticker: str, filing_type: str) -> List[Dict[str, Any]]:
        """
        Parse SEC EDGAR HTML table for filings.

        Extracts filing dates, accession numbers, and company names from the
        SEC browse-edgar HTML response.

        Args:
            html: HTML content from SEC EDGAR
            ticker: Ticker being scanned
            filing_type: Type of filing (8-K, 10-K, etc.)

        Returns:
            List of raw event dictionaries
        """
        events = []

        try:
            # Parse HTML to extract filing information
            # Look for table rows with filing data
            import re

            # Pattern: extracts filing date and accession number from HTML
            # Example: <td>2024-03-10</td> ... <a href="/cgi-bin/viewer?action=view&cik=...&accession_number=0001234567-24-000123">

            filing_pattern = r'<td[^>]*>(\d{4}-\d{2}-\d{2})</td>.*?<a[^>]*href="[^"]*accession_number=([0-9\-]+)"[^>]*>([^<]+)</a>'

            matches = re.finditer(filing_pattern, html, re.DOTALL | re.IGNORECASE)

            for match in matches:
                filing_date_str = match.group(1)
                accession_number = match.group(2)
                filing_title = match.group(3).strip()

                try:
                    filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d").date()
                except ValueError:
                    continue

                # Build source URL
                source_url = f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={self._ticker_to_cik(ticker)}&accession_number={accession_number}"

                raw_event = {
                    "ticker": ticker,
                    "filing_type": filing_type,
                    "filing_date": filing_date.isoformat(),
                    "accession_number": accession_number,
                    "filing_title": filing_title,
                    "source_url": source_url,
                    "source": "SEC_EDGAR",
                    "metadata": {
                        "cik": self._ticker_to_cik(ticker),
                        "filing_type_code": filing_type,
                    }
                }
                events.append(raw_event)

        except Exception as e:
            logger.error(f"Error parsing EDGAR HTML for {ticker} ({filing_type}): {e}")

        return events

    def scan_yfinance_calendar(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """
        Get earnings dates and ex-dividend dates from yfinance.

        Uses the yfinance library to fetch corporate calendar events
        (earnings announcements, dividend ex-dates).

        Args:
            tickers: List of stock tickers to scan

        Returns:
            List of raw event dictionaries with:
                - ticker, event_type, event_date, source_url, metadata
        """
        raw_events = []

        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance not available for calendar scanning")
            return raw_events

        for ticker in tickers:
            try:
                ticker_obj = yf.Ticker(ticker)
                info = ticker_obj.info

                # Check for earnings dates
                if "earningsDate" in info and info["earningsDate"]:
                    earnings_dates = info["earningsDate"]
                    if isinstance(earnings_dates, (list, tuple)) and len(earnings_dates) > 0:
                        # Earnings date is typically a list [start_date, end_date]
                        earnings_date = earnings_dates[0] if isinstance(earnings_dates[0], datetime) else earnings_dates[0]
                        if isinstance(earnings_date, datetime):
                            raw_event = {
                                "ticker": ticker,
                                "event_type": "earnings",
                                "event_date": earnings_date.date().isoformat(),
                                "headline": f"{ticker} earnings announcement",
                                "source": "YFINANCE",
                                "source_url": f"https://finance.yahoo.com/quote/{ticker}",
                                "metadata": {
                                    "event_type_detail": "earnings_announcement",
                                    "earnings_date": earnings_date.isoformat(),
                                }
                            }
                            raw_events.append(raw_event)

                # Check for next dividend date (ex-dividend date)
                if "exDividendDate" in info and info["exDividendDate"]:
                    ex_div_date = info["exDividendDate"]
                    if isinstance(ex_div_date, datetime):
                        dividend_yield = info.get("dividendYield", 0)
                        raw_event = {
                            "ticker": ticker,
                            "event_type": "dividend_ex_date",
                            "event_date": ex_div_date.date().isoformat(),
                            "headline": f"{ticker} ex-dividend date",
                            "source": "YFINANCE",
                            "source_url": f"https://finance.yahoo.com/quote/{ticker}",
                            "metadata": {
                                "event_type_detail": "ex_dividend_date",
                                "dividend_yield": float(dividend_yield) if dividend_yield else None,
                                "ex_dividend_date": ex_div_date.isoformat(),
                            }
                        }
                        raw_events.append(raw_event)

            except Exception as e:
                logger.warning(f"Error scanning yfinance calendar for {ticker}: {e}")
                continue

        return raw_events

    def scan_all(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """
        Run both SEC EDGAR and yfinance scanners.

        Combines results from both sources into a single list of raw events.

        Args:
            tickers: List of stock tickers to scan

        Returns:
            Combined list of raw events from all sources
        """
        all_events = []

        logger.info(f"Starting event scan for {len(tickers)} tickers")

        # Scan SEC EDGAR
        logger.info("Scanning SEC EDGAR filings...")
        edgar_events = self.scan_sec_edgar(tickers)
        all_events.extend(edgar_events)
        logger.info(f"Found {len(edgar_events)} SEC EDGAR events")

        # Scan yfinance calendar
        logger.info("Scanning yfinance calendar events...")
        calendar_events = self.scan_yfinance_calendar(tickers)
        all_events.extend(calendar_events)
        logger.info(f"Found {len(calendar_events)} yfinance calendar events")

        logger.info(f"Total events found: {len(all_events)}")
        return all_events
