def get_morning_drivers_prompt(date: str) -> str:
    """Generate prompt for morning market drivers analysis."""
    return f"""Today is {date}. Identify the 5 most impactful market drivers for today and the coming week.

For each driver, provide:
1. Title
2. Impact (positive/negative/neutral)
3. Affected assets (stocks, sectors, indices)
4. Key data points
5. Expected market implications

Search for:
- Overnight economic data releases
- Fed speakers and policy updates
- Earnings surprises
- Geopolitical events
- Technical breakouts/breakdowns
- Sector rotation signals

Return ONLY a valid JSON object with this exact structure:
{{
  "date": "{date}",
  "drivers": [
    {{
      "title": "string",
      "impact": "positive|negative|neutral",
      "affected_assets": ["string"],
      "key_data": "string",
      "market_implications": "string"
    }}
  ]
}}"""
