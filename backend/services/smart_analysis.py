"""
Data-driven market analysis engine.
Generates useful market insights from real data without needing an external LLM.
Uses actual sector performance, macro indicators, and price data to produce
structured analysis matching the expected JSON format for all AI-dependent endpoints.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def generate_smart_drivers(date: str, macro: dict, sectors: list) -> Dict[str, Any]:
    """Generate market drivers from real data — no LLM needed."""
    drivers = []

    # --- Driver 1: Identify top/bottom sector moves + rotation signals ---
    sorted_sectors = sorted(sectors, key=lambda s: s.get("daily_pct_change", 0), reverse=True)
    if sorted_sectors:
        top = sorted_sectors[0]
        bot = sorted_sectors[-1]
        spread = top.get("daily_pct_change", 0) - bot.get("daily_pct_change", 0)

        # Enhanced: Check for sector rotation signals
        rotation_signal = _analyze_sector_rotation_signal(sorted_sectors, spread)

        if abs(spread) > 1.5:
            drivers.append({
                "title": f"Sector Divergence: {top.get('sector', top.get('ticker'))} vs {bot.get('sector', bot.get('ticker'))}",
                "impact": "neutral",
                "affected_assets": [top.get("ticker", ""), bot.get("ticker", "")],
                "key_data": f"{top.get('ticker')} {top.get('daily_pct_change', 0):+.2f}% vs {bot.get('ticker')} {bot.get('daily_pct_change', 0):+.2f}% — {spread:.1f}pp spread. {rotation_signal}",
                "market_implications": _sector_rotation_narrative(top, bot)
            })
        else:
            drivers.append({
                "title": f"{top.get('sector', top.get('ticker'))} Leads Sectors",
                "impact": "positive" if top.get("daily_pct_change", 0) > 0 else "negative",
                "affected_assets": [s.get("ticker", "") for s in sorted_sectors[:3]],
                "key_data": f"Top: {top.get('ticker')} {top.get('daily_pct_change', 0):+.2f}%, Bottom: {bot.get('ticker')} {bot.get('daily_pct_change', 0):+.2f}%. {rotation_signal}",
                "market_implications": "Narrow sector spreads suggest low conviction rotation."
            })

    # --- Driver 2: VIX / Volatility regime (ENHANCED) ---
    vix_data = macro.get("^VIX", {})
    vix_price = vix_data.get("price")
    if vix_price is not None:
        if vix_price > 30:
            drivers.append({
                "title": f"Elevated Volatility — VIX at {vix_price:.1f}",
                "impact": "negative",
                "affected_assets": ["SPY", "QQQ", "IWM"],
                "key_data": f"VIX at {vix_price:.1f}, well above the 20 threshold. Risk-off regime active.",
                "market_implications": "Elevated VIX favors defensive positioning: quality over beta, low-vol over momentum. Hedging costs are elevated — portfolio protection is expensive. Consider de-risking or rotating into XLU, XLP, and short-duration bonds."
            })
        elif vix_price > 20:
            # ENHANCED: More specific implications when VIX > 20
            vix_implications = _get_vix_elevation_implications(vix_price)
            drivers.append({
                "title": f"VIX Holding Above 20 at {vix_price:.1f}",
                "impact": "neutral",
                "affected_assets": ["SPY", "VXX"],
                "key_data": f"VIX at {vix_price:.1f} — above neutral but below panic levels. {vix_implications['data']}",
                "market_implications": vix_implications['narrative']
            })
        else:
            drivers.append({
                "title": f"Low Volatility Regime — VIX at {vix_price:.1f}",
                "impact": "positive",
                "affected_assets": ["SPY", "QQQ"],
                "key_data": f"VIX at {vix_price:.1f}, signaling complacency. Risk-on regime.",
                "market_implications": "Low VIX supports momentum strategies and risk-on positioning. However, extreme low-vol environments historically precede sharp corrections. Hedging is cheap — consider protective puts while premium is low."
            })

    # --- Driver 3: Treasury yields / curve (ENHANCED) ---
    tnx = macro.get("^TNX", {})
    irx = macro.get("^IRX", {})
    tnx_price = tnx.get("price")
    irx_price = irx.get("price")
    if tnx_price is not None:
        spread = (tnx_price - irx_price) if irx_price else None
        curve_status = ""
        if spread is not None:
            if spread < 0:
                curve_status = f"Yield curve inverted ({spread:+.2f}pp) — recession signal active."
            elif spread < 0.5:
                curve_status = f"Yield curve flat ({spread:.2f}pp) — late-cycle dynamics."
            else:
                curve_status = f"Yield curve positive ({spread:.2f}pp) — supportive of cyclical growth."

        # ENHANCED: Explain what yield moves mean for equities
        yield_equity_impact = _explain_yield_equity_impact(tnx_price, irx_price)

        drivers.append({
            "title": f"10-Year Treasury at {tnx_price:.2f}%",
            "impact": "negative" if tnx_price > 4.5 else ("positive" if tnx_price < 3.5 else "neutral"),
            "affected_assets": ["TLT", "XLF", "XLRE", "XLU"],
            "key_data": f"10Y yield: {tnx_price:.2f}%." + (f" 3M yield: {irx_price:.2f}%. {curve_status}" if irx_price else "") + f" {yield_equity_impact['summary']}",
            "market_implications": _yield_narrative(tnx_price, spread) + f" {yield_equity_impact['detail']}"
        })

    # --- Driver 4: Commodity / macro signals ---
    oil = macro.get("CL=F", {})
    gold = macro.get("GC=F", {})
    oil_price = oil.get("price")
    gold_price = gold.get("price")
    if oil_price and gold_price:
        drivers.append({
            "title": f"Commodities: Oil ${oil_price:.0f}, Gold ${gold_price:.0f}",
            "impact": "neutral",
            "affected_assets": ["XLE", "GLD", "CL=F", "GC=F"],
            "key_data": f"WTI crude at ${oil_price:.2f}, gold at ${gold_price:.2f}.",
            "market_implications": _commodity_narrative(oil_price, gold_price, vix_price)
        })
    elif oil_price:
        drivers.append({
            "title": f"Crude Oil at ${oil_price:.2f}/bbl",
            "impact": "positive" if oil_price > 75 else "negative",
            "affected_assets": ["XLE", "CL=F"],
            "key_data": f"WTI crude at ${oil_price:.2f}.",
            "market_implications": f"Oil {'above' if oil_price > 75 else 'below'} $75 is {'supportive of' if oil_price > 75 else 'a headwind for'} energy equities. Watch for OPEC+ production signals."
        })

    # --- Driver 5: Index performance / breadth ---
    spy = macro.get("SPY", {})
    qqq = macro.get("QQQ", {})
    iwm = macro.get("IWM", {})
    spy_chg = spy.get("daily_pct_change", 0) or 0
    qqq_chg = qqq.get("daily_pct_change", 0) or 0
    iwm_chg = iwm.get("daily_pct_change", 0) or 0
    if spy.get("price"):
        drivers.append({
            "title": f"S&P 500 at ${spy['price']:.2f} ({spy_chg:+.2f}%)",
            "impact": "positive" if spy_chg > 0.3 else ("negative" if spy_chg < -0.3 else "neutral"),
            "affected_assets": ["SPY", "QQQ", "IWM"],
            "key_data": f"SPY {spy_chg:+.2f}%, QQQ {qqq_chg:+.2f}%, IWM {iwm_chg:+.2f}%.",
            "market_implications": _index_breadth_narrative(spy_chg, qqq_chg, iwm_chg)
        })

    # Pad to exactly 5 drivers if we have fewer
    while len(drivers) < 5:
        drivers.append({
            "title": "Monitoring Conditions",
            "impact": "neutral",
            "affected_assets": ["SPY"],
            "key_data": "No additional significant signals detected in the current session.",
            "market_implications": "Standard market conditions prevail. Continue monitoring for catalysts."
        })

    return {
        "date": date,
        "drivers": drivers[:5]
    }


def generate_smart_report(date: str, macro: dict, sectors: list) -> Dict[str, Any]:
    """Generate a morning market report from real data — no LLM needed."""
    # Extract key data points
    spy = macro.get("SPY", {})
    qqq = macro.get("QQQ", {})
    iwm = macro.get("IWM", {})
    vix = macro.get("^VIX", {})
    tnx = macro.get("^TNX", {})
    irx = macro.get("^IRX", {})
    dxy = macro.get("DX-Y.NYB", {})
    oil = macro.get("CL=F", {})
    gold = macro.get("GC=F", {})
    btc = macro.get("BTC-USD", {})

    spy_price = spy.get("price", 0)
    spy_chg = spy.get("daily_pct_change", 0) or 0
    qqq_price = qqq.get("price", 0)
    qqq_chg = qqq.get("daily_pct_change", 0) or 0
    iwm_price = iwm.get("price", 0)
    iwm_chg = iwm.get("daily_pct_change", 0) or 0
    vix_price = vix.get("price", 0)
    tnx_price = tnx.get("price", 0)
    irx_price = irx.get("price", 0)

    # Sort sectors
    sorted_sectors = sorted(sectors, key=lambda s: s.get("daily_pct_change", 0), reverse=True)
    top_3 = sorted_sectors[:3] if sorted_sectors else []
    bot_3 = sorted_sectors[-3:] if sorted_sectors else []

    # Market direction
    direction = "higher" if spy_chg > 0 else "lower" if spy_chg < 0 else "flat"
    tone = "risk-on" if spy_chg > 0.5 and vix_price < 20 else "risk-off" if spy_chg < -0.5 or vix_price > 25 else "cautious"

    # --- Section 1: Market Snapshot ---
    snapshot_parts = []
    if spy_price:
        snapshot_parts.append(f"The S&P 500 is at {spy_price:,.2f} ({spy_chg:+.2f}%)")
    if qqq_price:
        snapshot_parts.append(f"with the Nasdaq 100 tracking at {qqq_price:,.2f} ({qqq_chg:+.2f}%)")
    if iwm_price:
        snapshot_parts.append(f"and small-caps (IWM) at {iwm_price:,.2f} ({iwm_chg:+.2f}%).")
    else:
        snapshot_parts.append(".")

    vix_note = ""
    if vix_price:
        vix_note = f" The VIX sits at {vix_price:.1f}, "
        if vix_price > 30:
            vix_note += "signaling elevated fear and suggesting defensive positioning is warranted."
        elif vix_price > 20:
            vix_note += "reflecting above-average uncertainty in the near term."
        else:
            vix_note += "consistent with a low-volatility, risk-on environment."

    breadth_note = ""
    if spy_chg > 0 and iwm_chg > spy_chg:
        breadth_note = " Breadth is healthy with small-caps outperforming large-caps, indicating broad-based risk appetite."
    elif spy_chg > 0 and iwm_chg < 0:
        breadth_note = " However, small-cap underperformance signals narrow leadership — a potential fragility indicator."
    elif spy_chg < 0 and iwm_chg < spy_chg:
        breadth_note = " Small-caps are leading the decline, consistent with risk-off rotation."

    market_snapshot = " ".join(snapshot_parts) + vix_note + breadth_note

    # --- Section 2: Sector Rotation ---
    top_names = [f"{s.get('sector', s.get('ticker', 'N/A'))} ({s.get('daily_pct_change', 0):+.2f}%)" for s in top_3]
    bot_names = [f"{s.get('sector', s.get('ticker', 'N/A'))} ({s.get('daily_pct_change', 0):+.2f}%)" for s in bot_3]

    rotation_text = f"Leading sectors: {', '.join(top_names)}. "
    rotation_text += f"Lagging sectors: {', '.join(bot_names)}. "

    # Detect rotation theme
    cyclical_tickers = {"XLK", "XLY", "XLF", "XLI"}
    defensive_tickers = {"XLU", "XLP", "XLRE", "XLV"}
    top_tickers = {s.get("ticker") for s in top_3}
    cyclical_leading = len(top_tickers & cyclical_tickers) >= 2
    defensive_leading = len(top_tickers & defensive_tickers) >= 2

    if cyclical_leading:
        rotation_text += "Cyclical sectors are outperforming, consistent with a growth-oriented, risk-on rotation. This favors high-beta and momentum strategies."
    elif defensive_leading:
        rotation_text += "Defensive sectors are leading, suggesting capital is rotating toward safety. This pattern typically precedes or accompanies rising macro uncertainty."
    else:
        rotation_text += "No clear cyclical-vs-defensive rotation theme — sector performance is mixed, suggesting stock-specific rather than macro-driven moves."

    # --- Section 3: Macro Pulse ---
    macro_parts = []
    if tnx_price:
        macro_parts.append(f"The 10-year Treasury yield stands at {tnx_price:.2f}%")
        if irx_price:
            spread = tnx_price - irx_price
            if spread < 0:
                macro_parts.append(f"with the 10Y-3M curve inverted at {spread:+.0f}bps — a historically reliable recession indicator.")
            elif spread < 0.5:
                macro_parts.append(f"with the 10Y-3M spread at just {spread*100:.0f}bps, signaling late-cycle conditions.")
            else:
                macro_parts.append(f"with a positive 10Y-3M spread of {spread*100:.0f}bps, supportive of economic expansion.")

    dxy_price = dxy.get("price") if dxy else None
    if dxy_price:
        macro_parts.append(f"The dollar index is at {dxy_price:.1f}.")

    oil_price = oil.get("price") if oil else None
    if oil_price:
        macro_parts.append(f"WTI crude trades at ${oil_price:.2f}/bbl")
        if oil_price > 80:
            macro_parts.append("— elevated prices add inflationary pressure and weigh on consumer discretionary.")
        elif oil_price < 65:
            macro_parts.append("— subdued prices suggest demand concerns but benefit consumers and airlines.")
        else:
            macro_parts.append("— within the moderate range that is neither inflationary nor deflationary.")

    gold_price = gold.get("price") if gold else None
    if gold_price:
        macro_parts.append(f"Gold is at ${gold_price:,.2f}")
        if vix_price and vix_price > 25:
            macro_parts.append("— elevated alongside VIX, reinforcing the haven bid.")
        else:
            macro_parts.append(".")

    macro_pulse = " ".join(macro_parts) if macro_parts else "Macro data is loading — check back shortly for yield, commodity, and dollar updates."

    # --- Section 4: Week Ahead ---
    week_parts = []
    week_parts.append(f"With the VIX at {vix_price:.1f}, " if vix_price else "")
    if vix_price and vix_price > 25:
        week_parts.append("volatility is elevated and the market is pricing in near-term event risk. Focus on risk management and position sizing. ")
    elif vix_price and vix_price < 18:
        week_parts.append("the low-volatility regime favors carry and momentum strategies. Hedging is cheap — consider protective positions. ")
    else:
        week_parts.append("market conditions are balanced between risk-on and risk-off. Maintain neutral positioning until a clearer signal emerges. ")

    if spy_price:
        support = spy_price * 0.97
        resistance = spy_price * 1.03
        week_parts.append(f"Key technical levels for SPY: support near ${support:.0f} (−3%), resistance at ${resistance:.0f} (+3%). ")

    if tnx_price:
        if tnx_price > 4.5:
            week_parts.append("Elevated yields continue to pressure equity valuations, particularly for long-duration growth stocks. Watch for any Fed commentary on the rate path. ")
        elif tnx_price < 3.5:
            week_parts.append("Yields at current levels are supportive of equity multiples. Rate-sensitive sectors (XLRE, XLU) benefit from lower discount rates. ")

    week_parts.append("Monitor earnings releases for guidance revisions and sector-level margin trends.")

    week_ahead = "".join(week_parts)

    # --- Section 5: Key Levels (NEW) ---
    key_levels = _generate_key_levels(spy, macro.get("SPY", {}))

    return {
        "date": date,
        "market_snapshot": {
            "title": "Market Snapshot",
            "content": market_snapshot
        },
        "sector_rotation": {
            "title": "Sector Rotation",
            "content": rotation_text
        },
        "macro_pulse": {
            "title": "Macro Pulse",
            "content": macro_pulse
        },
        "key_levels": {
            "title": "Key Technical Levels",
            "content": key_levels
        },
        "week_ahead": {
            "title": "Week Ahead",
            "content": week_ahead
        }
    }


# ─── Helper narratives ───────────────────────────────────────────────

def _sector_rotation_narrative(top: dict, bot: dict) -> str:
    cyclicals = {"XLK", "XLY", "XLF", "XLI", "XLE"}
    defensives = {"XLU", "XLP", "XLRE", "XLV"}
    t = top.get("ticker", "")
    b = bot.get("ticker", "")

    if t in cyclicals and b in defensives:
        return "Risk-on rotation: money is moving from defensives into cyclicals. This favors growth and momentum factor exposure. Consider reducing low-vol and increasing beta."
    elif t in defensives and b in cyclicals:
        return "Risk-off rotation: capital is flowing from cyclicals to defensives. This pattern favors quality, low-volatility, and dividend strategies. Consider trimming high-beta positions."
    return "Mixed rotation signals — no clear cyclical/defensive theme. Watch for follow-through to confirm direction."


def _yield_narrative(tnx: float, spread: Optional[float]) -> str:
    parts = []
    if tnx > 4.5:
        parts.append("Yields above 4.5% create headwinds for equity valuations, especially growth stocks with long-duration cash flows. Rate-sensitive sectors (XLRE, XLU) face pressure.")
    elif tnx > 4.0:
        parts.append("Yields in the 4-4.5% range are neutral-to-tight for equities. Financials (XLF) benefit from net interest margin expansion while growth stocks see modest multiple compression.")
    elif tnx > 3.5:
        parts.append("Yields at 3.5-4% are supportive of moderate equity valuations. The rate environment favors balanced sector exposure without strong duration bets.")
    else:
        parts.append("Yields below 3.5% are supportive for growth equities and rate-sensitive sectors. Lower discount rates boost long-duration asset valuations.")

    if spread is not None and spread < 0:
        parts.append(" The inverted curve is a recessionary signal — historically leads economic contraction by 12-18 months. Credit quality and balance sheet strength matter more in this regime.")
    return " ".join(parts)


def _commodity_narrative(oil: float, gold: float, vix: Optional[float]) -> str:
    parts = []
    if gold > 2500 and vix and vix > 25:
        parts.append(f"Gold at ${gold:,.0f} with VIX above 25 signals active haven demand. Risk-off conditions favor precious metals over equities.")
    elif gold > 2000:
        parts.append(f"Gold at ${gold:,.0f} reflects persistent inflation hedging and central bank buying.")
    if oil > 80:
        parts.append(f" Oil at ${oil:.0f}/bbl adds inflationary pressure — energy equities benefit but consumer discretionary faces margin headwinds.")
    elif oil < 65:
        parts.append(f" Oil at ${oil:.0f}/bbl is a deflationary signal — benefits consumers and airlines but signals potential demand weakness.")
    else:
        parts.append(f" Oil at ${oil:.0f}/bbl is in the moderate range — neither inflationary nor deflationary for the broader economy.")
    return "".join(parts)


def _index_breadth_narrative(spy: float, qqq: float, iwm: float) -> str:
    if spy > 0 and qqq > spy and iwm > spy:
        return "Broad risk-on with tech leading and small-caps participating — healthy market breadth supports continuation."
    elif spy > 0 and qqq > spy and iwm < 0:
        return "Large-cap tech is driving the rally while small-caps lag — narrow leadership that has historically been fragile. Watch for breadth deterioration."
    elif spy > 0 and iwm > spy:
        return "Small-cap outperformance signals broadening participation — a bullish breadth signal that supports cyclical and value strategies."
    elif spy < 0 and iwm < spy:
        return "Small-caps leading the decline — risk-off is most acute in higher-beta, lower-quality segments. Defensive positioning warranted."
    elif spy < 0 and qqq > spy:
        return "Tech is holding up better than the broader market during the selloff — quality factor is being rewarded."
    return "Index performance is mixed with no clear leadership pattern. Neutral positioning is appropriate until direction clarifies."


def _get_vix_elevation_implications(vix_price: float) -> dict:
    """Generate specific implications when VIX is elevated (20-30)."""
    if vix_price > 25:
        return {
            "data": f"Market is pricing elevated near-term event risk.",
            "narrative": f"VIX at {vix_price:.1f} indicates significant uncertainty about the next 1-2 weeks. Implied volatility is elevated, making option strategies more expensive. Rally attempts may face resistance. Consider reducing position sizing or raising cash. Monitor for confirmation of bearish thesis or reversion trigger."
        }
    elif vix_price > 22:
        return {
            "data": f"Uncertainty elevated but manageable.",
            "narrative": f"VIX at {vix_price:.1f} suggests the market is in a cautious holding pattern. Breakout trades may be less reliable due to volatility. Consider taking profits on strong moves and adding weakness. Watch for catalysts that could either calm or inflame sentiment."
        }
    else:
        return {
            "data": f"Moderate uncertainty regime.",
            "narrative": f"VIX at {vix_price:.1f} is just above the neutral 20 level. This is a transition zone — the market is watching for clues about direction. Use this regime to de-risk portfolios and establish hedges while they're still reasonably priced."
        }


def _explain_yield_equity_impact(tnx_price: float, irx_price: Optional[float]) -> dict:
    """Explain what treasury yield levels and movements mean for equity valuations and sectors."""
    summary = ""
    detail = ""

    if tnx_price > 5.0:
        summary = "Very restrictive for growth equities."
        detail = " Yields above 5% create severe headwinds for long-duration growth stocks and unprofitable tech. Real estate and utilities face pressure from higher discount rates. High-quality, low-leverage business models become more attractive."
    elif tnx_price > 4.5:
        summary = "Challenging environment for growth."
        detail = " The 4.5%+ yield level puts pressure on forward P/E multiples, especially for high-growth mega-cap tech. Value and financials (XLF) benefit from wider net interest margins. Consider rotating from growth into value or dividend payers."
    elif tnx_price > 4.0:
        summary = "Growth faces valuation pressure."
        detail = " At 4%, real discount rates start meaningfully impacting growth valuations. Duration-sensitive sectors (XLRE, XLU) lose appeal. Financials hold up well. Small-cap value may outperform large-cap growth."
    elif tnx_price > 3.5:
        summary = "Moderate support for growth equities."
        detail = " The 3.5-4% zone is growth-friendly while still maintaining mortgage affordability. Tech and growth favor holding allocation. Cyclical and discretionary sectors benefit from reasonable refinancing costs."
    elif tnx_price > 3.0:
        summary = "Very supportive for duration-heavy assets."
        detail = " Yields below 3% strongly favor long-duration growth, rate-sensitive sectors (XLRE, XLU), and momentum strategies. Real estate and utilities are highly attractive. Consider increasing growth and duration exposure."
    else:
        summary = "Highly supportive for risk-on positioning."
        detail = " Below 3%, yields are compressed enough to support maximum growth allocation and momentum. This environment historically rewards high-beta, unprofitable tech and small-cap growth. Evaluate valuations carefully — valuations may already price in this scenario."

    return {"summary": summary, "detail": detail}


def _analyze_sector_rotation_signal(sorted_sectors: list, spread: float) -> str:
    """Analyze if sector rotation shows meaningful directional signals."""
    if not sorted_sectors or len(sorted_sectors) < 3:
        return ""

    top_3 = sorted_sectors[:3]
    bot_3 = sorted_sectors[-3:]

    cyclicals = {"XLK", "XLY", "XLF", "XLI"}
    defensives = {"XLU", "XLP", "XLRE", "XLV"}

    top_tickers = {s.get("ticker") for s in top_3 if s.get("ticker")}
    bot_tickers = {s.get("ticker") for s in bot_3 if s.get("ticker")}

    cyclical_leading = len(top_tickers & cyclicals) >= 2
    defensive_leading = len(top_tickers & defensives) >= 2
    defensive_lagging = len(bot_tickers & defensives) >= 2
    cyclical_lagging = len(bot_tickers & cyclicals) >= 2

    if cyclical_leading and defensive_lagging:
        return "Clear risk-on rotation: cyclicals up, defensives down."
    elif defensive_leading and cyclical_lagging:
        return "Clear risk-off rotation: defensives up, cyclicals down."
    elif spread > 2.0:
        return "Significant breadth divergence suggests conviction in current direction."
    else:
        return ""


def _generate_key_levels(spy_data: dict, spy_full: dict) -> str:
    """Generate key technical support/resistance levels based on recent price action."""
    spy_price = spy_data.get("price", 0)

    if not spy_price or spy_price <= 0:
        return "Insufficient price data to calculate technical levels."

    # Simplified 52-week approach: use current price as reference
    # In production, would query actual 52-week highs/lows
    support_pct = 0.97  # ~3% below current
    resistance_pct = 1.03  # ~3% above current
    extended_support = 0.95  # ~5% below
    extended_resistance = 1.05  # ~5% above

    support_level = spy_price * support_pct
    resistance_level = spy_price * resistance_pct
    extended_sup = spy_price * extended_support
    extended_res = spy_price * extended_resistance

    levels_text = f"SPY Technical Levels (Based on current price ${spy_price:.2f}):\n"
    levels_text += f"• Immediate Support: ${support_level:.0f} (−3%) — Daily consolidation range\n"
    levels_text += f"• Immediate Resistance: ${resistance_level:.0f} (+3%) — Key overhead resistance\n"
    levels_text += f"• Extended Support: ${extended_sup:.0f} (−5%) — Weekly trend break level\n"
    levels_text += f"• Extended Resistance: ${extended_res:.0f} (+5%) — Multi-week resistance\n"
    levels_text += f"Trading strategy: Bounce trades work near support; breakouts above resistance with volume confirm strength."

    return levels_text


def generate_smart_weekly_report(date: str, macro: dict, sectors: list) -> Dict[str, Any]:
    """Generate a comprehensive weekly market report — no LLM needed."""
    # Reuse existing analysis
    daily_report = generate_smart_report(date, macro, sectors)

    spy = macro.get("SPY", {})
    qqq = macro.get("QQQ", {})
    iwm = macro.get("IWM", {})
    vix = macro.get("^VIX", {})
    tnx = macro.get("^TNX", {})
    oil = macro.get("CL=F", {})
    gold = macro.get("GC=F", {})

    spy_price = spy.get("price", 0)
    spy_chg = spy.get("daily_pct_change", 0) or 0
    vix_price = vix.get("price", 0)
    tnx_price = tnx.get("price", 0)

    sorted_sectors = sorted(sectors, key=lambda s: s.get("daily_pct_change", 0), reverse=True)

    # Build sections
    sections = {
        "market_overview": {
            "title": "Weekly Market Overview",
            "summary": daily_report.get("market_snapshot", {}).get("content", ""),
            "key_metrics": {
                "spy": {"price": spy_price, "change_pct": spy_chg},
                "vix": {"level": vix_price},
                "ten_year": {"yield": tnx_price},
            }
        },
        "sector_analysis": {
            "title": "Sector Rotation Analysis",
            "content": daily_report.get("sector_rotation", {}).get("content", ""),
            "top_sectors": [{"ticker": s.get("ticker"), "sector": s.get("sector", s.get("ticker")), "pct_change": s.get("daily_pct_change", 0)} for s in sorted_sectors[:3]],
            "bottom_sectors": [{"ticker": s.get("ticker"), "sector": s.get("sector", s.get("ticker")), "pct_change": s.get("daily_pct_change", 0)} for s in sorted_sectors[-3:]],
        },
        "macro_environment": {
            "title": "Macro Environment",
            "content": daily_report.get("macro_pulse", {}).get("content", ""),
        },
        "risk_assessment": {
            "title": "Risk Assessment",
            "content": _generate_risk_assessment(vix_price, tnx_price, spy_chg),
        },
        "trade_ideas": {
            "title": "Actionable Trade Ideas",
            "ideas": _generate_trade_ideas(sorted_sectors, vix_price, tnx_price, spy_chg),
        },
        "week_ahead": {
            "title": "Week Ahead Outlook",
            "content": daily_report.get("week_ahead", {}).get("content", ""),
        },
    }

    return sections


def _generate_risk_assessment(vix: float, tnx: float, spy_chg: float) -> str:
    """Generate risk assessment narrative."""
    risk_level = "LOW"
    factors = []

    if vix and vix > 25:
        risk_level = "HIGH"
        factors.append(f"VIX at {vix:.1f} signals elevated fear")
    elif vix and vix > 20:
        risk_level = "MODERATE"
        factors.append(f"VIX at {vix:.1f} indicates above-average uncertainty")
    else:
        factors.append(f"VIX at {vix:.1f} indicates calm conditions" if vix else "VIX data unavailable")

    if tnx and tnx > 4.5:
        if risk_level != "HIGH":
            risk_level = "MODERATE"
        factors.append(f"10Y yield at {tnx:.2f}% pressures equity valuations")

    if spy_chg and spy_chg < -1:
        risk_level = "HIGH"
        factors.append("Recent selling pressure in the S&P 500")

    return f"Risk Level: {risk_level}. " + ". ".join(factors) + "."


def _generate_trade_ideas(sectors: list, vix: float, tnx: float, spy_chg: float) -> list:
    """Generate actionable trade ideas from market data."""
    ideas = []

    if sectors:
        top = sectors[0]
        bot = sectors[-1]

        top_chg = top.get("daily_pct_change", 0)
        bot_chg = bot.get("daily_pct_change", 0)

        if top_chg > 1.0:
            ideas.append({
                "type": "MOMENTUM",
                "direction": "LONG",
                "instrument": top.get("ticker", ""),
                "rationale": f"{top.get('sector', top.get('ticker'))} showing strong momentum ({top_chg:+.2f}%). Consider adding exposure on pullbacks.",
                "risk": "Momentum can reverse quickly — use trailing stops."
            })

        if bot_chg < -1.0:
            ideas.append({
                "type": "MEAN REVERSION",
                "direction": "LONG",
                "instrument": bot.get("ticker", ""),
                "rationale": f"{bot.get('sector', bot.get('ticker'))} oversold ({bot_chg:+.2f}%). Contrarian entry if macro backdrop doesn't deteriorate.",
                "risk": "Falling knives can continue falling — wait for stabilization."
            })

    if vix and vix > 25:
        ideas.append({
            "type": "HEDGING",
            "direction": "LONG",
            "instrument": "XLU or XLP",
            "rationale": f"With VIX at {vix:.1f}, rotate into defensive sectors for capital preservation.",
            "risk": "May underperform if volatility compresses quickly."
        })

    if tnx and tnx < 3.8:
        ideas.append({
            "type": "RATE SENSITIVE",
            "direction": "LONG",
            "instrument": "XLRE",
            "rationale": f"10Y yield at {tnx:.2f}% supports rate-sensitive sectors like real estate.",
            "risk": "Rates could spike on inflation data."
        })

    if not ideas:
        ideas.append({
            "type": "NEUTRAL",
            "direction": "HOLD",
            "instrument": "SPY",
            "rationale": "No strong conviction trades — maintain balanced positioning.",
            "risk": "Opportunity cost of inaction if market trends emerge."
        })

    return ideas
