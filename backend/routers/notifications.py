"""
Notifications API Router - REST endpoints for the Alert Notification Pipeline.

Provides endpoints for:
- GET /api/notifications: List notifications with optional filtering
- GET /api/notifications/count: Get unread notification count
- POST /api/notifications/read/{id}: Mark a notification as read
- POST /api/notifications/read-all: Mark all notifications as read
- GET /api/notifications/config: Get notification configuration
- PUT /api/notifications/config: Update notification configuration
- POST /api/notifications/test-webhook: Send a test notification to webhook
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from backend.database import get_session
from backend.models.notifications import Notification, NotificationConfig
from backend.services.notification_engine import NotificationEngine

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ==================== Pydantic Response Models ====================


class NotificationResponse(BaseModel):
    """Notification response model."""
    id: int
    type: str
    severity: str
    title: str
    body: str
    ticker: Optional[str] = None
    sector: Optional[str] = None
    read: bool
    created_at: datetime
    webhook_sent: bool
    email_sent: bool

    class Config:
        from_attributes = True


class NotificationCountResponse(BaseModel):
    """Response with unread notification count."""
    unread: int


class NotificationConfigResponse(BaseModel):
    """Notification configuration response."""
    id: int
    webhook_url: Optional[str] = None
    email: Optional[str] = None
    enabled_types: List[str]
    min_severity: str

    class Config:
        from_attributes = True


class UpdateConfigRequest(BaseModel):
    """Request to update notification configuration."""
    webhook_url: Optional[str] = None
    email: Optional[str] = None
    enabled_types: Optional[List[str]] = None
    min_severity: Optional[str] = None


class TestWebhookRequest(BaseModel):
    """Request to test a webhook."""
    webhook_url: str


class TestWebhookResponse(BaseModel):
    """Response from webhook test."""
    success: bool
    message: str
    webhook_url: str


# ==================== Endpoints ====================


@router.get("", response_model=List[NotificationResponse])
def list_notifications(
    session: Session = Depends(get_session),
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=500),
) -> List[NotificationResponse]:
    """
    List notifications.

    Args:
        session: Database session
        unread_only: If true, only return unread notifications
        limit: Maximum number of notifications to return (default: 50, max: 500)

    Returns:
        List of notifications
    """
    notifications = NotificationEngine.get_notifications(
        session,
        limit=limit,
        unread_only=unread_only,
    )

    return [
        NotificationResponse(
            id=n.id,
            type=n.type,
            severity=n.severity,
            title=n.title,
            body=n.body,
            ticker=n.ticker,
            sector=n.sector,
            read=n.read,
            created_at=n.created_at,
            webhook_sent=n.webhook_sent,
            email_sent=n.email_sent,
        )
        for n in notifications
    ]


@router.get("/count", response_model=NotificationCountResponse)
def get_notification_count(
    session: Session = Depends(get_session),
) -> NotificationCountResponse:
    """
    Get count of unread notifications.

    Args:
        session: Database session

    Returns:
        NotificationCountResponse with unread count
    """
    count = NotificationEngine.get_unread_count(session)
    return NotificationCountResponse(unread=count)


@router.post("/read/{notification_id}")
def mark_notification_read(
    notification_id: int,
    session: Session = Depends(get_session),
) -> NotificationResponse:
    """
    Mark a single notification as read.

    Args:
        notification_id: ID of the notification to mark as read
        session: Database session

    Returns:
        Updated NotificationResponse

    Raises:
        HTTPException: 404 if notification not found
    """
    notification = NotificationEngine.mark_as_read(session, notification_id)

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    return NotificationResponse(
        id=notification.id,
        type=notification.type,
        severity=notification.severity,
        title=notification.title,
        body=notification.body,
        ticker=notification.ticker,
        sector=notification.sector,
        read=notification.read,
        created_at=notification.created_at,
        webhook_sent=notification.webhook_sent,
        email_sent=notification.email_sent,
    )


@router.post("/read-all")
def mark_all_notifications_read(
    session: Session = Depends(get_session),
) -> dict:
    """
    Mark all notifications as read.

    Args:
        session: Database session

    Returns:
        Dict with count of notifications marked as read
    """
    count = NotificationEngine.mark_all_read(session)
    return {"count": count, "message": f"Marked {count} notifications as read"}


@router.get("/config", response_model=NotificationConfigResponse)
def get_config(
    session: Session = Depends(get_session),
) -> NotificationConfigResponse:
    """
    Get notification configuration.

    Args:
        session: Database session

    Returns:
        NotificationConfigResponse with current configuration
    """
    config = NotificationEngine.get_config(session)

    import json
    enabled_types = json.loads(config.enabled_types)

    return NotificationConfigResponse(
        id=config.id,
        webhook_url=config.webhook_url,
        email=config.email,
        enabled_types=enabled_types,
        min_severity=config.min_severity,
    )


@router.put("/config", response_model=NotificationConfigResponse)
def update_config(
    request: UpdateConfigRequest,
    session: Session = Depends(get_session),
) -> NotificationConfigResponse:
    """
    Update notification configuration.

    Args:
        request: UpdateConfigRequest with fields to update
        session: Database session

    Returns:
        NotificationConfigResponse with updated configuration
    """
    config = NotificationEngine.update_config(
        session,
        webhook_url=request.webhook_url,
        email=request.email,
        enabled_types=request.enabled_types,
        min_severity=request.min_severity,
    )

    import json
    enabled_types = json.loads(config.enabled_types)

    return NotificationConfigResponse(
        id=config.id,
        webhook_url=config.webhook_url,
        email=config.email,
        enabled_types=enabled_types,
        min_severity=config.min_severity,
    )


@router.post("/test-webhook", response_model=TestWebhookResponse)
def test_webhook(
    request: TestWebhookRequest,
) -> TestWebhookResponse:
    """
    Send a test notification to a webhook URL.

    Args:
        request: TestWebhookRequest with webhook_url

    Returns:
        TestWebhookResponse with success status
    """
    result = NotificationEngine.test_webhook(request.webhook_url)

    return TestWebhookResponse(
        success=result["success"],
        message=result["message"],
        webhook_url=result["webhook_url"],
    )
