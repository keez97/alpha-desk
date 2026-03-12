"""
Background cache refresh daemon for AlphaDesk.

Proactively refreshes hot cache keys before TTL expiry to ensure
the /all endpoint always serves cached data instantly.
Replaces the one-shot _prewarm() in main.py with continuous refresh.
"""

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()

# Refresh intervals (seconds) — set slightly below cache TTL to keep data warm
_MACRO_INTERVAL = 720      # 12 min (cache TTL is 15 min / 900s, but we set 1800 in data_provider)
_SECTOR_INTERVAL = 240     # 4 min (cache TTL is 300s / 5 min)
_SPY_HISTORY_INTERVAL = 1500  # 25 min (cache TTL is 1800s / 30 min)
_NEWS_INTERVAL = 720       # 12 min (cache TTL is 900s / 15 min)
_REGIME_INTERVAL = 1500    # 25 min (cache TTL is 1800s / 30 min)
_CLEANUP_INTERVAL = 300    # 5 min — sweep expired cache entries

def _refresh_loop():
    """Main refresh loop. Runs in daemon thread."""
    # Initial delay — let app fully start
    _stop_event.wait(5)
    if _stop_event.is_set():
        return

    last_macro = 0
    last_sector = 0
    last_spy = 0
    last_news = 0
    last_regime = 0
    last_cleanup = 0

    while not _stop_event.is_set():
        now = time.time()

        # Macro data
        if now - last_macro >= _MACRO_INTERVAL:
            try:
                from backend.services.data_provider import get_macro_data
                macro = get_macro_data()
                logger.info(f"Cache refresh: macro data — {len(macro)} tickers")
                last_macro = time.time()
            except Exception as e:
                logger.warning(f"Cache refresh: macro failed — {e}")
                last_macro = time.time()  # Don't hammer on failure

        # Sector chart data
        if now - last_sector >= _SECTOR_INTERVAL:
            try:
                from backend.services.data_provider import get_sector_chart_data
                sectors = get_sector_chart_data("1D")
                count = len(sectors.get("sectors", [])) if isinstance(sectors, dict) else 0
                logger.info(f"Cache refresh: sector charts — {count} sectors")
                last_sector = time.time()
            except Exception as e:
                logger.warning(f"Cache refresh: sectors failed — {e}")
                last_sector = time.time()

        # SPY 1y history (for historical analogs)
        if now - last_spy >= _SPY_HISTORY_INTERVAL:
            try:
                from backend.services import yahoo_direct as yd
                spy_hist = yd.get_history("SPY", range_str="1y", interval="1d")
                logger.info(f"Cache refresh: SPY history — {len(spy_hist) if spy_hist else 0} records")
                last_spy = time.time()
            except Exception as e:
                logger.warning(f"Cache refresh: SPY history failed — {e}")
                last_spy = time.time()

        # Market news (for sentiment headlines)
        if now - last_news >= _NEWS_INTERVAL:
            try:
                from backend.services.web_search import search_market_news
                # Need macro data for contextual news search
                from backend.services.data_provider import get_macro_data as _get_macro
                macro = _get_macro()
                articles = search_market_news(macro_data=macro, max_total=15)
                logger.info(f"Cache refresh: news — {len(articles)} articles")
                last_news = time.time()
            except Exception as e:
                logger.warning(f"Cache refresh: news failed — {e}")
                last_news = time.time()

        # Regime detection (proactive refresh keeps the internal _regime_cache warm
        # so /all endpoint always hits cache instead of making ~10 FRED/Yahoo calls)
        if now - last_regime >= _REGIME_INTERVAL:
            try:
                from backend.services.regime_detector import detect_regime
                from backend.services.data_provider import get_macro_data as _get_macro_regime
                macro_for_regime = _get_macro_regime()
                regime = detect_regime(macro_for_regime)
                layer_count = len(regime.get("layers", {})) if regime else 0
                logger.info(f"Cache refresh: regime detection — {layer_count} layers, regime={regime.get('regime', '?')}")
                last_regime = time.time()
            except Exception as e:
                logger.warning(f"Cache refresh: regime detection failed — {e}")
                last_regime = time.time()

        # Periodic cache cleanup
        if now - last_cleanup >= _CLEANUP_INTERVAL:
            try:
                from backend.services.cache import cache
                cache.cleanup_expired()
                logger.debug("Cache refresh: expired entries cleaned up")
                last_cleanup = time.time()
            except Exception as e:
                logger.warning(f"Cache refresh: cleanup failed — {e}")
                last_cleanup = time.time()

        # Sleep in small increments so stop_event is responsive
        _stop_event.wait(30)


def start():
    """Start the background cache refresh daemon."""
    global _thread
    if _thread is not None and _thread.is_alive():
        logger.warning("Cache refresh thread already running")
        return

    _stop_event.clear()
    _thread = threading.Thread(target=_refresh_loop, daemon=True, name="cache-refresh")
    _thread.start()
    logger.info("Cache refresh daemon started")


def stop():
    """Stop the background cache refresh daemon."""
    global _thread
    _stop_event.set()
    if _thread is not None:
        _thread.join(timeout=5)
        logger.info("Cache refresh daemon stopped")
    _thread = None
