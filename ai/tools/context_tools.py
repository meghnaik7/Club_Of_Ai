from typing import Optional, List, Dict, Any
try:
    from langchain_core.tools import tool
except ImportError:
    from ai.tools.compat import tool

try:
    from app.db.session import SessionLocal
except ImportError:
    from backend.app.db.session import SessionLocal

try:
    from app.services import context_service
except ImportError:
    from backend.app.services import context_service


@tool
def get_event_context(event_id: int) -> Dict[str, Any]:
    """
    Returns important event information for the AI in a single structured payload.
    Provides event title, description, venue, budget, attendance, task metrics,
    assigned volunteers, recent announcements, and attached documents without multiple queries.
    """
    db = SessionLocal()
    try:
        return context_service.get_event_context(db=db, event_id=event_id)
    except Exception as e:
        return {"error": f"Failed to retrieve event context: {str(e)}"}
    finally:
        db.close()


@tool
def get_task_context(task_id: int) -> Dict[str, Any]:
    """
    Returns task information, associated event, assigned volunteers, and assignment status.
    """
    db = SessionLocal()
    try:
        return context_service.get_task_context(db=db, task_id=task_id)
    except Exception as e:
        return {"error": f"Failed to retrieve task context: {str(e)}"}
    finally:
        db.close()


@tool
def get_volunteer_context(volunteer_id: int) -> Dict[str, Any]:
    """
    Returns volunteer profile, parsed skills, availability, and current active/completed workload metrics.
    """
    db = SessionLocal()
    try:
        return context_service.get_volunteer_context(db=db, volunteer_id=volunteer_id)
    except Exception as e:
        return {"error": f"Failed to retrieve volunteer context: {str(e)}"}
    finally:
        db.close()


@tool
def get_project_summary(event_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Returns high-level project summary including total events, total tasks, active tasks,
    completed tasks, overall completion rate percentage, active volunteers count, and pending proposals.
    """
    db = SessionLocal()
    try:
        return context_service.get_project_summary(db=db, event_id=event_id)
    except Exception as e:
        return {"error": f"Failed to retrieve project summary: {str(e)}"}
    finally:
        db.close()


@tool
def search_tasks(
    query: str,
    event_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search tasks across titles and descriptions with optional event_id and status filters.
    """
    db = SessionLocal()
    try:
        return context_service.search_tasks(
            db=db,
            query=query,
            event_id=event_id,
            status=status,
            limit=limit
        )
    except Exception as e:
        return [{"error": f"Failed to search tasks: {str(e)}"}]
    finally:
        db.close()


@tool
def search_volunteers(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search volunteers by natural-language requirements across skills, availability, name, or email.
    """
    db = SessionLocal()
    try:
        return context_service.search_volunteers(db=db, query=query, limit=limit)
    except Exception as e:
        return [{"error": f"Failed to search volunteers: {str(e)}"}]
    finally:
        db.close()


@tool
def search_event_data(
    query: str,
    event_id: Optional[int] = None,
    limit: int = 15
) -> Dict[str, Any]:
    """
    Unified search across all event entities (tasks, announcements, and documents).
    """
    db = SessionLocal()
    try:
        return context_service.search_event_data(
            db=db,
            query=query,
            event_id=event_id,
            limit=limit
        )
    except Exception as e:
        return {"error": f"Failed to search event data: {str(e)}"}
    finally:
        db.close()


@tool
def get_next_event() -> Dict[str, Any]:
    """
    Returns full details about the immediate next upcoming club event,
    including title, date, venue, attendance, budget, and task progress summary.
    Use this whenever a user asks 'What is the next event?', 'When is our next event?',
    or asks for upcoming event information.
    """
    db = SessionLocal()
    try:
        return context_service.get_next_event(db=db)
    except Exception as e:
        return {"error": f"Failed to retrieve next event: {str(e)}"}
    finally:
        db.close()


@tool
def get_upcoming_events(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Returns a list of all upcoming events ordered chronologically.
    Provides title, date, venue, attendance, budget, and task progress for each event.
    """
    db = SessionLocal()
    try:
        return context_service.get_upcoming_events(db=db, limit=limit)
    except Exception as e:
        return [{"error": f"Failed to retrieve upcoming events: {str(e)}"}]
    finally:
        db.close()

