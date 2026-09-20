import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Set, Tuple
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.task import Task, TaskStatus
from app.models.notification import (
    Notification,
    NotificationType,
    NotificationSeverity,
    EscalationLevelRole,
)
from app.services.hierarchy_service import get_notification_recipients
from app.services.notification_service import (
    NotificationService,
    format_overdue_duration,
    format_team_lead_overdue_message,
    format_head_escalation_message,
    format_unassigned_overdue_message,
)
from app.scheduler.config import (
    TASK_OVERDUE_ESCALATION_ENABLED,
    TASK_OVERDUE_ESCALATION_MINUTES,
)

logger = logging.getLogger(__name__)


def check_overdue_volunteer_tasks(
    db: Optional[Session] = None,
    current_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Scheduled cron job to detect overdue incomplete tasks and dispatch
    hierarchical notifications (Volunteer → Team Lead → Club Head → Admin).

    Deterministic, strictly idempotent, transaction-safe, and auditable.
    """
    execution_id = str(uuid.uuid4())[:8]
    now = current_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    logger.info(
        f"[Cron Start] JOB=check_overdue_volunteer_tasks EXECUTION_ID={execution_id} "
        f"TIMESTAMP={now.isoformat()}"
    )

    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True

    summary = {
        "job_name": "check_overdue_volunteer_tasks",
        "execution_id": execution_id,
        "timestamp": now.isoformat(),
        "overdue_tasks_checked": 0,
        "overdue_tasks_found": 0,
        "team_leads_notified": 0,
        "heads_notified": 0,
        "admins_notified": 0,
        "skipped_duplicates": 0,
        "completed_tasks_ignored": 0,
        "errors": 0,
    }

    team_leads_notified_keys: Set[Tuple[int, int]] = set()
    heads_notified_keys: Set[Tuple[int, int]] = set()
    admins_notified_keys: Set[Tuple[int, int]] = set()

    try:
        # Step 1: Count completed tasks that are past due (for audit summary)
        completed_past_due = (
            db.query(Task)
            .filter(
                Task.status == TaskStatus.DONE,
                Task.due_date != None,
                Task.due_date < now,
            )
            .count()
        )
        summary["completed_tasks_ignored"] = completed_past_due

        # Step 2: Query active, incomplete tasks past their deadline with an event
        overdue_tasks = (
            db.query(Task)
            .filter(
                Task.status != TaskStatus.DONE,
                Task.status != TaskStatus.CANCELLED,
                Task.due_date != None,
                Task.due_date < now,
                Task.event_id != None,
            )
            .all()
        )

        summary["overdue_tasks_checked"] = len(overdue_tasks) + completed_past_due
        summary["overdue_tasks_found"] = len(overdue_tasks)

        for task in overdue_tasks:
            try:
                # Ensure UTC normalization for task.due_date
                task_due = task.due_date
                if task_due.tzinfo is None:
                    task_due = task_due.replace(tzinfo=timezone.utc)

                overdue_seconds = max(0, int((now - task_due).total_seconds()))
                overdue_minutes = overdue_seconds / 60.0
                overdue_str = format_overdue_duration(task_due, now)
                due_str = task_due.strftime("%d %B %Y, %I:%M %p")
                event_title = task.event.title if task.event else "Club Event"

                # ─── CASE A: UNASSIGNED OVERDUE TASK ─────────────────────────
                if not task.assignments:
                    # Resolve recipient for unassigned task: Team Lead or Club Head
                    recipients = get_notification_recipients(
                        volunteer_id=0,
                        event_id=task.event_id,
                        db=db,
                        task_team_id=task.team_id,
                    )
                    recipient = recipients.team_lead or recipients.head or recipients.admin
                    level = (
                        EscalationLevelRole.TEAM_LEAD.value
                        if recipients.team_lead
                        else (
                            EscalationLevelRole.HEAD.value
                            if recipients.head
                            else EscalationLevelRole.ADMIN.value
                        )
                    )

                    if recipient:
                        title, message = format_unassigned_overdue_message(
                            task=task,
                            event_title=event_title,
                            overdue_str=overdue_str,
                            due_str=due_str,
                        )
                        notif, created = NotificationService.send_in_app_notification(
                            db=db,
                            recipient_id=recipient.id,
                            task_id=task.id,
                            event_id=task.event_id,
                            notification_type=NotificationType.UNASSIGNED_TASK_OVERDUE.value,
                            escalation_level=level,
                            title=title,
                            message=message,
                            severity=NotificationSeverity.WARNING.value,
                            volunteer_id=None,
                        )
                        if created:
                            db.commit()
                            if level == EscalationLevelRole.TEAM_LEAD.value:
                                team_leads_notified_keys.add((task.id, recipient.id))
                            elif level == EscalationLevelRole.HEAD.value:
                                heads_notified_keys.add((task.id, recipient.id))
                            else:
                                admins_notified_keys.add((task.id, recipient.id))

                            logger.info(
                                f"JOB=check_overdue_volunteer_tasks EXECUTION_ID={execution_id} "
                                f"TASK={task.id} VOLUNTEER=None RECIPIENT={recipient.id} "
                                f"TYPE=UNASSIGNED_TASK_OVERDUE LEVEL={level} STATUS=NOTIFIED"
                            )
                        else:
                            summary["skipped_duplicates"] += 1
                            logger.info(
                                f"JOB=check_overdue_volunteer_tasks EXECUTION_ID={execution_id} "
                                f"TASK={task.id} VOLUNTEER=None RECIPIENT={recipient.id} "
                                f"TYPE=UNASSIGNED_TASK_OVERDUE LEVEL={level} STATUS=SKIPPED_DUPLICATE"
                            )
                    continue

                # ─── CASE B: ASSIGNED VOLUNTEER(S) OVERDUE TASK ──────────────
                for assignment in task.assignments:
                    vol_id = assignment.volunteer_id
                    recipients = get_notification_recipients(
                        volunteer_id=vol_id,
                        event_id=task.event_id,
                        db=db,
                        task_team_id=task.team_id,
                    )

                    volunteer_user = recipients.volunteer
                    vol_name = (
                        volunteer_user.full_name
                        if volunteer_user
                        else f"Volunteer #{vol_id}"
                    )
                    team_lead = recipients.team_lead
                    head = recipients.head
                    admin = recipients.admin

                    # 1. Level 1 Notification: Team Lead (or immediate Head if no Team Lead)
                    if team_lead:
                        title, msg = format_team_lead_overdue_message(
                            task=task,
                            volunteer_name=vol_name,
                            event_title=event_title,
                            overdue_str=overdue_str,
                            due_str=due_str,
                        )
                        notif, created = NotificationService.send_in_app_notification(
                            db=db,
                            recipient_id=team_lead.id,
                            task_id=task.id,
                            event_id=task.event_id,
                            notification_type=NotificationType.TASK_OVERDUE.value,
                            escalation_level=EscalationLevelRole.TEAM_LEAD.value,
                            title=title,
                            message=msg,
                            severity=NotificationSeverity.WARNING.value,
                            volunteer_id=vol_id,
                        )
                        if created:
                            db.commit()
                            team_leads_notified_keys.add((task.id, team_lead.id))
                            logger.info(
                                f"JOB=check_overdue_volunteer_tasks EXECUTION_ID={execution_id} "
                                f"TASK={task.id} VOLUNTEER={vol_id} RECIPIENT={team_lead.id} "
                                f"TYPE=TASK_OVERDUE LEVEL=TEAM_LEAD STATUS=NOTIFIED"
                            )
                        else:
                            summary["skipped_duplicates"] += 1
                            logger.info(
                                f"JOB=check_overdue_volunteer_tasks EXECUTION_ID={execution_id} "
                                f"TASK={task.id} VOLUNTEER={vol_id} RECIPIENT={team_lead.id} "
                                f"TYPE=TASK_OVERDUE LEVEL=TEAM_LEAD STATUS=SKIPPED_DUPLICATE"
                            )
                    else:
                        # Edge Case 4 & 5: Volunteer has no Team Lead or Team Lead is inactive
                        # Direct fallback to Head (or Admin if no Head)
                        fallback_recipient = head or admin
                        fallback_level = (
                            EscalationLevelRole.HEAD.value
                            if head
                            else EscalationLevelRole.ADMIN.value
                        )
                        if fallback_recipient:
                            title = f"⚠️ Overdue Task: {task.title}"
                            msg = (
                                f"⚠️ Overdue Task (No Active Team Lead)\n\n"
                                f"Volunteer: {vol_name}\n"
                                f"Task: {task.title}\n"
                                f"Event: {event_title}\n\n"
                                f"Due:\n{due_str}\n\n"
                                f"Overdue By:\n{overdue_str}\n\n"
                                f"No active Team Lead is assigned. Direct leadership notification."
                            )
                            notif, created = NotificationService.send_in_app_notification(
                                db=db,
                                recipient_id=fallback_recipient.id,
                                task_id=task.id,
                                event_id=task.event_id,
                                notification_type=NotificationType.TASK_OVERDUE.value,
                                escalation_level=fallback_level,
                                title=title,
                                message=msg,
                                severity=NotificationSeverity.WARNING.value,
                                volunteer_id=vol_id,
                            )
                            if created:
                                db.commit()
                                if head:
                                    heads_notified_keys.add((task.id, fallback_recipient.id))
                                else:
                                    admins_notified_keys.add((task.id, fallback_recipient.id))
                                logger.info(
                                    f"JOB=check_overdue_volunteer_tasks EXECUTION_ID={execution_id} "
                                    f"TASK={task.id} VOLUNTEER={vol_id} RECIPIENT={fallback_recipient.id} "
                                    f"TYPE=TASK_OVERDUE LEVEL={fallback_level} STATUS=NOTIFIED"
                                )
                            else:
                                summary["skipped_duplicates"] += 1
                                logger.info(
                                    f"JOB=check_overdue_volunteer_tasks EXECUTION_ID={execution_id} "
                                    f"TASK={task.id} VOLUNTEER={vol_id} RECIPIENT={fallback_recipient.id} "
                                    f"TYPE=TASK_OVERDUE LEVEL={fallback_level} STATUS=SKIPPED_DUPLICATE"
                                )

                    # 2. Level 2 Escalation: Head (if overdue threshold exceeded)
                    if (
                        TASK_OVERDUE_ESCALATION_ENABLED
                        and overdue_minutes >= TASK_OVERDUE_ESCALATION_MINUTES
                    ):
                        escalation_target = head or admin
                        escalation_level = (
                            EscalationLevelRole.HEAD.value
                            if head
                            else EscalationLevelRole.ADMIN.value
                        )

                        if escalation_target:
                            team_lead_name = (
                                team_lead.full_name if team_lead else "None"
                            )
                            esc_title, esc_msg = format_head_escalation_message(
                                task=task,
                                volunteer_name=vol_name,
                                team_lead_name=team_lead_name,
                                event_title=event_title,
                                overdue_str=overdue_str,
                                due_str=due_str,
                            )
                            esc_notif, esc_created = NotificationService.send_in_app_notification(
                                db=db,
                                recipient_id=escalation_target.id,
                                task_id=task.id,
                                event_id=task.event_id,
                                notification_type=NotificationType.TASK_OVERDUE_ESCALATION.value,
                                escalation_level=escalation_level,
                                title=esc_title,
                                message=esc_msg,
                                severity=NotificationSeverity.CRITICAL.value,
                                volunteer_id=vol_id,
                            )
                            if esc_created:
                                db.commit()
                                if head:
                                    heads_notified_keys.add((task.id, escalation_target.id))
                                else:
                                    admins_notified_keys.add((task.id, escalation_target.id))
                                logger.info(
                                    f"JOB=check_overdue_volunteer_tasks EXECUTION_ID={execution_id} "
                                    f"TASK={task.id} VOLUNTEER={vol_id} RECIPIENT={escalation_target.id} "
                                    f"TYPE=TASK_OVERDUE_ESCALATION LEVEL={escalation_level} STATUS=NOTIFIED"
                                )
                            else:
                                summary["skipped_duplicates"] += 1
                                logger.info(
                                    f"JOB=check_overdue_volunteer_tasks EXECUTION_ID={execution_id} "
                                    f"TASK={task.id} VOLUNTEER={vol_id} RECIPIENT={escalation_target.id} "
                                    f"TYPE=TASK_OVERDUE_ESCALATION LEVEL={escalation_level} STATUS=SKIPPED_DUPLICATE"
                                )

            except Exception as task_err:
                db.rollback()
                summary["errors"] += 1
                logger.error(
                    f"JOB=check_overdue_volunteer_tasks EXECUTION_ID={execution_id} "
                    f"TASK={task.id} STATUS=ERROR DETAIL={task_err}",
                    exc_info=True,
                )
                continue

    except Exception as job_err:
        db.rollback()
        summary["errors"] += 1
        logger.error(
            f"JOB=check_overdue_volunteer_tasks EXECUTION_ID={execution_id} "
            f"FATAL_JOB_ERROR={job_err}",
            exc_info=True,
        )
    finally:
        if should_close_db:
            db.close()

    summary["team_leads_notified"] = len(team_leads_notified_keys)
    summary["heads_notified"] = len(heads_notified_keys)
    summary["admins_notified"] = len(admins_notified_keys)

    # Log Execution Summary (Section 18)
    logger.info(
        f"\n==================== JOB EXECUTION SUMMARY ====================\n"
        f"Job: {summary['job_name']} (ID: {summary['execution_id']})\n"
        f"Overdue tasks checked: {summary['overdue_tasks_checked']}\n"
        f"Overdue tasks found: {summary['overdue_tasks_found']}\n"
        f"Team Leads notified: {summary['team_leads_notified']}\n"
        f"Heads notified: {summary['heads_notified']}\n"
        f"Admins notified: {summary['admins_notified']}\n"
        f"Skipped duplicates: {summary['skipped_duplicates']}\n"
        f"Completed tasks ignored: {summary['completed_tasks_ignored']}\n"
        f"Errors: {summary['errors']}\n"
        f"==============================================================="
    )

    return summary
