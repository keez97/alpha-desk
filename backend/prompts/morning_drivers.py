def get_morning_drivers_prompt(date: str, macro: dict = None, sectors: list = None) -> str:
    """Generate prompt for morning market drivers analysis with real data context."""
    # Build data context from real market data
    data_context = ""
    if macro:
        lines = []
        vix = macro.get("^VIX", {})
        if vix.get("price"):
            lines.append(f"VIX: {vix['price']:.1f} ({vix.get('pct_change', 0):+.2f}%)")
        tnx = macro.get("^TNX", {})
        if tnx.get("price"):
            lines.append(f"10Y Yield: {tnx['price']:.2f}% ({tnx.get('pct_change', 0):+.2f}%)")
        irx = macro.get("^IRX", {})
        if irx.get("price"):
            lines.append(f"3M Yield: {irx['price']:.2f}%")
        dxy = macro.get("DX-Y.NYB", {})
        if dxy.get("price"):
            lines.append(f"Dollar Index: {dxy['price']:.2f} ({dxy.get('pct_change', 0):+.2f}%)")
        cl = macro.get("CL=F", {})
        if cl.get("price"):
            lines.append(f"Crude Oil: ${cl['price']:.2f} ({cl.get('pct_change', 0):+.2f}%)")
        spy = macro.get("SPY", {})
        if spy.get("price"):
            lines.append(f"S&P 500: ${spy['price']:.2f} ({spy.get('pct_change', 0):+.2f}%)")

        if lines:
            data_context += "CURRENT MARKET DATA:\n" + "\n".join(lines) + "\n\n"

    if sectors:
        sector_lines = []
        sorted_s = sorted(sectors, key=lambda s: abs(s.get("daily_pct_change", 0) or s.get("pct_change", 0) or 0), reverse=True)
        for s in sorted_s[:5]:
            pct = s.get("daily_pct_change", 0) or s.get("pct_change", 0) or 0
            ticker = s.get("ticker", "")
            name = s.get("sector", s.get("name", ticker))
            sector_lines.append(f"  {ticker} ({name}): {pct:+.2f}%")
        if sector_lines:
            data_context += "TOP SECTOR MOVES:\n" + "\n".join(sector_lines) + "\n\n"

    return f"""Today is {date}. Using the market data below, identify the 5 most impactful market drivers for today.

{data_context}Based on this data, analyze:
- Which moves are most significant and why
- Volatility regime and what it implies for positioning
- Yield curve dynamics and rate expectations
- Commodity/energy signals
- Sector rotation patterns

For each driver, explain the data-driven rationale and actionable positioning implications.

Return ONLY a valid JSON object with this exact structure:
{{
  "date": "{date}",
  "drivers": [
    {{
      "title": "string - concise driver name",
      "impact": "positive|negative|neutral",
      "affected_assets": ["ticker1", "ticker2"],
      "key_data": "string - key numbers and what they signal",
      "market_implications": "string - 2-3 sentences on positioning implications"
    }}
  ]
}}"""
