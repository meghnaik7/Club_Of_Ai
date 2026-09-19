import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.task import Task, TaskStatus, TaskPriority
from app.models.event import Event
from app.models.escalation import TaskEscalation, EscalationLevel, EscalationStatus
from app.schemas.escalation import EscalationResult
from app.engine.critical_path import calculate_critical_path

logger = logging.getLogger(__name__)

class TaskEscalationService:
    """
    Deterministic Automatic Task Escalation Service for ClubOps AI.
    Zero-LLM, rule-based escalation engine enforcing Rules 1-5 with strict idempotency.
    """

    def __init__(
        self,
        hours_before_due: int = 24,
        team_leader_escalation_minutes: int = 60,
        critical_path_escalation_minutes: int = 30
    ):
        self.HOURS_BEFORE_DUE = hours_before_due
        self.TEAM_LEADER_ESCALATION_MINUTES = team_leader_escalation_minutes
        self.CRITICAL_PATH_ESCALATION_MINUTES = critical_path_escalation_minutes
        self.dispatched_notifications: List[Dict[str, Any]] = []

    def _get_critical_task_ids(self, db: Session, event_id: int) -> Set[int]:
        """Calculates the set of task IDs on the event's critical path."""
        try:
            cpm = calculate_critical_path(db, event_id)
            return set(cpm.get("critical_task_ids", []))
        except Exception as e:
            logger.warning(f"Failed to calculate critical path for event {event_id}: {e}")
            return set()

    def _send_notification(
        self,
        task: Task,
        escalation: TaskEscalation,
        recipient_role: str,
        message: str
    ):
        """
        Dispatches notification to the specified role.
        Maintains audit log of dispatched notifications.
        """
        notification_payload = {
            "task_id": task.id,
            "task_title": task.title,
            "event_id": task.event_id,
            "level": escalation.level,
            "recipient_role": recipient_role,
            "message": message,
            "sent_at": datetime.now(timezone.utc).isoformat()
        }
        self.dispatched_notifications.append(notification_payload)
        logger.info(f"[Escalation Notification] To {recipient_role}: {message}")

    @staticmethod
    def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
        """Normalizes naive or aware datetimes to UTC timezone-aware."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _build_result(self, task: Task, escalation: Optional[TaskEscalation], required: bool, reason: str) -> EscalationResult:
        """Helper to build consistent EscalationResult schema."""
        if escalation:
            return EscalationResult(
                task_id=task.id,
                task_title=task.title,
                event_id=task.event_id,
                escalation_required=required,
                reason=reason,
                escalation_level=escalation.level,
                escalation_status=escalation.status,
                rule_triggered=escalation.rule_triggered,
                is_critical_path=escalation.is_critical_path,
                team_leader_notified=escalation.team_leader_notified_at is not None,
                main_leader_notified=escalation.main_leader_notified_at is not None,
                notification_count=escalation.notification_count,
                next_escalation_at=self._to_utc(escalation.next_escalation_at),
                acknowledged_at=self._to_utc(escalation.acknowledged_at),
                resolved_at=self._to_utc(escalation.resolved_at),
                resolution_note=escalation.resolution_note
            )
        return EscalationResult(
            task_id=task.id,
            task_title=task.title,
            event_id=task.event_id,
            escalation_required=required,
            reason=reason,
            escalation_level=EscalationLevel.NONE.value,
            escalation_status=EscalationStatus.RESOLVED.value if task.status == TaskStatus.DONE else EscalationStatus.PENDING.value,
            rule_triggered=None,
            is_critical_path=False,
            team_leader_notified=False,
            main_leader_notified=False,
            notification_count=0,
            next_escalation_at=None,
            acknowledged_at=None,
            resolved_at=None,
            resolution_note=None
        )

    def check_task(self, db: Session, task_id: int, now: Optional[datetime] = None) -> EscalationResult:
        """
        Deterministically evaluates whether a task requires escalation against Rules 1-5.
        Guarantees strict idempotency without creating duplicate records or duplicate alerts.
        """
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task #{task_id} not found")

        # Fetch existing active escalation for this task
        active_escalation = db.query(TaskEscalation).filter(
            TaskEscalation.task_id == task.id,
            TaskEscalation.status.in_([EscalationStatus.PENDING.value, EscalationStatus.ACKNOWLEDGED.value])
        ).first()

        # =========================================================================
        # EXCLUSIONS: DONE tasks, CANCELLED tasks, already resolved escalations
        # =========================================================================
        if task.status == TaskStatus.DONE:
            if active_escalation:
                active_escalation.status = EscalationStatus.RESOLVED.value
                active_escalation.resolved_at = current_time
                active_escalation.resolution_note = "Task completed successfully (DONE)."
                active_escalation.next_escalation_at = None
                db.commit()
                db.refresh(active_escalation)
                return self._build_result(task, active_escalation, False, "Task is completed (DONE). Active escalation resolved.")
            return self._build_result(task, None, False, "Task is DONE. Escalation excluded.")

        if task.status == TaskStatus.CANCELLED:
            if active_escalation:
                active_escalation.status = EscalationStatus.CANCELLED.value
                active_escalation.resolution_note = "Task was cancelled."
                active_escalation.next_escalation_at = None
                db.commit()
                db.refresh(active_escalation)
                return self._build_result(task, active_escalation, False, "Task is CANCELLED. Active escalation cancelled.")
            return self._build_result(task, None, False, "Task is CANCELLED. Escalation excluded.")

        # Determine critical path status
        critical_ids = self._get_critical_task_ids(db, task.event_id)
        is_critical_path = task.id in critical_ids

        # Normalize task due date to UTC
        due_date_utc = None
        if task.due_date:
            due_date_utc = task.due_date if task.due_date.tzinfo else task.due_date.replace(tzinfo=timezone.utc)

        # Normalize active escalation notification timestamps
        tl_notified_at_utc = None
        if active_escalation and active_escalation.team_leader_notified_at:
            tl_notified_at_utc = active_escalation.team_leader_notified_at
            if tl_notified_at_utc.tzinfo is None:
                tl_notified_at_utc = tl_notified_at_utc.replace(tzinfo=timezone.utc)

        # =========================================================================
        # DETERMINISTIC RULE EVALUATION (RULES 1 - 5)
        # =========================================================================
        target_level = EscalationLevel.NONE.value
        triggered_rule: Optional[str] = None
        reason: str = "No escalation criteria met."
        next_escalation_at: Optional[datetime] = None

        # RULE 5: Critical-path task remains unresolved after configured escalation interval
        if is_critical_path and active_escalation and active_escalation.level == EscalationLevel.TEAM_LEADER.value and tl_notified_at_utc:
            cp_escalate_time = tl_notified_at_utc + timedelta(minutes=self.CRITICAL_PATH_ESCALATION_MINUTES)
            if current_time >= cp_escalate_time:
                target_level = EscalationLevel.MAIN_LEADER.value
                triggered_rule = "RULE_5_CRITICAL_PATH_TIMEOUT"
                reason = f"Critical-path task unresolved {self.CRITICAL_PATH_ESCALATION_MINUTES}m after Team Leader notification."

        # RULE 3: Team Leader notified and task remains unresolved for TEAM_LEADER_ESCALATION_MINUTES
        if target_level == EscalationLevel.NONE.value and active_escalation and active_escalation.level == EscalationLevel.TEAM_LEADER.value and tl_notified_at_utc:
            tl_timeout = tl_notified_at_utc + timedelta(minutes=self.TEAM_LEADER_ESCALATION_MINUTES)
            if current_time >= tl_timeout:
                target_level = EscalationLevel.MAIN_LEADER.value
                triggered_rule = "RULE_3_TEAM_LEADER_TIMEOUT"
                reason = f"Task unresolved {self.TEAM_LEADER_ESCALATION_MINUTES}m after Team Leader notification."

        # RULE 4: Blocked task is on the critical path -> immediately escalate to Team Leader
        if target_level == EscalationLevel.NONE.value and task.status == TaskStatus.BLOCKED and is_critical_path:
            target_level = EscalationLevel.TEAM_LEADER.value
            triggered_rule = "RULE_4_BLOCKED_CRITICAL_PATH"
            reason = "Task is BLOCKED and lies on the critical path."
            next_escalation_at = current_time + timedelta(minutes=self.CRITICAL_PATH_ESCALATION_MINUTES)

        # RULE 2: Any relevant task becomes overdue and remains incomplete -> notify Team Leader
        if target_level == EscalationLevel.NONE.value and due_date_utc and due_date_utc < current_time:
            target_level = EscalationLevel.TEAM_LEADER.value
            triggered_rule = "RULE_2_OVERDUE"
            overdue_duration = current_time - due_date_utc
            hours_over = int(overdue_duration.total_seconds() // 3600)
            reason = f"Task is overdue by {hours_over}h and incomplete."
            interval = self.CRITICAL_PATH_ESCALATION_MINUTES if is_critical_path else self.TEAM_LEADER_ESCALATION_MINUTES
            next_escalation_at = current_time + timedelta(minutes=interval)

        # RULE 1: High/critical task due within HOURS_BEFORE_DUE and incomplete -> escalation candidate
        if target_level == EscalationLevel.NONE.value and task.priority in (TaskPriority.HIGH, TaskPriority.URGENT) and due_date_utc:
            window_start = current_time
            window_end = current_time + timedelta(hours=self.HOURS_BEFORE_DUE)
            if window_start <= due_date_utc <= window_end:
                target_level = EscalationLevel.CANDIDATE.value
                triggered_rule = "RULE_1_APPROACHING_DUE"
                hours_left = int((due_date_utc - current_time).total_seconds() // 3600)
                reason = f"High-priority task is due within {hours_left}h (threshold: {self.HOURS_BEFORE_DUE}h)."
                next_escalation_at = due_date_utc

        # If already at MAIN_LEADER, preserve it
        if active_escalation and active_escalation.level == EscalationLevel.MAIN_LEADER.value:
            target_level = EscalationLevel.MAIN_LEADER.value
            triggered_rule = active_escalation.rule_triggered
            reason = active_escalation.reason
            next_escalation_at = None

        # =========================================================================
        # IDEMPOTENT PERSISTENCE & NOTIFICATION DISPATCH
        # =========================================================================
        escalation_required = target_level != EscalationLevel.NONE.value

        if not active_escalation:
            if not escalation_required:
                return self._build_result(task, None, False, reason)

            # Create initial escalation record
            escalation = TaskEscalation(
                task_id=task.id,
                event_id=task.event_id,
                level=target_level,
                status=EscalationStatus.PENDING.value,
                rule_triggered=triggered_rule,
                reason=reason,
                is_critical_path=is_critical_path,
                next_escalation_at=next_escalation_at
            )

            # Handle initial notifications
            if target_level == EscalationLevel.TEAM_LEADER.value:
                escalation.team_leader_notified_at = current_time
                escalation.notification_count = 1
                self._send_notification(task, escalation, "Team Leader", reason)
            elif target_level == EscalationLevel.MAIN_LEADER.value:
                escalation.team_leader_notified_at = current_time
                escalation.main_leader_notified_at = current_time
                escalation.notification_count = 2
                self._send_notification(task, escalation, "Main Leader", reason)

            db.add(escalation)
            db.commit()
            db.refresh(escalation)
            return self._build_result(task, escalation, True, reason)

        # Existing active escalation exists: check for promotion or idempotent no-op
        prev_level = active_escalation.level
        active_escalation.is_critical_path = is_critical_path

        # Promotion from CANDIDATE to TEAM_LEADER
        if prev_level == EscalationLevel.CANDIDATE.value and target_level == EscalationLevel.TEAM_LEADER.value:
            active_escalation.level = EscalationLevel.TEAM_LEADER.value
            active_escalation.rule_triggered = triggered_rule
            active_escalation.reason = reason
            active_escalation.next_escalation_at = next_escalation_at
            if not active_escalation.team_leader_notified_at:
                active_escalation.team_leader_notified_at = current_time
                active_escalation.notification_count += 1
                self._send_notification(task, active_escalation, "Team Leader", reason)
            db.commit()
            db.refresh(active_escalation)
            return self._build_result(task, active_escalation, True, reason)

        # Promotion from TEAM_LEADER (or CANDIDATE) to MAIN_LEADER
        if prev_level in (EscalationLevel.CANDIDATE.value, EscalationLevel.TEAM_LEADER.value) and target_level == EscalationLevel.MAIN_LEADER.value:
            active_escalation.level = EscalationLevel.MAIN_LEADER.value
            active_escalation.rule_triggered = triggered_rule
            active_escalation.reason = reason
            active_escalation.next_escalation_at = None
            if not active_escalation.main_leader_notified_at:
                active_escalation.main_leader_notified_at = current_time
                active_escalation.notification_count += 1
                self._send_notification(task, active_escalation, "Main Leader", reason)
            db.commit()
            db.refresh(active_escalation)
            return self._build_result(task, active_escalation, True, reason)

        # Idempotent re-check at same level: NO duplicate notifications
        if active_escalation.next_escalation_at is None and next_escalation_at is not None:
            active_escalation.next_escalation_at = next_escalation_at
            db.commit()
            db.refresh(active_escalation)

        return self._build_result(task, active_escalation, escalation_required, active_escalation.reason)

    def check_event(self, db: Session, event_id: int, now: Optional[datetime] = None) -> List[EscalationResult]:
        """Runs escalation checks for all tasks associated with an event."""
        tasks = db.query(Task).filter(Task.event_id == event_id).all()
        results = []
        for task in tasks:
            res = self.check_task(db=db, task_id=task.id, now=now)
            results.append(res)
        return results

    def process_pending_escalations(self, db: Session, now: Optional[datetime] = None) -> List[EscalationResult]:
        """
        Batch job processing:
        Inspects all incomplete tasks and pending escalations to promote timed-out escalations.
        """
        incomplete_tasks = db.query(Task).filter(
            Task.status != TaskStatus.DONE,
            Task.status != TaskStatus.CANCELLED
        ).all()

        results = []
        for task in incomplete_tasks:
            res = self.check_task(db=db, task_id=task.id, now=now)
            if res.escalation_required:
                results.append(res)
        return results

    def acknowledge_escalation(self, db: Session, task_id: int, user_id: Optional[int] = None) -> EscalationResult:
        """Marks an active escalation as acknowledged by a team leader."""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task #{task_id} not found")

        escalation = db.query(TaskEscalation).filter(
            TaskEscalation.task_id == task.id,
            TaskEscalation.status == EscalationStatus.PENDING.value
        ).first()

        if not escalation:
            # If already acknowledged, return existing
            ack_esc = db.query(TaskEscalation).filter(
                TaskEscalation.task_id == task.id,
                TaskEscalation.status == EscalationStatus.ACKNOWLEDGED.value
            ).first()
            if ack_esc:
                return self._build_result(task, ack_esc, True, "Escalation already acknowledged.")
            return self._build_result(task, None, False, "No active pending escalation to acknowledge.")

        escalation.status = EscalationStatus.ACKNOWLEDGED.value
        escalation.acknowledged_at = datetime.now(timezone.utc)
        escalation.acknowledged_by = user_id
        db.commit()
        db.refresh(escalation)
        return self._build_result(task, escalation, True, f"Escalation acknowledged by user #{user_id or 'unknown'}.")

    def resolve_escalation(self, db: Session, task_id: int, resolution_note: Optional[str] = None) -> EscalationResult:
        """Manually resolves an active escalation with a resolution note."""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task #{task_id} not found")

        escalation = db.query(TaskEscalation).filter(
            TaskEscalation.task_id == task.id,
            TaskEscalation.status.in_([EscalationStatus.PENDING.value, EscalationStatus.ACKNOWLEDGED.value])
        ).first()

        if not escalation:
            return self._build_result(task, None, False, "No active escalation to resolve.")

        escalation.status = EscalationStatus.RESOLVED.value
        escalation.resolved_at = datetime.now(timezone.utc)
        escalation.resolution_note = resolution_note or "Escalation marked as resolved."
        escalation.next_escalation_at = None
        db.commit()
        db.refresh(escalation)
        return self._build_result(task, escalation, False, escalation.resolution_note)

    def escalate_to_main_leader(self, db: Session, task_id: int, reason: Optional[str] = None, now: Optional[datetime] = None) -> EscalationResult:
        """Explicitly promotes an active escalation to Main Leader."""
        current_time = now or datetime.now(timezone.utc)
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task #{task_id} not found")

        escalation = db.query(TaskEscalation).filter(
            TaskEscalation.task_id == task.id,
            TaskEscalation.status.in_([EscalationStatus.PENDING.value, EscalationStatus.ACKNOWLEDGED.value])
        ).first()

        final_reason = reason or "Manually escalated to Main Leader."
        if not escalation:
            escalation = TaskEscalation(
                task_id=task.id,
                event_id=task.event_id,
                level=EscalationLevel.MAIN_LEADER.value,
                status=EscalationStatus.PENDING.value,
                rule_triggered="MANUAL_MAIN_LEADER_ESCALATION",
                reason=final_reason,
                main_leader_notified_at=current_time,
                notification_count=1,
                next_escalation_at=None
            )
            self._send_notification(task, escalation, "Main Leader", final_reason)
            db.add(escalation)
        else:
            escalation.level = EscalationLevel.MAIN_LEADER.value
            escalation.rule_triggered = "MANUAL_MAIN_LEADER_ESCALATION"
            escalation.reason = final_reason
            escalation.next_escalation_at = None
            if not escalation.main_leader_notified_at:
                escalation.main_leader_notified_at = current_time
                escalation.notification_count += 1
                self._send_notification(task, escalation, "Main Leader", final_reason)

        db.commit()
        db.refresh(escalation)
        return self._build_result(task, escalation, True, final_reason)

    def cancel_escalation(self, db: Session, task_id: int, reason: Optional[str] = None) -> EscalationResult:
        """Cancels an active escalation."""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task #{task_id} not found")

        escalation = db.query(TaskEscalation).filter(
            TaskEscalation.task_id == task.id,
            TaskEscalation.status.in_([EscalationStatus.PENDING.value, EscalationStatus.ACKNOWLEDGED.value])
        ).first()

        if not escalation:
            return self._build_result(task, None, False, "No active escalation to cancel.")

        escalation.status = EscalationStatus.CANCELLED.value
        escalation.resolution_note = reason or "Escalation was cancelled."
        escalation.next_escalation_at = None
        db.commit()
        db.refresh(escalation)
        return self._build_result(task, escalation, False, escalation.resolution_note)

# Singleton instance with default configuration
task_escalation_service = TaskEscalationService()
