"""Router for scenario-aware risk dashboard."""
import asyncio
from fastapi import APIRouter
from datetime import datetime
import logging
from backend.services.scenario_risk import get_scenario_risk_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["scenario-risk"])


@router.get("/scenario-risk")
async def get_scenario_risk_endpoint():
    """
    Get scenario-aware risk dashboard data including:
    - Historical VaR (95th percentile)
    - Regime-adjusted VaR
    - Historical analogs (3 most similar past periods)
    - Scenario-specific loss estimates (VIX spike, yield curve, correction)
    """
    try:
        data = await asyncio.wait_for(
            asyncio.to_thread(get_scenario_risk_data),
            timeout=20.0,
        )
        return {
            "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
            "var_95_historical": data.get("var_95_historical", 0.0),
            "var_95_regime_adjusted": data.get("var_95_regime_adjusted", 0.0),
            "current_regime": data.get("current_regime", "unknown"),
            "historical_analogs": data.get("historical_analogs", []),
            "scenarios": data.get("scenarios", []),
        }
    except asyncio.TimeoutError:
        logger.warning("Scenario risk timed out after 20s")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "var_95_historical": 0.0,
            "var_95_regime_adjusted": 0.0,
            "current_regime": "unknown",
            "historical_analogs": [],
            "scenarios": [],
            "error": "timeout",
        }
    except Exception as e:
        logger.error(f"Error in get_scenario_risk_endpoint: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "var_95_historical": 0.0,
            "var_95_regime_adjusted": 0.0,
            "current_regime": "unknown",
            "historical_analogs": [],
            "scenarios": [],
            "error": str(e),
        }
