"""
Notification models for the Alert Notification Pipeline.

Provides tables for:
- Notification: Individual notifications for rotation alerts, confluence changes, etc.
- NotificationConfig: User configuration for notification delivery (webhook, email, severity filtering)
"""

from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class Notification(SQLModel, table=True):
    """Notification record for alerts pushed to users."""
    __tablename__ = "notification"

    id: Optional[int] = Field(default=None, primary_key=True)
    type: str = Field(
        index=True,
        description="notification type: rotation_alert, confluence_change, earnings_catalyst, breakout"
    )
    severity: str = Field(
        index=True,
        description="severity level: critical, warning, info"
    )
    title: str = Field(description="Short notification title")
    body: str = Field(description="Full notification message")
    ticker: Optional[str] = Field(default=None, index=True, description="Optional ticker symbol")
    sector: Optional[str] = Field(default=None, description="Optional sector name")
    read: bool = Field(default=False, index=True, description="Whether the notification has been read")
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    webhook_sent: bool = Field(default=False, description="Whether webhook was successfully sent")
    email_sent: bool = Field(default=False, description="Whether email was successfully sent")


class NotificationConfig(SQLModel, table=True):
    """User configuration for notification delivery."""
    __tablename__ = "notification_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for external notifications")
    email: Optional[str] = Field(default=None, description="Email address for notifications")
    enabled_types: str = Field(
        default='["rotation_alert", "confluence_change", "earnings_catalyst", "breakout"]',
        description="JSON array of enabled notification types"
    )
    min_severity: str = Field(default="warning", description="Minimum severity to send: info, warning, critical")
