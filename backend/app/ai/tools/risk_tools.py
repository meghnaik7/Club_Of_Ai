from typing import List, Dict, Any, Optional
from app.db.session import SessionLocal
from app.services.risk_service import risk_service

def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def list_risks(
    event_id: int,
    status: Optional[str] = "ACTIVE",
    category: Optional[str] = None,
    severity: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve active risks for an event."""
    db = next(_get_db())
    try:
        risks = risk_service.list_risks(
            db=db,
            event_id=event_id,
            status=status,
            category=category,
            severity=severity
        )
        return {
            "success": True,
            "event_id": event_id,
            "count": len(risks),
            "risks": [
                {
                    "id": r.id,
                    "title": r.title,
                    "category": r.category,
                    "severity": r.severity,
                    "status": r.status,
                    "task_id": r.task_id,
                    "description": r.description
                }
                for r in risks
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_risk(risk_id: int) -> Dict[str, Any]:
    """Retrieve detailed information about a specific risk."""
    db = next(_get_db())
    try:
        risk = risk_service.get_risk(db, risk_id)
        if not risk:
            return {"success": False, "error": f"Risk with ID {risk_id} not found"}

        return {
            "success": True,
            "risk": {
                "id": risk.id,
                "event_id": risk.event_id,
                "task_id": risk.task_id,
                "category": risk.category,
                "severity": risk.severity,
                "title": risk.title,
                "description": risk.description,
                "root_cause": risk.root_cause,
                "suggested_fix": risk.suggested_fix,
                "status": risk.status,
                "resolved_at": risk.resolved_at.isoformat() if risk.resolved_at else None,
                "resolved_by": risk.resolved_by,
                "resolution_notes": risk.resolution_notes
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def detect_event_risks(event_id: int, persist: bool = True) -> Dict[str, Any]:
    """Analyze the event and automatically detect scheduling, ownership, dependency, workload, and planning risks."""
    db = next(_get_db())
    try:
        summary = risk_service.detect_event_risks(db, event_id=event_id, persist=persist)
        return {
            "success": True,
            "summary": summary.model_dump()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def detect_task_risks(task_id: int) -> Dict[str, Any]:
    """Analyze a task and its dependencies for potential risks."""
    db = next(_get_db())
    try:
        risks = risk_service.detect_task_risks(db, task_id)
        return {
            "success": True,
            "task_id": task_id,
            "risk_count": len(risks),
            "risks": risks
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def explain_risk(risk_id: int) -> Dict[str, Any]:
    """Explain why a risk exists and what underlying conditions caused it."""
    db = next(_get_db())
    try:
        explanation = risk_service.explain_risk(db, risk_id)
        return {
            "success": True,
            "explanation": explanation.model_dump()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def suggest_risk_fix(risk_id: int) -> Dict[str, Any]:
    """Generate one or more possible fixes such as reassignment, rescheduling, splitting, or creating a missing task."""
    db = next(_get_db())
    try:
        fix = risk_service.suggest_risk_fix(db, risk_id)
        return {
            "success": True,
            "fix_suggestion": fix.model_dump()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def resolve_risk(
    risk_id: int,
    resolution_notes: Optional[str] = None,
    resolved_by: Optional[str] = "AI Assistant"
) -> Dict[str, Any]:
    """Mark a manually managed risk as resolved when appropriate."""
    db = next(_get_db())
    try:
        risk = risk_service.resolve_risk(
            db=db,
            risk_id=risk_id,
            resolution_notes=resolution_notes,
            resolved_by=resolved_by
        )
        return {
            "success": True,
            "risk_id": risk.id,
            "status": risk.status,
            "resolved_at": risk.resolved_at.isoformat() if risk.resolved_at else None,
            "resolution_notes": risk.resolution_notes
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_unowned_tasks_near_deadline(event_id: int, days_threshold: int = 7) -> Dict[str, Any]:
    """Find tasks approaching their deadlines that have no owner."""
    db = next(_get_db())
    try:
        results = risk_service.get_unowned_tasks_near_deadline(db, event_id, days_threshold=days_threshold)
        return {
            "success": True,
            "event_id": event_id,
            "unowned_count": len(results),
            "unowned_tasks": results
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_overload_risks(event_id: int) -> Dict[str, Any]:
    """Identify volunteers with excessive workload or deadline collisions."""
    db = next(_get_db())
    try:
        results = risk_service.get_overload_risks(db, event_id)
        return {
            "success": True,
            "event_id": event_id,
            "overload_risk_count": len(results),
            "overload_risks": results
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_dependency_conflicts(event_id: int) -> Dict[str, Any]:
    """Detect invalid, conflicting, blocked, or impossible dependency chains."""
    db = next(_get_db())
    try:
        results = risk_service.get_dependency_conflicts(db, event_id)
        return {
            "success": True,
            "event_id": event_id,
            "conflict_count": len(results),
            "dependency_conflicts": results
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_missing_activity_risks(event_id: int) -> Dict[str, Any]:
    """Detect potentially missing activities required for the event based on the event type/plan."""
    db = next(_get_db())
    try:
        results = risk_service.get_missing_activity_risks(db, event_id)
        return {
            "success": True,
            "event_id": event_id,
            "missing_activity_count": len(results),
            "missing_activities": results
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
