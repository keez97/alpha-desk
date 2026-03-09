def get_screener_prompt(date: str) -> str:
    """Generate prompt for stock screener analysis."""
    return f"""Run a stock screener as of {date} to identify the most compelling investment opportunities.

Screen for:
1. Momentum Breakouts (stocks breaking above 200-day moving average)
2. Value Opportunities (low PE with positive earnings growth)
3. Sector Rotation Plays (emerging leaders in rotating sectors)
4. Earnings Surprises (recent positive beats with upside revision)
5. Technical Setup (bullish consolidation patterns, volume confirmation)

For each stock found:
- Ticker and name
- Current price
- Key catalyst
- Risk/reward
- Entry strategy

Use web search to find current market data and screens. Must identify at least 3-5 stocks.

Return ONLY a valid JSON object with this exact structure:
{{
  "date": "{date}",
  "screens": [
    {{
      "name": "string",
      "description": "string",
      "stocks": [
        {{
          "ticker": "string",
          "name": "string",
          "price": "string",
          "catalyst": "string",
          "risk_reward": "string",
          "entry": "string"
        }}
      ]
    }}
  ],
  "summary": "string"
}}"""
