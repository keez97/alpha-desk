"""
Earnings Confluence Engine - Integration of earnings catalysts with confluence signals.

Detects when upcoming earnings for major holdings align with bullish confluence,
generating catalyst-boosted conviction scores.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, date
import yfinance as yf
import math

logger = logging.getLogger(__name__)

# Major holdings mapping by sector ETF
SECTOR_HOLDINGS = {
    "XLK": ["AAPL", "MSFT", "NVDA", "AVGO", "CRM"],
    "XLV": ["UNH", "JNJ", "LLY", "ABBV", "MRK"],
    "XLF": ["BRK-B", "JPM", "V", "MA", "BAC"],
    "XLY": ["AMZN", "TSLA", "HD", "MCD", "NKE"],
    "XLP": ["PG", "KO", "PEP", "COST", "WMT"],
    "XLE": ["XOM", "CVX", "COP", "SLB", "EOG"],
    "XLRE": ["PLD", "AMT", "EQIX", "SPG", "PSA"],
    "XLI": ["GE", "CAT", "UNP", "HON", "RTX"],
    "XLU": ["NEE", "SO", "DUK", "SRE", "AEP"],
    "XLC": ["META", "GOOGL", "GOOG", "NFLX", "DIS"],
}

# Sector names for reference
SECTOR_NAMES = {
    "XLK": "Technology",
    "XLV": "Healthcare",
    "XLF": "Financials",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLRE": "Real Estate",
    "XLI": "Industrials",
    "XLU": "Utilities",
    "XLC": "Communication Services",
}

# Mock earnings data for fallback
MOCK_EARNINGS = {
    # Tech
    "AAPL": {"date": (datetime.now() + timedelta(days=5)).date(), "name": "Apple"},
    "MSFT": {"date": (datetime.now() + timedelta(days=8)).date(), "name": "Microsoft"},
    "NVDA": {"date": (datetime.now() + timedelta(days=12)).date(), "name": "NVIDIA"},
    "AVGO": {"date": (datetime.now() + timedelta(days=6)).date(), "name": "Broadcom"},
    "CRM": {"date": (datetime.now() + timedelta(days=10)).date(), "name": "Salesforce"},
    # Healthcare
    "UNH": {"date": (datetime.now() + timedelta(days=3)).date(), "name": "UnitedHealth"},
    "JNJ": {"date": (datetime.now() + timedelta(days=7)).date(), "name": "Johnson & Johnson"},
    "LLY": {"date": (datetime.now() + timedelta(days=4)).date(), "name": "Eli Lilly"},
    "ABBV": {"date": (datetime.now() + timedelta(days=9)).date(), "name": "AbbVie"},
    "MRK": {"date": (datetime.now() + timedelta(days=11)).date(), "name": "Merck"},
    # Financials
    "BRK-B": {"date": (datetime.now() + timedelta(days=14)).date(), "name": "Berkshire Hathaway"},
    "JPM": {"date": (datetime.now() + timedelta(days=2)).date(), "name": "JPMorgan Chase"},
    "V": {"date": (datetime.now() + timedelta(days=6)).date(), "name": "Visa"},
    "MA": {"date": (datetime.now() + timedelta(days=7)).date(), "name": "Mastercard"},
    "BAC": {"date": (datetime.now() + timedelta(days=3)).date(), "name": "Bank of America"},
}


def get_earnings_date_for_ticker(ticker: str) -> Optional[date]:
    """
    Fetch earnings date from yfinance.

    Args:
        ticker: Ticker symbol

    Returns:
        date object if found, None otherwise
    """
    try:
        stock = yf.Ticker(ticker)
        calendar = stock.calendar

        if calendar is None or calendar.empty:
            return None

        # Get the first upcoming earnings date
        for idx, row in calendar.iterrows():
            earnings_date_str = row.get("Earnings Date")
            if earnings_date_str:
                if isinstance(earnings_date_str, str):
                    earnings_date = datetime.fromisoformat(earnings_date_str.split()[0]).date()
                else:
                    earnings_date = earnings_date_str

                # Only return future earnings
                if earnings_date >= date.today():
                    return earnings_date

        return None

    except Exception as e:
        logger.warning(f"Failed to fetch earnings for {ticker}: {e}")
        return None


def get_company_name(ticker: str) -> str:
    """
    Get company name for a ticker.

    Args:
        ticker: Ticker symbol

    Returns:
        Company name or ticker if lookup fails
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        name = info.get("longName")
        return name if name else ticker
    except Exception:
        # Return mock name if available
        if ticker in MOCK_EARNINGS:
            return MOCK_EARNINGS[ticker]["name"]
        return ticker


def get_upcoming_earnings_for_holdings(
    holdings: List[str],
    days_ahead: int = 14,
) -> List[Dict[str, Any]]:
    """
    Get upcoming earnings for a list of holdings.

    Args:
        holdings: List of ticker symbols
        days_ahead: Number of days ahead to look (default 14)

    Returns:
        List of upcoming earnings with dates
    """
    upcoming = []
    today = date.today()
    future_date = today + timedelta(days=days_ahead)

    for ticker in holdings:
        # Try yfinance first
        earnings_date = get_earnings_date_for_ticker(ticker)

        # Fallback to mock data
        if earnings_date is None and ticker in MOCK_EARNINGS:
            earnings_date = MOCK_EARNINGS[ticker]["date"]
        elif earnings_date is None:
            continue

        # Check if within window
        if today <= earnings_date <= future_date:
            company_name = get_company_name(ticker)
            days_until = (earnings_date - today).days

            upcoming.append({
                "ticker": ticker,
                "name": company_name,
                "date": earnings_date.isoformat(),
                "daysUntil": days_until,
            })

    # Sort by days until earnings
    upcoming.sort(key=lambda x: x["daysUntil"])
    return upcoming


