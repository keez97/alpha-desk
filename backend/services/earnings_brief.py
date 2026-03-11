"""
Earnings Brief Service for Morning Brief.

Data source cascade for earnings dates:
  1. SEC EDGAR (8-K Item 2.02 filings, no auth, 10 req/sec)
  2. yfinance calendar (library, rate-limited)

Data source cascade for price/drift data:
  1. financialdatasets.ai (FDS, paid API, reliable)
  2. yahoo_direct (v8 API for price history)
  3. yfinance (library for prices)

Provides:
- Upcoming earnings dates (2-week window)
- Pre-earnings drift signals (10-day return > 1.5 std dev)
- Earnings clustering (3+ stocks in same sector reporting same week)
"""

import logging
import time
from typing import Dict, List, Any
from datetime import datetime, timedelta
import yfinance as yf
from backend.services import yfinance_service
from backend.services import yahoo_direct
from backend.services import edgar_service
from backend.services import fds_client as fds
from backend.services.yfinance_service import _yf_session

logger = logging.getLogger(__name__)

# Cache for earnings brief (30 min TTL)
_cache_earnings_brief = None
_cache_earnings_brief_expires = 0

DEFAULT_EARNINGS_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "JPM", "BAC", "GS",
    "UNH", "JNJ", "PG",
    "XOM", "HD",
]

SECTOR_MAP = {
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology", "AMZN": "Technology",
    "NVDA": "Technology", "META": "Technology", "TSLA": "Consumer Disc",
    "JPM": "Financials", "BAC": "Financials", "GS": "Financials",
    "UNH": "Healthcare", "JNJ": "Healthcare", "PG": "Consumer Staples",
    "XOM": "Energy", "HD": "Consumer Disc",
}


# Cache for EDGAR earnings data (fetched in batch, reused per-ticker)
_edgar_earnings_cache: Dict[str, Any] = {}
_edgar_cache_expires = 0


def _get_edgar_earnings_batch() -> Dict[str, Any]:
    """Fetch earnings dates for all default tickers from SEC EDGAR in one batch."""
    global _edgar_earnings_cache, _edgar_cache_expires

    if _edgar_earnings_cache and time.time() < _edgar_cache_expires:
        return _edgar_earnings_cache

    try:
        result = edgar_service.get_earnings_dates(DEFAULT_EARNINGS_TICKERS)
        if result:
            _edgar_earnings_cache = result
            _edgar_cache_expires = time.time() + 4 * 3600  # 4 hour cache
            return result
    except Exception as e:
        logger.debug(f"EDGAR batch earnings fetch failed: {e}")

    return {}


def _get_earnings_date(ticker: str) -> tuple[str | None, str]:
    """
    Fetch upcoming earnings date using cascade:
    1. SEC EDGAR (8-K Item 2.02)
    2. yfinance calendar

    Returns (date_str, source) tuple.
    """
    # --- Tier 1: SEC EDGAR ---
    try:
        edgar_data = _get_edgar_earnings_batch()
        if ticker in edgar_data:
            entry = edgar_data[ticker]
            estimated_next = entry.get("estimated_next_earnings")
            if estimated_next:
                # Validate the date is reasonable (within next 120 days)
                date_obj = datetime.fromisoformat(estimated_next).date()
                today = datetime.utcnow().date()
                days_until = (date_obj - today).days
                if -7 <= days_until <= 120:
                    return estimated_next, "sec_edgar"
    except Exception as e:
        logger.debug(f"EDGAR earnings lookup failed for {ticker}: {e}")

    # --- Tier 2: yfinance calendar ---
    try:
        if time.time() < yfinance_service._rate_limited_until:
            return None, "none"
        data = yf.Ticker(ticker, session=_yf_session)
        calendar = data.calendar
        if calendar is not None and isinstance(calendar, dict):
            earnings_date = calendar.get("Earnings Date")
            if earnings_date:
                if hasattr(earnings_date, "date"):
                    return earnings_date.date().isoformat(), "yfinance"
                return str(earnings_date).split()[0], "yfinance"
        return None, "none"
    except Exception as e:
        logger.debug(f"Could not fetch earnings date for {ticker}: {e}")
        return None, "none"


def _calculate_pre_drift_cascade(ticker: str) -> Dict[str, Any] | None:
    """
    Calculate 10-day pre-earnings drift using data source cascade.
    Tier 1: FDS (financialdatasets.ai), Tier 2: yahoo_direct, Tier 3: yfinance
    """
    # --- Tier 1: FDS (financialdatasets.ai) ---
    if fds.is_available():
        try:
            end_date = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
            start_date = (datetime.utcnow().date() - timedelta(days=90)).isoformat()
            records = fds.get_historical_prices(ticker, start_date, end_date)
            if records and len(records) >= 15:
                closes = [r["close"] for r in records if r.get("close") is not None]
                if len(closes) >= 15:
                    return _compute_drift_from_closes(closes)
        except Exception as e:
            logger.debug(f"FDS drift {ticker}: {e}")

    # --- Tier 2: yahoo_direct ---
    hist = yahoo_direct.get_history(ticker, range_str="3mo")
    if len(hist) >= 15:
        closes = [d["close"] for d in hist]
        return _compute_drift_from_closes(closes)

    # --- Tier 3: yfinance ---
    if time.time() >= yfinance_service._rate_limited_until:
        try:
            data = yf.Ticker(ticker, session=_yf_session)
            yf_hist = data.history(period="3mo")
            if not yf_hist.empty and len(yf_hist) >= 15:
                closes = yf_hist["Close"].tolist()
                return _compute_drift_from_closes(closes)
        except Exception as e:
            logger.debug(f"yfinance drift {ticker}: {e}")

    return None


