def get_stock_grader_prompt(ticker: str, company_name: str, data: dict) -> str:
    """Generate prompt for stock grading analysis."""
    fundamentals_str = "\n".join([
        f"- {k}: {v}" for k, v in data.items() if k not in ["name", "sector", "industry"]
    ])

    return f"""Grade the stock {ticker} ({company_name}) based on the following fundamental data:

{fundamentals_str}

Evaluate:
1. Valuation (PE, PEG, Price-to-Sales, Price-to-Book)
2. Growth (EPS growth, revenue growth, FCF growth)
3. Financial Health (debt ratio, current ratio, cash flow)
4. Quality (margins, ROE, asset turnover)
5. Momentum (price action vs moving averages, recent performance)

Assign a grade: BUY, STRONG_BUY, HOLD, SELL, STRONG_SELL

Return ONLY a valid JSON object with this exact structure:
{{
  "ticker": "{ticker}",
  "company_name": "{company_name}",
  "grade": "BUY|STRONG_BUY|HOLD|SELL|STRONG_SELL",
  "valuation_score": 0-10,
  "growth_score": 0-10,
  "quality_score": 0-10,
  "momentum_score": 0-10,
  "thesis": "string - 2-3 sentences explaining the grade",
  "key_risks": ["string"],
  "catalysts": ["string"]
}}"""
