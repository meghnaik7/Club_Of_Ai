try:
    from langchain_core.tools import tool
except ImportError:
    from ai.tools.compat import tool
from typing import Optional, List, Dict, Any

from ai.workflows import task_planning_engine

@tool
def generate_task_graph(
    event_brief: str,
    event_id: Optional[int] = None,
    event_date: Optional[str] = None,
    target_attendees: Optional[int] = None
) -> dict:
    """Generate tasks, subtasks, dependencies, phases, and suggested owners from an event brief."""
    return task_planning_engine.generate_task_graph(
        event_brief=event_brief,
        event_id=event_id,
        event_date=event_date,
        target_attendees=target_attendees
    )

@tool
def split_task(
    task_title: str,
    task_description: Optional[str] = None,
    task_id: Optional[int] = None,
    num_subtasks: Optional[int] = 3,
    total_duration_hours: Optional[int] = None
) -> dict:
    """Break a large task into smaller executable subtasks with dependencies."""
    return task_planning_engine.split_task(
        task_title=task_title,
        task_description=task_description,
        task_id=task_id,
        num_subtasks=num_subtasks or 3,
        total_duration_hours=total_duration_hours
    )

@tool
def suggest_task_owner(
    task_title: str,
    task_skills: Optional[List[str]] = None,
    task_id: Optional[int] = None,
    deadline: Optional[str] = None
) -> dict:
    """Suggest suitable volunteers based on skills, availability, workload, and deadline."""
    return task_planning_engine.suggest_task_owner(
        task_title=task_title,
        task_skills=task_skills,
        task_id=task_id,
        deadline=deadline
    )

@tool
def reschedule_task(
    task_id: Any,
    new_start_date: str,
    new_deadline: str,
    tasks_data: Optional[List[dict]] = None
) -> dict:
    """Change a task's schedule while analyzing affected dependencies."""
    return task_planning_engine.reschedule_task(
        task_id=task_id,
        new_start_date=new_start_date,
        new_deadline=new_deadline,
        tasks_data=tasks_data
    )

@tool
def cascade_reschedule(
    task_id: Any,
    time_shift_hours: int,
    tasks_data: Optional[List[dict]] = None
) -> dict:
    """Reschedule dependent tasks when an upstream task changes."""
    return task_planning_engine.cascade_reschedule(
        task_id=task_id,
        time_shift_hours=time_shift_hours,
        tasks_data=tasks_data
    )

@tool
def detect_dependency_conflicts(tasks_data: List[dict]) -> dict:
    """Detect circular dependencies, impossible schedules, blocked chains, and date conflicts."""
    return task_planning_engine.detect_dependency_conflicts(tasks_data=tasks_data)

@tool
def explain_dependency_conflict(conflict_data: Any) -> dict:
    """Explain the cause and impact of a dependency conflict in plain language."""
    return task_planning_engine.explain_dependency_conflict(conflict_data=conflict_data)
