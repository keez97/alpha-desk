# AlphaDesk — Analyst Prompt Templates

## Version History
| Version | Date | Change |
|---------|------|--------|
| v1.0 | 2026-03-09 | Initial prompt set |

## BASE_ANALYST_PERSONA (System Prompt — All Calls)
```
You are a data-driven equity analyst. Provide structured analysis using only verifiable market data, price action, macro indicators, earnings results, and reputable institutional sources. Avoid speculation. Social sentiment is allowed only as a minor, secondary signal. All claims must be traceable to observable data. Format all output for a sophisticated institutional investor who values precision and evidence over narrative.
```

## PROMPT_MORNING_DRIVERS_V1
**Feature:** Morning Brief — 5 Market Drivers
**Tools:** web_search
**Streaming:** No

```
Identify the 5 most significant market-moving factors active in US equity markets today ({date}).

For each driver, provide:
1. A bold headline (max 12 words)
2. A 2-3 sentence data-grounded explanation citing specific numbers, percentages, or data points
3. 2-3 source URLs you found during your research

Return ONLY valid JSON with no markdown fencing:
{{
  "drivers": [
    {{
      "headline": "string (max 12 words)",
      "explanation": "string (2-3 sentences with data)",
      "sources": [{{"title": "string", "url": "string"}}]
    }}
  ]
}}
```

## PROMPT_STOCK_GRADE_V1
**Feature:** Stock Screener — AI Stock Grader
**Tools:** None (data pre-fetched and injected)
**Streaming:** No

```
Grade {ticker} ({company_name}) across the following metrics using the data provided below.

=== MARKET DATA ===
{pre_fetched_data_json}

For each metric, assign a letter grade (A/B/C/D/F) where:
- A = Top quintile / exceptional
- B = Above average
- C = Average / neutral
- D = Below average / concern
- F = Bottom quintile / significant risk

Metrics to grade:
1. Sector rotation positioning
2. Distance from 52-week low (% above low)
3. Forward P/E vs sector median
4. Net debt / EBITDA
5. Revenue growth (YoY)
6. Operating margin vs peers
7. Beta
8. Max drawdown (1Y)
9. 30-day realised volatility
10. Average daily volume vs 90-day avg
11. Institutional ownership %
12. Short interest %
13. FCF yield
14. PEG ratio

Return ONLY valid JSON with no markdown fencing:
{{
  "ticker": "{ticker}",
  "grades": {{
    "metric_name": {{
      "score": "A|B|C|D|F",
      "value": "the actual metric value as string",
      "rationale": "one sentence explanation"
    }}
  }},
  "overall_grade": "A|B|C|D|F",
  "summary": "2-3 sentence overall assessment",
  "risks": ["risk 1", "risk 2", "risk 3"],
  "catalysts": ["catalyst 1", "catalyst 2"]
}}
```

## PROMPT_WEEKLY_REPORT_V1
**Feature:** Weekly Market Report
**Tools:** web_search
**Streaming:** Yes (SSE)

```
Generate a comprehensive weekly market report for the week ending {end_date}.

You MUST search the web for current market data, news, and analysis to inform each section.

Structure your response as valid JSON matching this exact schema. Return ONLY valid JSON with no markdown fencing.

{{
  "value_opportunities": {{
    "stocks": [
      {{
        "ticker": "string",
        "company_name": "string",
        "sector": "string",
        "market_cap": "string",
        "current_price": 0,
        "pct_from_52w_low": 0,
        "forward_pe": 0,
        "peg_ratio": 0,
        "fcf_yield": 0,
        "ttm_revenue": "string",
        "eps_trend": "string",
        "debt_ebitda": 0,
        "current_ratio": 0,
        "thesis": "string (3-4 sentences, data-backed)",
        "risks": ["string"]
      }}
    ]
  }},
  "momentum_leaders": {{
    "stocks": [
      {{
        "ticker": "string",
        "company_name": "string",
        "sector": "string",
        "perf_1w": 0,
        "perf_1m": 0,
        "perf_3m": 0,
        "rs_vs_sector": 0,
        "rs_vs_sp500": 0,
        "volume_ratio": 0,
        "new_high_weekly": false,
        "new_high_monthly": false,
        "catalyst": "string"
      }}
    ]
  }},
  "macro_trends": {{
    "indices": [{{"name": "string", "ticker": "string", "weekly_return": 0, "ytd_return": 0}}],
    "rates": {{"us_2y": "string", "us_10y": "string", "us_30y": "string", "fed_funds_expectation": "string"}},
    "data_prints": ["string"],
    "sector_rotation": "string",
    "liquidity": "string",
    "geopolitical": "string"
  }},
  "risks_catalysts": {{
    "upcoming_events": [{{"date": "string", "event": "string", "prior": "string", "consensus": "string"}}],
    "earnings_next_week": [{{"ticker": "string", "expected_eps": "string", "expected_revenue": "string", "implied_move": "string"}}],
    "vix_analysis": "string",
    "market_breadth": "string",
    "bond_equity_correlation": "string",
    "credit_signals": "string"
  }},
  "sentiment": {{
    "institutional_commentary": "string",
    "earnings_call_tone": "string",
    "overall_verdict": "Bullish|Neutral|Bearish",
    "reasons": ["string"]
  }},
  "executive_summary": {{
    "direction": "string",
    "top_opportunities": ["string"],
    "top_risks": ["string"],
    "spx_1w_bias": "string",
    "spx_1m_bias": "string"
  }}
}}
```

## PROMPT_SCREENER_V1
**Feature:** AI Screener (Proactive)
**Tools:** web_search
**Streaming:** No

```
Screen the US equity market for the top investment opportunities right now ({date}).

Search for current market data and identify:

1. Top 5 Value Opportunities — stocks that appear undervalued based on:
   - Low forward P/E relative to sector and growth
   - Strong FCF yield
   - Reasonable debt levels
   - Positive revenue/earnings trajectory
   - Clear catalyst for re-rating

2. Top 5 Momentum Leaders — stocks showing strong technical momentum:
   - Strong 1W, 1M, 3M price performance
   - Outperforming sector and S&P 500
   - Rising volume trends
   - Recent new highs
   - Identifiable catalyst

Return ONLY valid JSON with no markdown fencing, matching this schema:
{{
  "value_opportunities": [
    {{
      "ticker": "string",
      "company_name": "string",
      "sector": "string",
      "market_cap": "string",
      "current_price": 0,
      "pct_from_52w_low": 0,
      "forward_pe": 0,
      "peg_ratio": 0,
      "fcf_yield": 0,
      "ttm_revenue": "string",
      "eps_trend": "string",
      "debt_ebitda": 0,
      "current_ratio": 0,
      "thesis": "string",
      "risks": ["string"]
    }}
  ],
  "momentum_leaders": [
    {{
      "ticker": "string",
      "company_name": "string",
      "sector": "string",
      "perf_1w": 0,
      "perf_1m": 0,
      "perf_3m": 0,
      "rs_vs_sector": 0,
      "rs_vs_sp500": 0,
      "volume_ratio": 0,
      "new_high_weekly": false,
      "new_high_monthly": false,
      "catalyst": "string"
    }}
  ]
}}
```
