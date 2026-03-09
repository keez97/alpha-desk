import yfinance as yf
import pandas as pd
from functools import lru_cache
from typing import Dict, List, Any
import logging
import time
from backend.services import mock_data

logger = logging.getLogger(__name__)

# Flag to track if network is available
USE_MOCK = False


def _retry_with_backoff(func, max_retries=3, initial_delay=1.0, backoff_factor=2.0):
    """Execute function with exponential backoff on rate limit."""
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                logger.warning(f"Failed after {max_retries} attempts: {e}")
                return None
            time.sleep(delay)
            delay *= backoff_factor


def get_quote(ticker: str) -> Dict[str, Any]:
    """Get stock quote including price, change, volume, and market cap."""
    def _fetch():
        try:
            data = yf.Ticker(ticker)
            hist = data.history(period="1d")
            info = data.info

            if hist.empty:
                return {}

            current_price = info.get("currentPrice", hist["Close"].iloc[-1])
            prev_close = info.get("previousClose", current_price)
            change = current_price - prev_close
            pct_change = (change / prev_close * 100) if prev_close else 0

            return {
                "ticker": ticker,
                "price": float(current_price),
                "change": float(change),
                "pct_change": float(pct_change),
                "volume": int(info.get("volume", 0)),
                "52w_high": float(info.get("fiftyTwoWeekHigh", 0)),
                "52w_low": float(info.get("fiftyTwoWeekLow", 0)),
                "market_cap": info.get("marketCap", 0),
                "name": info.get("longName", ticker),
                "sector": info.get("sector", ""),
            }
        except Exception as e:
            logger.error(f"Error fetching quote for {ticker}: {e}")
            # Try mock data as fallback
            if ticker in mock_data.MOCK_QUOTE_DATA:
                logger.info(f"Using mock data for quote: {ticker}")
                return mock_data.MOCK_QUOTE_DATA[ticker]
            return {}

    return _retry_with_backoff(_fetch) or {}


def get_history(ticker: str, period: str = "1y", interval: str = "1d") -> List[Dict[str, Any]]:
    """Get historical price data."""
    def _fetch():
        try:
            data = yf.Ticker(ticker)
            hist = data.history(period=period, interval=interval)

            if hist.empty:
                return []

            result = []
            for date, row in hist.iterrows():
                result.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                })
            return result
        except Exception as e:
            logger.error(f"Error fetching history for {ticker}: {e}")
            # Return empty list for mock (history is complex to mock)
            logger.info(f"Using mock data (empty) for history: {ticker}")
            return []

    return _retry_with_backoff(_fetch) or []


@lru_cache(maxsize=1)
def get_macro_data() -> Dict[str, Any]:
    """Fetch macro indicators: TNX, IRX, VIX, Dollar, Gold, Oil, BTC, SPY, QQQ, IWM."""
    def _fetch():
        try:
            tickers = ["^TNX", "^IRX", "^VIX", "DX-Y.NYB", "GC=F", "CL=F", "BTC-USD", "SPY", "QQQ", "IWM"]
            result = {}

            for ticker in tickers:
                try:
                    data = yf.Ticker(ticker)
                    hist = data.history(period="1d")
                    info = data.info

                    if hist.empty:
                        continue

                    current = hist["Close"].iloc[-1]
                    prev_close = info.get("previousClose", current)
                    change = current - prev_close
                    pct_change = (change / prev_close * 100) if prev_close else 0

                    result[ticker] = {
                        "price": float(current),
                        "change": float(change),
                        "pct_change": float(pct_change),
                    }
                except Exception as e:
                    logger.error(f"Error fetching {ticker}: {e}")
                    continue

            return result if result else None
        except Exception as e:
            logger.error(f"Error in get_macro_data: {e}")
            return None

    fetched = _retry_with_backoff(_fetch)
    if fetched:
        return fetched
    # Fall back to mock data
    logger.info("Using mock macro data")
    return mock_data.MOCK_MACRO_DATA


