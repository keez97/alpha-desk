from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from datetime import datetime
import json
import logging
from backend.database import get_session
from backend.models.cache import ScreenerCache
from backend.services.claude_service import run_screener

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.post("/run")
async def run_screener_endpoint(session: Session = Depends(get_session)):
    """Run stock screener and cache results."""
    try:
        today = datetime.utcnow().date().isoformat()

        # Run screener
        results = await run_screener(today)

        # Cache results
        try:
            cache_entry = ScreenerCache(
                screen_type="daily",
                results_json=json.dumps(results)
            )
            session.add(cache_entry)
            session.commit()
        except Exception as cache_err:
            logger.error(f"Failed to cache screener results: {cache_err}")
            session.rollback()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "date": today,
            "results": results
        }
    except Exception as e:
        logger.error(f"Screener error: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "date": datetime.utcnow().date().isoformat(),
            "results": None
        }


@router.get("/latest")
def get_latest_screener(session: Session = Depends(get_session)):
    """Get most recent screener results."""
    try:
        cached = session.exec(
            select(ScreenerCache).where(
                ScreenerCache.screen_type == "daily"
            )
        ).first()

        if not cached:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "results": None
            }

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "generated_at": cached.generated_at.isoformat(),
            "results": json.loads(cached.results_json)
        }
    except Exception as e:
        logger.error(f"Error getting latest screener results: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "results": None
        }
