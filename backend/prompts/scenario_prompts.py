"""
Prompt generators for Claude-powered stress scenario generation and drill-down.
"""


def get_scenario_generation_prompt(macro_snapshot: dict) -> str:
    """
    Build a prompt for Claude to generate 3 stress scenarios based on current macro data.

    Returns exactly 3 scenarios with calibrated probability distributions.
    """
    # Extract macro data points
    vix = macro_snapshot.get("^VIX", {}).get("price", 20.0)
    spy = macro_snapshot.get("SPY", {}).get("price", 450.0)
    qqq = macro_snapshot.get("QQQ", {}).get("price", 350.0)
    tnx = macro_snapshot.get("^TNX", {}).get("price", 4.5)
    irx = macro_snapshot.get("^IRX", {}).get("price", 5.0)
    dxy = macro_snapshot.get("DXY", {}).get("price", 107.0)
    oil = macro_snapshot.get("CL=F", {}).get("price", 80.0)
    gold = macro_snapshot.get("GC=F", {}).get("price", 2050.0)
    btc = macro_snapshot.get("BTC-USD", {}).get("price", 65000.0)

    # Determine current regime
    if vix > 25:
        current_regime = "bear"
    elif vix < 15:
        current_regime = "bull"
    else:
        current_regime = "neutral"

    # Format macro data for prompt
    macro_formatted = f"""Current Market Data:
- VIX (Volatility Index): {vix:.2f}
- SPY (S&P 500): ${spy:.2f}
- QQQ (Nasdaq-100): ${qqq:.2f}
- TNX (10-Year Yield): {tnx:.2f}%
- IRX (3-Month Yield): {irx:.2f}%
- DXY (Dollar Index): {dxy:.2f}
- Oil (WTI Crude): ${oil:.2f}
- Gold (Spot): ${gold:.2f}
- BTC (Bitcoin): ${btc:.2f}
- Current Regime: {current_regime.upper()}
- Yield Curve Spread (10Y-3M): {tnx - irx:.2f}%"""

    prompt = f"""{macro_formatted}

Based on current market conditions, generate exactly 3 stress test scenarios that represent meaningful market dislocations. Each scenario should:

1. Be plausible given current regime and macro backdrop
2. Have calibrated probability (most scenarios 5-20%, tail risks under 5%)
3. Represent different risk vectors (geopolitical, policy, growth, volatility, etc.)
4. Include specific market impacts and transmission mechanisms

Return ONLY a valid JSON array with exactly 3 objects. Each object must have these fields:
- name: short scenario label (e.g., "Fed Policy Shock")
- description: 1-2 sentence description of what triggers the scenario
- probability: float 0.0-1.0 (calibrated: most scenarios 5-20%, tail risks under 5%)
- probability_reasoning: brief 1-sentence explanation for the probability
- estimated_impact_pct: negative number -1 to -30 (portfolio impact percentage)
- severity: "mild" (< -5%), "moderate" (-5% to -15%), or "severe" (< -15%)
- affected_sectors: list of 3-5 sector names that are most impacted
- historical_analog: real historical event with date (e.g., "2018 Q4 Volatility Spike" or "March 2020 COVID Crash")
- key_indicators: list of 2-3 specific data points to watch if this scenario unfolds

CRITICAL: Return ONLY valid JSON array. No markdown, no code fences, no commentary. Start with [ and end with ]."""

    return prompt


def get_scenario_drilldown_prompt(scenario: dict, macro_snapshot: dict) -> str:
    """
    Build a prompt for detailed drill-down analysis of a specific scenario.

    Returns analysis with transmission mechanism, precedent, hedging ideas, etc.
    """
    vix = macro_snapshot.get("^VIX", {}).get("price", 20.0)
    spy = macro_snapshot.get("SPY", {}).get("price", 450.0)
    tnx = macro_snapshot.get("^TNX", {}).get("price", 4.5)

    scenario_name = scenario.get("name", "Stress Scenario")
    scenario_desc = scenario.get("description", "")
    impact = scenario.get("estimated_impact_pct", -5)

    prompt = f"""You are a senior macro strategist analyzing a stress scenario for a hedge fund portfolio.

Current Market Context:
- VIX: {vix:.1f}
- S&P 500: ${spy:.0f}
- 10Y Yield: {tnx:.2f}%

Scenario to Analyze:
- Name: {scenario_name}
- Description: {scenario_desc}
- Estimated Portfolio Impact: {impact}%

Provide a detailed drill-down analysis in JSON format with exactly these 5 fields:

1. "transmission_mechanism": Step-by-step explanation (3-4 sentences) of HOW this scenario would unfold in markets. What's the causal chain from trigger to portfolio impact?

2. "historical_precedent": 2-3 sentence analysis of what happened during a similar historical event. What were the key market moves and timeline?

3. "portfolio_positioning": 3-4 bullet points of specific defensive hedge suggestions:
   - Specific hedges (e.g., "Long put spreads on SPY", "Long duration", "Volatility shorts reduce")
   - Sector tilts and positioning adjustments
   - Macro positioning changes

4. "leading_indicators": 3-4 bullet points of daily/weekly indicators to monitor:
   - Specific market signals that would confirm scenario is unfolding
   - Data points that are early warning signs
   - Technical levels or volatility thresholds to watch

5. "counter_argument": 1-2 sentence explanation of why this scenario might NOT happen or why market is pricing it incorrectly.

Return ONLY valid JSON object with those 5 fields. No markdown, no code fences, no commentary."""

    return prompt
