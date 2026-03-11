from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from datetime import datetime, timedelta, date
import asyncio
import json
import logging
import time
from backend.services.data_provider import get_macro_data


def _json_serial(obj):
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

from backend.database import get_session
from backend.models.cache import MorningBriefCache, MorningReportCache
from backend.config import CACHE_TTL_HOURS
from backend.services.data_provider import get_macro_data, get_sector_data, get_sector_chart_data
from backend.services.claude_service import generate_morning_drivers, generate_morning_report
from backend.services.market_breadth_engine import calculate_breadth
from backend.services.regime_detector import detect_regime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/morning-brief", tags=["morning-brief"])

REPORT_CACHE_TTL_HOURS = 4  # Morning report refreshes every 4 hours


@router.get("/debug/yahoo")
async def debug_yahoo():
    """Debug endpoint to test yahoo_direct on Railway."""
    from backend.services import yahoo_direct as yd
    from backend.services.cache import cache as global_cache
    import traceback

    results = {}

    # Test 1: Single quote
    try:
        quote = yd.get_quote("SPY")
        results["spy_quote"] = quote if quote else "None returned"
    except Exception as e:
        results["spy_quote_error"] = f"{e}\n{traceback.format_exc()}"

    # Test 2: Rate limit state
    results["rate_limited"] = yd._is_rate_limited()
    results["consecutive_failures"] = yd._consecutive_failures
    results["rate_limited_until"] = yd._rate_limited_until

    # Test 3: Cache state
    try:
        macro_cached = global_cache.get("macro:all")
        results["macro_cache_keys"] = list(macro_cached.keys()) if macro_cached else "not cached"
        results["macro_cache_has_spy"] = "SPY" in macro_cached if macro_cached else False
    except Exception as e:
        results["macro_cache_error"] = str(e)

    # Test 4: Clear macro cache and force refetch
    try:
        global_cache.delete("macro:all")
        results["macro_cache_cleared"] = True
    except Exception:
        try:
            # TTLCache might not have delete - try invalidating
            global_cache.set("macro:all", None, 0)
            results["macro_cache_invalidated"] = True
        except Exception as e:
            results["macro_cache_clear_error"] = str(e)

    return results


@router.get("/macro")
async def get_macro(session: Session = Depends(get_session)):
    """Get macro indicators (VIX, yields, commodities, etc.) with regime detection."""
    macro_data = await asyncio.to_thread(get_macro_data)
    try:
        regime = await asyncio.to_thread(detect_regime, macro_data)
    except Exception as e:
        logger.warning(f"Regime detection failed: {e}")
        regime = {"regime": "neutral", "confidence": 50, "signals": []}
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "data": macro_data,
        "regime": regime
    }


@router.get("/sectors")
async def get_sectors(period: str = "1D", session: Session = Depends(get_session)):
    """Get sector performance data with actual prices and real dates."""
    try:
        sector_data = await asyncio.wait_for(
            asyncio.to_thread(get_sector_chart_data, period=period),
            timeout=20.0  # 20s timeout for sector chart data
        )
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "period": period,
            "sectors": sector_data.get("sectors", [])
        }
    except asyncio.TimeoutError:
        logger.warning(f"Sector chart data timed out for period={period}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "period": period,
            "sectors": [],
            "error": "timeout"
        }
    except Exception as e:
        logger.error(f"Error fetching sector chart data: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "period": period,
            "sectors": [],
            "error": str(e)
        }


@router.get("/drivers")
async def get_drivers(session: Session = Depends(get_session)):
    """Get market drivers, using cache if available."""
    today = datetime.utcnow().date().isoformat()
    cache_key = f"drivers_{today}"

    # Check cache (with error handling for DB issues)
    try:
        cached = session.exec(
            select(MorningBriefCache).where(
                MorningBriefCache.cache_key == cache_key,
                MorningBriefCache.expires_at > datetime.utcnow()
            )
        ).first()

        if cached:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cached": True,
                "data": json.loads(cached.data_json)
            }
    except Exception as e:
        logger.warning(f"Cache read failed for drivers, generating fresh: {e}")

    # Generate new drivers
    drivers = await generate_morning_drivers(today)

    # Cache result (best-effort — don't 500 if cache write fails)
    try:
        expires_at = datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)
        cache_entry = MorningBriefCache(
            cache_key=cache_key,
            data_json=json.dumps(drivers, default=_json_serial),
            expires_at=expires_at
        )
        session.add(cache_entry)
        session.commit()
    except Exception as e:
        logger.warning(f"Cache write failed for drivers: {e}")
        try:
            session.rollback()
        except Exception:
            pass

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cached": False,
        "data": drivers
    }


