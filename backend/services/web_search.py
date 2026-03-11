"""
Web Search Service — fetches real-time market news via DuckDuckGo + RSS feeds.

Provides a unified news pipeline for Claude-enhanced market analysis:
1. DuckDuckGo news search (no API key needed, instant results)
2. RSS feeds from major financial sources (existing system)
3. Deduplication and relevance scoring

Results are formatted for direct inclusion in Claude prompts.
"""

import logging
import time
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

logger = logging.getLogger(__name__)

# ─── Cache ──────────────────────────────────────────────────────────────
_search_cache: Dict[str, Any] = {}
_SEARCH_CACHE_TTL = 900  # 15 minutes


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text).strip()


# ─── DuckDuckGo News Search ────────────────────────────────────────────
_ddgs_instance = None

def _get_ddgs():
    """Get or create shared DDGS instance."""
    global _ddgs_instance
    if _ddgs_instance is None:
        try:
            from duckduckgo_search import DDGS
            _ddgs_instance = DDGS()
        except ImportError:
            logger.warning("duckduckgo_search not installed, DDG news unavailable")
            return None
    return _ddgs_instance


def _search_ddg_news(query: str, max_results: int = 8) -> List[Dict[str, Any]]:
    """
    Search DuckDuckGo for recent news articles using duckduckgo_search library.

    Uses the dedicated news endpoint for real, timestamped headlines.
    """
    articles = []
    try:
        ddgs = _get_ddgs()
        if ddgs is None:
            return articles

        results = ddgs.news(query, max_results=max_results, timelimit="d")
        for r in results:
            headline = r.get("title", "").strip()
            if not headline or len(headline) < 10:
                continue
            articles.append({
                "headline": headline[:200],
                "source": r.get("source", "News"),
                "url": r.get("url", ""),
                "snippet": r.get("body", "")[:300],
                "published_at": r.get("date", datetime.now(timezone.utc).isoformat()),
            })
    except Exception as e:
        logger.warning(f"DDG news search failed for '{query}': {e}")

    # Fallback: try text search if news returns nothing
    if not articles:
        try:
            ddgs = _get_ddgs()
            if ddgs:
                results = ddgs.text(f"{query} news today", max_results=max_results, timelimit="d")
                for r in results:
                    title = r.get("title", "").strip()
                    if title and len(title) > 15:
                        articles.append({
                            "headline": title[:200],
                            "source": "Web Search",
                            "url": r.get("href", ""),
                            "snippet": r.get("body", "")[:300],
                            "published_at": datetime.now(timezone.utc).isoformat(),
                        })
        except Exception as e:
            logger.warning(f"DDG text search fallback failed: {e}")

    return articles


