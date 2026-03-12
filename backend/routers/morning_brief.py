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
    import httpx

    results = {}

    # Reset rate limit to test fresh
    yd._rate_limited_until = 0
    yd._consecutive_failures = 0
    results["rate_limit_reset"] = True

    # Test 0: Get crumb
    try:
        crumb, cookies = yd._get_crumb_and_cookies()
        results["crumb"] = crumb[:10] + "..." if crumb else "None"
        results["cookies"] = list(cookies.keys()) if cookies else "None"
    except Exception as e:
        results["crumb_error"] = str(e)

    # Test 1: Raw HTTP test (bypassing yahoo_direct entirely)
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            # Try query2 first
            r = client.get(
                "https://query2.finance.yahoo.com/v8/finance/chart/SPY",
                headers=yd._HEADERS,
                params={"range": "2d", "interval": "1d", "crumb": crumb or ""},
                cookies=cookies or {},
            )
            results["raw_query2_status"] = r.status_code
            results["raw_query2_body"] = r.text[:200] if r.status_code != 200 else "OK"
            if r.status_code == 200:
                data = r.json()
                meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
                results["raw_spy_price"] = meta.get("regularMarketPrice")
    except Exception as e:
        results["raw_test_error"] = str(e)

    # Test 2: yahoo_direct quote
    try:
        quote = yd.get_quote("SPY")
        results["spy_quote"] = quote if quote else "None returned"
    except Exception as e:
        results["spy_quote_error"] = f"{e}\n{traceback.format_exc()}"

    # Test 3: Rate limit state after test
    results["rate_limited_after"] = yd._is_rate_limited()
    results["consecutive_failures_after"] = yd._consecutive_failures

    # Test 4: Clear all caches
    try:
        for key in ["macro:all", "sector:1D", "sector:1M", "sector_chart:1M", "sector_chart:1D"]:
            global_cache.set(key, None, 0)
        results["caches_cleared"] = True
    except Exception as e:
        results["cache_clear_error"] = str(e)

    # Test 5: Circuit breaker status
    try:
        from backend.services.circuit_breaker import all_status
        results["circuit_breakers"] = all_status()
    except Exception as e:
        results["circuit_breaker_error"] = str(e)

    return results