def get_sector_data(period: str = "1D") -> List[Dict[str, Any]]:
    """Fetch all 11 sector ETFs with price action and normalized chart data."""
    sector_etfs = {
        "XLK": "Information Technology",
        "XLV": "Healthcare",
        "XLF": "Financials",
        "XLY": "Consumer Discretionary",
        "XLP": "Consumer Staples",
        "XLE": "Energy",
        "XLRE": "Real Estate",
        "XLI": "Industrials",
        "XLU": "Utilities",
        "XLCQ": "Communication Services",
        "XLC": "Communication Services",
    }

    def _fetch():
        try:
            results = []
            hist_period = "1mo" if period == "1D" else "1y" if period == "1Y" else "3mo"

            for ticker, sector_name in sector_etfs.items():
                try:
                    data = yf.Ticker(ticker)
                    hist = data.history(period=hist_period)
                    info = data.info

                    if hist.empty:
                        continue

                    current_price = hist["Close"].iloc[-1]
                    prev_close = info.get("previousClose", current_price)
                    daily_change = current_price - prev_close
                    daily_pct_change = (daily_change / prev_close * 100) if prev_close else 0

                    # Rebase chart to 100
                    first_price = hist["Close"].iloc[0]
                    normalized_prices = [(float(p) / first_price * 100) for p in hist["Close"]]

                    results.append({
                        "ticker": ticker,
                        "sector": sector_name,
                        "price": float(current_price),
                        "daily_change": float(daily_change),
                        "daily_pct_change": float(daily_pct_change),
                        "chart_data": normalized_prices,
                    })
                except Exception as e:
                    logger.error(f"Error fetching sector {ticker}: {e}")
                    continue

            return results if results else None
        except Exception as e:
            logger.error(f"Error in get_sector_data: {e}")
            return None

    fetched = _retry_with_backoff(_fetch)
    if fetched:
        return fetched
    # Fall back to mock data
    logger.info("Using mock sector data")
    return mock_data.MOCK_SECTOR_DATA


def search_ticker(query: str) -> List[Dict[str, str]]:
    """Search for tickers matching query."""
    def _fetch():
        try:
            # yfinance doesn't have native search, so we'll return partial matches
            # In production, you'd use a dedicated API or database
            result = yf.Ticker(query)
            info = result.info

            if "longName" in info:
                return [{
                    "ticker": query.upper(),
                    "name": info.get("longName", ""),
                    "sector": info.get("sector", ""),
                }]
            return None
        except Exception as e:
            logger.error(f"Error searching ticker {query}: {e}")
            return None

    fetched = _retry_with_backoff(_fetch)
    if fetched:
        return fetched

    # Try mock search results
    query_lower = query.lower()
    if query_lower in mock_data.MOCK_SEARCH_RESULTS:
        logger.info(f"Using mock search results for: {query}")
        return mock_data.MOCK_SEARCH_RESULTS[query_lower]

    return []


def get_stock_fundamentals(ticker: str) -> Dict[str, Any]:
    """Get comprehensive fundamental data for stock grading."""
    def _fetch():
        try:
            data = yf.Ticker(ticker)
            info = data.info

            # Get financials
            fundamentals = {
                "ticker": ticker,
                "name": info.get("longName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap", 0),
                "pe_ratio": info.get("trailingPE", None),
                "peg_ratio": info.get("pegRatio", None),
                "forward_pe": info.get("forwardPE", None),
                "price_to_book": info.get("priceToBook", None),
                "price_to_sales": info.get("priceToSalesTrailing12Months", None),
                "debt_to_equity": info.get("debtToEquity", None),
                "current_ratio": info.get("currentRatio", None),
                "quick_ratio": info.get("quickRatio", None),
                "beta": info.get("beta", None),
                "dividend_yield": info.get("dividendYield", None),
                "payout_ratio": info.get("payoutRatio", None),
                "short_interest": info.get("shortPercentOfFloat", None),
                "institutional_ownership": info.get("heldPercentInstitutions", None),
                "insider_ownership": info.get("heldPercentInsiders", None),
                "eps": info.get("trailingEps", None),
                "eps_growth": info.get("epsTrailingTwelveMonths", None),
                "revenue": info.get("totalRevenue", 0),
                "net_income": info.get("netIncomeToCommon", 0),
                "operating_cash_flow": info.get("operatingCashflow", 0),
                "free_cash_flow": info.get("freeCashflow", 0),
                "52w_high": info.get("fiftyTwoWeekHigh", None),
                "52w_low": info.get("fiftyTwoWeekLow", None),
                "50day_ma": info.get("fiftyDayAverage", None),
                "200day_ma": info.get("twoHundredDayAverage", None),
            }
            return fundamentals
        except Exception as e:
            logger.error(f"Error fetching fundamentals for {ticker}: {e}")
            return None

    fetched = _retry_with_backoff(_fetch)
    if fetched:
        return fetched

    # Try mock fundamentals
    if ticker in mock_data.MOCK_FUNDAMENTALS:
        logger.info(f"Using mock fundamentals for: {ticker}")
        return mock_data.MOCK_FUNDAMENTALS[ticker]

    return {"ticker": ticker}
