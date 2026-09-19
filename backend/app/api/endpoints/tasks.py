from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import schemas
from app.api import deps
from app.models.task import Task, TaskStatus, TaskPriority, TaskPhase, TaskAssignment
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=List[schemas.Task])
def list_tasks(
    db: Session = Depends(deps.get_db),
    event_id: Optional[int] = Query(None, description="Filter tasks by event"),
    status: Optional[TaskStatus] = Query(None),
    priority: Optional[TaskPriority] = Query(None),
    phase: Optional[TaskPhase] = Query(None),
    skip: int = 0,
    limit: int = 200,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """List all tasks, optionally filtered by event/status/priority/phase."""
    q = db.query(Task)
    if event_id is not None:
        q = q.filter(Task.event_id == event_id)
    if status is not None:
        q = q.filter(Task.status == status)
    if priority is not None:
        q = q.filter(Task.priority == priority)
    if phase is not None:
        q = q.filter(Task.phase == phase)
    return q.offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.Task)
def create_task(
    *,
    db: Session = Depends(deps.get_db),
    task_in: schemas.TaskCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Create a new task (and optionally assign volunteers immediately)."""
    task = Task(
        event_id=task_in.event_id,
        title=task_in.title,
        description=task_in.description,
        status=task_in.status or TaskStatus.TODO,
        priority=task_in.priority or TaskPriority.MEDIUM,
        phase=task_in.phase,
        start_date=task_in.start_date,
        due_date=task_in.due_date,
        parent_id=task_in.parent_id,
    )
    db.add(task)
    db.flush()  # Get the ID before adding assignments

    # Assign volunteers if provided
    for vol_id in (task_in.owner_ids or []):
        db.add(TaskAssignment(task_id=task.id, volunteer_id=vol_id))

    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=schemas.Task)
def get_task(
    task_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get a single task by ID."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=schemas.Task)
def update_task(
    *,
    db: Session = Depends(deps.get_db),
    task_id: int,
    task_in: schemas.TaskUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Update a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(
    *,
    db: Session = Depends(deps.get_db),
    task_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Delete a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"ok": True}


@router.post("/{task_id}/assign/{volunteer_id}", response_model=schemas.Task)
def assign_volunteer(
    *,
    db: Session = Depends(deps.get_db),
    task_id: int,
    volunteer_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Assign a volunteer to a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Avoid duplicate assignment
    existing = db.query(TaskAssignment).filter(
        TaskAssignment.task_id == task_id,
        TaskAssignment.volunteer_id == volunteer_id
    ).first()
    if not existing:
        db.add(TaskAssignment(task_id=task_id, volunteer_id=volunteer_id))
        db.commit()
        db.refresh(task)
    return task


@router.delete("/{task_id}/assign/{volunteer_id}", response_model=schemas.Task)
def unassign_volunteer(
    *,
    db: Session = Depends(deps.get_db),
    task_id: int,
    volunteer_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Remove a volunteer assignment from a task."""
    assignment = db.query(TaskAssignment).filter(
        TaskAssignment.task_id == task_id,
        TaskAssignment.volunteer_id == volunteer_id
    ).first()
    if assignment:
        db.delete(assignment)
        db.commit()
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.refresh(task)
    return task
