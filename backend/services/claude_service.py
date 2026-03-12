import json
import logging
from typing import Dict, Any, AsyncGenerator
from backend.config import (
    LLM_PROVIDER,
    ANTHROPIC_API_KEY,
    OPENROUTER_API_KEY,
    get_model_id,
)
from backend.prompts.base import BASE_ANALYST_PERSONA
from backend.prompts import morning_drivers, stock_grader, weekly_report, screener, morning_report
from backend.services import mock_data
from backend.services.weight_calculator import get_weights
from backend.services.data_provider import get_macro_data
from datetime import datetime

logger = logging.getLogger(__name__)

# --- LLM Client Setup ---
USE_MOCK = LLM_PROVIDER == "none"
_anthropic_client = None
_openrouter_client = None

if LLM_PROVIDER == "anthropic":
    try:
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        logger.info("LLM service using Anthropic direct API")
    except Exception as e:
        logger.warning(f"Failed to init Anthropic client: {e}")
        USE_MOCK = True
elif LLM_PROVIDER == "openrouter":
    try:
        from openai import OpenAI
        _openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
        logger.info("LLM service using OpenRouter API")
    except Exception as e:
        logger.warning(f"Failed to init OpenRouter client: {e}")
        USE_MOCK = True
else:
    logger.info("Running LLM service in mock mode - no API key provided")

