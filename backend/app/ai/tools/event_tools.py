from typing import List, Dict, Any, Optional
from datetime import datetime
from app.db.session import SessionLocal
from app.services.event_service import event_service
from app.models.event import EventStatus
from app.schemas.event import EventCreate, EventUpdate

def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_event(
    name: str,
    date: str,
    venue: Optional[str] = None,
    budget: float = 0.0,
    expected_attendance: int = 0,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """Create an event with name, date, venue, budget, and expected attendance."""
    db = next(_get_db())
    try:
        # Parse date string (ISO format or common YYYY-MM-DD)
        parsed_date = datetime.fromisoformat(date) if isinstance(date, str) else date
        event_in = EventCreate(
            title=name,
            date=parsed_date,
            venue=venue,
            budget=budget,
            expected_attendance=expected_attendance,
            description=description,
            status=EventStatus.DRAFT
        )
        event = event_service.create_event(db, event_in)
        return {
            "success": True,
            "event_id": event.id,
            "title": event.title,
            "date": event.date.isoformat(),
            "venue": event.venue,
            "budget": event.budget,
            "status": event.status.value
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_event(event_id: int) -> Dict[str, Any]:
    """Retrieve complete event details including categories and expenses."""
    db = next(_get_db())
    try:
        event = event_service.get_event(db, event_id)
        if not event:
            return {"success": False, "error": f"Event {event_id} not found"}
        return {
            "success": True,
            "event": {
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "date": event.date.isoformat() if event.date else None,
                "venue": event.venue,
                "budget": event.budget,
                "budget_spent": event.budget_spent,
                "expected_attendance": event.expected_attendance,
                "status": event.status.value,
                "budget_categories": [
                    {"id": c.id, "name": c.name, "allocated_amount": c.allocated_amount}
                    for c in event.budget_categories
                ],
                "expense_count": len(event.expenses),
                "task_count": len(event.tasks)
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_events(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
) -> Dict[str, Any]:
    """Retrieve events with optional date/status filters."""
    db = next(_get_db())
    try:
        p_from = datetime.fromisoformat(date_from) if date_from else None
        p_to = datetime.fromisoformat(date_to) if date_to else None
        p_status = EventStatus(status) if status else None

        events = event_service.list_events(
            db=db,
            date_from=p_from,
            date_to=p_to,
            status=p_status,
            skip=skip,
            limit=limit
        )
        return {
            "success": True,
            "count": len(events),
            "events": [
                {
                    "id": e.id,
                    "title": e.title,
                    "date": e.date.isoformat() if e.date else None,
                    "venue": e.venue,
                    "budget": e.budget,
                    "status": e.status.value
                }
                for e in events
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def update_event(
    event_id: int,
    name: Optional[str] = None,
    date: Optional[str] = None,
    venue: Optional[str] = None,
    budget: Optional[float] = None,
    expected_attendance: Optional[int] = None,
    status: Optional[str] = None,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """Modify event name, date, venue, budget, attendance, or other event details."""
    db = next(_get_db())
    try:
        event = event_service.get_event(db, event_id)
        if not event:
            return {"success": False, "error": f"Event {event_id} not found"}

        update_dict = {}
        if name is not None: update_dict["title"] = name
        if date is not None: update_dict["date"] = datetime.fromisoformat(date)
        if venue is not None: update_dict["venue"] = venue
        if budget is not None: update_dict["budget"] = budget
        if expected_attendance is not None: update_dict["expected_attendance"] = expected_attendance
        if status is not None: update_dict["status"] = EventStatus(status)
        if description is not None: update_dict["description"] = description

        event_in = EventUpdate(**update_dict)
        updated = event_service.update_event(db, event, event_in)
        return {
            "success": True,
            "event_id": updated.id,
            "title": updated.title,
            "date": updated.date.isoformat() if updated.date else None,
            "venue": updated.venue,
            "budget": updated.budget,
            "status": updated.status.value
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_event(
    event_id: int,
    delete_documents: bool = False
) -> Dict[str, Any]:
    """Delete an event and handle associated tasks, volunteers, and documents according to configured rules."""
    db = next(_get_db())
    try:
        result = event_service.delete_event(
            db=db,
            event_id=event_id,
            delete_documents=delete_documents
        )
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_event_dashboard(event_id: int) -> Dict[str, Any]:
    """Return task completion, risks, volunteer count, budget status, and days remaining."""
    db = next(_get_db())
    try:
        dashboard = event_service.get_event_dashboard(db, event_id)
        return {
            "success": True,
            "dashboard": dashboard.model_dump()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_event_timeline(event_id: int) -> Dict[str, Any]:
    """Return tasks with start dates, due dates, dependencies, and phases for timeline visualization."""
    db = next(_get_db())
    try:
        timeline = event_service.get_event_timeline(db, event_id)
        return {
            "success": True,
            "event_id": event_id,
            "timeline": [item.model_dump() for item in timeline]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_event_budget(event_id: int) -> Dict[str, Any]:
    """Return allocated, spent, and remaining budget grouped by task/category."""
    db = next(_get_db())
    try:
        summary = event_service.get_event_budget(db, event_id)
        return {
            "success": True,
            "budget_summary": summary.model_dump()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def record_expense(
    event_id: int,
    amount: float,
    description: Optional[str] = None,
    category: Optional[str] = None,
    task_id: Optional[int] = None,
    recorded_by: Optional[str] = "AI Assistant"
) -> Dict[str, Any]:
    """Add an expense against an event, task, or budget category."""
    db = next(_get_db())
    try:
        expense = event_service.record_expense(
            db=db,
            event_id=event_id,
            amount=amount,
            description=description,
            category=category,
            task_id=task_id,
            recorded_by=recorded_by
        )
        return {
            "success": True,
            "expense_id": expense.id,
            "event_id": expense.event_id,
            "category": expense.category,
            "amount": expense.amount,
            "description": expense.description,
            "date": expense.date.isoformat()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def update_budget_allocation(
    event_id: int,
    total_budget: Optional[float] = None,
    category_allocations: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Change the allocated budget for an event/category/task."""
    db = next(_get_db())
    try:
        event = event_service.update_budget_allocation(
            db=db,
            event_id=event_id,
            total_budget=total_budget,
            category_allocations=category_allocations
        )
        return {
            "success": True,
            "event_id": event.id,
            "total_budget": event.budget,
            "categories": [
                {"name": c.name, "allocated_amount": c.allocated_amount}
                for c in event.budget_categories
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def generate_event_plan(
    event_brief: str,
    event_title: Optional[str] = None,
    estimated_budget: Optional[float] = None,
    target_date: Optional[str] = None,
    auto_create_in_event_id: Optional[int] = None
) -> Dict[str, Any]:
    """Generate a complete event plan from a natural-language event brief, including phases, tasks, dependencies, and suggested owners."""
    db = next(_get_db())
    try:
        p_date = datetime.fromisoformat(target_date) if target_date else None
        plan = event_service.generate_event_plan(
            db=db,
            event_brief=event_brief,
            event_title=event_title,
            target_date=p_date,
            estimated_budget=estimated_budget,
            auto_create_event_id=auto_create_in_event_id
        )
        return {
            "success": True,
            "plan": plan.model_dump()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
