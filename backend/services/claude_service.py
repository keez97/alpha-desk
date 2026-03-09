import json
import logging
from typing import Dict, Any, AsyncGenerator
from openai import OpenAI
from backend.config import (
    OPENROUTER_API_KEY,
    get_openrouter_model_id,
)
from backend.prompts.base import BASE_ANALYST_PERSONA
from backend.prompts import morning_drivers, stock_grader, weekly_report, screener
from backend.services import mock_data
from datetime import datetime

logger = logging.getLogger(__name__)

# Check if API key is available
USE_MOCK = not OPENROUTER_API_KEY or OPENROUTER_API_KEY.strip() == ""

if not USE_MOCK:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
else:
    client = None
    logger.info("Running LLM service in mock mode - no API key provided")

BASE_SYSTEM_PROMPT = BASE_ANALYST_PERSONA


def _extract_text(response) -> str:
    """Extract text content from an OpenAI-style response."""
    if response.choices and response.choices[0].message.content:
        return response.choices[0].message.content
    return ""


def _parse_json_from_text(text: str) -> dict | None:
    """Try to extract a JSON object from text."""
    try:
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = text[json_start:json_end]
            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass
    return None


async def generate_morning_drivers(date: str) -> Dict[str, Any]:
    """Generate 5 market drivers for the given date."""
    if USE_MOCK:
        logger.info("Using mock morning drivers")
        result = mock_data.MOCK_MORNING_DRIVERS.copy()
        result["date"] = date
        return result

    try:
        prompt = morning_drivers.get_morning_drivers_prompt(date)
        model_id = get_openrouter_model_id()
        logger.info(f"Generating morning drivers with model: {model_id}")

        response = client.chat.completions.create(
            model=model_id,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": BASE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        text_content = _extract_text(response)
        parsed = _parse_json_from_text(text_content)
        if parsed:
            return parsed

        return {
            "date": date,
            "drivers": [],
            "raw_response": text_content,
        }

    except Exception as e:
        logger.error(f"Error generating morning drivers: {e}")
        return {"date": date, "drivers": [], "error": str(e)}


async def grade_stock(ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Grade a stock based on pre-fetched fundamental data."""
    if USE_MOCK:
        logger.info(f"Using mock grade for stock: {ticker}")
        if ticker in mock_data.MOCK_STOCK_GRADES:
            return mock_data.MOCK_STOCK_GRADES[ticker]
        return {
            "ticker": ticker,
            "name": data.get("name", ticker),
            "grade": "HOLD",
            "overall_score": 6.5,
            "metrics": {},
            "recommendation": "Insufficient mock data available",
        }

    try:
        company_name = data.get("name", ticker)
        prompt = stock_grader.get_stock_grader_prompt(ticker, company_name, data)
        model_id = get_openrouter_model_id()
        logger.info(f"Grading {ticker} with model: {model_id}")

        response = client.chat.completions.create(
            model=model_id,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": BASE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        text_content = _extract_text(response)
        parsed = _parse_json_from_text(text_content)
        if parsed:
            return parsed

        return {"ticker": ticker, "grade": "HOLD", "raw_response": text_content}

    except Exception as e:
        logger.error(f"Error grading stock {ticker}: {e}")
        return {"ticker": ticker, "grade": "HOLD", "error": str(e)}


async def generate_weekly_report(end_date: str) -> AsyncGenerator[str, None]:
    """Generate weekly report with streaming response."""
    if USE_MOCK:
        logger.info("Using mock weekly report")
        report = mock_data.MOCK_WEEKLY_REPORT.copy()
        yield json.dumps(report)
        return

    try:
        prompt = weekly_report.get_weekly_report_prompt(end_date)
        model_id = get_openrouter_model_id()
        logger.info(f"Generating weekly report with model: {model_id}")

        stream = client.chat.completions.create(
            model=model_id,
            max_tokens=4000,
            stream=True,
            messages=[
                {"role": "system", "content": BASE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        yield json.dumps({"error": str(e), "sections": []})


async def run_screener(date: str) -> Dict[str, Any]:
    """Run stock screener."""
    if USE_MOCK:
        logger.info("Using mock screener results")
        result = mock_data.MOCK_SCREENER_RESULTS.copy()
        result["date"] = date
        return result

    try:
        prompt = screener.get_screener_prompt(date)
        model_id = get_openrouter_model_id()
        logger.info(f"Running screener with model: {model_id}")

        response = client.chat.completions.create(
            model=model_id,
            max_tokens=3000,
            messages=[
                {"role": "system", "content": BASE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        text_content = _extract_text(response)
        parsed = _parse_json_from_text(text_content)
        if parsed:
            return parsed

        return {"date": date, "results": [], "raw_response": text_content}

    except Exception as e:
        logger.error(f"Error running screener: {e}")
        return {"date": date, "results": [], "error": str(e)}
