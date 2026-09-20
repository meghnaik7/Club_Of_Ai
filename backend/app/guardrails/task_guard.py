"""
Task & Business Rule Guardrails (20, 21, 23):
- Business Rule Guardrail: Enforces state machine transitions (TODO -> IN_PROGRESS -> DONE/BLOCKED)
- Hallucination Guardrail: Validates entity existence in DB (never allowing invented entity IDs)
- Confidence Guardrail: Flags low-confidence entity resolutions (e.g. multiple matching volunteer names)
"""
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus, TaskPriority, TaskPhase, TaskDependency
from app.models.event import Event
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.user import User

class StatusTransitionError(ValueError):
    """Raised when an invalid task status transition is attempted."""
    pass

class EntityNotFoundError(ValueError):
    """Raised when an entity referenced by the AI does not exist in the database."""
    pass

class LowConfidenceError(ValueError):
    """Raised when entity resolution is ambiguous and requires human review."""
    pass

class TaskGuard:
    # Allowed status state machine transitions
    VALID_TRANSITIONS = {
        TaskStatus.TODO: {TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED},
        TaskStatus.IN_PROGRESS: {TaskStatus.IN_PROGRESS, TaskStatus.DONE, TaskStatus.BLOCKED, TaskStatus.TODO},
        TaskStatus.BLOCKED: {TaskStatus.BLOCKED, TaskStatus.IN_PROGRESS, TaskStatus.TODO, TaskStatus.DONE},
        TaskStatus.DONE: {TaskStatus.DONE, TaskStatus.TODO, TaskStatus.IN_PROGRESS}, # Allow re-opening if needed
    }

    @classmethod
    def verify_task_exists(cls, db: Session, task_id: int) -> Task:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise EntityNotFoundError(f"Hallucinated or non-existent Task ID: {task_id}")
        return task

    @classmethod
    def check_confidence_threshold(cls, confidence_score: float, threshold: float = 0.85) -> bool:
        if confidence_score < threshold:
            raise LowConfidenceError(
                f"Confidence score {confidence_score:.2f} is below safety threshold {threshold:.2f}. Human confirmation required."
            )
        return True


    @classmethod
    def validate_status_transition(
        cls,
        current_status: TaskStatus,
        new_status: TaskStatus,
        unresolved_dependencies_count: int = 0
    ) -> Tuple[bool, Optional[str]]:
        """
        Guardrail 23: Enforces valid status state transitions.
        Warns or prevents completing a task with active blocking dependencies.
        """
        if current_status == new_status:
            return True, None

        allowed = cls.VALID_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise StatusTransitionError(
                f"Invalid status transition from {current_status.value if hasattr(current_status, 'value') else current_status} "
                f"to {new_status.value if hasattr(new_status, 'value') else new_status}."
            )

        if new_status == TaskStatus.DONE and unresolved_dependencies_count > 0:
            return True, f"Warning: Task has {unresolved_dependencies_count} unresolved blocking prerequisite(s)."

        return True, None

    @classmethod
    def verify_entities_exist(
        cls,
        db: Session,
        event_id: int,
        owner_ids: Optional[List[int]] = None,
        parent_id: Optional[int] = None
    ) -> bool:
        """
        Guardrail 20: Hallucination Guardrail.
        Verifies that event_id, owner_ids, and parent_id actually exist in the DB.
        Rejects operations referencing invented or hallucinated IDs.
        """
        # 1. Check Event
        if not db.query(Event).filter(Event.id == event_id).first():
            raise EntityNotFoundError(f"Hallucinated or non-existent Event ID: {event_id}")

        # 2. Check Parent Task
        if parent_id is not None:
            parent = db.query(Task).filter(Task.id == parent_id, Task.event_id == event_id).first()
            if not parent:
                raise EntityNotFoundError(f"Parent Task ID {parent_id} does not exist for Event {event_id}.")

        # 3. Check Volunteers
        if owner_ids:
            for vol_id in owner_ids:
                vol = db.query(Volunteer).filter(Volunteer.id == vol_id).first()
                if not vol:
                    raise EntityNotFoundError(f"Hallucinated or non-existent Volunteer ID: {vol_id}")
                if vol.status != VolunteerStatus.ACTIVE:
                    raise ValueError(f"Volunteer #{vol_id} is currently INACTIVE and cannot be assigned.")

        return True

    @classmethod
    def resolve_volunteer_by_name(
        cls,
        db: Session,
        name_query: str
    ) -> Tuple[Optional[Volunteer], str, float]:
        """
        Guardrail 21: Confidence Guardrail.
        Resolves volunteer name against DB users:
        - Exact match (1 result) -> HIGH confidence (1.0)
        - Partial match (1 result) -> MEDIUM confidence (0.7)
        - Multiple candidate matches -> LOW confidence (0.3), raises LowConfidenceError requiring human selection
        - 0 matches -> None, confidence 0.0
        """
        if not name_query or not name_query.strip():
            return None, "Empty name query", 0.0

        clean_name = name_query.strip().lower()

        # 1. Exact match search
        exact_matches = db.query(Volunteer).join(User).filter(
            User.full_name.ilike(clean_name)
        ).all()

        if len(exact_matches) == 1:
            return exact_matches[0], "Exact unique match found", 1.0
        elif len(exact_matches) > 1:
            candidates = [f"{v.user.full_name} ({v.user.email})" for v in exact_matches if v.user]
            raise LowConfidenceError(
                f"Multiple volunteers matched '{name_query}': {', '.join(candidates)}. Human disambiguation required."
            )

        # 2. Substring match
        partial_matches = db.query(Volunteer).join(User).filter(
            User.full_name.ilike(f"%{clean_name}%")
        ).all()

        if len(partial_matches) == 1:
            return partial_matches[0], "Single partial match found", 0.7
        elif len(partial_matches) > 1:
            candidates = [f"{v.user.full_name} (ID: {v.id})" for v in partial_matches if v.user]
            raise LowConfidenceError(
                f"Ambiguous matches for '{name_query}': {', '.join(candidates)}. Please specify the exact volunteer."
            )

        return None, "No volunteer found matching query", 0.0