def _compute_drift_from_closes(closes: List[float]) -> Dict[str, Any] | None:
    """Compute pre-earnings drift from a list of closing prices."""
    if len(closes) < 15:
        return None

    # 10-day return
    recent = closes[-11:]
    if len(recent) < 11:
        return None

    start_price = recent[0]
    end_price = recent[-1]
    if start_price == 0:
        return None

    pre_drift_pct = ((end_price - start_price) / start_price) * 100

    # 60-day std dev
    all_returns = []
    for i in range(1, min(61, len(closes))):
        prev = closes[-(i + 1)]
        curr = closes[-i]
        if prev != 0:
            ret = ((curr - prev) / prev) * 100
            all_returns.append(ret)

    if all_returns:
        avg_return = sum(all_returns) / len(all_returns)
        variance = sum((x - avg_return) ** 2 for x in all_returns) / len(all_returns)
        std_return = variance ** 0.5
    else:
        std_return = 1.0

    z_score = (pre_drift_pct / std_return) if std_return > 0 else 0
    is_signal = abs(pre_drift_pct) > (1.5 * std_return)

    return {
        "pre_drift_pct": round(pre_drift_pct, 2),
        "is_signal": is_signal,
        "signal_strength": round(abs(z_score), 2),
    }


def _cluster_earnings_by_week(upcoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Identify earnings clusters: 3+ stocks in same sector same week."""
    week_sector_map = {}
    for item in upcoming:
        earnings_date = item.get("earnings_date")
        if not earnings_date:
            continue
        date_obj = datetime.fromisoformat(earnings_date).date()
        week_start = date_obj - timedelta(days=date_obj.weekday())
        key = (week_start.isoformat(), item.get("sector", "Unknown"))
        if key not in week_sector_map:
            week_sector_map[key] = []
        week_sector_map[key].append(item["ticker"])

    return [
        {"week": week_key, "sector": sector, "count": len(tickers), "tickers": tickers}
        for (week_key, sector), tickers in week_sector_map.items()
        if len(tickers) >= 3
    ]


def get_earnings_brief() -> Dict[str, Any]:
    """
    Get earnings brief for morning brief.
    Uses cascade for drift calculation; yfinance for earnings dates.
    Falls back to minimal response if all sources fail.
    """
    global _cache_earnings_brief, _cache_earnings_brief_expires

    if _cache_earnings_brief and time.time() < _cache_earnings_brief_expires:
        return _cache_earnings_brief

    # Check if rate-limited — still try yahoo_direct for drift data
    yf_rate_limited = time.time() < yfinance_service._rate_limited_until

    upcoming = []
    alerts = []
    consecutive_failures = 0
    data_sources = set()

    for ticker in DEFAULT_EARNINGS_TICKERS:
        if consecutive_failures >= 4 and yf_rate_limited:
            break

        # Get earnings date (SEC EDGAR → yfinance cascade)
        earnings_date, date_source = _get_earnings_date(ticker)
        if not earnings_date:
            consecutive_failures += 1
            continue
        consecutive_failures = 0
        if date_source:
            data_sources.add(date_source)

        date_obj = datetime.fromisoformat(earnings_date).date()
        today = datetime.utcnow().date()
        days_until = (date_obj - today).days

        if days_until < -1 or days_until > 14:
            continue

        # Get pre-drift data via cascade
        drift_data = _calculate_pre_drift_cascade(ticker)
        pre_drift_pct = drift_data["pre_drift_pct"] if drift_data else 0
        pre_drift_signal = drift_data["is_signal"] if drift_data else False

        if drift_data:
            if fds.is_available():
                data_sources.add("financialdatasets.ai")
            elif yahoo_direct.is_available():
                data_sources.add("yahoo_direct")
            else:
                data_sources.add("yfinance")

        sector = SECTOR_MAP.get(ticker, "Unknown")

        item = {
            "ticker": ticker,
            "name": ticker,
            "earnings_date": earnings_date,
            "days_until": max(0, days_until),
            "pre_drift_pct": pre_drift_pct,
            "pre_drift_signal": pre_drift_signal,
            "sector": sector,
        }
        upcoming.append(item)

        if pre_drift_signal:
            alert_type = "pre_earnings_surge" if pre_drift_pct > 0 else "pre_earnings_decline"
            alerts.append({
                "ticker": ticker,
                "alert_type": alert_type,
                "pre_drift_pct": pre_drift_pct,
                "earnings_date": earnings_date,
            })

    upcoming.sort(key=lambda x: x["days_until"])
    clusters = _cluster_earnings_by_week(upcoming)

    if upcoming:
        response = {
            "timestamp": datetime.utcnow().isoformat(),
            "upcoming": upcoming,
            "clusters": clusters,
            "alerts": alerts,
            "data_sources": list(data_sources),
        }
        _cache_earnings_brief = response
        _cache_earnings_brief_expires = time.time() + 30 * 60
        return response

    # Minimal fallback — empty but honest
    logger.warning("No earnings data available from any source")
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "upcoming": [],
        "clusters": [],
        "alerts": [],
        "data_source": "none",
        "note": "Earnings calendar unavailable — yfinance may be rate-limited",
    }
