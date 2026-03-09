def get_morning_report_prompt(date: str) -> str:
    """Generate prompt for condensed morning market report."""
    return f"""Generate a concise morning market report for {date}. This is an auto-generated daily briefing for an institutional investor.

Write a 4-section report. Each section should be 3-5 sentences of dense, data-rich analysis. No filler, no disclaimers.

SECTIONS:

1. MARKET SNAPSHOT
   - S&P 500, Nasdaq 100, Russell 2000: prior close, overnight futures, key levels
   - VIX level and trend
   - Market breadth (advance/decline ratio if available)
   - Any overnight gaps or notable pre-market moves

2. SECTOR ROTATION
   - Top 3 and bottom 3 sectors by recent performance
   - Rotation themes: is money moving from growth → value, cyclicals → defensives, etc.?
   - Any sector-specific catalysts driving the rotation

3. MACRO PULSE
   - US Treasury yields (2Y, 10Y) and curve shape
   - Dollar index trend
   - Crude oil, gold, key commodities
   - Any economic data releases today/this week and expected impact

4. WEEK AHEAD
   - Key earnings reports this week with expected impact
   - Economic calendar highlights (FOMC, CPI, payrolls, etc.)
   - Technical levels to watch on major indices (support/resistance)
   - Any geopolitical or event risk on the horizon

FORMATTING RULES:
- Be specific with numbers: "S&P 500 closed at 5,234 (+0.3%)" not "the market rose"
- Use present tense for current state, past tense for prior session
- No hedging language ("may", "could potentially") — state your read of the data
- If you don't have exact data, use your best estimate based on recent trends and clearly note it

Return ONLY valid JSON:
{{
  "date": "{date}",
  "market_snapshot": {{
    "title": "Market Snapshot",
    "content": "..."
  }},
  "sector_rotation": {{
    "title": "Sector Rotation",
    "content": "..."
  }},
  "macro_pulse": {{
    "title": "Macro Pulse",
    "content": "..."
  }},
  "week_ahead": {{
    "title": "Week Ahead",
    "content": "..."
  }}
}}"""
