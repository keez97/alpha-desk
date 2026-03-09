def get_stock_grader_prompt(ticker: str, company_name: str, data: dict, weights: dict = None, regime: str = "neutral") -> str:
    """Generate institutional-grade equity research prompt with regime-adaptive weights."""

    fundamentals_str = "\n".join([
        f"- {k}: {v}" for k, v in data.items()
        if k not in ["name", "sector", "industry"]
    ])

    sector = data.get("sector", "Unknown")
    industry = data.get("industry", "Unknown")

    # Default weights if not provided
    if weights is None:
        weights = {
            "valuation": 0.20,
            "growth_quality": 0.12,
            "profitability": 0.18,
            "balance_sheet": 0.10,
            "earnings_quality": 0.13,
            "momentum": 0.12,
            "positioning": 0.07,
            "catalysts": 0.08,
        }

    regime_context = ""
    if regime == "risk_off":
        regime_context = (
            "REGIME CONTEXT: The market is currently in a RISK-OFF environment "
            "(elevated VIX, inverted or flat yield curve). Weight your analysis "
            "toward balance sheet resilience, earnings quality, and defensive "
            "characteristics. Be more skeptical of growth-at-any-price narratives."
        )
    elif regime == "risk_on":
        regime_context = (
            "REGIME CONTEXT: The market is currently in a RISK-ON environment "
            "(low VIX, steepening yield curve). Growth and momentum factors are "
            "being rewarded. However, maintain discipline on valuation — stretched "
            "multiples still create downside risk."
        )
    else:
        regime_context = (
            "REGIME CONTEXT: The market is in a NEUTRAL environment. "
            "Apply balanced factor weighting across all dimensions."
        )

    weights_str = "\n".join([
        f"   - {name.replace('_', ' ').title()}: {w:.0%}"
        for name, w in weights.items()
    ])

    return f"""Conduct a rigorous equity analysis of {ticker} ({company_name}) in the {industry} industry, {sector} sector.

{regime_context}

FUNDAMENTAL DATA PROVIDED:
{fundamentals_str}

DIMENSION WEIGHTS (regime-adjusted):
{weights_str}

ANALYSIS FRAMEWORK — Score each dimension 1-10. A score of 5 means sector-median.
Scores must be anchored to the data provided, not narrative conviction.

1. VALUATION (weight: {weights.get('valuation', 0.20):.0%})
   Compare P/E, EV/EBITDA, P/FCF, and P/S to:
   (a) the {sector} sector median,
   (b) the stock's own 5-year historical average where estimable.
   Score of 5 = fairly valued vs. sector. Above 5 = undervalued. Below 5 = overvalued.
   Flag if the stock is in the top or bottom decile of its sector on any multiple.

2. GROWTH QUALITY (weight: {weights.get('growth_quality', 0.12):.0%})
   Evaluate revenue growth, EPS growth, and FCF growth.
   Distinguish organic growth from acquisition-driven or one-time items.
   Penalize decelerating growth even if absolute numbers look strong.
   Reward durable, compounding growth (3+ year acceleration or consistency).

3. PROFITABILITY & MARGINS (weight: {weights.get('profitability', 0.18):.0%})
   Assess gross margin, operating margin, net margin, and ROIC.
   Compare margins to sector peers. Score margin trajectory — expanding margins
   score higher than stable ones at the same level.
   Calculate ROIC vs. estimated WACC spread. Positive spread = value creation.

4. BALANCE SHEET & CAPITAL ALLOCATION (weight: {weights.get('balance_sheet', 0.10):.0%})
   Evaluate net debt/EBITDA, interest coverage, FCF yield.
   Assess capital allocation: buyback effectiveness, dividend sustainability.
   Penalize overleveraged balance sheets even if growth is strong.

5. EARNINGS QUALITY (weight: {weights.get('earnings_quality', 0.13):.0%})
   Check cash conversion ratio (CFO / Net Income). Below 0.8 is a red flag.
   Flag high accruals, aggressive revenue recognition, unusual working capital changes.
   Reward companies where cash earnings consistently exceed reported earnings.

6. MOMENTUM & TECHNICALS (weight: {weights.get('momentum', 0.12):.0%})
   Assess price relative to 50-day and 200-day moving averages.
   Evaluate relative strength vs. sector and vs. SPY over 1M, 3M, 6M.
   Note volume trends. This is a confirming factor, not a primary driver.

7. INSTITUTIONAL POSITIONING (weight: {weights.get('positioning', 0.07):.0%})
   Evaluate short interest as % of float. Above 10% = crowded short or squeeze risk.
   Note analyst consensus and recent revision direction.
   Flag unusual insider activity if data suggests it.

8. CATALYST PIPELINE (weight: {weights.get('catalysts', 0.08):.0%})
   Identify specific, time-bound events in the next 1-6 months:
   earnings dates, product launches, FDA decisions, regulatory rulings, M&A.
   Each catalyst needs estimated probability and directional impact.
   No catalyst = no urgency = lower score.

COMPOSITE SCORE:
Calculate the weighted average of all 8 dimension scores using the weights above. Map to grade:
- 8.5-10.0 → STRONG_BUY
- 7.0-8.4  → BUY
- 5.0-6.9  → HOLD
- 3.0-4.9  → SELL
- 1.0-2.9  → STRONG_SELL

OBJECTIVITY RULES:
- Do NOT use "we recommend", "investors should", or "this is a great opportunity."
- Present data and let the score speak. The thesis reads like a research note, not a pitch.
- If the data is mixed, say so. A HOLD is a perfectly valid output.
- Acknowledge what you DON'T know — flag missing metrics as data gaps.
- If the stock is controversial, present both sides without bias beyond what the score implies.

SCENARIO ANALYSIS:
Provide three cases with probability based on the data:
- Bull: What goes right? Implied upside % from current price.
- Base: Status quo continuation. Where does the stock settle?
- Bear: What breaks? Implied downside % from current price.
Probabilities must sum to ~100%.

CONTRARIAN CHECK:
Identify at least one area where consensus may be wrong.
An overlooked risk in a popular name, or an underappreciated catalyst in a hated one.

Return ONLY valid JSON:
{{
  "ticker": "{ticker}",
  "company_name": "{company_name}",
  "sector": "{sector}",
  "regime": "{regime}",
  "composite_score": 0.0,
  "grade": "STRONG_BUY|BUY|HOLD|SELL|STRONG_SELL",
  "dimensions": [
    {{
      "name": "Valuation",
      "score": 0,
      "weight": {weights.get('valuation', 0.20)},
      "assessment": "2-3 sentences with specific numbers",
      "data_points": ["P/E: Xx vs sector Yx", "EV/EBITDA: Xx"]
    }},
    {{
      "name": "Growth Quality",
      "score": 0,
      "weight": {weights.get('growth_quality', 0.12)},
      "assessment": "",
      "data_points": []
    }},
    {{
      "name": "Profitability",
      "score": 0,
      "weight": {weights.get('profitability', 0.18)},
      "assessment": "",
      "data_points": []
    }},
    {{
      "name": "Balance Sheet",
      "score": 0,
      "weight": {weights.get('balance_sheet', 0.10)},
      "assessment": "",
      "data_points": []
    }},
    {{
      "name": "Earnings Quality",
      "score": 0,
      "weight": {weights.get('earnings_quality', 0.13)},
      "assessment": "",
      "data_points": []
    }},
    {{
      "name": "Momentum",
      "score": 0,
      "weight": {weights.get('momentum', 0.12)},
      "assessment": "",
      "data_points": []
    }},
    {{
      "name": "Positioning",
      "score": 0,
      "weight": {weights.get('positioning', 0.07)},
      "assessment": "",
      "data_points": []
    }},
    {{
      "name": "Catalysts",
      "score": 0,
      "weight": {weights.get('catalysts', 0.08)},
      "assessment": "",
      "data_points": []
    }}
  ],
  "thesis": "3-4 sentence objective summary of what the data says",
  "scenarios": {{
    "bull": {{ "target_pct": 0.0, "probability": 0.0, "drivers": [] }},
    "base": {{ "target_pct": 0.0, "probability": 0.0, "drivers": [] }},
    "bear": {{ "target_pct": 0.0, "probability": 0.0, "drivers": [] }}
  }},
  "key_risks": [],
  "catalysts": [
    {{ "event": "", "expected_date": "", "impact": "positive|negative|uncertain", "probability": 0.0 }}
  ],
  "contrarian_signal": "",
  "data_gaps": []
}}"""