@router.post("/drivers/refresh")
async def refresh_drivers(session: Session = Depends(get_session)):
    """Force refresh of market drivers."""
    today = datetime.utcnow().date().isoformat()

    # Delete existing cache (best-effort)
    try:
        cache_key = f"drivers_{today}"
        cached = session.exec(
            select(MorningBriefCache).where(MorningBriefCache.cache_key == cache_key)
        ).first()
        if cached:
            session.delete(cached)
            session.commit()
    except Exception as e:
        logger.warning(f"Cache delete failed: {e}")
        try:
            session.rollback()
        except Exception:
            pass

    # Generate new drivers
    drivers = await generate_morning_drivers(today)

    # Cache result (best-effort)
    try:
        expires_at = datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)
        cache_entry = MorningBriefCache(
            cache_key=cache_key,
            data_json=json.dumps(drivers, default=_json_serial),
            expires_at=expires_at
        )
        session.add(cache_entry)
        session.commit()
    except Exception as e:
        logger.warning(f"Cache write failed: {e}")
        try:
            session.rollback()
        except Exception:
            pass

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "data": drivers
    }


@router.get("/report")
async def get_morning_report(session: Session = Depends(get_session)):
    """Get auto-generated morning market report with caching."""
    today = datetime.utcnow().date().isoformat()
    cache_key = f"report_{today}"

    # Check cache (best-effort)
    try:
        cached = session.exec(
            select(MorningReportCache).where(
                MorningReportCache.cache_key == cache_key,
                MorningReportCache.expires_at > datetime.utcnow()
            )
        ).first()

        if cached:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cached": True,
                "data": json.loads(cached.data_json)
            }
    except Exception as e:
        logger.warning(f"Cache read failed for report, generating fresh: {e}")

    # Generate new report
    report = await generate_morning_report(today)

    # Cache result (best-effort)
    try:
        expires_at = datetime.utcnow() + timedelta(hours=REPORT_CACHE_TTL_HOURS)
        cache_entry = MorningReportCache(
            cache_key=cache_key,
            data_json=json.dumps(report, default=_json_serial),
            expires_at=expires_at
        )
        session.add(cache_entry)
        session.commit()
    except Exception as e:
        logger.warning(f"Cache write failed for report: {e}")
        try:
            session.rollback()
        except Exception:
            pass

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cached": False,
        "data": report
    }


@router.post("/report/refresh")
async def refresh_morning_report(session: Session = Depends(get_session)):
    """Force regenerate morning report."""
    today = datetime.utcnow().date().isoformat()
    cache_key = f"report_{today}"

    # Delete existing cache (best-effort)
    try:
        cached = session.exec(
            select(MorningReportCache).where(MorningReportCache.cache_key == cache_key)
        ).first()
        if cached:
            session.delete(cached)
            session.commit()
    except Exception as e:
        logger.warning(f"Cache delete failed: {e}")
        try:
            session.rollback()
        except Exception:
            pass

    # Generate new report
    report = await generate_morning_report(today)

    # Cache result (best-effort)
    try:
        expires_at = datetime.utcnow() + timedelta(hours=REPORT_CACHE_TTL_HOURS)
        cache_entry = MorningReportCache(
            cache_key=cache_key,
            data_json=json.dumps(report, default=_json_serial),
            expires_at=expires_at
        )
        session.add(cache_entry)
        session.commit()
    except Exception as e:
        logger.warning(f"Cache write failed: {e}")
        try:
            session.rollback()
        except Exception:
            pass

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "data": report
    }


@router.get("/breadth")
async def get_breadth():
    """Get market breadth metrics (advance/decline, McClellan, breadth thrust)."""
    try:
        breadth = await asyncio.wait_for(
            asyncio.to_thread(calculate_breadth),
            timeout=15.0  # 15s timeout — breadth cascades through multiple data sources
        )
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data": breadth
        }
    except asyncio.TimeoutError:
        logger.warning("Breadth calculation timed out after 15s")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"error": "timeout", "signal": "neutral", "advances": 0, "declines": 0, "total": 0, "ad_ratio": 1.0}
        }
    except Exception as e:
        logger.error(f"Error calculating breadth: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"error": str(e), "signal": "neutral", "advances": 0, "declines": 0, "total": 0, "ad_ratio": 1.0}
        }


