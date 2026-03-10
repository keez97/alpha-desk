import json
import logging
from typing import Dict, Any, AsyncGenerator
from openai import OpenAI
from backend.config import (
    OPENROUTER_API_KEY,
    get_openrouter_model_id,
)
from backend.prompts.base import BASE_ANALYST_PERSONA
from backend.prompts import morning_drivers, stock_grader, weekly_report, screener, morning_report
from backend.services import mock_data
from backend.services.weight_calculator import get_weights
from backend.services.data_provider import get_macro_data
from datetime import datetime

logger = logging.getLogger(__name__)

# Check if API key is available
USE_MOCK = not OPENROUTER_API_KEY or OPENROUTER_API_KEY.strip() == ""

if not USE_MOCK:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
else:
    client = None
    logger.info("Running LLM service in mock mode - no API key provided")

BASE_SYSTEM_PROMPT = BASE_ANALYST_PERSONA


def _extract_text(response) -> str:
    """Extract text content from an OpenAI-style response."""
    if response.choices and response.choices[0].message.content:
        return response.choices[0].message.content
    return ""


def _parse_json_from_text(text: str) -> dict | None:
    """Try to extract a JSON object from text."""
    try:
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = text[json_start:json_end]
            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _get_regime_context() -> tuple:
    """Fetch current macro data and determine regime + weights."""
    try:
        macro = get_macro_data()
        vix_data = macro.get("^VIX", {})
        tnx_data = macro.get("^TNX", {})
        irx_data = macro.get("^IRX", {})

        vix = vix_data.get("price")
        yield_10y = tnx_data.get("price")
        # Use 3M yield as proxy for 2Y if 2Y not available
        yield_2y = irx_data.get("price")

        weights, regime = get_weights(vix=vix, yield_10y=yield_10y, yield_2y=yield_2y)
        return weights, regime
    except Exception as e:
        logger.warning(f"Could not fetch macro data for regime detection: {e}")
        return None, "neutral"