@router.get("/debug/circuit-breakers")
async def debug_circuit_breakers():
    """Debug endpoint to check circuit breaker states for all data sources."""
    from backend.services.circuit_breaker import all_status
    from backend.services.cache import cache as global_cache

    return {
        "circuit_breakers": all_status(),
        "cache_stats": global_cache.stats(),
        "timestamp": datetime.utcnow().isoformat(),
    }


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
    """Get auto-generated morning market report with caching.

    Cache is automatically invalidated when the regime changes (e.g. neutral → bear)
    so the report always reflects the current market state.
    """
    today = datetime.utcnow().date().isoformat()

    # Step 1: Get current regime (lightweight, ~30s cached internally)
    current_regime = None
    current_regime_label = "unknown"
    try:
        macro_data = await asyncio.to_thread(get_macro_data)
        current_regime = await asyncio.to_thread(detect_regime, macro_data)
        current_regime_label = current_regime.get("regime", "unknown")
    except Exception as e:
        logger.warning(f"Regime detection for report cache check failed: {e}")

    # Step 2: Check cache — invalidate if regime has shifted
    cache_key = f"report_{today}"
    regime_cache_key = f"report_regime_{today}"

    try:
        cached = session.exec(
            select(MorningReportCache).where(
                MorningReportCache.cache_key == cache_key,
                MorningReportCache.expires_at > datetime.utcnow()
            )
        ).first()

        if cached:
            # Check if regime has changed since the report was cached
            cached_regime = None
            try:
                cached_regime_entry = session.exec(
                    select(MorningReportCache).where(
                        MorningReportCache.cache_key == regime_cache_key
                    )
                ).first()
                if cached_regime_entry:
                    cached_regime = cached_regime_entry.data_json
            except Exception:
                pass

            if cached_regime and cached_regime != current_regime_label:
                logger.info(
                    f"Regime shifted ({cached_regime} → {current_regime_label}), "
                    f"invalidating cached morning report"
                )
                # Delete stale cache entries
                try:
                    session.delete(cached)
                    if cached_regime_entry:
                        session.delete(cached_regime_entry)
                    session.commit()
                except Exception:
                    session.rollback()
            else:
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "cached": True,
                    "data": json.loads(cached.data_json)
                }
    except Exception as e:
        logger.warning(f"Cache read failed for report, generating fresh: {e}")

    # Step 3: Generate new report with regime context
    report = await generate_morning_report(today, regime=current_regime)

    # Step 4: Cache result + regime label (best-effort)
    try:
        expires_at = datetime.utcnow() + timedelta(hours=REPORT_CACHE_TTL_HOURS)
        cache_entry = MorningReportCache(
            cache_key=cache_key,
            data_json=json.dumps(report, default=_json_serial),
            expires_at=expires_at
        )
        session.add(cache_entry)

        # Store the regime label alongside the report for invalidation checks
        regime_entry = session.exec(
            select(MorningReportCache).where(
                MorningReportCache.cache_key == regime_cache_key
            )
        ).first()
        if regime_entry:
            regime_entry.data_json = current_regime_label
            regime_entry.expires_at = expires_at
        else:
            regime_entry = MorningReportCache(
                cache_key=regime_cache_key,
                data_json=current_regime_label,
                expires_at=expires_at
            )
            session.add(regime_entry)

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

    # Get current regime for report context
    current_regime = None
    try:
        macro_data = await asyncio.to_thread(get_macro_data)
        current_regime = await asyncio.to_thread(detect_regime, macro_data)
    except Exception as e:
        logger.warning(f"Regime detection for refreshed report failed: {e}")

    # Generate new report with regime
    report = await generate_morning_report(today, regime=current_regime)

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
        # Fetch current regime so the report reflects systemic risk state
        current_regime = None
        try:
            current_regime = await asyncio.to_thread(detect_regime, macro)
        except Exception as e:
            logger.warning(f"Regime detection for custom report failed: {e}")
        report = generate_custom_report(today, macro, sectors, topics, regime=current_regime)
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
    from backend.services.data_provider import get_macro_data as dp_get_macro

    try:
        macro_data = await asyncio.wait_for(
            asyncio.to_thread(dp_get_macro), timeout=10.0
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


@router.get("/regime-insight")
async def get_regime_insight():
    """Generate a Claude-powered narrative market assessment from regime data.

    Synthesizes all 6 regime layers, VIX term structure, market breadth,
    and overnight gaps into a rich, actionable insight. Cached 15 min.
    """
    from backend.services.vix_term_structure import get_vix_term_structure
    from backend.services.overnight_returns import get_overnight_returns, ALL_TICKERS as OVERNIGHT_TICKERS
    from backend.services import synthetic_estimator
    from backend.services.claude_service import generate_regime_insight, USE_MOCK
    from backend.services.cache import cache as global_cache

    cache_key = "regime_insight"
    cached = global_cache.get(cache_key)
    if cached:
        return {"timestamp": datetime.utcnow().isoformat(), "cached": True, "data": cached}

    # Gather inputs in parallel
    try:
        macro_raw, breadth_raw, vix_raw, overnight_raw = await asyncio.gather(
            asyncio.wait_for(asyncio.to_thread(get_macro_data), timeout=10.0),
            asyncio.wait_for(asyncio.to_thread(calculate_breadth), timeout=8.0),
            asyncio.wait_for(asyncio.to_thread(get_vix_term_structure), timeout=8.0),
            asyncio.wait_for(asyncio.to_thread(synthetic_estimator.estimate_overnight_returns, OVERNIGHT_TICKERS), timeout=4.0),
        )
    except Exception as e:
        logger.warning(f"Data gathering for regime insight failed: {e}")
        macro_raw, breadth_raw, vix_raw, overnight_raw = {}, {}, {}, {}

    # Detect regime
    try:
        regime_raw = await asyncio.wait_for(
            asyncio.to_thread(detect_regime, macro_raw or {}), timeout=20.0
        )
    except Exception as e:
        logger.warning(f"Regime detection failed for insight: {e}")
        regime_raw = {"regime": "neutral", "confidence": 0, "composite_score": 0, "layers": {}, "windham": {}, "recession_probability": None}

    # Generate insight via Claude
    try:
        insight = await asyncio.wait_for(
            asyncio.to_thread(generate_regime_insight, regime_raw, vix_raw or {}, breadth_raw or {}, overnight_raw or {}),
            timeout=15.0,
        )
    except asyncio.TimeoutError:
        logger.warning("Claude regime insight timed out")
        insight = {"narrative": "Insight generation timed out. See factor signals above for current market read.", "factors": [], "stance": "Unknown", "conviction": "low"}
    except Exception as e:
        logger.warning(f"Claude regime insight error: {e}")
        insight = {"narrative": f"Insight unavailable: {e}", "factors": [], "stance": "Unknown", "conviction": "low"}

    # Cache for 15 minutes
    global_cache.set(cache_key, insight, 900)

    return {"timestamp": datetime.utcnow().isoformat(), "cached": False, "data": insight}


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
        safe("breadth", calculate_breadth, timeout_s=10.0),
        safe("vix", get_vix_term_structure),
    )
    # Batch 2a: Sector data + RRG + Regime (4 concurrent)
    # Regime depends on macro result but runs in parallel with sector fetches.
    # Regime needs extra time because detect_regime() internally makes ~10+
    # sequential FRED + Yahoo API calls (VIX, VVIX, yield curve, credit spreads,
    # macro series, SPY history, multi-asset turbulence).
    # On cold starts these can take 8-15s total.
    regime_raw, sectors_raw, sector_perf_raw, rrg_raw = await asyncio.gather(
        safe("regime", detect_regime, macro_raw or {}, timeout_s=20.0),
        safe("sectors", get_sector_chart_data, "1D", timeout_s=15.0),
        safe("sector_perf", get_sector_data, "1D", timeout_s=12.0),
        safe("rrg", calculate_rrg, list(SECTOR_ETFS.keys()), "SPY", 10, timeout_s=12.0),
    )

    # Batch 2b: Sector transitions (reuses rrg_raw + macro_raw to avoid duplicate fetches)
    transitions_raw = await safe("transitions", get_sector_transitions, rrg_raw, macro_raw or {}, timeout_s=15.0)

    # Batch 3+4 combined: Market signals + analysis (7 concurrent)
    # Railway has a 30s proxy timeout. With caching, all batches complete in <5s.
    # On cold starts, regime detection (20s) runs in parallel with sectors (15s).
    # NOTE: overnight uses synthetic estimator (instant) as primary in /all
    # because the full 4-tier cascade (14 tickers × 4 APIs) can't finish in 8s.
    # The dedicated /overnight-returns endpoint still uses the full cascade.
    # NOTE: get_scenario_risk_fast already accepts macro_data parameter
    (sentiment_raw, options_raw, earnings_raw, overnight_raw,
     positioning_raw, risk_raw, spillover_raw) = await asyncio.gather(
        safe("sentiment", get_sentiment_velocity_fast, macro_raw or {}, timeout_s=10.0),
        safe("options", get_options_flow),
        safe("earnings", get_earnings_brief),
        safe("overnight", synthetic_estimator.estimate_overnight_returns, OVERNIGHT_TICKERS, timeout_s=4.0),
        safe("positioning", get_cot_positioning),
        safe("risk", get_scenario_risk_fast, macro_raw or {}, timeout_s=8.0),
        safe("spillover", get_momentum_spillover),
    )
    logger.info("[all] Done")

    # Enrich synthetic overnight returns with real prices from macro + sector data
    if overnight_raw and isinstance(overnight_raw, dict):
        price_map = {}
        # Macro data has SPY, QQQ, IWM, etc.
        if macro_raw and isinstance(macro_raw, dict):
            for k, v in macro_raw.items():
                if isinstance(v, dict) and v.get("price"):
                    price_map[k] = float(v["price"])
        # Sector perf data has XLK, XLF, XLV, etc.
        for sec in (sector_perf_raw or []):
            t = sec.get("ticker", "")
            p = sec.get("price", 0)
            if t and p:
                price_map[t] = float(p)
        # Apply prices to overnight items
        for idx_item in overnight_raw.get("indices", []):
            ticker = idx_item.get("ticker", "")
            price = price_map.get(ticker, 0)
            if price:
                idx_item["last_price"] = round(price, 2)

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
