import json
import logging
from typing import Dict, Any, AsyncGenerator
from anthropic import Anthropic
from backend.config import CLAUDE_MODEL, ANTHROPIC_API_KEY
from backend.prompts.base import BASE_ANALYST_PERSONA
from backend.prompts import morning_drivers, stock_grader, weekly_report, screener
from backend.services import mock_data
from datetime import datetime

logger = logging.getLogger(__name__)

# Check if API key is available
USE_MOCK = not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY.strip() == ""

if not USE_MOCK:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    client = None
    logger.info("Running Claude service in mock mode - no API key provided")

BASE_SYSTEM_PROMPT = BASE_ANALYST_PERSONA


async def generate_morning_drivers(date: str) -> Dict[str, Any]:
    """Generate 5 market drivers for the given date using web search."""
    if USE_MOCK:
        logger.info("Using mock morning drivers")
        result = mock_data.MOCK_MORNING_DRIVERS.copy()
        result["date"] = date
        return result

    try:
        prompt = morning_drivers.get_morning_drivers_prompt(date)

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            system=BASE_SYSTEM_PROMPT,
            tools=[{
                "name": "web_search",
                "description": "Search the web for current market news and data",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        }
                    },
                    "required": ["query"]
                }
            }],
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract text from response
        text_content = ""
        for block in response.content:
            if hasattr(block, "text"):
                text_content += block.text

        # Parse JSON from response
        try:
            json_start = text_content.find("{")
            json_end = text_content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = text_content[json_start:json_end]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing morning drivers JSON: {e}")
            return {
                "date": date,
                "drivers": [],
                "error": "Failed to parse response"
            }

        return {
            "date": date,
            "drivers": [],
            "raw_response": text_content
        }
    except Exception as e:
        logger.error(f"Error generating morning drivers: {e}")
        return {
            "date": date,
            "drivers": [],
            "error": str(e)
        }


async def grade_stock(ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Grade a stock based on pre-fetched fundamental data."""
    if USE_MOCK:
        logger.info(f"Using mock grade for stock: {ticker}")
        if ticker in mock_data.MOCK_STOCK_GRADES:
            return mock_data.MOCK_STOCK_GRADES[ticker]
        # Return a generic hold if not in mock data
        return {
            "ticker": ticker,
            "name": data.get("name", ticker),
            "grade": "HOLD",
            "overall_score": 6.5,
            "metrics": {},
            "recommendation": "Insufficient mock data available"
        }

    try:
        company_name = data.get("name", ticker)
        prompt = stock_grader.get_stock_grader_prompt(ticker, company_name, data)

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            system=BASE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        text_content = ""
        for block in response.content:
            if hasattr(block, "text"):
                text_content += block.text

        try:
            json_start = text_content.find("{")
            json_end = text_content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = text_content[json_start:json_end]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing stock grade JSON: {e}")
            return {
                "ticker": ticker,
                "grade": "HOLD",
                "error": "Failed to parse response"
            }

        return {
            "ticker": ticker,
            "grade": "HOLD",
            "raw_response": text_content
        }
    except Exception as e:
        logger.error(f"Error grading stock {ticker}: {e}")
        return {
            "ticker": ticker,
            "grade": "HOLD",
            "error": str(e)
        }


async def generate_weekly_report(end_date: str) -> AsyncGenerator[str, None]:
    """Generate weekly report with streaming response."""
    if USE_MOCK:
        logger.info("Using mock weekly report")
        # Yield mock report as JSON
        report = mock_data.MOCK_WEEKLY_REPORT.copy()
        yield json.dumps(report)
        return

    try:
        prompt = weekly_report.get_weekly_report_prompt(end_date)

        with client.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=4000,
            system=BASE_SYSTEM_PROMPT,
            tools=[{
                "name": "web_search",
                "description": "Search the web for market data and news",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        }
                    },
                    "required": ["query"]
                }
            }],
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                yield text
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        yield json.dumps({
            "error": str(e),
            "sections": []
        })


async def run_screener(date: str) -> Dict[str, Any]:
    """Run stock screener with web search."""
    if USE_MOCK:
        logger.info("Using mock screener results")
        result = mock_data.MOCK_SCREENER_RESULTS.copy()
        result["date"] = date
        return result

    try:
        prompt = screener.get_screener_prompt(date)

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=3000,
            system=BASE_SYSTEM_PROMPT,
            tools=[{
                "name": "web_search",
                "description": "Search the web for market data and stock screening results",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        }
                    },
                    "required": ["query"]
                }
            }],
            messages=[{"role": "user", "content": prompt}]
        )

        text_content = ""
        for block in response.content:
            if hasattr(block, "text"):
                text_content += block.text

        try:
            json_start = text_content.find("{")
            json_end = text_content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = text_content[json_start:json_end]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing screener JSON: {e}")
            return {
                "date": date,
                "results": [],
                "error": "Failed to parse response"
            }

        return {
            "date": date,
            "results": [],
            "raw_response": text_content
        }
    except Exception as e:
        logger.error(f"Error running screener: {e}")
        return {
            "date": date,
            "results": [],
            "error": str(e)
        }
