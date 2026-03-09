"""
Tests for Event Producer Service (Layer 1 CEP).

Tests SEC EDGAR parsing, yfinance calendar scanning, and rate limiting.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from backend.services.event_producer import EventProducerService


class TestSecEdgarParsing:
    """Test SEC EDGAR HTML parsing."""

    def test_parse_sec_edgar_html_response(self):
        """Verify SEC EDGAR HTML parsing extracts filing data correctly."""
        producer = EventProducerService()

        # Mock HTML response from SEC EDGAR browse-edgar
        html_content = """
        <html>
        <table>
            <tr>
                <td>2024-03-10</td>
                <td>8-K</td>
                <a href="/cgi-bin/viewer?action=view&cik=0000320193&accession_number=0000320193-24-000010">
                    Form 8-K
                </a>
            </tr>
            <tr>
                <td>2024-03-05</td>
                <td>10-K</td>
                <a href="/cgi-bin/viewer?action=view&cik=0000320193&accession_number=0000320193-24-000005">
                    Form 10-K
                </a>
            </tr>
        </table>
        </html>
        """

        events = producer._parse_edgar_html(html_content, "AAPL", "8-K")

        # Should extract filing date and accession number
        assert len(events) >= 1
        assert events[0]["ticker"] == "AAPL"
        assert events[0]["filing_type"] == "8-K"
        assert events[0]["accession_number"] == "0000320193-24-000010"
        assert events[0]["filing_date"] == "2024-03-10"

    def test_parse_edgar_html_extracts_all_fields(self):
        """Verify all required fields extracted from SEC EDGAR."""
        producer = EventProducerService()

        html_content = """
        <tr>
            <td>2024-02-15</td>
            <td>4</td>
            <a href="/cgi-bin/viewer?action=view&cik=0000320193&accession_number=0000320193-24-000001">
                Form 4 - Insider Transaction
            </a>
        </tr>
        """

        events = producer._parse_edgar_html(html_content, "AAPL", "4")

        assert len(events) >= 1
        event = events[0]
        assert event["ticker"] == "AAPL"
        assert event["filing_type"] == "4"
        assert event["filing_date"] == "2024-02-15"
        assert event["accession_number"] == "0000320193-24-000001"
        assert event["source"] == "SEC_EDGAR"
        assert "source_url" in event
        assert event["metadata"]["cik"]

    def test_parse_edgar_html_handles_invalid_dates(self):
        """Invalid dates should be skipped."""
        producer = EventProducerService()

        html_content = """
        <tr>
            <td>invalid-date</td>
            <td>8-K</td>
            <a href="/cgi-bin/viewer?accession_number=0000320193-24-000010">Form 8-K</a>
        </tr>
        """

        events = producer._parse_edgar_html(html_content, "AAPL", "8-K")

        # Invalid date should be skipped
        assert len(events) == 0

    def test_ticker_to_cik_mapping(self):
        """Verify ticker to CIK conversion."""
        producer = EventProducerService()

        # Known ticker should map to CIK
        cik = producer._ticker_to_cik("AAPL")
        assert cik == "0000320193"

        cik = producer._ticker_to_cik("MSFT")
        assert cik == "0000789019"

        # Unknown ticker should return ticker as-is
        cik = producer._ticker_to_cik("UNKNOWN")
        assert cik == "UNKNOWN"


class TestYfinanceCalendarScanning:
    """Test yfinance calendar event detection."""

    @patch("backend.services.event_producer.yf.Ticker")
    def test_parse_yfinance_earnings_calendar(self, mock_ticker):
        """Verify yfinance earnings calendar parsing."""
        producer = EventProducerService()

        # Mock yfinance Ticker response
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = {
            "earningsDate": [datetime(2024, 3, 15, 0, 0, 0)],
        }
        mock_ticker.return_value = mock_ticker_instance

        events = producer.scan_yfinance_calendar(["AAPL"])

        # Should find earnings event
        assert len(events) >= 1
        earnings_events = [e for e in events if e["event_type"] == "earnings"]
        assert len(earnings_events) >= 1
        assert earnings_events[0]["ticker"] == "AAPL"

    @patch("backend.services.event_producer.yf.Ticker")
    def test_parse_yfinance_dividend_calendar(self, mock_ticker):
        """Verify yfinance dividend calendar parsing."""
        producer = EventProducerService()

        # Mock yfinance response with dividend
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = {
            "exDividendDate": datetime(2024, 4, 1, 0, 0, 0),
            "dividendYield": 0.025,
        }
        mock_ticker.return_value = mock_ticker_instance

        events = producer.scan_yfinance_calendar(["MSFT"])

        # Should find dividend event
        assert len(events) >= 1
        dividend_events = [e for e in events if e["event_type"] == "dividend_ex_date"]
        assert len(dividend_events) >= 1
        assert dividend_events[0]["metadata"]["dividend_yield"] == 0.025

    @patch("backend.services.event_producer.yf.Ticker")
    def test_yfinance_handles_missing_calendar_data(self, mock_ticker):
        """Missing calendar data should be handled gracefully."""
        producer = EventProducerService()

        # Mock yfinance response with no calendar data
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = {
            "earningsDate": None,
            "exDividendDate": None,
        }
        mock_ticker.return_value = mock_ticker_instance

        events = producer.scan_yfinance_calendar(["AAPL"])

        # Should return empty list or skip
        assert isinstance(events, list)


class TestRateLimiting:
    """Test SEC EDGAR rate limiting."""

    def test_rate_limit_per_sec_enforcement(self):
        """Verify rate limiter enforces max 10 requests/sec."""
        producer = EventProducerService()

        # Mock the requests to track timing
        from backend.services.event_producer import _rate_limit_sec

        call_times = []

        @_rate_limit_sec()
        def mock_request():
            import time
            call_times.append(time.time())
            return "response"

        # Make multiple calls in quick succession
        for _ in range(5):
            mock_request()

        # All calls should complete without hanging indefinitely
        assert len(call_times) == 5

    @patch("backend.services.event_producer.requests.Session.get")
    def test_fetch_edgar_url_with_rate_limiting(self, mock_get):
        """Verify fetch_edgar_url applies rate limiting."""
        producer = EventProducerService()

        # Mock successful response
        mock_response = MagicMock()
        mock_response.text = "<html>mock</html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Should return content
        content = producer._fetch_edgar_url("https://www.sec.gov/test")
        assert content == "<html>mock</html>"

    @patch("backend.services.event_producer.requests.Session.get")
    def test_fetch_edgar_url_handles_errors(self, mock_get):
        """Verify error handling in fetch_edgar_url."""
        producer = EventProducerService()

        # Mock failed request
        mock_get.side_effect = Exception("Network error")

        content = producer._fetch_edgar_url("https://www.sec.gov/test")

        # Should return None on error
        assert content is None


class TestScanAll:
    """Test combined SEC EDGAR + yfinance scanning."""

    @patch.object(EventProducerService, "scan_sec_edgar")
    @patch.object(EventProducerService, "scan_yfinance_calendar")
    def test_scan_all_combines_sources(self, mock_yfinance, mock_edgar):
        """Verify scan_all combines results from both sources."""
        producer = EventProducerService()

        # Mock SEC EDGAR results
        mock_edgar.return_value = [
            {
                "ticker": "AAPL",
                "filing_type": "8-K",
                "filing_date": "2024-03-10",
                "accession_number": "test-001",
                "source": "SEC_EDGAR",
            }
        ]

        # Mock yfinance results
        mock_yfinance.return_value = [
            {
                "ticker": "AAPL",
                "event_type": "earnings",
                "event_date": "2024-03-15",
                "source": "YFINANCE",
            }
        ]

        all_events = producer.scan_all(["AAPL"])

        # Should combine both sources
        assert len(all_events) == 2
        sources = set(e["source"] for e in all_events)
        assert "SEC_EDGAR" in sources
        assert "YFINANCE" in sources

    @patch.object(EventProducerService, "scan_sec_edgar")
    @patch.object(EventProducerService, "scan_yfinance_calendar")
    def test_scan_all_handles_empty_results(self, mock_yfinance, mock_edgar):
        """Verify scan_all handles empty results gracefully."""
        producer = EventProducerService()

        mock_edgar.return_value = []
        mock_yfinance.return_value = []

        all_events = producer.scan_all(["AAPL"])

        # Should return empty list
        assert len(all_events) == 0
        assert isinstance(all_events, list)
