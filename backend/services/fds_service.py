import httpx
import logging
from typing import Dict, List, Any, Optional
from backend.config import FDS_API_KEY

logger = logging.getLogger(__name__)

BASE_URL = "https://api.financialdatasets.ai"


async def get_income_statements(ticker: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Fetch income statements for a ticker."""
    try:
        async with httpx.AsyncClient() as client:
            url = f"{BASE_URL}/financials"
            headers = {"X-API-KEY": FDS_API_KEY}
            params = {
                "ticker": ticker,
                "statement": "income",
                "limit": limit,
            }

            response = await client.get(url, headers=headers, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return data.get("data", []) if isinstance(data, dict) else []
    except Exception as e:
        logger.error(f"Error fetching income statements for {ticker}: {e}")
        # Return empty but valid structure
        logger.info(f"Returning empty income statements for {ticker} due to network error")
        return []


async def get_balance_sheets(ticker: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Fetch balance sheets for a ticker."""
    try:
        async with httpx.AsyncClient() as client:
            url = f"{BASE_URL}/financials"
            headers = {"X-API-KEY": FDS_API_KEY}
            params = {
                "ticker": ticker,
                "statement": "balance",
                "limit": limit,
            }

            response = await client.get(url, headers=headers, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return data.get("data", []) if isinstance(data, dict) else []
    except Exception as e:
        logger.error(f"Error fetching balance sheets for {ticker}: {e}")
        # Return empty but valid structure
        logger.info(f"Returning empty balance sheets for {ticker} due to network error")
        return []


async def get_cash_flow_statements(ticker: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Fetch cash flow statements for a ticker."""
    try:
        async with httpx.AsyncClient() as client:
            url = f"{BASE_URL}/financials"
            headers = {"X-API-KEY": FDS_API_KEY}
            params = {
                "ticker": ticker,
                "statement": "cash_flow",
                "limit": limit,
            }

            response = await client.get(url, headers=headers, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return data.get("data", []) if isinstance(data, dict) else []
    except Exception as e:
        logger.error(f"Error fetching cash flow statements for {ticker}: {e}")
        # Return empty but valid structure
        logger.info(f"Returning empty cash flow statements for {ticker} due to network error")
        return []
