from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from datetime import datetime, timedelta
import json
from backend.database import get_session
from backend.models.cache import MorningBriefCache, MorningReportCache
from backend.config import CACHE_TTL_HOURS
from backend.services.yfinance_service import get_macro_data, get_sector_data
from backend.services.claude_service import generate_morning_drivers, generate_morning_report

router = APIRouter(prefix="/api/morning-brief", tags=["morning-brief"])

REPORT_CACHE_TTL_HOURS = 4  # Morning report refreshes every 4 hours


@router.get("/macro")
def get_macro(session: Session = Depends(get_session)):
    """Get macro indicators (VIX, yields, commodities, etc.)"""
    macro_data = get_macro_data()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "data": macro_data
    }


@router.get("/sectors")
def get_sectors(period: str = "1D", session: Session = Depends(get_session)):
    """Get sector performance data with normalized charts."""
    sector_data = get_sector_data(period=period)
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "period": period,
        "sectors": sector_data
    }


@router.get("/drivers")
async def get_drivers(session: Session = Depends(get_session)):
    """Get market drivers, using cache if available."""
    today = datetime.utcnow().date().isoformat()
    cache_key = f"drivers_{today}"

    # Check cache
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

    # Generate new drivers
    drivers = await generate_morning_drivers(today)

    # Cache result
    expires_at = datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)
    cache_entry = MorningBriefCache(
        cache_key=cache_key,
        data_json=json.dumps(drivers),
        expires_at=expires_at
    )
    session.add(cache_entry)
    session.commit()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cached": False,
        "data": drivers
    }


@router.post("/drivers/refresh")
async def refresh_drivers(session: Session = Depends(get_session)):
    """Force refresh of market drivers."""
    today = datetime.utcnow().date().isoformat()

    # Delete existing cache
    cache_key = f"drivers_{today}"
    cached = session.exec(
        select(MorningBriefCache).where(MorningBriefCache.cache_key == cache_key)
    ).first()
    if cached:
        session.delete(cached)
        session.commit()

    # Generate new drivers
    drivers = await generate_morning_drivers(today)

    # Cache result
    expires_at = datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)
    cache_entry = MorningBriefCache(
        cache_key=cache_key,
        data_json=json.dumps(drivers),
        expires_at=expires_at
    )
    session.add(cache_entry)
    session.commit()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "data": drivers
    }


@router.get("/report")
async def get_morning_report(session: Session = Depends(get_session)):
    """Get auto-generated morning market report with caching."""
    today = datetime.utcnow().date().isoformat()
    cache_key = f"report_{today}"

    # Check cache — return if fresh (< 4 hours old)
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

    # Generate new report (non-streaming)
    report = await generate_morning_report(today)

    # Cache result
    expires_at = datetime.utcnow() + timedelta(hours=REPORT_CACHE_TTL_HOURS)
    cache_entry = MorningReportCache(
        cache_key=cache_key,
        data_json=json.dumps(report),
        expires_at=expires_at
    )
    session.add(cache_entry)
    session.commit()

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

    # Delete existing cache
    cached = session.exec(
        select(MorningReportCache).where(MorningReportCache.cache_key == cache_key)
    ).first()
    if cached:
        session.delete(cached)
        session.commit()

    # Generate new report
    report = await generate_morning_report(today)

    # Cache result
    expires_at = datetime.utcnow() + timedelta(hours=REPORT_CACHE_TTL_HOURS)
    cache_entry = MorningReportCache(
        cache_key=cache_key,
        data_json=json.dumps(report),
        expires_at=expires_at
    )
    session.add(cache_entry)
    session.commit()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "data": report
    }
