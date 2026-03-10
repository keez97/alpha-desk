"""
Notification Engine - Handles creation, delivery, and management of notifications.

Manages:
- Creating notifications in the database
- Retrieving and filtering notifications
- Marking notifications as read
- Sending webhooks and emails
- Managing notification configuration
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select

from backend.database import engine
from backend.models.notifications import Notification, NotificationConfig

logger = logging.getLogger(__name__)


class NotificationEngine:
    """Engine for handling all notification operations."""

    @staticmethod
    def create_notification(
        session: Session,
        type: str,
        severity: str,
        title: str,
        body: str,
        ticker: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> Notification:
        """
        Create a new notification and persist to database.

        Args:
            session: Database session
            type: Notification type (rotation_alert, confluence_change, earnings_catalyst, breakout)
            severity: Severity level (critical, warning, info)
            title: Short notification title
            body: Full notification message
            ticker: Optional ticker symbol
            sector: Optional sector name

        Returns:
            Created Notification object
        """
        notification = Notification(
            type=type,
            severity=severity,
            title=title,
            body=body,
            ticker=ticker,
            sector=sector,
            read=False,
            webhook_sent=False,
            email_sent=False,
        )
        session.add(notification)
        session.commit()
        session.refresh(notification)

        # Try to send webhook and email if configured
        try:
            NotificationEngine._send_notification(session, notification)
        except Exception as e:
            logger.error(f"Error sending notification {notification.id}: {str(e)}")

        return notification

    @staticmethod
    def get_unread_notifications(
        session: Session,
        limit: int = 50,
    ) -> List[Notification]:
        """
        Get unread notifications sorted by created_at descending.

        Args:
            session: Database session
            limit: Maximum number of notifications to return

        Returns:
            List of unread Notification objects
        """
        query = select(Notification).where(
            Notification.read == False
        ).order_by(
            Notification.created_at.desc()
        ).limit(limit)

        return session.exec(query).all()

    @staticmethod
    def get_notifications(
        session: Session,
        limit: int = 50,
        unread_only: bool = False,
    ) -> List[Notification]:
        """
        Get notifications with optional filtering.

        Args:
            session: Database session
            limit: Maximum number of notifications to return
            unread_only: If True, only return unread notifications

        Returns:
            List of Notification objects
        """
        query = select(Notification).order_by(
            Notification.created_at.desc()
        )

        if unread_only:
            query = query.where(Notification.read == False)

        query = query.limit(limit)
        return session.exec(query).all()

    @staticmethod
    def mark_as_read(session: Session, notification_id: int) -> Optional[Notification]:
        """
        Mark a single notification as read.

        Args:
            session: Database session
            notification_id: ID of the notification to mark as read

        Returns:
            Updated Notification object or None if not found
        """
        notification = session.exec(
            select(Notification).where(Notification.id == notification_id)
        ).first()

        if notification:
            notification.read = True
            session.add(notification)
            session.commit()
            session.refresh(notification)

        return notification

    @staticmethod
    def mark_all_read(session: Session) -> int:
        """
        Mark all notifications as read.

        Args:
            session: Database session

        Returns:
            Number of notifications marked as read
        """
        notifications = session.exec(
            select(Notification).where(Notification.read == False)
        ).all()

        for notification in notifications:
            notification.read = True
            session.add(notification)

        session.commit()
        return len(notifications)

    @staticmethod
    def get_unread_count(session: Session) -> int:
        """
        Get count of unread notifications.

        Args:
            session: Database session

        Returns:
            Number of unread notifications
        """
        query = select(Notification).where(Notification.read == False)
        notifications = session.exec(query).all()
        return len(notifications)

    @staticmethod
    def get_config(session: Session) -> NotificationConfig:
        """
        Get notification configuration.

        Creates a default config if none exists.

        Args:
            session: Database session

        Returns:
            NotificationConfig object
        """
        config = session.exec(select(NotificationConfig)).first()

        if not config:
            config = NotificationConfig(
                webhook_url=None,
                email=None,
                enabled_types='["rotation_alert", "confluence_change", "earnings_catalyst", "breakout"]',
                min_severity="warning",
            )
            session.add(config)
            session.commit()
            session.refresh(config)

        return config

    @staticmethod
    def update_config(
        session: Session,
        webhook_url: Optional[str] = None,
        email: Optional[str] = None,
        enabled_types: Optional[List[str]] = None,
        min_severity: Optional[str] = None,
    ) -> NotificationConfig:
        """
        Update notification configuration.

        Args:
            session: Database session
            webhook_url: Webhook URL (optional)
            email: Email address (optional)
            enabled_types: List of enabled notification types (optional)
            min_severity: Minimum severity level (optional)

        Returns:
            Updated NotificationConfig object
        """
        config = NotificationEngine.get_config(session)

        if webhook_url is not None:
            config.webhook_url = webhook_url
        if email is not None:
            config.email = email
        if enabled_types is not None:
            config.enabled_types = json.dumps(enabled_types)
        if min_severity is not None:
            config.min_severity = min_severity

        session.add(config)
        session.commit()
        session.refresh(config)

        return config

    @staticmethod
    def send_webhook(
        notification: Notification,
        webhook_url: str,
    ) -> bool:
        """
        Send notification to a webhook URL via POST.

        Args:
            notification: The notification to send
            webhook_url: Target webhook URL

        Returns:
            True if successful, False otherwise
        """
        try:
            import httpx

            payload = {
                "type": notification.type,
                "severity": notification.severity,
                "title": notification.title,
                "body": notification.body,
                "ticker": notification.ticker,
                "timestamp": notification.created_at.isoformat() + "Z",
            }

            response = httpx.post(webhook_url, json=payload, timeout=10)
            return response.status_code in [200, 201, 202, 204]
        except Exception as e:
            logger.error(f"Failed to send webhook to {webhook_url}: {str(e)}")
            return False

    @staticmethod
    def send_email(
        notification: Notification,
        email: str,
    ) -> bool:
        """
        Send notification via email.

        Currently logs the email content (actual SMTP would require credentials).

        Args:
            notification: The notification to send
            email: Target email address

        Returns:
            True (logging only, no actual SMTP)
        """
        try:
            logger.info(
                f"[EMAIL NOTIFICATION] To: {email}\n"
                f"Subject: {notification.type}: {notification.title}\n"
                f"Severity: {notification.severity}\n"
                f"Body: {notification.body}\n"
                f"Ticker: {notification.ticker}\n"
                f"Timestamp: {notification.created_at.isoformat()}\n"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {email}: {str(e)}")
            return False

    @staticmethod
    def _send_notification(
        session: Session,
        notification: Notification,
    ) -> None:
        """
        Internal method to send notification via configured channels.

        Args:
            session: Database session
            notification: The notification to send
        """
        config = NotificationEngine.get_config(session)

        # Check if this notification type is enabled
        enabled_types = json.loads(config.enabled_types)
        if notification.type not in enabled_types:
            logger.debug(f"Notification type {notification.type} is disabled")
            return

        # Check severity threshold
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        min_severity_level = severity_order.get(config.min_severity, 1)
        notification_level = severity_order.get(notification.severity, 2)

        if notification_level > min_severity_level:
            logger.debug(
                f"Notification severity {notification.severity} below threshold {config.min_severity}"
            )
            return

        # Send webhook if configured
        if config.webhook_url:
            success = NotificationEngine.send_webhook(notification, config.webhook_url)
            notification.webhook_sent = success
            session.add(notification)

        # Send email if configured
        if config.email:
            success = NotificationEngine.send_email(notification, config.email)
            notification.email_sent = success
            session.add(notification)

        session.commit()

    @staticmethod
    def test_webhook(webhook_url: str) -> Dict[str, Any]:
        """
        Send a test notification to a webhook URL.

        Args:
            webhook_url: Target webhook URL

        Returns:
            Dict with success status and message
        """
        test_notification = Notification(
            type="test",
            severity="info",
            title="Test Notification",
            body="This is a test notification from AlphaDesk.",
            ticker=None,
            sector=None,
            read=False,
            webhook_sent=False,
            email_sent=False,
        )

        success = NotificationEngine.send_webhook(test_notification, webhook_url)

        return {
            "success": success,
            "message": "Test webhook sent successfully" if success else "Failed to send test webhook",
            "webhook_url": webhook_url,
        }
