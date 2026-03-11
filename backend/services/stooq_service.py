"""
Stooq CSV Historical Price Service.

Provides free historical OHLCV data via Stooq's public CSV download endpoint.
No API key required. Works for US stocks, ETFs, indices, and commodities.

Use as fallback when both yahoo_direct and yfinance are rate-limited.

Ticker mapping:
  • US stocks/ETFs: append ".US" (e.g., SPY → SPY.US)
  • Indices: use stooq format (e.g., ^SPX → ^SPX)
  • Futures: use stooq codes
"""

import logging
import csv
import time
from io import StringIO
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

import requests

from backend.services.cache import TTLCache

logger = logging.getLogger(__name__)

_cache = TTLCache()
_CACHE_TTL = 3600  # 1 hour (stooq data is EOD)

_BASE_URL = "https://stooq.com/q/d/l/"

_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
})

# Map internal tickers to stooq format
_TICKER_MAP = {
    "SPY": "spy.us",
    "QQQ": "qqq.us",
    "IWM": "iwm.us",
    "DIA": "dia.us",
    "TLT": "tlt.us",
    "GLD": "gld.us",
    "USO": "uso.us",
    "UUP": "uup.us",
    "XLK": "xlk.us",
    "XLV": "xlv.us",
    "XLF": "xlf.us",
    "XLY": "xly.us",
    "XLP": "xlp.us",
    "XLE": "xle.us",
    "XLRE": "xlre.us",
    "XLI": "xli.us",
    "XLU": "xlu.us",
    "XLC": "xlc.us",
    "AAPL": "aapl.us",
    "MSFT": "msft.us",
    "GOOGL": "googl.us",
    "AMZN": "amzn.us",
    "NVDA": "nvda.us",
    "META": "meta.us",
    "TSLA": "tsla.us",
    "BTC-USD": "btc.v",
}

# Track availability
_available = True
_last_failure = 0


def _to_stooq_ticker(ticker: str) -> str:
    """Convert internal ticker to stooq format."""
    if ticker in _TICKER_MAP:
        return _TICKER_MAP[ticker]
    # Default: append .us for US equities
    return f"{ticker.lower()}.us"


def get_history(
    ticker: str,
    lookback_days: int = 120,
) -> List[Dict[str, Any]]:
    """
    Fetch historical OHLCV data from Stooq.

    Returns list of dicts with: date, open, high, low, close, volume
    Sorted oldest to newest.
    """
    global _available, _last_failure

    cache_key = f"stooq_hist:{ticker}:{lookback_days}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    # Skip if recently failed
    if not _available and time.time() - _last_failure < 600:
        return []

    stooq_ticker = _to_stooq_ticker(ticker)
    end_date = datetime.now(timezone.utc).strftime("%Y%m%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y%m%d")

    try:
        # Small delay between requests to avoid connection resets
        time.sleep(0.5)

        url = _BASE_URL
        params = {
            "s": stooq_ticker,
            "d1": start_date,
            "d2": end_date,
            "i": "d",  # daily
        }
        resp = _session.get(url, params=params, timeout=10)

        if resp.status_code != 200:
            logger.warning("Stooq %s: HTTP %d", ticker, resp.status_code)
            _last_failure = time.time()
            return []

        # Parse CSV
        reader = csv.DictReader(StringIO(resp.text))
        rows = []
        for row in reader:
            try:
                rows.append({
                    "date": row["Date"],
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(float(row.get("Volume", 0))),
                })
            except (ValueError, KeyError):
                continue

        if not rows:
            _last_failure = time.time()
            return []

        # Stooq returns newest first — reverse to oldest first
        rows.sort(key=lambda x: x["date"])

        _available = True
        _cache.set(cache_key, rows, _CACHE_TTL)
        logger.info("Stooq %s: %d data points", ticker, len(rows))
        return rows

    except Exception as e:
        logger.warning("Stooq fetch %s: %s", ticker, e)
        _last_failure = time.time()
        return []


def get_latest_close(ticker: str) -> Optional[float]:
    """Get the most recent closing price."""
    hist = get_history(ticker, lookback_days=10)
    if hist:
        return hist[-1]["close"]
    return None


def get_overnight_return(ticker: str) -> Optional[Dict[str, float]]:
    """
    Calculate overnight return from stooq EOD data.
    Note: This uses close-to-open, which is yesterday's close to today's open.
    Less accurate than intraday data but better than mock.
    """
    hist = get_history(ticker, lookback_days=10)
    if len(hist) < 2:
        return None

    yesterday = hist[-2]
    today = hist[-1]

    if yesterday["close"] == 0:
        return None

    overnight_pct = (today["open"] - yesterday["close"]) / yesterday["close"] * 100
    return {
        "overnight_pct": round(overnight_pct, 4),
        "today_open": today["open"],
        "yesterday_close": yesterday["close"],
    }


def get_momentum(ticker: str) -> Optional[Dict[str, float]]:
    """
    Calculate 1-month and 3-month momentum from stooq historical data.
    """
    hist = get_history(ticker, lookback_days=120)
    if len(hist) < 22:
        return None

    current = hist[-1]["close"]

    # 1-month momentum (21 trading days)
    if len(hist) >= 22:
        m1_start = hist[-22]["close"]
        momentum_1m = (current - m1_start) / m1_start if m1_start else 0
    else:
        momentum_1m = 0

    # 3-month momentum (63 trading days)
    if len(hist) >= 64:
        m3_start = hist[-64]["close"]
        momentum_3m = (current - m3_start) / m3_start if m3_start else 0
    else:
        momentum_3m = 0

    return {
        "momentum_1m": round(momentum_1m, 5),
        "momentum_3m": round(momentum_3m, 5),
        "current_price": current,
    }


def is_available() -> bool:
    """Check if Stooq is currently accessible."""
    return _available or (time.time() - _last_failure >= 600)
