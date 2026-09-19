from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.models.escalation import TaskEscalation, EscalationStatus
from app.schemas.escalation import (
    EscalationResult,
    EscalationAcknowledgeRequest,
    EscalationResolveRequest,
    EscalationManualPromoteRequest,
    EscalationCancelRequest
)
from app.services.task_escalation_service import task_escalation_service

router = APIRouter()

@router.post("/check-task/{task_id}", response_model=EscalationResult)
def check_task_escalation(
    task_id: int,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """
    Deterministically evaluates a task against escalation rules (Rules 1-5).
    """
    try:
        return task_escalation_service.check_task(db=db, task_id=task_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/check-event/{event_id}", response_model=List[EscalationResult])
def check_event_escalations(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """
    Evaluates all tasks belonging to an event and returns their escalation states.
    """
    return task_escalation_service.check_event(db=db, event_id=event_id)

@router.post("/process-pending", response_model=List[EscalationResult])
def process_pending_escalations(
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """
    Batch evaluates all incomplete tasks and pending escalations.
    """
    return task_escalation_service.process_pending_escalations(db=db)

@router.post("/{task_id}/acknowledge", response_model=EscalationResult)
def acknowledge_escalation(
    task_id: int,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """
    Acknowledges an active escalation (e.g. by Team Leader).
    """
    user_id = current_user.id if current_user else None
    try:
        return task_escalation_service.acknowledge_escalation(db=db, task_id=task_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/{task_id}/resolve", response_model=EscalationResult)
def resolve_escalation(
    task_id: int,
    body: EscalationResolveRequest,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """
    Resolves an active escalation with a resolution note.
    """
    try:
        return task_escalation_service.resolve_escalation(db=db, task_id=task_id, resolution_note=body.resolution_note)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/{task_id}/escalate-main", response_model=EscalationResult)
def escalate_to_main_leader(
    task_id: int,
    body: Optional[EscalationManualPromoteRequest] = None,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """
    Explicitly escalates a task to Main Leader.
    """
    reason = body.reason if body else None
    try:
        return task_escalation_service.escalate_to_main_leader(db=db, task_id=task_id, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/{task_id}/cancel", response_model=EscalationResult)
def cancel_escalation(
    task_id: int,
    body: Optional[EscalationCancelRequest] = None,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """
    Cancels an active escalation.
    """
    reason = body.reason if body else None
    try:
        return task_escalation_service.cancel_escalation(db=db, task_id=task_id, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/active", response_model=List[dict])
def get_active_escalations(
    event_id: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """
    List all active (PENDING or ACKNOWLEDGED) escalations.
    """
    query = db.query(TaskEscalation).filter(
        TaskEscalation.status.in_([EscalationStatus.PENDING.value, EscalationStatus.ACKNOWLEDGED.value])
    )
    if event_id is not None:
        query = query.filter(TaskEscalation.event_id == event_id)
    records = query.order_by(TaskEscalation.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "task_id": r.task_id,
            "task_title": r.task.title if r.task else f"Task #{r.task_id}",
            "event_id": r.event_id,
            "level": r.level,
            "status": r.status,
            "rule_triggered": r.rule_triggered,
            "reason": r.reason,
            "is_critical_path": r.is_critical_path,
            "team_leader_notified_at": r.team_leader_notified_at.isoformat() if r.team_leader_notified_at else None,
            "main_leader_notified_at": r.main_leader_notified_at.isoformat() if r.main_leader_notified_at else None,
            "next_escalation_at": r.next_escalation_at.isoformat() if r.next_escalation_at else None,
            "acknowledged_at": r.acknowledged_at.isoformat() if r.acknowledged_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in records
    ]
