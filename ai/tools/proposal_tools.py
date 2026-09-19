try:
    from langchain_core.tools import tool
except ImportError:
    from ai.tools.compat import tool
from typing import Optional, List, Dict, Any

try:
    from app.db.session import SessionLocal
except ImportError:
    from backend.app.db.session import SessionLocal

from ai.workflows import proposal_service
from ai.schemas.ai_plan import EventPlan, GeneratedTask

@tool
def create_action_proposal(
    intent: str,
    changes: Optional[List[Dict[str, Any]]] = None,
    event_title: Optional[str] = None,
    tasks: Optional[List[dict]] = None,
    user_id: Optional[int] = None
) -> dict:
    """Generate a proposed set of changes without modifying application state."""
    db = SessionLocal()
    try:
        event_plan = None
        if event_title:
            task_objs = []
            for t in (tasks or []):
                task_objs.append(GeneratedTask(
                    title=t.get("title", "Untitled Task"),
                    description=t.get("description", ""),
                    phase=t.get("phase", "PRE_EVENT"),
                    priority=t.get("priority", "MEDIUM"),
                    estimated_duration_hours=t.get("estimated_duration_hours", 4)
                ))
            event_plan = EventPlan(
                event_title=event_title,
                tasks=task_objs if task_objs else [GeneratedTask(title="Initial Event Coordination")]
            )

        resp = proposal_service.create_proposal(
            db=db,
            user_id=user_id,
            intent=intent,
            event_plan=event_plan,
            changes=changes
        )
        return resp.model_dump()
    finally:
        db.close()

@tool
def get_action_proposal(proposal_id: int) -> dict:
    """Retrieve the proposed changes and their current status."""
    db = SessionLocal()
    try:
        resp = proposal_service.get_proposal(db=db, proposal_id=proposal_id)
        return resp.model_dump()
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@tool
def preview_action_diff(proposal_id: int) -> dict:
    """Calculate exactly what entities and fields will change if the proposal is applied."""
    db = SessionLocal()
    try:
        diff_preview = proposal_service.preview_action_diff(db=db, proposal_id=proposal_id)
        return diff_preview.model_dump()
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@tool
def apply_action_proposal(proposal_id: int, user_id: Optional[int] = None) -> dict:
    """Apply an approved proposal atomically."""
    db = SessionLocal()
    try:
        resp = proposal_service.apply_proposal(db=db, proposal_id=proposal_id, user_id=user_id)
        return {
            "success": True,
            "proposal_id": resp.proposal_id,
            "status": resp.status,
            "message": f"Proposal #{proposal_id} successfully applied to production state."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@tool
def reject_action_proposal(proposal_id: int, reason: Optional[str] = None) -> dict:
    """Reject a pending AI proposal without modifying application state."""
    db = SessionLocal()
    try:
        resp = proposal_service.reject_proposal(db=db, proposal_id=proposal_id, reason=reason)
        return {
            "success": True,
            "proposal_id": resp.proposal_id,
            "status": resp.status,
            "message": f"Proposal #{proposal_id} was rejected without modifying application state."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@tool
def undo_action(proposal_id: int, user_id: Optional[int] = None) -> dict:
    """Reverse a previously applied AI action using its audit information."""
    db = SessionLocal()
    try:
        resp = proposal_service.undo_proposal(db=db, proposal_id=proposal_id, user_id=user_id)
        return {
            "success": True,
            "proposal_id": resp.proposal_id,
            "status": resp.status,
            "message": f"Proposal #{proposal_id} and all created entities were successfully reverted."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@tool
def get_action_audit_log(
    proposal_id: Optional[int] = None,
    user_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    limit: Optional[int] = 50
) -> list:
    """Retrieve AI actions, timestamps, tools used, changes made, and triggering user."""
    db = SessionLocal()
    try:
        entries = proposal_service.get_action_audit_log(
            db=db,
            proposal_id=proposal_id,
            user_id=user_id,
            entity_type=entity_type,
            limit=limit or 50
        )
        return [e.model_dump() for e in entries]
    finally:
        db.close()

# Backward-compatibility helper
@tool
def propose_event_plan(intent: str, event_title: str, tasks: list[dict], user_id: int) -> str:
    """Propose a new event and a set of tasks for it."""
    db = SessionLocal()
    try:
        task_objs = [
            GeneratedTask(
                title=t.get("title", ""),
                description=t.get("description", ""),
                phase=t.get("phase", "PRE_EVENT"),
                priority=t.get("priority", "MEDIUM"),
                estimated_duration_hours=t.get("estimated_duration_hours", 4)
            )
            for t in tasks
        ]
        event_plan = EventPlan(event_title=event_title, tasks=task_objs)
        proposal = proposal_service.create_proposal(db, user_id, intent, event_plan)
        return f"Created Proposal ID: {proposal.proposal_id}. The user must review and approve these changes."
    except Exception as e:
        return f"Failed to create proposal: {str(e)}"
    finally:
        db.close()
