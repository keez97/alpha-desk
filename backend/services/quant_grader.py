"""
Quantitative Stock Grading Engine.
Grades stocks using real market data — momentum, value, quality, volatility factors.
No LLM dependency.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def grade_stock_quantitative(ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Grade a stock using quantitative factors from real data.

    Uses the `data` dict which comes from the frontend/yfinance with fields like:
    - name, sector, price, marketCap
    - pe_ratio, pb_ratio, dividend_yield
    - fiftyDayAverage, twoHundredDayAverage
    - beta, trailingEps

    Returns a grade dict matching the existing claude_service format.
    """
    from backend.services.data_provider import get_history, get_quote

    company_name = data.get("name", ticker)
    sector = data.get("sector", "Unknown")
    price = data.get("price") or data.get("regularMarketPrice", 0)

    # Try to get real quote data if not provided
    if not price:
        try:
            quote = get_quote(ticker)
            price = quote.get("price", 0)
        except Exception:
            price = 0

    # Extract fundamental data
    pe_ratio = data.get("pe_ratio") or data.get("trailingPE") or data.get("forwardPE")
    pb_ratio = data.get("pb_ratio") or data.get("priceToBook")
    dividend_yield = data.get("dividend_yield") or data.get("dividendYield", 0) or 0
    market_cap = data.get("marketCap", 0)
    beta = data.get("beta", 1.0) or 1.0
    fifty_day_ma = data.get("fiftyDayAverage", 0)
    two_hundred_day_ma = data.get("twoHundredDayAverage", 0)
    trailing_eps = data.get("trailingEps", 0)
    profit_margin = data.get("profitMargins", 0) or 0
    revenue_growth = data.get("revenueGrowth", 0) or 0
    roe = data.get("returnOnEquity", 0) or 0
    debt_to_equity = data.get("debtToEquity", 0) or 0

    # Calculate momentum from price history
    momentum_score = 6  # default neutral
    price_vs_50d = 0
    price_vs_200d = 0

    if price and fifty_day_ma and fifty_day_ma > 0:
        price_vs_50d = ((price - fifty_day_ma) / fifty_day_ma) * 100
    if price and two_hundred_day_ma and two_hundred_day_ma > 0:
        price_vs_200d = ((price - two_hundred_day_ma) / two_hundred_day_ma) * 100

    # Momentum scoring
    if price_vs_50d > 5 and price_vs_200d > 10:
        momentum_score = 9
    elif price_vs_50d > 2 and price_vs_200d > 5:
        momentum_score = 8
    elif price_vs_50d > 0 and price_vs_200d > 0:
        momentum_score = 7
    elif price_vs_50d < -5 and price_vs_200d < -10:
        momentum_score = 3
    elif price_vs_50d < -2 and price_vs_200d < -5:
        momentum_score = 4
    elif price_vs_50d < 0:
        momentum_score = 5

    # Valuation scoring
    valuation_score = 6
    val_data_points = []
    if pe_ratio and pe_ratio > 0:
        val_data_points.append(f"P/E: {pe_ratio:.1f}x")
        if pe_ratio < 12:
            valuation_score = 9
        elif pe_ratio < 18:
            valuation_score = 8
        elif pe_ratio < 25:
            valuation_score = 7
        elif pe_ratio < 35:
            valuation_score = 5
        elif pe_ratio < 50:
            valuation_score = 4
        else:
            valuation_score = 3
    if pb_ratio and pb_ratio > 0:
        val_data_points.append(f"P/B: {pb_ratio:.1f}x")
    if dividend_yield and dividend_yield > 0:
        div_pct = dividend_yield * 100 if dividend_yield < 1 else dividend_yield
        val_data_points.append(f"Div yield: {div_pct:.2f}%")
    if not val_data_points:
        val_data_points = ["Fundamental data limited"]

    # Growth scoring
    growth_score = 6
    growth_data = []
    if revenue_growth:
        rg_pct = revenue_growth * 100 if abs(revenue_growth) < 1 else revenue_growth
        growth_data.append(f"Revenue growth: {rg_pct:.1f}%")
        if rg_pct > 25:
            growth_score = 9
        elif rg_pct > 15:
            growth_score = 8
        elif rg_pct > 5:
            growth_score = 7
        elif rg_pct > 0:
            growth_score = 6
        elif rg_pct > -5:
            growth_score = 5
        else:
            growth_score = 4
    if trailing_eps:
        growth_data.append(f"EPS: ${trailing_eps:.2f}")
    if not growth_data:
        growth_data = ["Growth data limited"]

    # Profitability scoring
    profitability_score = 6
    prof_data = []
    if profit_margin:
        pm_pct = profit_margin * 100 if abs(profit_margin) < 1 else profit_margin
        prof_data.append(f"Profit margin: {pm_pct:.1f}%")
        if pm_pct > 25:
            profitability_score = 9
        elif pm_pct > 15:
            profitability_score = 8
        elif pm_pct > 8:
            profitability_score = 7
        elif pm_pct > 0:
            profitability_score = 5
        else:
            profitability_score = 3
    if roe:
        roe_pct = roe * 100 if abs(roe) < 1 else roe
        prof_data.append(f"ROE: {roe_pct:.1f}%")
    if not prof_data:
        prof_data = ["Profitability data limited"]

    # Balance sheet scoring
    balance_score = 6
    balance_data = []
    if debt_to_equity:
        balance_data.append(f"D/E: {debt_to_equity:.1f}")
        if debt_to_equity < 30:
            balance_score = 9
        elif debt_to_equity < 80:
            balance_score = 8
        elif debt_to_equity < 150:
            balance_score = 6
        elif debt_to_equity < 250:
            balance_score = 4
        else:
            balance_score = 3
    if not balance_data:
        balance_data = ["Balance sheet data limited"]

    # Volatility scoring (lower beta = higher score for quality-oriented scoring)
    volatility_score = 6
    vol_data = [f"Beta: {beta:.2f}"]
    if beta < 0.7:
        volatility_score = 9
    elif beta < 0.9:
        volatility_score = 8
    elif beta < 1.1:
        volatility_score = 7
    elif beta < 1.3:
        volatility_score = 5
    else:
        volatility_score = 4

    # Composite score (weighted)
    weights = {
        "Valuation": 0.20,
        "Growth Quality": 0.12,
        "Profitability": 0.18,
        "Balance Sheet": 0.10,
        "Momentum": 0.15,
        "Volatility": 0.10,
        "Positioning": 0.07,
        "Catalysts": 0.08,
    }

    positioning_score = 6  # neutral default
    catalyst_score = 5  # limited info default

    scores = {
        "Valuation": valuation_score,
        "Growth Quality": growth_score,
        "Profitability": profitability_score,
        "Balance Sheet": balance_score,
        "Momentum": momentum_score,
        "Volatility": volatility_score,
        "Positioning": positioning_score,
        "Catalysts": catalyst_score,
    }

    composite = sum(scores[k] * weights[k] for k in weights)

    # Grade from composite
    if composite >= 8.0:
        grade = "STRONG BUY"
    elif composite >= 7.0:
        grade = "BUY"
    elif composite >= 5.5:
        grade = "HOLD"
    elif composite >= 4.5:
        grade = "SELL"
    else:
        grade = "STRONG SELL"

    # Generate thesis
    strengths = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
    weaknesses = sorted(scores.items(), key=lambda x: x[1])[:2]

    thesis_parts = [f"{company_name} ({ticker})"]
    if grade in ("BUY", "STRONG BUY"):
        thesis_parts.append(f"scores well on {strengths[0][0].lower()} and {strengths[1][0].lower()}")
        thesis_parts.append(f"with a composite score of {composite:.1f}/10.")
        if pe_ratio:
            thesis_parts.append(f"At {pe_ratio:.1f}x earnings,")
            thesis_parts.append("valuation is attractive relative to growth." if pe_ratio < 20 else "premium valuation is supported by quality metrics.")
    elif grade == "HOLD":
        thesis_parts.append(f"presents a balanced risk/reward at current levels (composite {composite:.1f}/10).")
        thesis_parts.append(f"{strengths[0][0]} is a bright spot, but {weaknesses[0][0].lower()} tempers the outlook.")
    else:
        thesis_parts.append(f"faces headwinds in {weaknesses[0][0].lower()} and {weaknesses[1][0].lower()}")
        thesis_parts.append(f"with a composite score of {composite:.1f}/10.")

    thesis = " ".join(thesis_parts)

    # Build dimensions array
    dimensions = [
        {"name": "Valuation", "score": valuation_score, "weight": 0.20,
         "assessment": f"{'Attractive' if valuation_score >= 7 else 'Fair' if valuation_score >= 5 else 'Stretched'} valuation metrics.",
         "data_points": val_data_points},
        {"name": "Growth Quality", "score": growth_score, "weight": 0.12,
         "assessment": f"{'Strong' if growth_score >= 7 else 'Moderate' if growth_score >= 5 else 'Weak'} growth profile.",
         "data_points": growth_data},
        {"name": "Profitability", "score": profitability_score, "weight": 0.18,
         "assessment": f"{'Excellent' if profitability_score >= 8 else 'Good' if profitability_score >= 6 else 'Below average'} margin profile.",
         "data_points": prof_data},
        {"name": "Balance Sheet", "score": balance_score, "weight": 0.10,
         "assessment": f"{'Conservative' if balance_score >= 8 else 'Adequate' if balance_score >= 6 else 'Leveraged'} capital structure.",
         "data_points": balance_data},
        {"name": "Momentum", "score": momentum_score, "weight": 0.15,
         "assessment": f"Price {'above' if price_vs_50d > 0 else 'below'} 50-day MA ({price_vs_50d:+.1f}%), {'above' if price_vs_200d > 0 else 'below'} 200-day MA ({price_vs_200d:+.1f}%).",
         "data_points": [f"vs 50-day MA: {price_vs_50d:+.1f}%", f"vs 200-day MA: {price_vs_200d:+.1f}%", f"Beta: {beta:.2f}"]},
        {"name": "Volatility", "score": volatility_score, "weight": 0.10,
         "assessment": f"Beta of {beta:.2f} — {'low' if beta < 0.9 else 'market-level' if beta < 1.1 else 'elevated'} volatility profile.",
         "data_points": vol_data},
        {"name": "Positioning", "score": positioning_score, "weight": 0.07,
         "assessment": "Market positioning data is limited for quantitative assessment.",
         "data_points": ["Positioning: Neutral (limited data)"]},
        {"name": "Catalysts", "score": catalyst_score, "weight": 0.08,
         "assessment": "Near-term catalyst identification requires additional data sources.",
         "data_points": ["Monitor upcoming earnings", "Watch sector rotation trends"]},
    ]

    # Scenarios
    base_return = 0 if grade == "HOLD" else (8.0 if "BUY" in grade else -8.0)
    scenarios = {
        "bull": {"target_pct": base_return + 12, "probability": 0.30,
                 "drivers": [f"{strengths[0][0]} thesis plays out", "Multiple expansion", "Sector tailwinds"]},
        "base": {"target_pct": base_return, "probability": 0.50,
                 "drivers": ["Business executes as expected", "Stable margins", "Market-in-line returns"]},
        "bear": {"target_pct": base_return - 18, "probability": 0.20,
                 "drivers": [f"{weaknesses[0][0]} deteriorates", "Multiple compression", "Macro headwinds"]}
    }

    return {
        "ticker": ticker,
        "company_name": company_name,
        "sector": sector,
        "composite_score": round(composite, 1),
        "grade": grade,
        "thesis": thesis,
        "dimensions": dimensions,
        "scenarios": scenarios,
        "key_risks": [
            f"{weaknesses[0][0]} could deteriorate further",
            "Broader market or sector rotation risk",
            "Earnings miss or guidance downgrade",
            "Macro headwinds (rates, recession)"
        ],
        "catalysts": [
            {"event": "Next quarterly earnings", "expected_date": "TBD", "impact": "uncertain", "probability": 0.50},
            {"event": "Sector rotation catalysts", "expected_date": "TBD", "impact": "uncertain", "probability": 0.40}
        ],
        "contrarian_signal": f"{'Consensus is cautious — potential upside if execution improves.' if grade in ('HOLD', 'SELL') else 'Strong consensus — watch for crowding risk and mean reversion.'}",
        "data_gaps": [
            "Real-time institutional flow data not available",
            "Forward guidance visibility limited",
            "Peer comparison requires additional context"
        ]
    }
