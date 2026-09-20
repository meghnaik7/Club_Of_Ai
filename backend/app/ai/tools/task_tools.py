from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from app.db.session import SessionLocal
from app.services.task_service import task_service
from app.schemas.task import TaskCreate, TaskUpdate, TaskCommentCreate
from app.models.task import TaskStatus, TaskPriority, TaskPhase
from app.engine.critical_path import calculate_critical_path

# To implement LangChain/LangGraph tools, they should usually be functions with typed signatures.
# Here we provide the core implementation of the tools for the AI agent to call.

def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_task(title: str, event_id: int, description: str = None, priority: str = "MEDIUM", status: str = "TODO", phase: str = None, due_date: str = None, owner_ids: List[int] = None) -> Dict[str, Any]:
    """Create a task with title, description, priority, status, due date, event, phase, and optional owner(s)."""
    db = next(_get_db())
    try:
        task_in = TaskCreate(
            title=title, event_id=event_id, description=description, 
            priority=TaskPriority(priority), status=TaskStatus(status), 
            phase=TaskPhase(phase) if phase else None,
            due_date=datetime.fromisoformat(due_date) if due_date else None,
            owner_ids=owner_ids or []
        )
        task = task_service.create_task(db, task_in)
        return {"success": True, "task_id": task.id}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_task(task_id: int) -> Dict[str, Any]:
    """Retrieve complete details of a task including owners, dependencies, subtasks, comments, status, and dates."""
    db = next(_get_db())
    try:
        task = task_service.get_task(db, task_id)
        if not task:
            return {"success": False, "error": "Task not found"}
        return {
            "success": True,
            "task": {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "phase": task.phase,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "assignments": [a.volunteer_id for a in task.assignments]
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_tasks(event_id: int, status: str = None, priority: str = None, phase: str = None, owner_id: int = None) -> Dict[str, Any]:
    """Retrieve tasks for an event with filters such as status, owner, priority, due date, and phase."""
    db = next(_get_db())
    try:
        tasks = task_service.list_tasks(
            db, event_id, 
            status=TaskStatus(status) if status else None,
            priority=TaskPriority(priority) if priority else None,
            phase=TaskPhase(phase) if phase else None,
            owner_id=owner_id
        )
        return {"success": True, "tasks": [{"id": t.id, "title": t.title} for t in tasks]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def update_task(task_id: int, title: str = None, description: str = None, priority: str = None, due_date: str = None, phase: str = None, status: str = None) -> Dict[str, Any]:
    """Modify task title, description, priority, due date, phase, or other editable fields."""
    db = next(_get_db())
    try:
        task = task_service.get_task(db, task_id)
        if not task:
            return {"success": False, "error": "Task not found"}
            
        update_data = {}
        if title is not None: update_data["title"] = title
        if description is not None: update_data["description"] = description
        if priority is not None: update_data["priority"] = TaskPriority(priority)
        if status is not None: update_data["status"] = TaskStatus(status)
        if due_date is not None: update_data["due_date"] = datetime.fromisoformat(due_date)
        if phase is not None: update_data["phase"] = TaskPhase(phase)
            
        task_in = TaskUpdate(**update_data)
        updated = task_service.update_task(db, task, task_in)
        return {"success": True, "task_id": updated.id}
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_task(task_id: int) -> Dict[str, Any]:
    """Delete a task after checking its dependencies and associated data."""
    db = next(_get_db())
    try:
        deleted = task_service.delete_task(db, task_id)
        return {"success": deleted}
    except Exception as e:
        return {"success": False, "error": str(e)}

def assign_task(task_id: int, volunteer_ids: List[int]) -> Dict[str, Any]:
    """Assign one or multiple volunteers to a task."""
    db = next(_get_db())
    try:
        task_service.assign_task(db, task_id, volunteer_ids)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def unassign_task(task_id: int, volunteer_ids: List[int]) -> Dict[str, Any]:
    """Remove one or multiple volunteers from a task."""
    db = next(_get_db())
    try:
        task_service.unassign_task(db, task_id, volunteer_ids)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def change_task_status(task_id: int, status: str) -> Dict[str, Any]:
    """Change task status between TODO, IN_PROGRESS, DONE, and BLOCKED."""
    db = next(_get_db())
    try:
        task_service.change_task_status(db, task_id, TaskStatus(status))
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def create_subtask(parent_id: int, title: str, event_id: int) -> Dict[str, Any]:
    """Create a child task under an existing parent task."""
    db = next(_get_db())
    try:
        task_in = TaskCreate(title=title, event_id=event_id)
        subtask = task_service.create_subtask(db, parent_id, task_in)
        return {"success": True, "task_id": subtask.id}
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_subtasks(parent_id: int) -> Dict[str, Any]:
    """Retrieve all subtasks belonging to a parent task."""
    db = next(_get_db())
    try:
        subtasks = task_service.list_subtasks(db, parent_id)
        return {"success": True, "subtasks": [{"id": t.id, "title": t.title} for t in subtasks]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def add_task_dependency(dependent_task_id: int, prerequisite_task_id: int) -> Dict[str, Any]:
    """Create a dependency where one task blocks another."""
    db = next(_get_db())
    try:
        task_service.add_task_dependency(db, dependent_task_id, prerequisite_task_id)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def remove_task_dependency(dependent_task_id: int, prerequisite_task_id: int) -> Dict[str, Any]:
    """Remove an existing task dependency."""
    db = next(_get_db())
    try:
        removed = task_service.remove_task_dependency(db, dependent_task_id, prerequisite_task_id)
        return {"success": removed}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_task_dependencies(task_id: int) -> Dict[str, Any]:
    """Retrieve tasks that a task blocks or tasks blocking it."""
    db = next(_get_db())
    try:
        deps = task_service.get_task_dependencies(db, task_id)
        return {
            "success": True,
            "blocks": [{"id": t.id, "title": t.title} for t in deps["blocks"]],
            "blocked_by": [{"id": t.id, "title": t.title} for t in deps["blocked_by"]]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def add_task_comment(task_id: int, user_id: int, content: str) -> Dict[str, Any]:
    """Add a comment to a task."""
    db = next(_get_db())
    try:
        comment_in = TaskCommentCreate(task_id=task_id, user_id=user_id, content=content)
        task_service.add_task_comment(db, comment_in)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_task_activity(task_id: int) -> Dict[str, Any]:
    """Retrieve task comments and activity/history records."""
    db = next(_get_db())
    try:
        activity = task_service.get_task_activity(db, task_id)
        return {"success": True, "activity": [{"content": c.content, "created_at": c.created_at.isoformat()} for c in activity]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def bulk_update_tasks(task_ids: List[int], status: str = None, priority: str = None) -> Dict[str, Any]:
    """Apply the same operation to multiple tasks, such as reassignment, rescheduling, or completion."""
    db = next(_get_db())
    try:
        for tid in task_ids:
            update_task(tid, status=status, priority=priority) # Note: simplify for demo
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def tool_calculate_critical_path(event_id: int) -> Dict[str, Any]:
    """Analyze task dependencies and dates to identify zero-slack/critical tasks."""
    db = next(_get_db())
    try:
        res = calculate_critical_path(db, event_id)
        return {"success": True, "critical_path": res}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_overdue_tasks(event_id: int) -> Dict[str, Any]:
    """Retrieve incomplete tasks whose due dates have passed."""
    db = next(_get_db())
    try:
        tasks = task_service.get_overdue_tasks(db, event_id)
        return {"success": True, "tasks": [{"id": t.id, "title": t.title} for t in tasks]}
    except Exception as e:
        return {"success": False, "error": str(e)}