BASE_SYSTEM_PROMPT = BASE_ANALYST_PERSONA


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
    """Unified LLM call that works with both Anthropic and OpenRouter."""
    model_id = get_model_id()

    if LLM_PROVIDER == "anthropic" and _anthropic_client:
        response = _anthropic_client.messages.create(
            model=model_id,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        # Extract text from Anthropic response
        if response.content and len(response.content) > 0:
            return response.content[0].text
        return ""

    elif LLM_PROVIDER == "openrouter" and _openrouter_client:
        response = _openrouter_client.chat.completions.create(
            model=model_id,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content
        return ""

    raise RuntimeError("No LLM client available")


def generate_regime_insight(regime_data: dict, vix_data: dict, breadth_data: dict, overnight_data: dict) -> dict:
    """Use Claude to generate a rich narrative market insight from regime + supporting data.

    Returns: { "narrative": str, "factors": [...], "stance": str, "conviction": str }
    """
    if USE_MOCK:
        return {
            "narrative": "Markets are in a mixed regime with diverging signals across asset classes. "
                         "Trend remains positive but systemic fragility indicators warrant caution. "
                         "Consider maintaining core positions while hedging tail risk.",
            "factors": [
                {"label": "Trend", "assessment": "Positive", "bias": "bull"},
                {"label": "Volatility", "assessment": "Elevated", "bias": "neutral"},
                {"label": "Credit", "assessment": "Mixed", "bias": "neutral"},
            ],
            "stance": "Cautiously Bullish",
            "conviction": "medium",
        }

    # Build a rich context payload for Claude
    layers = regime_data.get("layers", {})
    windham = regime_data.get("windham", {})
    insights = regime_data.get("alpha_insights", [])

    layer_summary = []
    for name in ["trend", "volatility", "yield_credit", "sentiment", "macro", "systemic"]:
        layer = layers.get(name, {})
        if layer:
            signals_text = "; ".join(
                f"{s['name']}={s['value']} ({s['bias']})" for s in layer.get("signals", [])
            )
            layer_summary.append(f"  {name}: score={layer.get('score', 0):.2f}, weight={layer.get('weight', 0):.0%}, signals=[{signals_text}]")

    overnight_text = ""
    if overnight_data:
        indices = overnight_data.get("indices", [])
        gaps = [f"{i['ticker']} {i.get('overnight_return_pct', 0):+.2f}%" for i in indices[:6]]
        overnight_text = f"Overnight gaps: {', '.join(gaps)}"

    breadth_text = ""
    if breadth_data:
        breadth_text = (
            f"Market Breadth: A/D ratio={breadth_data.get('ad_ratio', 0):.2f}, "
            f"advances={breadth_data.get('advances', 0)}, declines={breadth_data.get('declines', 0)}, "
            f"McClellan={breadth_data.get('mcclellan', 0):.1f}, "
            f"breadth_thrust={'YES' if breadth_data.get('breadth_thrust') else 'No'}"
        )

    vix_text = ""
    if vix_data:
        vix_text = (
            f"VIX: spot={vix_data.get('vix_spot', 0):.1f}, 3m={vix_data.get('vix_3m', 0):.1f}, "
            f"state={vix_data.get('state', 'unknown')}, magnitude={vix_data.get('magnitude', 0):.1f}%, "
            f"percentile={vix_data.get('percentile', 50)}"
        )

    # ── Extract recession probability from multiple sources ──
    # Priority: top-level field > yield_credit layer details > None
    recession_prob = regime_data.get("recession_probability")
    if recession_prob is None:
        recession_prob = layers.get("yield_credit", {}).get("details", {}).get("recession_probability")
    recession_text = f"{recession_prob:.0f}%" if recession_prob is not None else "unavailable (data still loading)"

    prompt = f"""Analyze the current market regime and generate a concise, actionable morning assessment.

REGIME DATA:
- Overall: {regime_data.get('regime', 'neutral')} (confidence {regime_data.get('confidence', 50)}%, composite score {regime_data.get('composite_score', 0):.2f})
- Windham State: {windham.get('state', 'unknown')} — {windham.get('label', '')} ({windham.get('description', '')})
- Recession Probability (Estrella model): {recession_text}

LAYER SCORES:
{chr(10).join(layer_summary)}

{vix_text}
{breadth_text}
{overnight_text}

Return ONLY valid JSON with this exact structure:
{{
  "narrative": "<2-3 sentence assessment written like a senior macro strategist's morning note. Be specific about what the data shows, reference actual numbers, and give a clear directional view. No hedging or vague language. End with one concrete action.>",
  "factors": [
    {{"label": "<factor name>", "assessment": "<1-3 word summary>", "bias": "bull|bear|neutral"}},
    ... (include 4-6 factors covering trend, vol, credit, sentiment, breadth, systemic)
  ],
  "stance": "<2-3 word market stance, e.g. 'Defensively Long', 'Risk Off', 'Cautiously Bullish'>",
  "conviction": "high|medium|low"
}}"""

    system = (
        "You are a senior macro strategist at a systematic hedge fund. "
        "You synthesize quantitative regime signals into clear, actionable assessments. "
        "Be direct and opinionated — PMs pay you for conviction, not caveats. "
        "Always reference specific data points to support your view."
    )

    try:
        text = _call_llm(system, prompt, max_tokens=600)
        result = json.loads(text) if text.strip().startswith("{") else None
        if not result:
            result = _parse_json_from_text(text)
        if result and "narrative" in result:
            return result
    except Exception as e:
        logger.warning(f"Claude regime insight failed: {e}")

    # Fallback: build from existing alpha_insights
    fallback_narrative = "; ".join(
        f"{ins.get('category', '')}: {ins.get('action', '')}" for ins in insights[:2]
    ) or "Mixed regime — monitor key signals for directional clarity."

    return {
        "narrative": fallback_narrative,
        "factors": [],
        "stance": regime_data.get("regime", "neutral").title(),
        "conviction": "low",
    }


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


def _enrich_claude_drivers(
    parsed: Dict[str, Any], macro: dict, sectors: list,
    prefetched_news: list = None,
) -> Dict[str, Any]:
    """Enrich Claude's driver response with quantitative features.

    Adds impact scores, contrarian signals, per-driver metrics, and real news articles
    that the frontend is built to display (ImpactBadge, ContrarianBadge, MetricChip, NewsItem).

    Uses prefetched_news (from web search + RSS already done in step 2) rather than
    making another slow RSS call, which avoids Railway timeouts.
    """
    from backend.services.smart_analysis import (
        _calculate_impact_score,
        _detect_contrarian_signal,
    )

    drivers = parsed.get("drivers", [])

    # ── Build per-driver metrics from macro data based on affected assets ──
    metric_map = {
        "SPY": lambda: {"label": "S&P 500", "value": f"${macro.get('SPY', {}).get('price', 0):.2f}", "direction": "up" if (macro.get("SPY", {}).get("pct_change") or 0) > 0 else "down"},
        "QQQ": lambda: {"label": "Nasdaq", "value": f"${macro.get('QQQ', {}).get('price', 0):.2f}", "direction": "up" if (macro.get("QQQ", {}).get("pct_change") or 0) > 0 else "down"},
        "IWM": lambda: {"label": "Russell 2K", "value": f"${macro.get('IWM', {}).get('price', 0):.2f}", "direction": "up" if (macro.get("IWM", {}).get("pct_change") or 0) > 0 else "down"},
        "^VIX": lambda: {"label": "VIX", "value": f"{macro.get('^VIX', {}).get('price', 0):.1f}", "direction": "up" if (macro.get("^VIX", {}).get("price") or 0) > 20 else "down"},
        "^TNX": lambda: {"label": "10Y Yield", "value": f"{macro.get('^TNX', {}).get('price', 0):.2f}%", "direction": "up" if (macro.get("^TNX", {}).get("price") or 0) > 4.0 else "down"},
        "CL=F": lambda: {"label": "Crude Oil", "value": f"${macro.get('CL=F', {}).get('price', 0):.0f}", "direction": "up" if (macro.get("CL=F", {}).get("pct_change") or 0) > 0 else "down"},
        "GC=F": lambda: {"label": "Gold", "value": f"${macro.get('GC=F', {}).get('price', 0):,.0f}", "direction": "up" if (macro.get("GC=F", {}).get("pct_change") or 0) > 0 else "down"},
        "DX-Y.NYB": lambda: {"label": "Dollar", "value": f"{macro.get('DX-Y.NYB', {}).get('price', 0):.1f}", "direction": "up" if (macro.get("DX-Y.NYB", {}).get("pct_change") or 0) > 0 else "down"},
        "TLT": lambda: {"label": "10Y Yield", "value": f"{macro.get('^TNX', {}).get('price', 0):.2f}%", "direction": "up" if (macro.get("^TNX", {}).get("price") or 0) > 4.0 else "down"},
    }

    # Also map sector tickers to their data
    sector_data = {s.get("ticker", ""): s for s in sectors} if sectors else {}
    for ticker, s in sector_data.items():
        if ticker not in metric_map:
            pct = s.get("daily_pct_change") or s.get("pct_change") or 0
            price = s.get("price", 0)
            metric_map[ticker] = lambda t=ticker, p=price, pc=pct: {
                "label": t, "value": f"${p:.2f}" if p else f"{pc:+.2f}%",
                "direction": "up" if pc > 0 else "down"
            }

    # ── Keyword mapping for news search per driver ──
    driver_news_keywords = {
        "sector": ["sector", "rotation", "cyclical", "defensive"],
        "vix": ["volatility", "vix", "fear", "options", "hedge"],
        "vol": ["volatility", "vix", "fear", "options", "hedge"],
        "yield": ["treasury", "yield", "bond", "rate", "fed"],
        "bond": ["treasury", "yield", "bond", "rate", "fed"],
        "treasury": ["treasury", "yield", "bond", "rate", "fed"],
        "oil": ["oil", "crude", "opec", "energy", "petroleum"],
        "gold": ["gold", "commodity", "precious", "metals"],
        "dollar": ["dollar", "currency", "forex", "dxy"],
        "tech": ["technology", "tech", "semiconductor", "software", "ai"],
        "inflation": ["inflation", "cpi", "pce", "prices"],
        "fed": ["federal reserve", "fed", "rate", "monetary policy"],
        "geopolitical": ["geopolitical", "war", "tariff", "trade", "sanctions"],
        "china": ["china", "trade", "tariff", "asia"],
    }

    all_news = []
    for driver in drivers:
        # Build metrics from affected_assets
        if not driver.get("metrics"):
            driver_metrics = []
            for asset in driver.get("affected_assets", [])[:4]:
                if asset in metric_map:
                    try:
                        m = metric_map[asset]()
                        if m.get("value") and m["value"] not in ("$0.00", "0.0", "$0"):
                            driver_metrics.append(m)
                    except Exception:
                        pass
            driver["metrics"] = driver_metrics

        # Match news articles from prefetched results (already fetched in step 2)
        if not driver.get("news_articles") and prefetched_news:
            title_lower = (driver.get("title") or "").lower()
            headline_lower = (driver.get("headline") or "").lower()
            keywords = []
            for key, kws in driver_news_keywords.items():
                if key in title_lower or key in headline_lower:
                    keywords.extend(kws)
                    break
            # Add affected assets as keywords too
            for asset in driver.get("affected_assets", [])[:3]:
                keywords.append(asset.lower())

            # Score and match prefetched articles by keyword relevance
            matched = []
            for article in prefetched_news:
                headline_lower = (article.get("headline") or article.get("title") or "").lower()
                score = sum(1 for kw in keywords if kw in headline_lower) if keywords else 0
                if score > 0 or not keywords:
                    matched.append((score, article))
            matched.sort(key=lambda x: x[0], reverse=True)
            news_articles = [a for _, a in matched[:6]]
            driver["news_articles"] = news_articles
            all_news.extend(news_articles)

            # If no articles matched from prefetched news, do a targeted DDG search
            if not news_articles and driver.get("title"):
                try:
                    from backend.services.web_search import _search_ddg_news
                    ddg_results = _search_ddg_news(driver["title"][:80], max_results=3)
                    if ddg_results:
                        driver["news_articles"] = ddg_results
                except Exception:
                    pass

        # Calculate impact score
        if not driver.get("impact_score"):
            driver["impact_score"] = _calculate_impact_score(driver, macro, all_news)

        # Detect contrarian signal
        if not driver.get("contrarian_signal"):
            contrarian = _detect_contrarian_signal(driver.get("news_articles", []))
            if contrarian:
                driver["contrarian_signal"] = contrarian

    parsed["drivers"] = drivers
    return parsed


async def generate_morning_drivers(date: str) -> Dict[str, Any]:
    """Generate 5 market drivers for the given date.

    Pipeline:
    1. Fetch real macro data + sector performance
    2. Fetch real-time news via web search (DDG) + RSS feeds
    3. Pass ALL context (data + news) to Claude for synthesis
    4. Fall back to data-driven analysis if Claude fails
    """
    from backend.services.smart_analysis import generate_smart_drivers

    # Step 1: Get real market data for data-driven analysis
    try:
        macro = get_macro_data()
        from backend.services.data_provider import get_sector_data
        sectors = get_sector_data(period="1D")
    except Exception as e:
        logger.warning(f"Could not fetch market data: {e}")
        macro, sectors = {}, []

    # Step 2: Fetch real-time news via web search + RSS
    news_context = ""
    fetched_news = []  # Keep reference for enrichment later
    try:
        from backend.services.web_search import search_market_news, format_news_for_prompt
        fetched_news = search_market_news(macro_data=macro, max_total=15)
        if fetched_news:
            news_context = format_news_for_prompt(fetched_news, max_articles=15)
            logger.info(f"Fetched {len(fetched_news)} news articles for drivers prompt")
        else:
            logger.warning("No news articles found from web search + RSS")
    except Exception as e:
        logger.warning(f"News fetch failed (will use data-only mode): {e}")

    # Step 3: Try LLM-enhanced generation with data + news context
    if not USE_MOCK and macro:
        try:
            prompt = morning_drivers.get_morning_drivers_prompt(
                date, macro=macro, sectors=sectors, news_context=news_context
            )
            model_id = get_model_id()
            logger.info(f"Generating morning drivers with model: {model_id} (news_articles={bool(news_context)})")

            text_content = _call_llm(BASE_SYSTEM_PROMPT, prompt, max_tokens=2500)
            parsed = _parse_json_from_text(text_content)
            # Validate: must have at least 2 proper drivers with titles
            if parsed and isinstance(parsed.get("drivers"), list) and len(parsed["drivers"]) >= 2:
                # Verify drivers have required fields
                valid = all(
                    d.get("title") and d.get("market_implications")
                    for d in parsed["drivers"][:3]
                )
                if valid:
                    # Enrich Claude's drivers with quantitative features
                    parsed = _enrich_claude_drivers(parsed, macro, sectors, prefetched_news=fetched_news)
                    return parsed
                else:
                    logger.warning("LLM drivers missing required fields, falling back to data-driven")
            else:
                logger.warning(f"LLM returned invalid drivers (count={len(parsed.get('drivers', []))}), falling back to data-driven")
        except Exception as e:
            logger.warning(f"LLM generation failed, using data-driven analysis: {e}")

    # Step 3: Data-driven analysis (always works, uses real market data)
    if macro or sectors:
        logger.info("Using data-driven smart analysis for morning drivers")
        return generate_smart_drivers(date, macro, sectors)

    # Step 4: Static mock as last resort
    logger.info("Using static mock morning drivers")
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
    from backend.services.quant_grader import grade_stock_quantitative

    if USE_MOCK:
        logger.info(f"Using quantitative grader for stock: {ticker}")
        return grade_stock_quantitative(ticker, data)

    try:
        company_name = data.get("name", ticker)

        # Get regime-adaptive weights
        weights, regime = _get_regime_context()

        prompt = stock_grader.get_stock_grader_prompt(
            ticker, company_name, data,
            weights=weights, regime=regime
        )
        model_id = get_model_id()
        logger.info(f"Grading {ticker} with model: {model_id} | regime: {regime}")

        text_content = _call_llm(BASE_SYSTEM_PROMPT, prompt, max_tokens=4000)
        parsed = _parse_json_from_text(text_content)
        if parsed:
            return parsed

        return {"ticker": ticker, "grade": "HOLD", "raw_response": text_content}

    except Exception as e:
        logger.warning(f"Error grading stock {ticker}, falling back to quantitative grader: {e}")
        from backend.services.quant_grader import grade_stock_quantitative
        return grade_stock_quantitative(ticker, data)


async def generate_morning_report(date: str) -> Dict[str, Any]:
    """Generate condensed morning market report (non-streaming).

    Strategy: Always try data-driven analysis first (works without LLM).
    Only call OpenRouter if key is valid and available.
    """
    from backend.services.smart_analysis import generate_smart_report

    # Step 1: Get real market data
    try:
        macro = get_macro_data()
        from backend.services.data_provider import get_sector_data
        sectors = get_sector_data(period="1D")
    except Exception as e:
        logger.warning(f"Could not fetch market data for report: {e}")
        macro, sectors = {}, []

    # Step 2: Try LLM-enhanced generation if available
    if not USE_MOCK:
        try:
            prompt = morning_report.get_morning_report_prompt(date)
            model_id = get_model_id()
            logger.info(f"Generating morning report with model: {model_id}")

            text_content = _call_llm(BASE_SYSTEM_PROMPT, prompt, max_tokens=3000)
            parsed = _parse_json_from_text(text_content)
            if parsed:
                return parsed
        except Exception as e:
            logger.warning(f"LLM report failed, using data-driven analysis: {e}")

    # Step 3: Data-driven analysis (always works, uses real market data)
    if macro or sectors:
        logger.info("Using data-driven smart analysis for morning report")
        return generate_smart_report(date, macro, sectors)

    # Step 4: Static fallback
    logger.info("Using static mock morning report (no data available)")
    result = mock_data.MOCK_MORNING_DRIVERS.copy()
    result["date"] = date
    return result


async def generate_weekly_report(end_date: str) -> AsyncGenerator[str, None]:
    """Generate weekly report — data-driven, no LLM needed."""
    from backend.services.smart_analysis import generate_smart_weekly_report

    try:
        macro = get_macro_data()
        from backend.services.data_provider import get_sector_data
        sectors = get_sector_data(period="5D")
        report = generate_smart_weekly_report(end_date, macro, sectors)
        yield json.dumps(report)
    except Exception as e:
        logger.warning(f"Error generating weekly report: {e}")
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
        model_id = get_model_id()
        logger.info(f"Running screener with model: {model_id}")

        text_content = _call_llm(BASE_SYSTEM_PROMPT, prompt, max_tokens=3000)
        parsed = _parse_json_from_text(text_content)
        if parsed:
            return parsed

        return {"date": date, "results": [], "raw_response": text_content}

    except Exception as e:
        logger.warning(f"Error running screener, falling back to mock: {e}")
        result = mock_data.MOCK_SCREENER_RESULTS.copy()
        result["date"] = date
        return result
