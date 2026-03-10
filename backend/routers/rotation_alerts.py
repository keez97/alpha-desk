"""
Rotation Alerts API Router - REST endpoints for RRG rotation detection.

Provides endpoints for:
- GET /api/rotation-alerts: Real-time alerts (computed from current RRG data)
- GET /api/rotation-alerts/history: Historical alerts from database
- POST /api/rotation-alerts/scan: Scan for new alerts and persist to DB
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from backend.database import get_session
from backend.models.rotation_alerts import RotationAlert
from backend.services.rotation_alert_engine import RotationAlertEngine
from backend.services.rrg_calculator import calculate_rrg, SECTOR_ETFS

router = APIRouter(prefix="/api/rotation-alerts", tags=["rotation-alerts"])


# ==================== Pydantic Response Models ====================


class RotationAlertResponse(BaseModel):
    """Rotation alert response."""
    id: Optional[int] = None
    ticker: str
    sector: str
    alert_type: str
    from_quadrant: Optional[str] = None
    to_quadrant: Optional[str] = None
    rs_ratio: float
    rs_momentum: float
    description: str
    severity: str
    created_at: datetime
    acknowledged: bool = False

    class Config:
        from_attributes = True


class AlertsScanResponse(BaseModel):
    """Response from scan operation."""
    alerts_generated: int
    alerts_persisted: int
    alerts: List[RotationAlertResponse]


# ==================== Endpoints ====================


@router.get("/")
def get_rotation_alerts(benchmark: str = "SPY", weeks: int = 10) -> dict:
    """
    Get current rotation alerts based on live RRG data.

    Computes alerts on-the-fly without persisting to database.
    Includes current RRG metrics alongside alerts.

    Args:
        benchmark: Benchmark ticker (default: SPY)
        weeks: Number of weeks for RS-Momentum calculation (default: 10)

    Returns:
        Dict with alerts list and RRG data
    """
    try:
        # Calculate current RRG
        tickers = list(SECTOR_ETFS.keys())
        rrg_data = calculate_rrg(tickers, benchmark=benchmark, weeks=weeks)

        # Detect alerts from RRG data
        if "error" in rrg_data:
            return {"alerts": [], "error": rrg_data["error"]}

        alerts = RotationAlertEngine.detect_alerts(rrg_data)

        # Sort by severity (critical > warning > info)
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        alerts.sort(key=lambda x: severity_order.get(x.get("severity"), 3))

        return {
            "alerts": alerts,
            "benchmark": benchmark,
            "weeks": weeks,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "alerts": [],
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/history")
def get_alert_history(
    session: Session = Depends(get_session),
    limit: int = 100,
    severity: Optional[str] = None,
) -> dict:
    """
    Get historical rotation alerts from database.

    Args:
        session: Database session
        limit: Maximum number of alerts to return (default: 100)
        severity: Filter by severity ('critical', 'warning', 'info'), optional

    Returns:
        Dict with historical alerts list
    """
    try:
        query = select(RotationAlert).order_by(RotationAlert.created_at.desc())

        if severity:
            query = query.where(RotationAlert.severity == severity)

        query = query.limit(limit)
        alerts = session.exec(query).all()

        return {
            "alerts": [
                RotationAlertResponse.from_orm(alert).dict() for alert in alerts
            ],
            "total": len(alerts),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "alerts": [],
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.post("/scan")
def scan_for_alerts(
    session: Session = Depends(get_session),
    benchmark: str = "SPY",
    weeks: int = 10,
) -> AlertsScanResponse:
    """
    Scan for new rotation alerts and persist them to database.

    Computes alerts from current RRG data and saves non-duplicate alerts
    to the database for historical tracking.

    Args:
        session: Database session
        benchmark: Benchmark ticker (default: SPY)
        weeks: Number of weeks for RS-Momentum calculation (default: 10)

    Returns:
        AlertsScanResponse with count of alerts generated and persisted
    """
    try:
        # Calculate current RRG
        tickers = list(SECTOR_ETFS.keys())
        rrg_data = calculate_rrg(tickers, benchmark=benchmark, weeks=weeks)

        if "error" in rrg_data:
            return AlertsScanResponse(
                alerts_generated=0, alerts_persisted=0, alerts=[]
            )

        # Detect alerts
        detected_alerts = RotationAlertEngine.detect_alerts(rrg_data)

        # Persist alerts (avoid duplicates from same timestamp)
        persisted_alerts = []
        for alert_data in detected_alerts:
            # Check if alert already exists (same ticker, type, and created_at within same minute)
            existing = session.exec(
                select(RotationAlert).where(
                    RotationAlert.ticker == alert_data["ticker"],
                    RotationAlert.alert_type == alert_data["alert_type"],
                )
            ).first()

            # Only persist if it doesn't already exist
            if not existing:
                alert_obj = RotationAlert(
                    ticker=alert_data["ticker"],
                    sector=alert_data["sector"],
                    alert_type=alert_data["alert_type"],
                    from_quadrant=alert_data.get("from_quadrant"),
                    to_quadrant=alert_data.get("to_quadrant"),
                    rs_ratio=alert_data["rs_ratio"],
                    rs_momentum=alert_data["rs_momentum"],
                    description=alert_data["description"],
                    severity=alert_data["severity"],
                )
                session.add(alert_obj)
                persisted_alerts.append(alert_obj)

        session.commit()

        # Return response
        return AlertsScanResponse(
            alerts_generated=len(detected_alerts),
            alerts_persisted=len(persisted_alerts),
            alerts=[
                RotationAlertResponse.from_orm(alert).dict()
                for alert in persisted_alerts
            ],
        )
    except Exception as e:
        return AlertsScanResponse(
            alerts_generated=0,
            alerts_persisted=0,
            alerts=[],
        )