@router.post("/report/custom")
async def custom_report(body: dict):
    """Generate a custom morning report with selected topics."""
    from backend.services.smart_analysis import generate_custom_report
    topics = body.get("topics", ["market_snapshot", "sector_rotation", "macro_pulse", "week_ahead"])
    today = datetime.utcnow().date().isoformat()
    try:
        macro = get_macro_data()
        sectors = get_sector_data(period="1D")
        report = generate_custom_report(today, macro, sectors, topics)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data": report
        }
    except Exception as e:
        logger.error(f"Error generating custom report: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data": {},
            "error": str(e)
        }


@router.get("/scenarios")
async def get_scenarios():
    """Generate Claude-powered scenarios and cache them.

    Called by frontend AFTER initial /all load to upgrade hardcoded scenarios
    with AI-generated ones. Populates the Claude scenario cache so subsequent
    /all calls return them instantly.
    """
    import asyncio
    from backend.services.scenario_risk import (
        _generate_scenarios_with_claude, _scenario_cache, _hardcoded_scenarios
    )
    from backend.services.yfinance_service import get_macro_data

    try:
        macro_data = await asyncio.wait_for(
            asyncio.to_thread(get_macro_data), timeout=10.0
        )
        vix = macro_data.get("^VIX", {}).get("price", 20.0)

        # Try Claude generation (up to 15s)
        claude_scenarios = await asyncio.wait_for(
            asyncio.to_thread(_generate_scenarios_with_claude, macro_data),
            timeout=15.0
        )

        if claude_scenarios and len(claude_scenarios) > 0:
            # Cache for 4 hours so /all picks them up
            _scenario_cache["scenario_risk_claude"] = {
                "ts": time.time(), "data": claude_scenarios
            }
            # Invalidate the fast cache so next /all uses Claude scenarios
            _scenario_cache.pop("scenario_risk_fast", None)
            return {"data": {"scenarios": claude_scenarios, "source": "claude"}}
        else:
            return {"data": {"scenarios": _hardcoded_scenarios(vix), "source": "fallback"}}
    except asyncio.TimeoutError:
        logger.warning("Claude scenario generation timed out")
        return {"data": {"scenarios": _hardcoded_scenarios(20.0), "source": "timeout"}}
    except Exception as e:
        logger.error(f"Error generating scenarios: {e}")
        return {"data": {"scenarios": _hardcoded_scenarios(20.0), "source": "error"}}