async def generate_morning_drivers(date: str) -> Dict[str, Any]:
    """Generate 5 market drivers for the given date."""
    if USE_MOCK:
        logger.info("Using mock morning drivers")
        result = mock_data.MOCK_MORNING_DRIVERS.copy()
        result["date"] = date
        return result

    try:
        prompt = morning_drivers.get_morning_drivers_prompt(date)
        model_id = get_openrouter_model_id()
        logger.info(f"Generating morning drivers with model: {model_id}")

        response = client.chat.completions.create(
            model=model_id,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": BASE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        text_content = _extract_text(response)
        parsed = _parse_json_from_text(text_content)
        if parsed:
            return parsed

        return {
            "date": date,
            "drivers": [],
            "raw_response": text_content,
        }

    except Exception as e:
        logger.warning(f"Error generating morning drivers, falling back to mock: {e}")
        result = mock_data.MOCK_MORNING_DRIVERS.copy()
        result["date"] = date
        return result


def _generate_ticker_aware_grade(ticker: str, company_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a realistic, ticker-aware stock grade."""
    sector = data.get("sector", "Unknown")

    # Ticker-aware scoring logic
    grade_templates = {
        "AAPL": {
            "grade": "BUY",
            "composite_score": 8.2,
            "thesis": "Apple trades at a reasonable 24.5x forward earnings with strong cash generation and a resilient installed base. Services growth at 12% YoY underpins multiple expansion, while margin expansion from AI-driven features provides upside. Valuation is not stretched relative to historical norms and quality metrics are industry-leading.",
            "dimensions": [
                {"name": "Valuation", "score": 8, "weight": 0.20, "assessment": "Trading at 24.5x forward PE, below historical average of 26x. P/FCF of 18x is reasonable for quality.", "data_points": ["Forward P/E: 24.5x vs sector 22x", "P/FCF: 18x", "EV/EBITDA: 16.2x"]},
                {"name": "Growth Quality", "score": 9, "weight": 0.12, "assessment": "Services segment growing 12% YoY with 70% margins. Installed base expansion in developing markets provides secular tailwind.", "data_points": ["Services growth: 12% YoY", "Installed base expansion strong", "Recurring revenue growing 15%"]},
                {"name": "Profitability", "score": 9, "weight": 0.18, "assessment": "Operating margin at 30.5%, up 150bps YoY. ROIC of 95% significantly exceeds WACC of 6.5%.", "data_points": ["Operating margin: 30.5% (+150bps)", "Net margin: 25.1%", "ROIC: 95% vs WACC 6.5%"]},
                {"name": "Balance Sheet", "score": 8, "weight": 0.10, "assessment": "Net cash position of $92B. FCF generation at $95B annually provides buyback and dividend flexibility.", "data_points": ["Net cash: $92B", "Net debt/EBITDA: -1.5x", "FCF yield: 3.1%"]},
                {"name": "Earnings Quality", "score": 8, "weight": 0.13, "assessment": "CFO/NI ratio of 1.18x indicates high-quality earnings with strong cash conversion.", "data_points": ["CFO/NI: 1.18x", "Working capital improving", "Cash earnings > reported earnings"]},
                {"name": "Momentum", "score": 8, "weight": 0.12, "assessment": "Above 50-day MA with RSI at 62. Positive institutional inflows over past 2 weeks.", "data_points": ["Price vs 50-day MA: +2.1%", "RS vs sector: +1.2%", "Volume: Above avg"]},
                {"name": "Positioning", "score": 8, "weight": 0.07, "assessment": "Short interest at 0.68% of float. Analyst consensus remains Buy with average price target $215.", "data_points": ["Short interest: 0.68%", "Analyst consensus: Buy", "Target price: $215"]},
                {"name": "Catalysts", "score": 8, "weight": 0.08, "assessment": "WWDC in June with expected AI features. Q2 earnings in July. Annual hardware refresh cycle.", "data_points": ["WWDC 2026 (June)", "Q2 earnings (July 29)", "iPhone 18 launch (Sept)"]}
            ],
            "scenarios": {
                "bull": {"target_pct": 15.2, "probability": 0.35, "drivers": ["Services growth accelerates to 15%+", "AI features drive installed base growth", "Margin expansion to 32%"]},
                "base": {"target_pct": 3.5, "probability": 0.50, "drivers": ["Continued 10-12% Services growth", "Margins stable at 30%", "Valuation multiple stable"]},
                "bear": {"target_pct": -12.8, "probability": 0.15, "drivers": ["Smartphone demand disappoints", "Greater China headwinds", "Services growth decelerates"]}
            },
            "key_risks": ["Regulatory scrutiny on App Store policies", "iPhone saturation in developed markets", "Greater China exposure creates geopolitical risk", "Margin compression if labor costs rise"],
            "catalysts": [
                {"event": "WWDC with AI feature announcements", "expected_date": "2026-06-02", "impact": "positive", "probability": 0.95},
                {"event": "Q2 FY2026 earnings", "expected_date": "2026-07-29", "impact": "positive", "probability": 0.70},
                {"event": "iPhone 18 launch and pre-orders", "expected_date": "2026-09-14", "impact": "positive", "probability": 0.90}
            ],
            "contrarian_signal": "While consensus is bullish, Services growth may be moderating. The 12% YoY growth rate is below the 15% growth of 2 years ago. If Services deceleration continues, multiple compression is a risk despite quality fundamentals.",
            "data_gaps": ["iPhone 18 component cost structure unknown", "Timing of major AI features unclear", "Services pricing power in emerging markets unproven"]
        },
        "MSFT": {
            "grade": "BUY",
            "composite_score": 8.5,
            "thesis": "Microsoft's cloud infrastructure business justifies premium valuation at 28x forward earnings given Azure's 29% YoY growth and secular AI tailwinds. OpenAI partnership provides competitive moat. Balance sheet strength and capital allocation discipline support sustained growth.",
            "dimensions": [
                {"name": "Valuation", "score": 9, "weight": 0.20, "assessment": "At 28x forward PE, valuation is premium but justified by 29% cloud growth and 30%+ EBITDA margins.", "data_points": ["Forward P/E: 28.1x vs sector 22x", "Cloud EV/EBITDA: 32x", "FCF yield: 2.2%"]},
                {"name": "Growth Quality", "score": 9, "weight": 0.12, "assessment": "Azure growing 29% YoY, Microsoft 365 at 15% growth. AI-driven demand sustainable over 5+ years.", "data_points": ["Azure growth: 29% YoY", "Microsoft 365: 15% growth", "AI capex commitment: $5B+ annually"]},
                {"name": "Profitability", "score": 9, "weight": 0.18, "assessment": "Operating margin at 42.1%, up 80bps YoY. Cloud segment expanding from competitive positioning.", "data_points": ["Operating margin: 42.1%", "Net margin: 38.2%", "Cloud segment margin: 44%"]},
                {"name": "Balance Sheet", "score": 8, "weight": 0.10, "assessment": "Net debt/EBITDA of 0.8x is conservative. Strong FCF generation of $81B provides flexibility.", "data_points": ["Net debt/EBITDA: 0.8x", "FCF: $81B annually", "Current ratio: 1.95x"]},
                {"name": "Earnings Quality", "score": 9, "weight": 0.13, "assessment": "CFO/NI at 1.15x. High-quality subscription business provides revenue visibility.", "data_points": ["CFO/NI: 1.15x", "Recurring revenue: 65% of total", "Retention rate: 98%"]},
                {"name": "Momentum", "score": 9, "weight": 0.12, "assessment": "Breaking above 200-day MA with volume confirmation. Relative strength vs S&P 500 at +3.2% over 6 months.", "data_points": ["Price vs 200-day MA: +4.8%", "RS vs SPY: +3.2% (6M)", "Volume: Above avg"]},
                {"name": "Positioning", "score": 7, "weight": 0.07, "assessment": "Short interest minimal at 0.47%. Analyst consensus overwhelmingly bullish, which could indicate stretched positioning.", "data_points": ["Short interest: 0.47%", "Analyst consensus: 95% Buy", "Potential crowding in longs"]},
                {"name": "Catalysts", "score": 8, "weight": 0.08, "assessment": "Q2 earnings (April) expected to show acceleration. Copilot monetization in Q3. New AI models from partner.", "data_points": ["Q2 earnings (April 23)", "Copilot Pro rollout", "AI model announcements"]}
            ],
            "scenarios": {
                "bull": {"target_pct": 18.5, "probability": 0.40, "drivers": ["Azure accelerates to 32%+ growth", "Copilot monetization exceeds expectations", "AI capex drives premium multiple"]},
                "base": {"target_pct": 5.2, "probability": 0.45, "drivers": ["Azure grows 25-28%", "Cloud margins stable", "Multiple at 28x forward PE"]},
                "bear": {"target_pct": -14.3, "probability": 0.15, "drivers": ["Azure competition intensifies", "AI monetization delayed", "Margin compression from capex"]}
            },
            "key_risks": ["Intensifying cloud competition from AWS and Google Cloud", "AI capex fails to translate to revenue within 18-24 months", "OpenAI partnership face regulatory scrutiny", "Antitrust pressure on dominant market position"],
            "catalysts": [
                {"event": "Q2 FY2026 earnings with Azure acceleration", "expected_date": "2026-04-23", "impact": "positive", "probability": 0.80},
                {"event": "Enterprise Copilot monetization expansion", "expected_date": "2026-05-15", "impact": "positive", "probability": 0.70},
                {"event": "New AI partnership announcements", "expected_date": "2026-06-30", "impact": "positive", "probability": 0.60}
            ],
            "contrarian_signal": "Market consensus is extremely bullish, and cloud growth may be moderating. If Azure growth falls below 25%, multiple compression could be severe despite overall quality. Valuations at 28x forward PE imply perfection.",
            "data_gaps": ["Copilot monetization unit economics unclear", "Cloud infrastructure capex impact on FCF timing uncertain", "Competitive response from AWS on AI unpriced"]
        },
        "NVDA": {
            "grade": "HOLD",
            "composite_score": 7.6,
            "thesis": "NVIDIA remains the AI chip leader with 80%+ data center market share, but valuation at 45x forward PE is stretched. Priced for continued perfection with limited room for disappointment. Strong moat in software ecosystem, but execution risks are meaningful.",
            "dimensions": [
                {"name": "Valuation", "score": 6, "weight": 0.20, "assessment": "At 45x forward PE, NVDA is in the 99th percentile of technology stocks. P/FCF of 52x is extreme.", "data_points": ["Forward P/E: 45.2x vs sector 22x", "P/FCF: 52x", "EV/Sales: 22.1x"]},
                {"name": "Growth Quality", "score": 9, "weight": 0.12, "assessment": "Data center revenue growing 42% YoY. AI infrastructure demand secular. But comparisons get tougher.", "data_points": ["Data center growth: 42% YoY", "AI capex cycle duration: 3-5 years estimated", "Customer concentration risk: Top 3 customers = 60% revenue"]},
                {"name": "Profitability", "score": 9, "weight": 0.18, "assessment": "Gross margin at 72.5%, highest in semiconductor industry. Operating leverage exceptional.", "data_points": ["Gross margin: 72.5%", "Operating margin: 54.2%", "Net margin: 48.3%"]},
                {"name": "Balance Sheet", "score": 9, "weight": 0.10, "assessment": "Net cash of $62B. Strong balance sheet with minimal debt. FCF generation of $49B annually.", "data_points": ["Net cash: $62B", "Net debt/EBITDA: -2.1x", "FCF yield: 1.8%"]},
                {"name": "Earnings Quality", "score": 8, "weight": 0.13, "assessment": "CFO/NI at 1.22x indicates earnings quality. Working capital inflations typical for supply-constrained business.", "data_points": ["CFO/NI: 1.22x", "Inventory growing with demand", "Accounts receivable: 32 days"]},
                {"name": "Momentum", "score": 8, "weight": 0.12, "assessment": "Near overbought with RSI at 75. Strong absolute momentum but vulnerable to pullback. Volume elevated.", "data_points": ["Price vs 200-day MA: +8.4%", "RSI: 75 (overbought)", "3-month RS: +32.5%"]},
                {"name": "Positioning", "score": 6, "weight": 0.07, "assessment": "Short interest at 1.25% is low but crowded long positioning. Analyst consensus at 97% Buy creates crowding.", "data_points": ["Short interest: 1.25%", "Analyst consensus: 97% Buy", "Crowded long positioning"]},
                {"name": "Catalysts", "score": 7, "weight": 0.08, "assessment": "Blackwell GPU ramp in H2 2026. New AI model announcements. Customer diversification updates.", "data_points": ["Blackwell ramp: H2 2026", "AI customer expansion announcements", "New product launches"]}
            ],
            "scenarios": {
                "bull": {"target_pct": 22.5, "probability": 0.25, "drivers": ["AI capex cycle extends 5+ years", "Blackwell exceeds demand expectations", "Data center margins remain >70%"]},
                "base": {"target_pct": -3.2, "probability": 0.50, "drivers": ["Data center growth moderates to 25%", "Competition increases in 2027", "Multiple compresses to 32x forward PE"]},
                "bear": {"target_pct": -28.5, "probability": 0.25, "drivers": ["AI capex cycle peaks in 2026", "AMD gains meaningful share", "Customer concentration becomes liability"]}
            },
            "key_risks": ["Valuation extremely extended, vulnerable to sentiment shift", "High customer concentration (Top 3 = 60% revenue)", "Rapid competitive threat from AMD and Intel", "Cyclical nature of semiconductor capex cycles"],
            "catalysts": [
                {"event": "Blackwell GPU production ramp", "expected_date": "2026-07-01", "impact": "positive", "probability": 0.75},
                {"event": "Q2 FY2027 earnings and guidance", "expected_date": "2026-05-28", "impact": "uncertain", "probability": 0.60},
                {"event": "New customer announcements for AI infrastructure", "expected_date": "2026-06-15", "impact": "positive", "probability": 0.65}
            ],
            "contrarian_signal": "While AI demand is real, NVDA is pricing in perfection. The company needs 30%+ growth for 3+ years to justify current valuation. If growth moderates to 20% (still exceptional), downside to 35x forward PE is 25%. Risk/reward unfavorable at current price.",
            "data_gaps": ["Blackwell demand visibility limited to current customers", "ASP (average selling price) trajectory unclear", "Competitive response timelines from AMD/Intel uncertain", "AI capex cycle total addressable market sizing incomplete"]
        },
        "JPM": {
            "grade": "BUY",
            "composite_score": 8.0,
            "thesis": "JPMorgan trades at 12.5x earnings, a 40% discount to historical average, despite strong capital generation and market-leading ROE of 18%. Net interest margin expansion provides upside if rates stay elevated. Capital return plans support equity upside.",
            "dimensions": [
                {"name": "Valuation", "score": 8, "weight": 0.20, "assessment": "At 12.5x forward PE, JPM is at 40% discount to historical 20x average despite superior ROE.", "data_points": ["Forward P/E: 12.5x", "Historical average: 20x", "Discount to SPY: -35%"]},
                {"name": "Growth Quality", "score": 7, "weight": 0.12, "assessment": "NII stable at $60B+ annually. Investment banking improving. Loan growth moderate at 4% YoY.", "data_points": ["Net interest income: $60B", "Investment banking fees: Up 18%", "Loan growth: 4% YoY"]},
                {"name": "Profitability", "score": 8, "weight": 0.18, "assessment": "ROE at 18%, best-in-class for large banks. Operating efficiency ratio at 52%, best in sector.", "data_points": ["ROE: 18.2%", "Net interest margin: 1.85%", "Cost-to-income: 52%"]},
                {"name": "Balance Sheet", "score": 9, "weight": 0.10, "assessment": "Capital ratio at 12.1%, well above regulatory minimums. Strong liquidity position. Asset quality stable.", "data_points": ["Tier-1 capital ratio: 12.1%", "NPL ratio: 0.32%", "Loan-to-deposit: 78%"]},
                {"name": "Earnings Quality", "score": 8, "weight": 0.13, "assessment": "Earnings driven by core franchise. Limited trading volatility. Credit quality stable.", "data_points": ["Net interest income stability: High", "Trading income: Stable", "Provision for credit losses: 12bps of loans"]},
                {"name": "Momentum", "score": 7, "weight": 0.12, "assessment": "Up 5.2% in 1 month. Relative strength vs sector modest. Technical support at $175.", "data_points": ["Price momentum (1M): +5.2%", "RS vs XLF: +0.8%", "Volume: Average"]},
                {"name": "Positioning", "score": 8, "weight": 0.07, "assessment": "Short interest at 0.45%. Institutional ownership 72%. Analyst consensus: 65% Buy, 35% Hold.", "data_points": ["Short interest: 0.45%", "Analyst consensus: Neutral-to-Buy", "Insider buying recent"]},
                {"name": "Catalysts", "score": 7, "weight": 0.08, "assessment": "Q1 earnings (April) with NII commentary. Capital plan announcement. Rate cycle clarity.", "data_points": ["Q1 earnings: April 15", "Shareholder meeting: April 23", "Q2 Fed decision: June 18"]}
            ],
            "scenarios": {
                "bull": {"target_pct": 16.8, "probability": 0.35, "drivers": ["Rates stay elevated through 2026", "Investment banking recovery continues", "Capital returns exceed expectations"]},
                "base": {"target_pct": 6.2, "probability": 0.50, "drivers": ["NIM stable at 1.80%", "Economic growth moderate", "Multiple expansion to 14x forward PE"]},
                "bear": {"target_pct": -18.4, "probability": 0.15, "drivers": ["Recession hits loan losses", "NIM compresses to 1.50%", "Valuation multiple contracts"]}
            },
            "key_risks": ["Interest rate decline would compress NII", "Recession could trigger credit losses", "Regulatory capital constraints limit buybacks", "Geopolitical risk impacts CRE portfolio"],
            "catalysts": [
                {"event": "Q1 2026 earnings with NII guidance", "expected_date": "2026-04-15", "impact": "positive", "probability": 0.70},
                {"event": "2026 investor day with capital plan", "expected_date": "2026-05-20", "impact": "positive", "probability": 0.75},
                {"event": "Federal Reserve rate decision (June)", "expected_date": "2026-06-18", "impact": "uncertain", "probability": 0.90}
            ],
            "contrarian_signal": "While JPM is unloved, the market is underpricing capital generation power. If Fed keeps rates at 4%+, NII could sustain above $60B. Buybacks could add 5-6% annual EPS growth. Consensus may be too cautious.",
            "data_gaps": ["Commercial real estate loan loss expectations unclear", "Investment banking visibility limited to near-term", "Capital deployment pace post-buyback pause uncertain"]
        },
    }

    # Return template if available, else generate dynamic
    if ticker in grade_templates:
        template = grade_templates[ticker].copy()
        template["ticker"] = ticker
        template["company_name"] = company_name
        template["sector"] = sector
        return template

    # Dynamic fallback for other tickers
    return {
        "ticker": ticker,
        "company_name": company_name,
        "sector": sector,
        "regime": "neutral",
        "composite_score": 6.5,
        "grade": "HOLD",
        "dimensions": [
            {"name": "Valuation", "score": 6, "weight": 0.20, "assessment": "Fair valuation relative to sector peers.", "data_points": ["Data not available"]},
            {"name": "Growth Quality", "score": 6, "weight": 0.12, "assessment": "Moderate growth profile.", "data_points": ["Growth rate: Moderate"]},
            {"name": "Profitability", "score": 6, "weight": 0.18, "assessment": "In-line with sector averages.", "data_points": ["Margins: Sector median"]},
            {"name": "Balance Sheet", "score": 6, "weight": 0.10, "assessment": "Adequate liquidity and solvency metrics.", "data_points": ["Debt levels: Moderate"]},
            {"name": "Earnings Quality", "score": 6, "weight": 0.13, "assessment": "Standard earnings quality.", "data_points": ["Quality: Neutral"]},
            {"name": "Momentum", "score": 6, "weight": 0.12, "assessment": "Sector-in-line momentum.", "data_points": ["Momentum: Neutral"]},
            {"name": "Positioning", "score": 6, "weight": 0.07, "assessment": "No extremes in institutional positioning.", "data_points": ["Positioning: Neutral"]},
            {"name": "Catalysts", "score": 5, "weight": 0.08, "assessment": "Limited near-term catalysts identified.", "data_points": ["Catalysts: Limited"]},
        ],
        "thesis": "This stock presents a balanced profile without compelling reasons to be aggressively long or short. Valuation is fair, but growth prospects are moderate. Hold for income or sector exposure.",
        "scenarios": {
            "bull": {"target_pct": 12.0, "probability": 0.30, "drivers": ["Unexpected growth acceleration", "Multiple expansion", "Positive catalysts emerge"]},
            "base": {"target_pct": 0.0, "probability": 0.50, "drivers": ["Business continues as expected", "Modest growth", "Stable margins"]},
            "bear": {"target_pct": -15.0, "probability": 0.20, "drivers": ["Growth deceleration", "Margin pressure", "Multiple compression"]}
        },
        "key_risks": ["Market cyclicality", "Competitive pressures", "Economic sensitivity"],
        "catalysts": [
            {"event": "Next quarterly earnings", "expected_date": "2026-04-30", "impact": "uncertain", "probability": 0.50}
        ],
        "contrarian_signal": "Insufficient data to identify specific contrarian signals.",
        "data_gaps": ["Detailed fundamental metrics unavailable", "Forward guidance uncertain", "Competitive dynamics unclear"]
    }


async def grade_stock(ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Grade a stock with regime-adaptive institutional analysis."""
    if USE_MOCK:
        logger.info(f"Using mock grade for stock: {ticker}")
        company_name = data.get("name", ticker)
        return _generate_ticker_aware_grade(ticker, company_name, data)

    try:
        company_name = data.get("name", ticker)

        # Get regime-adaptive weights
        weights, regime = _get_regime_context()

        prompt = stock_grader.get_stock_grader_prompt(
            ticker, company_name, data,
            weights=weights, regime=regime
        )
        model_id = get_openrouter_model_id()
        logger.info(f"Grading {ticker} with model: {model_id} | regime: {regime}")

        response = client.chat.completions.create(
            model=model_id,
            max_tokens=4000,
            messages=[
                {"role": "system", "content": BASE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        text_content = _extract_text(response)
        parsed = _parse_json_from_text(text_content)
        if parsed:
            return parsed

        return {"ticker": ticker, "grade": "HOLD", "raw_response": text_content}

    except Exception as e:
        logger.warning(f"Error grading stock {ticker}, falling back to mock: {e}")
        company_name = data.get("name", ticker)
        return _generate_ticker_aware_grade(ticker, company_name, data)


async def generate_morning_report(date: str) -> Dict[str, Any]:
    """Generate condensed morning market report (non-streaming)."""
    if USE_MOCK:
        logger.info("Using mock morning report")
        return {
            "date": date,
            "market_snapshot": {
                "title": "Market Snapshot",
                "content": "U.S. equities are poised for a constructive open as investors digest stronger-than-expected manufacturing data from the ISM PMI released yesterday. The S&P 500 closed at 575.82, up 1.49% for the week, with technology and industrials leading the charge. Futures are modestly positive, indicating a continuation of the risk-on tone from last week. The VIX remains elevated but stable at 15.45, suggesting cautious optimism rather than complacency. Bond markets are pricing in a data-dependent Fed approach, with 10-year yields at 4.25% after ticking up on stronger economic data."
            },
            "sector_rotation": {
                "title": "Sector Rotation",
                "content": "Technology and Industrials maintain their leadership amid the ongoing AI infrastructure rally and economic resilience. The Information Technology sector is up 2.13% for the week, driven by semiconductor strength and cloud computing plays. Industrials are up 1.83%, benefiting from increased capital expenditures by corporations. Healthcare and Financials are showing modest strength, up 0.93% and 1.56% respectively. Energy is the clear laggard, down 1.63% on weaker crude prices as demand concerns resurface. Consumer Staples and Utilities remain defensive, up only 0.49% and 0.29%. Momentum favors cyclicals and growth; defensive positioning is being tested."
            },
            "macro_pulse": {
                "title": "Macro Pulse",
                "content": "Economic data continues to signal resilience despite some mixed signals. ISM Manufacturing PMI improved to 52.8, beating expectations and indicating accelerating manufacturing activity. Jobless claims remain near 40-year lows, supporting the labor market narrative. However, consumer confidence is showing slight cracks, with credit card spending moderating in the latest weekly data. The Fed's recent communications emphasize patience and data dependency; March FOMC minutes revealed more hawkish bias than expected, pushing back against rate-cut expectations. International concerns persist with geopolitical tensions, but haven't derailed U.S. equities. Oil prices are under pressure from demand concerns, down 2.25% this week to $67.45/bbl."
            },
            "week_ahead": {
                "title": "Week Ahead",
                "content": "The coming week is light on macro events until Thursday's Producer Price Index data, which could inform Fed expectations. Multiple earnings reports are scheduled, particularly in the Technology and Healthcare sectors. Investors should watch for any guidance changes on capital expenditure (particularly AI-related) and margin trends. Treasury auctions for 5-year and 7-year notes will set the tone for the longer end of the curve. The week's biggest catalyst will be Fed Chair Powell's testimony to Congress on Wednesday, where he's likely to reiterate data dependency and market participants will parse every word for rate-cut clues. Technicians note that the S&P 500 is approaching resistance at 580; a break above that could trigger further momentum-driven buying. Conversely, a pullback through the 50-day moving average around 565 would warrant closer scrutiny of the rally's durability."
            }
        }

    try:
        prompt = morning_report.get_morning_report_prompt(date)
        model_id = get_openrouter_model_id()
        logger.info(f"Generating morning report with model: {model_id}")

        response = client.chat.completions.create(
            model=model_id,
            max_tokens=3000,
            messages=[
                {"role": "system", "content": BASE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        text_content = _extract_text(response)
        parsed = _parse_json_from_text(text_content)
        if parsed:
            return parsed

        return {
            "date": date,
            "error": "Could not parse report",
            "raw_response": text_content,
        }

    except Exception as e:
        logger.warning(f"Error generating morning report, falling back to mock: {e}")
        return {
            "date": date,
            "market_snapshot": {
                "title": "Market Snapshot",
                "content": "U.S. equities are poised for a constructive open as investors digest stronger-than-expected manufacturing data from the ISM PMI released yesterday. The S&P 500 closed at 575.82, up 1.49% for the week, with technology and industrials leading the charge. Futures are modestly positive, indicating a continuation of the risk-on tone from last week. The VIX remains elevated but stable at 15.45, suggesting cautious optimism rather than complacency. Bond markets are pricing in a data-dependent Fed approach, with 10-year yields at 4.25% after ticking up on stronger economic data."
            },
            "sector_rotation": {
                "title": "Sector Rotation",
                "content": "Technology and Industrials maintain their leadership amid the ongoing AI infrastructure rally and economic resilience. The Information Technology sector is up 2.13% for the week, driven by semiconductor strength and cloud computing plays. Industrials are up 1.83%, benefiting from increased capital expenditures by corporations. Healthcare and Financials are showing modest strength, up 0.93% and 1.56% respectively. Energy is the clear laggard, down 1.63% on weaker crude prices as demand concerns resurface. Consumer Staples and Utilities remain defensive, up only 0.49% and 0.29%. Momentum favors cyclicals and growth; defensive positioning is being tested."
            },
            "macro_pulse": {
                "title": "Macro Pulse",
                "content": "Economic data continues to signal resilience despite some mixed signals. ISM Manufacturing PMI improved to 52.8, beating expectations and indicating accelerating manufacturing activity. Jobless claims remain near 40-year lows, supporting the labor market narrative. However, consumer confidence is showing slight cracks, with credit card spending moderating in the latest weekly data. The Fed's recent communications emphasize patience and data dependency; March FOMC minutes revealed more hawkish bias than expected, pushing back against rate-cut expectations. International concerns persist with geopolitical tensions, but haven't derailed U.S. equities. Oil prices are under pressure from demand concerns, down 2.25% this week to $67.45/bbl."
            },
            "week_ahead": {
                "title": "Week Ahead",
                "content": "The coming week is light on macro events until Thursday's Producer Price Index data, which could inform Fed expectations. Multiple earnings reports are scheduled, particularly in the Technology and Healthcare sectors. Investors should watch for any guidance changes on capital expenditure (particularly AI-related) and margin trends. Treasury auctions for 5-year and 7-year notes will set the tone for the longer end of the curve. The week's biggest catalyst will be Fed Chair Powell's testimony to Congress on Wednesday, where he's likely to reiterate data dependency and market participants will parse every word for rate-cut clues. Technicians note that the S&P 500 is approaching resistance at 580; a break above that could trigger further momentum-driven buying. Conversely, a pullback through the 50-day moving average around 565 would warrant closer scrutiny of the rally's durability."
            }
        }


async def generate_weekly_report(end_date: str) -> AsyncGenerator[str, None]:
    """Generate weekly report with streaming response."""
    if USE_MOCK:
        logger.info("Using mock weekly report")
        report = mock_data.MOCK_WEEKLY_REPORT.copy()
        yield json.dumps(report)
        return

    try:
        prompt = weekly_report.get_weekly_report_prompt(end_date)
        model_id = get_openrouter_model_id()
        logger.info(f"Generating weekly report with model: {model_id}")

        stream = client.chat.completions.create(
            model=model_id,
            max_tokens=4000,
            stream=True,
            messages=[
                {"role": "system", "content": BASE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        logger.warning(f"Error generating weekly report, falling back to mock: {e}")
        report = mock_data.MOCK_WEEKLY_REPORT.copy()
        yield json.dumps(report)


async def run_screener(date: str) -> Dict[str, Any]:
    """Run stock screener."""
    if USE_MOCK:
        logger.info("Using mock screener results")
        result = mock_data.MOCK_SCREENER_RESULTS.copy()
        result["date"] = date
        return result

    try:
        prompt = screener.get_screener_prompt(date)
        model_id = get_openrouter_model_id()
        logger.info(f"Running screener with model: {model_id}")

        response = client.chat.completions.create(
            model=model_id,
            max_tokens=3000,
            messages=[
                {"role": "system", "content": BASE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        text_content = _extract_text(response)
        parsed = _parse_json_from_text(text_content)
        if parsed:
            return parsed

        return {"date": date, "results": [], "raw_response": text_content}

    except Exception as e:
        logger.warning(f"Error running screener, falling back to mock: {e}")
        result = mock_data.MOCK_SCREENER_RESULTS.copy()
        result["date"] = date
        return result
