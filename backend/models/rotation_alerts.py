"""
Rotation Alerts models for RRG quadrant boundary detection.

Detects when sectors cross RRG quadrant boundaries or show significant momentum changes.
"""

from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class RotationAlert(SQLModel, table=True):
    """Alert for RRG quadrant changes and momentum reversals."""
    __tablename__ = "rotation_alert"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(index=True, description="Sector ETF ticker")
    sector: str = Field(description="Sector name")
    alert_type: str = Field(description="Type: quadrant_change, momentum_reversal, breakout, breakdown")
    from_quadrant: Optional[str] = Field(default=None, description="Previous quadrant")
    to_quadrant: Optional[str] = Field(default=None, description="Current quadrant")
    rs_ratio: float = Field(description="Current RS-Ratio value")
    rs_momentum: float = Field(description="Current RS-Momentum value")
    description: str = Field(description="Human-readable alert description")
    severity: str = Field(default="info", description="info, warning, or critical")
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    acknowledged: bool = Field(default=False)