@router.get("/scenario-drilldown")
async def scenario_drilldown(scenario_name: str, session: Session = Depends(get_session)):
    """Fetch detailed drill-down analysis for a specific scenario.

    Takes scenario_name as query parameter and returns transmission mechanism,
    historical precedent, positioning ideas, and leading indicators.

    Uses 1-hour cache per scenario name.
    """
    import asyncio
    from backend.services.scenario_risk import get_scenario_risk_fast
    from backend.services.claude_service import _call_llm, USE_MOCK
    from backend.prompts.scenario_prompts import get_scenario_drilldown_prompt

    cache_key = f"scenario_drilldown_{scenario_name}"

    # Check cache first
    try:
        cached = session.exec(
            select(MorningBriefCache).where(
                MorningBriefCache.cache_key == cache_key,
                MorningBriefCache.expires_at > datetime.utcnow()
            )
        ).first()

        if cached:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "scenario_name": scenario_name,
                "cached": True,
                "data": json.loads(cached.data_json)
            }
    except Exception as e:
        logger.warning(f"Cache read failed for drilldown, generating fresh: {e}")

    # Get current macro data and scenarios
    try:
        macro_data = await asyncio.to_thread(get_macro_data)
        risk_data = await asyncio.to_thread(get_scenario_risk_fast, macro_data)
        scenarios = risk_data.get("scenarios", [])
    except Exception as e:
        logger.warning(f"Failed to fetch macro data: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "scenario_name": scenario_name,
            "error": "Could not fetch scenario data"
        }

    # Find the matching scenario
    matching_scenario = None
    for scenario in scenarios:
        if scenario.get("name", "").lower() == scenario_name.lower():
            matching_scenario = scenario
            break

    if not matching_scenario:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "scenario_name": scenario_name,
            "error": f"Scenario '{scenario_name}' not found"
        }

    # Generate drill-down using Claude if available
    if USE_MOCK:
        # Basic fallback response in mock mode
        drilldown_data = {
            "transmission_mechanism": f"In {scenario_name}, market conditions would deteriorate through cascading effects on portfolio composition.",
            "historical_precedent": "Similar scenarios have occurred during previous market stress periods.",
            "portfolio_positioning": [
                "Consider defensive positioning",
                "Reduce risk exposure gradually",
                "Monitor daily market indicators"
            ],
            "leading_indicators": [
                "Watch volatility measures",
                "Monitor correlation changes",
                "Track breadth signals"
            ],
            "counter_argument": "Market pricing may already be reflecting these risks."
        }
    else:
        try:
            # Build drill-down prompt and call Claude
            prompt = get_scenario_drilldown_prompt(matching_scenario, macro_data)

            system_prompt = "You are a senior macro strategist analyzing stress scenarios for a hedge fund. Provide detailed, actionable analysis."

            # Use Sonnet for higher quality drill-down analysis
            text_content = _call_llm(system_prompt, prompt, max_tokens=2000)

            # Parse JSON response
            try:
                drilldown_data = json.loads(text_content)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_start = text_content.find("{")
                json_end = text_content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = text_content[json_start:json_end]
                    drilldown_data = json.loads(json_str)
                else:
                    raise ValueError("Could not parse Claude response as JSON")

        except Exception as e:
            logger.warning(f"Claude drill-down failed: {e}")
            # Basic fallback
            drilldown_data = {
                "transmission_mechanism": f"In {scenario_name}, market conditions would deteriorate through cascading effects.",
                "historical_precedent": "Similar scenarios have occurred during previous market stress periods.",
                "portfolio_positioning": ["Consider defensive positioning"],
                "leading_indicators": ["Watch volatility measures"],
                "counter_argument": "Market pricing may already be reflecting these risks."
            }

    # Cache result (best-effort)
    try:
        expires_at = datetime.utcnow() + timedelta(hours=1)  # 1-hour cache for drill-down
        cache_entry = MorningBriefCache(
            cache_key=cache_key,
            data_json=json.dumps(drilldown_data, default=_json_serial),
            expires_at=expires_at
        )
        session.add(cache_entry)
        session.commit()
    except Exception as e:
        logger.warning(f"Cache write failed for drilldown: {e}")
        try:
            session.rollback()
        except Exception:
            pass

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "scenario_name": scenario_name,
        "cached": False,
        "data": drilldown_data
    }


