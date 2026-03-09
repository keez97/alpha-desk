from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from datetime import datetime
import json
from backend.database import get_session
from backend.models.cache import ScreenerCache
from backend.services.claude_service import run_screener

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.post("/run")
async def run_screener_endpoint(session: Session = Depends(get_session)):
    """Run stock screener and cache results."""
    today = datetime.utcnow().date().isoformat()

    # Run screener
    results = await run_screener(today)

    # Cache results
    cache_entry = ScreenerCache(
        screen_type="daily",
        results_json=json.dumps(results)
    )
    session.add(cache_entry)
    session.commit()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "date": today,
        "results": results
    }


@router.get("/latest")
def get_latest_screener(session: Session = Depends(get_session)):
    """Get most recent screener results."""
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
