def get_weekly_report_prompt(end_date: str) -> str:
    """Generate prompt for weekly market report generation."""
    return f"""Generate a comprehensive weekly market report as of {end_date}.

Include these sections:
1. Market Overview (SPY, QQQ, IWM performance, breadth metrics)
2. Sector Performance (ranked by weekly return, rotation signals)
3. Macro Indicators (VIX, 10Y yield, Dollar, Commodities)
4. Economic Calendar (key data from the past week)
5. Technical Analysis (key support/resistance levels, trend changes)
6. Earnings Highlights (major earnings beats/misses)
7. Geopolitical Events (if material to markets)
8. Outlook & Positioning (for the coming week)

Use web search to get current data. All claims must be backed by specific data points.

Return ONLY a valid JSON object with this exact structure:
{{
  "end_date": "{end_date}",
  "market_overview": {{
    "spy_return": "string",
    "qqq_return": "string",
    "iwm_return": "string",
    "market_breadth": "string",
    "summary": "string"
  }},
  "sector_performance": [
    {{
      "sector": "string",
      "return": "string",
      "signal": "string"
    }}
  ],
  "macro_indicators": {{
    "vix": "string",
    "yield_10y": "string",
    "dollar": "string",
    "commodities": "string"
  }},
  "earnings_highlights": ["string"],
  "technical_analysis": "string",
  "outlook": "string"
}}"""