def search_market_news(
    macro_data: dict = None,
    max_total: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fetch market news from multiple sources: DDG search + RSS feeds.

    Builds search queries dynamically based on current macro data, then
    combines results from DuckDuckGo search and RSS feeds.

    Args:
        macro_data: Current macro data dict (VIX, yields, etc.)
        max_total: Maximum total articles to return

    Returns:
        List of deduplicated, sorted article dicts with:
        - headline, source, url, published_at, snippet (optional)
    """
    cache_key = "market_news_combined"
    now = time.time()

    # Check cache
    if cache_key in _search_cache:
        cached = _search_cache[cache_key]
        if now - cached["ts"] < _SEARCH_CACHE_TTL:
            return cached["data"]

    all_articles: List[Dict[str, Any]] = []

    # Build smart search queries from macro data
    search_queries = _build_search_queries(macro_data)

    # Phase 1: Parallel DDG searches + RSS fetch
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}

        # Submit DDG search queries
        for query in search_queries[:4]:  # Max 4 parallel searches
            futures[executor.submit(_search_ddg_news, query, 5)] = f"ddg:{query}"

        # Submit RSS fetch
        try:
            from backend.services.news_ingestion import fetch_rss_articles
            futures[executor.submit(fetch_rss_articles, 8)] = "rss"
        except ImportError:
            logger.warning("RSS module not available")

        # Collect results
        for future in as_completed(futures, timeout=12):
            source = futures[future]
            try:
                results = future.result(timeout=10)
                if source == "rss":
                    # RSS articles need format normalization
                    for article in results:
                        all_articles.append({
                            "headline": article.get("headline", article.get("title", "")),
                            "source": article.get("source", article.get("publisher", "RSS")),
                            "url": article.get("url", ""),
                            "snippet": article.get("body_snippet", "")[:200],
                            "published_at": article.get("published_at", article.get("publishedAt", "")),
                        })
                else:
                    all_articles.extend(results)
            except Exception as e:
                logger.warning(f"Search source {source} failed: {e}")

    # Deduplicate by headline similarity
    seen_headlines = set()
    unique_articles = []
    for article in all_articles:
        headline = article.get("headline", "").lower().strip()
        # Simple dedup: skip if first 40 chars match
        key = headline[:40]
        if key and key not in seen_headlines:
            seen_headlines.add(key)
            unique_articles.append(article)

    # Sort by relevance (DDG results first, then RSS)
    unique_articles.sort(
        key=lambda a: (0 if a.get("source") in ("Web Search", "DuckDuckGo") else 1),
    )

    result = unique_articles[:max_total]

    # Cache
    _search_cache[cache_key] = {"ts": now, "data": result}
    logger.info(f"Market news search: {len(result)} articles from {len(search_queries)} queries + RSS")

    return result


def _build_search_queries(macro_data: dict = None) -> List[str]:
    """Build targeted search queries based on current market conditions."""
    queries = [
        "stock market news today",
        "financial markets today",
    ]

    if not macro_data:
        return queries

    vix = macro_data.get("^VIX", {}).get("price")
    cl = macro_data.get("CL=F", {})
    tnx = macro_data.get("^TNX", {})
    dxy = macro_data.get("DX-Y.NYB", {})

    # Add context-aware queries based on market conditions
    if vix and vix > 25:
        queries.append("market volatility VIX spike today")
    if vix and vix > 30:
        queries.append("stock market crash risk today")

    if cl.get("pct_change") and abs(cl["pct_change"]) > 3:
        direction = "surge" if cl["pct_change"] > 0 else "drop"
        queries.append(f"crude oil price {direction} today")

    if tnx.get("price"):
        queries.append("treasury yields bond market today")

    if dxy.get("pct_change") and abs(dxy["pct_change"]) > 0.5:
        queries.append("US dollar strength currency markets today")

    # Always include Fed/policy
    queries.append("Federal Reserve interest rate policy today")

    return queries[:6]  # Cap at 6 queries


def format_news_for_prompt(articles: List[Dict[str, Any]], max_articles: int = 15) -> str:
    """
    Format news articles into a clean text block for a Claude prompt.

    Returns a string like:
    RECENT NEWS & HEADLINES:
    1. "Fed signals patience on rate cuts" — Reuters (2026-03-11)
       https://reuters.com/...
    2. "VIX spikes above 25 as trade war fears mount" — MarketWatch (2026-03-11)
       https://marketwatch.com/...
    """
    if not articles:
        return "RECENT NEWS: No recent articles available.\n"

    lines = ["RECENT NEWS & HEADLINES (from web search + RSS feeds):"]

    for i, article in enumerate(articles[:max_articles], 1):
        headline = article.get("headline", "").strip()
        source = article.get("source", "Unknown")
        url = article.get("url", "")
        snippet = article.get("snippet", "")
        pub = article.get("published_at", "")[:10]  # Just the date

        if not headline:
            continue

        line = f'{i}. "{headline}" — {source}'
        if pub:
            line += f" ({pub})"
        lines.append(line)

        if snippet:
            lines.append(f"   Summary: {snippet[:150]}")
        if url:
            lines.append(f"   URL: {url}")

    return "\n".join(lines) + "\n"
