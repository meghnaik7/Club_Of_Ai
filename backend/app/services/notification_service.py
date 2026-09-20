import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.notification import (
    Notification,
    NotificationType,
    NotificationStatus,
    NotificationSeverity,
    EscalationLevelRole,
)
from app.models.task import Task
from app.models.user import User
from app.models.event import Event

logger = logging.getLogger(__name__)


def format_overdue_duration(due_date: datetime, current_time: datetime) -> str:
    """Formats the overdue duration human-readably (e.g., '1 hour', '45 minutes', '2 hours 15 minutes')."""
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)

    delta = current_time - due_date
    total_seconds = max(0, int(delta.total_seconds()))

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours == 0 and minutes == 0:
        return "Just overdue"
    elif hours == 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif minutes == 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    else:
        return f"{hours} hour{'s' if hours != 1 else ''} {minutes} min"


def format_team_lead_overdue_message(
    task: Task,
    volunteer_name: str,
    event_title: str,
    overdue_str: str,
    due_str: str,
) -> Tuple[str, str]:
    """Deterministic Level 1 notification message for Team Lead."""
    title = f"⚠️ Overdue Task: {task.title}"
    status_display = str(task.status.value if hasattr(task.status, 'value') else task.status).replace("_", " ").title()
    message = (
        f"⚠️ Overdue Task\n\n"
        f"Volunteer: {volunteer_name}\n"
        f"Task: {task.title}\n"
        f"Event: {event_title}\n\n"
        f"Due:\n{due_str}\n\n"
        f"Current Status:\n{status_display}\n\n"
        f"Overdue By:\n{overdue_str}\n\n"
        f"Please check the task and coordinate with the volunteer."
    )
    return title, message


def format_head_escalation_message(
    task: Task,
    volunteer_name: str,
    team_lead_name: str,
    event_title: str,
    overdue_str: str,
    due_str: str,
) -> Tuple[str, str]:
    """Deterministic Level 2 escalation notification message for Club Head."""
    title = f"🚨 Escalated Overdue Task: {task.title}"
    message = (
        f"🚨 Escalated Overdue Task\n\n"
        f"Volunteer: {volunteer_name}\n"
        f"Team Lead: {team_lead_name}\n"
        f"Task: {task.title}\n"
        f"Event: {event_title}\n\n"
        f"Due:\n{due_str}\n\n"
        f"Overdue By:\n{overdue_str}\n\n"
        f"The task is still incomplete after the configured escalation period."
    )
    return title, message


def format_unassigned_overdue_message(
    task: Task,
    event_title: str,
    overdue_str: str,
    due_str: str,
) -> Tuple[str, str]:
    """Deterministic notification for an unassigned task that is past its deadline."""
    title = f"⚠️ Unassigned Overdue Task: {task.title}"
    status_display = str(task.status.value if hasattr(task.status, 'value') else task.status).replace("_", " ").title()
    message = (
        f"⚠️ Unassigned Overdue Task\n\n"
        f"Task: {task.title}\n"
        f"Event: {event_title}\n\n"
        f"Due:\n{due_str}\n\n"
        f"Current Status:\n{status_display}\n\n"
        f"Overdue By:\n{overdue_str}\n\n"
        f"Please assign a volunteer and coordinate task completion."
    )
    return title, message


class NotificationService:
    """
    Manages in-app notification dispatch, deterministic template rendering,
    and database-enforced idempotency to prevent duplicate alerts.
    """

    @staticmethod
    def send_in_app_notification(
        db: Session,
        recipient_id: int,
        task_id: Optional[int],
        event_id: Optional[int],
        notification_type: str,
        escalation_level: str,
        title: str,
        message: str,
        severity: str = NotificationSeverity.WARNING.value,
        volunteer_id: Optional[int] = None,
    ) -> Tuple[Optional[Notification], bool]:
        """
        Idempotently sends and persists an in-app notification record.

        Returns:
            Tuple[Optional[Notification], bool]: (notification_record, was_created)
            If duplicate exists, was_created is False and existing record is returned.
        """
        # 1. Application-level idempotency pre-check
        existing = db.query(Notification).filter(
            Notification.task_id == task_id,
            Notification.recipient_id == recipient_id,
            Notification.notification_type == notification_type,
            Notification.escalation_level == escalation_level,
        ).first()

        if existing:
            logger.debug(
                f"[Idempotency Skip] Notification already exists for task #{task_id}, "
                f"recipient #{recipient_id}, type {notification_type}, level {escalation_level}."
            )
            return existing, False

        # 2. Construct new record
        new_notification = Notification(
            recipient_id=recipient_id,
            event_id=event_id,
            task_id=task_id,
            volunteer_id=volunteer_id,
            notification_type=notification_type,
            title=title,
            message=message,
            severity=severity,
            escalation_level=escalation_level,
            status=NotificationStatus.UNREAD.value,
            created_at=datetime.now(timezone.utc),
        )

        try:
            db.add(new_notification)
            db.flush()
            return new_notification, True
        except IntegrityError:
            db.rollback()
            # Concurrently created by another process/thread
            logger.info(
                f"[DB Uniqueness Enforced] Duplicate notification prevented by database constraint "
                f"for task #{task_id}, recipient #{recipient_id}, level {escalation_level}."
            )
            existing = db.query(Notification).filter(
                Notification.task_id == task_id,
                Notification.recipient_id == recipient_id,
                Notification.notification_type == notification_type,
                Notification.escalation_level == escalation_level,
            ).first()
            return existing, False
