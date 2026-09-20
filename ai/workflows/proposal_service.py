"""
ProposalService: Core business logic for the Proposal/Diff/Undo architecture.

RULES:
- create_proposal()    → saves AIProposal + AIProposalChange rows. NO DB writes to Event/Task/etc.
- preview_action_diff()→ calculates exact entity and field diffs before user approval.
- apply_proposal()     → inside a DB transaction, creates/updates/deletes entities and writes AuditLog entries.
- reject_proposal()    → marks proposal as REJECTED without modifying state.
- undo_proposal()      → reverses the applied changes (using AuditLog), marks as UNDONE.
- get_action_audit_log()→ retrieves audit trail of AI actions, timestamps, states, and users.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

try:
    from app.models.audit_log import AuditLog
    from app.models.event import Event as EventModel
    from app.models.task import Task as TaskModel
    from app.models.announcement import Announcement as AnnouncementModel
    from ai.schemas.ai_proposal import AIProposal, AIProposalChange, ProposalStatus, ProposalChangeAction
    from ai.schemas.ai_plan import EventPlan
except ImportError:
    from backend.app.models.audit_log import AuditLog
    from backend.app.models.event import Event as EventModel
    from backend.app.models.task import Task as TaskModel
    from backend.app.models.announcement import Announcement as AnnouncementModel
    from ai.schemas.ai_proposal import AIProposal, AIProposalChange, ProposalStatus, ProposalChangeAction
    from ai.schemas.ai_plan import EventPlan

from ai.schemas.proposal import (
    ProposalResponse, ProposalChangeOut, ProposalDiffPreview, EntityDiff, FieldDiff, AuditLogEntryOut
)

logger = logging.getLogger(__name__)

def _build_response(proposal: AIProposal, event_plan: Optional[EventPlan] = None) -> ProposalResponse:
    changes = [
        ProposalChangeOut(
            id=c.id,
            entity_type=c.entity_type,
            entity_id=c.entity_id,
            action=c.action.value if hasattr(c.action, "value") else str(c.action),
            proposed_data=c.proposed_data or {},
            previous_data=c.previous_data,
            explanation=c.explanation,
        )
        for c in (proposal.changes or [])
    ]
    return ProposalResponse(
        proposal_id=proposal.id,
        intent=proposal.intent,
        status=proposal.status.value if hasattr(proposal.status, "value") else str(proposal.status),
        event_plan=event_plan,
        changes=changes,
    )

def create_proposal(
    db: Session,
    user_id: Optional[int],
    intent: str,
    event_plan: Optional[EventPlan] = None,
    changes: Optional[List[Dict[str, Any]]] = None,
) -> ProposalResponse:
    """
    Persist an AIProposal and its AIProposalChanges.
    Does NOT touch production entity tables (Event, Task, etc.).
    """
    # Validate user authorization scope if user_id is provided
    if user_id:
        from app.models.user import User
        from app.services.authz import AuthorizationService
        actor = db.query(User).filter(User.id == user_id).first()
        if actor and not AuthorizationService.is_admin(actor):
            role_str = AuthorizationService.get_role_str(actor)
            if role_str in ["VOLUNTEER", "TEAM_MEMBER"] and not AuthorizationService.is_club_head(db, actor):
                if event_plan or (changes and any(c.get("action") in ["CREATE", "DELETE", "ASSIGN"] for c in changes)):
                    raise HTTPException(
                        status_code=403,
                        detail="Permission denied: Volunteers are not authorized to create event plans or assign tasks via AI."
                    )
            if AuthorizationService.is_subteam_lead(db, actor):
                user_subteam = AuthorizationService.get_user_subteam_id(db, actor)
                if changes:
                    for c in changes:
                        target_task_id = c.get("entity_id")
                        if target_task_id and c.get("entity_type") == "Task":
                            if not AuthorizationService.can_manage_task(db, actor, target_task_id):
                                raise HTTPException(
                                    status_code=403,
                                    detail=f"Permission denied: SubTeam Lead cannot modify Task #{target_task_id} outside their SubTeam scope."
                                )
                        target_team_id = (c.get("proposed_data") or {}).get("team_id")
                        if target_team_id and user_subteam and target_team_id != user_subteam:
                            raise HTTPException(
                                status_code=403,
                                detail=f"Permission denied: SubTeam Lead cannot move tasks to Team #{target_team_id}. Please escalate to Club Head."
                            )

    proposal = AIProposal(
        intent=intent,
        status=ProposalStatus.PENDING,
        created_by=user_id,
    )
    db.add(proposal)
    db.flush()  # Get proposal.id


    # 1. Staging changes from EventPlan (if provided)
    if event_plan:
        event_data = {
            "title": event_plan.event_title,
            "description": event_plan.event_description,
            "venue": event_plan.venue,
            "expected_attendance": event_plan.expected_attendance,
            "budget": event_plan.budget,
        }
        db.add(AIProposalChange(
            proposal_id=proposal.id,
            entity_type="Event",
            action=ProposalChangeAction.CREATE,
            proposed_data=event_data,
            explanation=f"Create event: {event_plan.event_title}",
        ))

        for i, task in enumerate(event_plan.tasks):
            task_deps = [d.model_dump() if hasattr(d, "model_dump") else d for d in (task.dependencies or [])]
            task_subs = [s.model_dump() if hasattr(s, "model_dump") else s for s in (task.subtasks or [])]
            task_data = {
                "title": task.title,
                "description": task.description,
                "phase": task.phase,
                "priority": task.priority,
                "estimated_duration_hours": task.estimated_duration_hours,
                "suggested_skills": task.suggested_skills,
                "dependencies": task_deps,
                "subtasks": task_subs,
                "task_index": i,
            }
            db.add(AIProposalChange(
                proposal_id=proposal.id,
                entity_type="Task",
                action=ProposalChangeAction.CREATE,
                proposed_data=task_data,
                explanation=f"Create task [{task.phase}]: {task.title}",
            ))

    # 2. Staging generic changes (if provided)
    if changes:
        for ch in changes:
            action_str = str(ch.get("action", "CREATE")).upper()
            action_enum = ProposalChangeAction(action_str) if action_str in ProposalChangeAction.__members__ else ProposalChangeAction.CREATE
            db.add(AIProposalChange(
                proposal_id=proposal.id,
                entity_type=ch.get("entity_type", "Unknown"),
                entity_id=ch.get("entity_id"),
                action=action_enum,
                proposed_data=ch.get("proposed_data", {}),
                explanation=ch.get("explanation", f"Proposed {action_str} on {ch.get('entity_type', 'Entity')}")
            ))

    db.commit()
    db.refresh(proposal)
    logger.info(f"Created proposal {proposal.id} with {len(proposal.changes)} changes.")
    return _build_response(proposal, event_plan)

def get_proposal(db: Session, proposal_id: int) -> ProposalResponse:
    """Retrieve the proposed changes and their current status."""
    proposal = db.query(AIProposal).filter(AIProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal with ID {proposal_id} not found")
    return _build_response(proposal)

def preview_action_diff(db: Session, proposal_id: int) -> ProposalDiffPreview:
    """
    Calculate exactly what entities and fields will change if the proposal is applied.
    Compares proposed_data against current database state.
    """
    proposal = db.query(AIProposal).filter(AIProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal with ID {proposal_id} not found")

    entity_diffs: List[EntityDiff] = []
    entities_affected_set = set()

    for ch in proposal.changes:
        action_str = ch.action.value if hasattr(ch.action, "value") else str(ch.action)
        entity_type = ch.entity_type
        entities_affected_set.add(entity_type)
        proposed = ch.proposed_data or {}
        field_diffs = []

        if action_str == "CREATE":
            for k, v in proposed.items():
                field_diffs.append(FieldDiff(
                    field=k,
                    old_value=None,
                    new_value=v,
                    change_type="ADDED"
                ))
            summary = f"Create new {entity_type} ('{proposed.get('title', 'Untitled')}') with {len(proposed)} fields"

        elif action_str == "UPDATE":
            # Retrieve existing entity to compare
            existing_data = {}
            if ch.entity_id:
                if entity_type == "Event":
                    ev = db.query(EventModel).filter(EventModel.id == ch.entity_id).first()
                    if ev:
                        existing_data = {"title": ev.title, "description": ev.description, "venue": ev.venue, "budget": ev.budget}
                elif entity_type == "Task":
                    tk = db.query(TaskModel).filter(TaskModel.id == ch.entity_id).first()
                    if tk:
                        existing_data = {"title": tk.title, "description": tk.description, "status": tk.status.value if hasattr(tk.status, "value") else str(tk.status)}
                elif entity_type == "Announcement":
                    an = db.query(AnnouncementModel).filter(AnnouncementModel.id == ch.entity_id).first()
                    if an:
                        existing_data = {"title": an.title, "content": an.content, "status": an.status}

            for k, new_v in proposed.items():
                old_v = existing_data.get(k)
                change_type = "MODIFIED" if old_v != new_v else "UNCHANGED"
                field_diffs.append(FieldDiff(
                    field=k,
                    old_value=old_v,
                    new_value=new_v,
                    change_type=change_type
                ))
            summary = f"Update existing {entity_type} #{ch.entity_id} ({len(field_diffs)} fields compared)"

        elif action_str == "DELETE":
            for k, v in proposed.items():
                field_diffs.append(FieldDiff(
                    field=k,
                    old_value=v,
                    new_value=None,
                    change_type="REMOVED"
                ))
            summary = f"Delete existing {entity_type} #{ch.entity_id}"
        # Construct clean Before vs Proposed card representations for HITL review
        before_card = None
        proposed_card = None
        reason_str = ch.explanation or f"Proposed {action_str} on {entity_type}"
        impact_str = proposed.get("impact", "No event-date delay expected.")
        confidence_str = proposed.get("confidence", "HIGH")

        entity_upper = (entity_type or "").upper()
        action_upper = (action_str or "").upper()

        if entity_upper == "TASK":
            if action_upper == "UPDATE" and ch.entity_id:
                tk = db.query(TaskModel).filter(TaskModel.id == ch.entity_id).first()
                if tk:
                    existing_owner = "Unassigned"
                    if tk.assignments:
                        assignee = tk.assignments[0].volunteer
                        if assignee and assignee.user:
                            existing_owner = assignee.user.full_name
                        elif assignee:
                            existing_owner = f"Volunteer #{assignee.id}"

                    due_str = tk.due_date.strftime("%b %d, %Y") if tk.due_date else "No deadline"
                    before_card = {
                        "task": tk.title,
                        "owner": existing_owner,
                        "due": due_str,
                        "status": tk.status.value if hasattr(tk.status, "value") else str(tk.status)
                    }

                    proposed_owner = proposed.get("volunteer_name")
                    if not proposed_owner and proposed.get("volunteer_id"):
                        from app.models.volunteer import Volunteer as VolModel
                        vol_obj = db.query(VolModel).filter(VolModel.id == proposed["volunteer_id"]).first()
                        if vol_obj and vol_obj.user:
                            proposed_owner = vol_obj.user.full_name

                    new_due = proposed.get("due_date") or proposed.get("deadline") or due_str
                    proposed_card = {
                        "task": proposed.get("title", tk.title),
                        "owner": proposed_owner or existing_owner,
                        "due": str(new_due),
                        "status": str(proposed.get("status", tk.status.value if hasattr(tk.status, "value") else str(tk.status)))
                    }
            elif action_upper == "CREATE":
                proposed_card = {
                    "task": proposed.get("title", "New Task"),
                    "owner": proposed.get("volunteer_name", "Unassigned"),
                    "due": str(proposed.get("due_date", proposed.get("deadline", "TBD"))),
                    "status": str(proposed.get("status", "TODO"))
                }
            elif action_upper == "DELETE" and ch.entity_id:
                tk = db.query(TaskModel).filter(TaskModel.id == ch.entity_id).first()
                if tk:
                    before_card = {
                        "task": tk.title,
                        "status": tk.status.value if hasattr(tk.status, "value") else str(tk.status)
                    }
        elif entity_upper == "EVENT":
            if action_upper == "CREATE":
                proposed_card = {
                    "task": proposed.get("title", "New Event"),
                    "venue": proposed.get("venue", "TBD"),
                    "due": str(proposed.get("date", "TBD")),
                    "status": "UPCOMING"
                }

        entity_diffs.append(EntityDiff(
            entity_type=entity_type,
            entity_id=ch.entity_id,
            action=action_str,
            summary=summary,
            field_diffs=field_diffs,
            before=before_card,
            proposed=proposed_card,
            reason=reason_str,
            impact=impact_str,
            confidence=confidence_str
        ))

    overall_impact = "All proposed changes maintain schedule integrity." if entity_diffs else "No changes."
    return ProposalDiffPreview(
        proposal_id=proposal.id,
        intent=proposal.intent,
        status=proposal.status.value if hasattr(proposal.status, "value") else str(proposal.status),
        total_changes=len(entity_diffs),
        entities_affected=list(entities_affected_set),
        diffs=entity_diffs,
        overall_impact=overall_impact,
        overall_confidence="HIGH"
    )

def apply_proposal(db: Session, proposal_id: int, user_id: Optional[int] = None) -> ProposalResponse:
    """
    Apply a PENDING proposal to the database inside an atomic transaction.
    Creates Event/Task/Announcement rows and writes AuditLog entries.
    """
    proposal = db.query(AIProposal).filter(AIProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if user_id:
        from app.models.user import User
        from app.services.authz import AuthorizationService
        actor = db.query(User).filter(User.id == user_id).first()
        if actor and not AuthorizationService.can_apply_ai_proposal(db, actor, proposal_id):
            raise HTTPException(
                status_code=403,
                detail="Permission denied: You are not authorized to apply this proposal due to organizational scope restrictions."
            )

    created_event_id = None


    try:
        for change in proposal.changes:
            action_str = change.action.value if hasattr(change.action, "value") else str(change.action)
            data = change.proposed_data or {}

            entity_type_upper = (change.entity_type or "").upper()
            action_upper = action_str.upper()

            if entity_type_upper in ["EVENT"]:
                if action_upper == "CREATE":
                    event = EventModel(
                        title=data.get("title", "Untitled Event"),
                        description=data.get("description", ""),
                        venue=data.get("venue"),
                        expected_attendance=data.get("expected_attendance", 0),
                        budget=data.get("budget", 0.0),
                        date=datetime.utcnow(),
                        created_by=user_id,
                    )
                    db.add(event)
                    db.flush()
                    created_event_id = event.id
                    change.entity_id = event.id

                    db.add(AuditLog(
                        proposal_id=proposal.id,
                        entity_type="Event",
                        entity_id=event.id,
                        action="CREATE",
                        previous_state=None,
                        new_state={"id": event.id, **data},
                        user_id=user_id,
                    ))
                elif action_upper == "UPDATE" and change.entity_id:
                    event = db.query(EventModel).filter(EventModel.id == change.entity_id).first()
                    if event:
                        prev_state = {"id": event.id, "title": event.title, "budget": event.budget}
                        for k, v in data.items():
                            if hasattr(event, k):
                                setattr(event, k, v)
                        db.flush()
                        db.add(AuditLog(
                            proposal_id=proposal.id,
                            entity_type="Event",
                            entity_id=event.id,
                            action="UPDATE",
                            previous_state=prev_state,
                            new_state={"id": event.id, **data},
                            user_id=user_id,
                        ))

            elif entity_type_upper in ["TASK"]:
                if action_upper == "CREATE":
                    # associate with newly created event or existing
                    ev_id = data.get("event_id", created_event_id)
                    task = TaskModel(
                        event_id=ev_id or 1,
                        title=data.get("title", "Untitled Task"),
                        description=data.get("description", ""),
                        status="TODO",
                    )
                    db.add(task)
                    db.flush()
                    change.entity_id = task.id

                    db.add(AuditLog(
                        proposal_id=proposal.id,
                        entity_type="Task",
                        entity_id=task.id,
                        action="CREATE",
                        previous_state=None,
                        new_state={"id": task.id, **data},
                        user_id=user_id,
                    ))
                elif action_upper == "UPDATE" and change.entity_id:
                    task = db.query(TaskModel).filter(TaskModel.id == change.entity_id).first()
                    if task:
                        # Re-verify authorization right before applying to database
                        if user_id:
                            try:
                                from app.services.authz import AuthorizationService
                                from app.models.user import User
                            except ImportError:
                                from backend.app.services.authz import AuthorizationService
                                from backend.app.models.user import User
                            user_obj = db.query(User).filter(User.id == user_id).first()
                            if user_obj:
                                if "volunteer_id" in data:
                                    AuthorizationService.require_permission(
                                        db, user_obj, "task.assign", resource=task,
                                        detail=f"User #{user_id} lacks permission to assign task #{task.id}"
                                    )
                                else:
                                    AuthorizationService.require_permission(
                                        db, user_obj, "task.update", resource=task,
                                        detail=f"User #{user_id} lacks permission to update task #{task.id}"
                                    )

                        prev_state = {"id": task.id, "title": task.title, "status": str(task.status)}
                        if "status" in data:
                            task.status = data["status"]
                        if "title" in data:
                            task.title = data["title"]
                        if "description" in data:
                            task.description = data["description"]
                        if "volunteer_id" in data:
                            from app.models.task import TaskAssignment
                            existing_assign = db.query(TaskAssignment).filter(
                                TaskAssignment.task_id == task.id,
                                TaskAssignment.volunteer_id == data["volunteer_id"]
                            ).first()
                            if not existing_assign:
                                db.add(TaskAssignment(task_id=task.id, volunteer_id=data["volunteer_id"]))
                        db.flush()
                        db.add(AuditLog(
                            proposal_id=proposal.id,
                            entity_type="Task",
                            entity_id=task.id,
                            action="UPDATE",
                            previous_state=prev_state,
                            new_state={"id": task.id, **data},
                            user_id=user_id,
                        ))

            elif entity_type_upper in ["ANNOUNCEMENT"]:
                if action_upper == "CREATE":
                    ann = AnnouncementModel(
                        event_id=data.get("event_id", created_event_id),
                        title=data.get("title", "Untitled Announcement"),
                        content=data.get("content", ""),
                        target_audience=data.get("target_audience"),
                        status="DRAFT",
                        created_by=user_id
                    )
                    db.add(ann)
                    db.flush()
                    change.entity_id = ann.id

                    db.add(AuditLog(
                        proposal_id=proposal.id,
                        entity_type="Announcement",
                        entity_id=ann.id,
                        action="CREATE",
                        previous_state=None,
                        new_state={"id": ann.id, **data},
                        user_id=user_id,
                    ))

        proposal.status = ProposalStatus.APPLIED
        db.commit()
        db.refresh(proposal)
        logger.info(f"Proposal {proposal_id} applied atomically.")
        return _build_response(proposal)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to apply proposal {proposal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to apply proposal: {str(e)}")

def reject_proposal(db: Session, proposal_id: int, reason: Optional[str] = None) -> ProposalResponse:
    """Reject a pending AI proposal without modifying application state."""
    proposal = db.query(AIProposal).filter(AIProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only PENDING proposals can be rejected")

    proposal.status = ProposalStatus.REJECTED
    db.commit()
    db.refresh(proposal)
    logger.info(f"Proposal {proposal_id} rejected. Reason: {reason or 'No reason provided'}")
    return _build_response(proposal)

def undo_proposal(db: Session, proposal_id: int, user_id: Optional[int] = None) -> ProposalResponse:
    """Reverse a previously applied AI action using its audit information."""
    proposal = db.query(AIProposal).filter(AIProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != ProposalStatus.APPLIED:
        raise HTTPException(status_code=400, detail="Only APPLIED proposals can be undone")

    audit_entries = db.query(AuditLog).filter(
        AuditLog.proposal_id == proposal_id
    ).all()

    try:
        # Revert in reverse order
        for entry in reversed(audit_entries):
            action_str = entry.action.value if hasattr(entry.action, "value") else str(entry.action)
            if action_str == "CREATE":
                if entry.entity_type == "Task":
                    task = db.query(TaskModel).filter(TaskModel.id == entry.entity_id).first()
                    if task:
                        db.delete(task)
                elif entry.entity_type == "Announcement":
                    ann = db.query(AnnouncementModel).filter(AnnouncementModel.id == entry.entity_id).first()
                    if ann:
                        db.delete(ann)
                elif entry.entity_type == "Event":
                    event = db.query(EventModel).filter(EventModel.id == entry.entity_id).first()
                    if event:
                        db.delete(event)
            elif action_str == "UPDATE":
                if entry.entity_type == "Task":
                    task = db.query(TaskModel).filter(TaskModel.id == entry.entity_id).first()
                    if task and entry.previous_state:
                        if "status" in entry.previous_state:
                            task.status = entry.previous_state["status"]
                        if "title" in entry.previous_state:
                            task.title = entry.previous_state["title"]
                        if "description" in entry.previous_state:
                            task.description = entry.previous_state["description"]
                        if entry.new_state and "volunteer_id" in entry.new_state:
                            from app.models.task import TaskAssignment
                            db.query(TaskAssignment).filter(
                                TaskAssignment.task_id == task.id,
                                TaskAssignment.volunteer_id == entry.new_state["volunteer_id"]
                            ).delete()
                elif entry.entity_type == "Event":
                    event = db.query(EventModel).filter(EventModel.id == entry.entity_id).first()
                    if event and entry.previous_state:
                        for k, v in entry.previous_state.items():
                            if hasattr(event, k):
                                setattr(event, k, v)

        proposal.status = ProposalStatus.UNDONE
        db.commit()
        db.refresh(proposal)
        logger.info(f"Proposal {proposal_id} undone successfully via audit trail.")
        return _build_response(proposal)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to undo proposal {proposal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to undo proposal: {str(e)}")

def get_action_audit_log(
    db: Session,
    proposal_id: Optional[int] = None,
    user_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    limit: int = 50
) -> List[AuditLogEntryOut]:
    """Retrieve AI actions, timestamps, tools used, changes made, and triggering user."""
    query = db.query(AuditLog)
    if proposal_id is not None:
        query = query.filter(AuditLog.proposal_id == proposal_id)
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    if entity_type is not None:
        query = query.filter(AuditLog.entity_type == entity_type)

    entries = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        AuditLogEntryOut(
            id=e.id,
            proposal_id=e.proposal_id,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            action=e.action,
            previous_state=e.previous_state,
            new_state=e.new_state,
            user_id=e.user_id,
            timestamp=e.timestamp
        )
        for e in entries
    ]