def determine_catalyst_boost(
    catalyst_count: int,
    confluence_direction: Optional[str] = None,
) -> str:
    """
    Determine confluence boost level based on catalyst count and confluence direction.

    Args:
        catalyst_count: Number of major holdings with upcoming earnings
        confluence_direction: Direction of confluence signal (bullish/bearish/neutral)

    Returns:
        Boost level: "HIGH", "MEDIUM", "NONE"
    """
    # HIGH: 2+ catalysts AND bullish confluence
    if catalyst_count >= 2 and confluence_direction == "bullish":
        return "HIGH"

    # MEDIUM: 1 catalyst
    elif catalyst_count == 1:
        return "MEDIUM"

    # NONE: No catalysts or bearish confluence
    else:
        return "NONE"


def upgrade_conviction(
    original_conviction: str,
    boost: str,
) -> str:
    """
    Upgrade conviction based on catalyst boost.

    Args:
        original_conviction: Original conviction level (HIGH/MEDIUM/LOW)
        boost: Catalyst boost level (HIGH/MEDIUM/NONE)

    Returns:
        Upgraded conviction level
    """
    if boost == "NONE":
        return original_conviction

    conviction_levels = ["LOW", "MEDIUM", "HIGH"]

    try:
        current_idx = conviction_levels.index(original_conviction)
    except ValueError:
        return original_conviction

    # HIGH boost: upgrade by 1 level
    if boost == "HIGH":
        new_idx = min(current_idx + 1, 2)  # Cap at HIGH
        return conviction_levels[new_idx]

    # MEDIUM boost: upgrade by 0.5 levels (prefer current or up)
    elif boost == "MEDIUM":
        if current_idx < 2:
            return conviction_levels[current_idx]
        return original_conviction

    return original_conviction


def calculate_earnings_catalysts(
    confluence_signals: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Calculate earnings catalysts for all sectors.

    Args:
        confluence_signals: Optional list of confluence signals for boost calculation

    Returns:
        List of EarningsCatalyst objects with conviction boosts
    """
    catalysts = []
    today = date.today()

    # Build confluence map by sector ticker
    confluence_map = {}
    if confluence_signals:
        for signal in confluence_signals:
            sector_ticker = signal.get("sectorTicker")
            confluence_map[sector_ticker] = {
                "direction": signal.get("direction", "neutral"),
                "conviction": signal.get("conviction", "LOW"),
            }

    # Analyze each sector
    for sector_ticker, holdings in SECTOR_HOLDINGS.items():
        sector_name = SECTOR_NAMES.get(sector_ticker, sector_ticker)

        # Get upcoming earnings for this sector
        upcoming_earnings = get_upcoming_earnings_for_holdings(holdings, days_ahead=14)

        if not upcoming_earnings:
            continue

        catalyst_count = len(upcoming_earnings)
        confluence = confluence_map.get(sector_ticker, {})
        confluence_direction = confluence.get("direction", "neutral")
        original_conviction = confluence.get("conviction", "LOW")

        # Determine boost
        catalyst_boost = determine_catalyst_boost(catalyst_count, confluence_direction)

        # Upgrade conviction
        combined_conviction = upgrade_conviction(original_conviction, catalyst_boost)

        catalysts.append({
            "sectorTicker": sector_ticker,
            "sectorName": sector_name,
            "upcomingEarnings": upcoming_earnings,
            "catalystCount": catalyst_count,
            "confluenceBoost": catalyst_boost,
            "originalConviction": original_conviction,
            "combinedConviction": combined_conviction,
        })

    # Sort by catalyst count descending
    catalysts.sort(key=lambda x: x["catalystCount"], reverse=True)

    return catalysts


def calculate_earnings_confluence() -> Dict[str, Any]:
    """
    Main entry point: calculate earnings catalysts with confluence integration.

    Returns:
        Dict with catalysts and timestamp
    """
    try:
        # Import here to avoid circular imports
        from backend.services.confluence_engine import calculate_confluence_signals

        # Get confluence signals for context
        confluence_result = calculate_confluence_signals()
        confluence_signals = confluence_result.get("confluence_signals", [])

        # Calculate catalysts
        catalysts = calculate_earnings_catalysts(confluence_signals)

        return {
            "catalysts": catalysts,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error calculating earnings confluence: {e}")
        return {
            "catalysts": [],
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }


def get_sector_earnings_detail(sector_ticker: str) -> Dict[str, Any]:
    """
    Get detailed earnings information for a specific sector.

    Args:
        sector_ticker: Sector ETF ticker

    Returns:
        Dict with detailed earnings for all holdings
    """
    try:
        if sector_ticker not in SECTOR_HOLDINGS:
            return {"error": f"Unknown sector: {sector_ticker}"}

        holdings = SECTOR_HOLDINGS[sector_ticker]
        sector_name = SECTOR_NAMES.get(sector_ticker, sector_ticker)

        # Get earnings for all holdings (30 days ahead for detail)
        upcoming_earnings = get_upcoming_earnings_for_holdings(holdings, days_ahead=30)

        return {
            "sectorTicker": sector_ticker,
            "sectorName": sector_name,
            "holdings": holdings,
            "upcomingEarnings": upcoming_earnings,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting sector earnings detail for {sector_ticker}: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