@router.get("/all")
async def get_all_morning_brief(session: Session = Depends(get_session)):
    """Aggregate endpoint \u2013 returns ALL morning brief panel data in one response.
    Avoids 16+ concurrent browser requests which triggers VM rate-limiting.
    """
    from backend.services.vix_term_structure import get_vix_term_structure
    from backend.services.sector_transitions import get_sector_transitions
    from backend.services.sentiment_velocity import get_sentiment_velocity_fast
    from backend.services.options_flow import get_options_flow
    from backend.services.earnings_brief import get_earnings_brief
    from backend.services.cot_positioning import get_cot_positioning
    from backend.services.scenario_risk import get_scenario_risk_fast
    from backend.services.cross_asset_momentum import get_momentum_spillover
    from backend.services.overnight_returns import get_overnight_returns, ALL_TICKERS as OVERNIGHT_TICKERS
    from backend.services import synthetic_estimator
    from backend.services.data_provider import get_sector_data
    from backend.services.rrg_calculator import calculate_rrg, SECTOR_ETFS

    async def safe(name, fn, *args, timeout_s=4.0, **kwargs):
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(fn, *args, **kwargs),
                timeout=timeout_s  # Cached calls return <100ms; cold calls get 4s
            )
        except asyncio.TimeoutError:
            logger.warning(f"[all] {name} timed out ({timeout_s}s)")
            return None
        except Exception as e:
            logger.warning(f"[all] {name} failed: {e}")
            return None

    # Fetch in small batches (3-4 concurrent) to balance speed vs resource usage.
    # Fully sequential was too slow (15\u00d78s=120s worst case).
    # Fully parallel crashed the server. Batches of 3-4 are the sweet spot.
    logger.info("[all] Starting aggregate fetch (batched)")

    # Batch 1: Core macro data (3 concurrent) — macro gets extra time for yfinance fallback
    macro_raw, breadth_raw, vix_raw = await asyncio.gather(
        safe("macro", get_macro_data, timeout_s=10.0),
        safe("breadth", calculate_breadth),
        safe("vix", get_vix_term_structure),
    )
    # Regime depends on macro result
    regime_raw = await safe("regime", detect_regime, macro_raw or {})

    # Batch 2: Sector data (4 concurrent) — increased timeouts for FDS cascade
    sectors_raw, sector_perf_raw, transitions_raw, rrg_raw = await asyncio.gather(
        safe("sectors", get_sector_chart_data, "1D", timeout_s=15.0),
        safe("sector_perf", get_sector_data, "1D", timeout_s=8.0),
        safe("transitions", get_sector_transitions, timeout_s=15.0),
        safe("rrg", calculate_rrg, list(SECTOR_ETFS.keys()), "SPY", 10, timeout_s=8.0),
    )

    # Batch 3+4 combined: Market signals + analysis (7 concurrent)
    # Must stay under Railway's 30s proxy timeout (4+4+4+8 = 20s worst case)
    # NOTE: overnight uses synthetic estimator (instant) as primary in /all
    # because the full 4-tier cascade (14 tickers × 4 APIs) can't finish in 8s.
    # The dedicated /overnight-returns endpoint still uses the full cascade.
    (sentiment_raw, options_raw, earnings_raw, overnight_raw,
     positioning_raw, risk_raw, spillover_raw) = await asyncio.gather(
        safe("sentiment", get_sentiment_velocity_fast, macro_raw or {}, timeout_s=4.0),
        safe("options", get_options_flow),
        safe("earnings", get_earnings_brief),
        safe("overnight", synthetic_estimator.estimate_overnight_returns, OVERNIGHT_TICKERS, timeout_s=4.0),
        safe("positioning", get_cot_positioning),
        safe("risk", get_scenario_risk_fast, macro_raw or {}, timeout_s=4.0),
        safe("spillover", get_momentum_spillover),
    )
    logger.info("[all] Done")

    ts = datetime.utcnow().isoformat()

    # Build enhanced sectors from sector_perf + rrg
    enhanced_sectors = []
    rrg_sectors = (rrg_raw or {}).get("sectors", [])
    rrg_lookup = {s["ticker"]: s for s in rrg_sectors}
    for sector in (sector_perf_raw or []):
        ticker = sector.get("ticker")
        rrg_info = rrg_lookup.get(ticker, {})
        pct_change = sector.get("daily_pct_change", 0) or 0
        enhanced_sectors.append({
            "ticker": ticker,
            "name": sector.get("sector") or sector.get("name") or ticker,
            "price": sector.get("price", 0),
            "change": sector.get("daily_change", 0),
            "pct_change": pct_change,
            "rs_ratio": rrg_info.get("rs_ratio", round(100 + pct_change * 2, 2)),
            "rs_momentum": rrg_info.get("rs_momentum", round(pct_change * 5, 2)),
            "quadrant": rrg_info.get("quadrant", "Unknown"),
            "tail_length": rrg_info.get("tail_length", 0),
            "quadrant_age": rrg_info.get("quadrant_age", 0),
            "rs_trend": rrg_info.get("rs_trend", "flat"),
            "rotation_direction": rrg_info.get("rotation_direction", "clockwise"),
        })

    result = {
        "timestamp": ts,
        "macro": {"timestamp": ts, "data": macro_raw or {}, "regime": regime_raw or {"regime": "neutral", "confidence": 50, "signals": []}},
        "breadth": {"timestamp": ts, "data": breadth_raw or {}},
        "vix_term_structure": vix_raw or {},
        "sectors": {"timestamp": ts, "period": "1D", "sectors": (sectors_raw or {}).get("sectors", [])},
        "enhanced_sectors": {"timestamp": ts, "period": "1D", "sectors": enhanced_sectors},
        "sector_transitions": transitions_raw or {},
        "sentiment_velocity": sentiment_raw or {},
        "options_flow": options_raw or {},
        "earnings_brief": earnings_raw or {},
        "cot_positioning": positioning_raw or {},
        "scenario_risk": risk_raw or {},
        "momentum_spillover": spillover_raw or {},
        "overnight_returns": {"timestamp": ts, "data": overnight_raw or {}},
    }

    return json.loads(json.dumps(result, default=_json_serial))
