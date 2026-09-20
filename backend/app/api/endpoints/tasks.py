from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app import schemas
from app.api import deps
from app.models.task import Task, TaskStatus, TaskPriority, TaskPhase, TaskAssignment
from app.models.volunteer import Volunteer
from app.models.team import TeamMembership
from app.models.user import User
from app.services.authz import AuthorizationService

router = APIRouter()


@router.get("/", response_model=List[schemas.Task])
def list_tasks(
    db: Session = Depends(deps.get_db),
    event_id: Optional[int] = Query(None, description="Filter tasks by event"),
    team_id: Optional[int] = Query(None, description="Filter tasks by team"),
    status: Optional[TaskStatus] = Query(None),
    priority: Optional[TaskPriority] = Query(None),
    phase: Optional[TaskPhase] = Query(None),
    skip: int = 0,
    limit: int = 200,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """List all tasks, scoped by user authorization and roles."""
    q = db.query(Task)
    if event_id is not None:
        q = q.filter(Task.event_id == event_id)
    if team_id is not None:
        q = q.filter(Task.team_id == team_id)
    if status is not None:
        q = q.filter(Task.status == status)
    if priority is not None:
        q = q.filter(Task.priority == priority)
    if phase is not None:
        q = q.filter(Task.phase == phase)

    # Scoping for non-admin users
    if not AuthorizationService.is_admin(current_user):
        user_club = AuthorizationService.get_user_club_id(db, current_user)
        if AuthorizationService.is_club_head(db, current_user, club_id=user_club):
            from app.models.event import Event
            from app.models.team import Team
            q = q.filter(
                or_(
                    Task.event.has(Event.club_id == user_club),
                    Task.team.has(Team.club_id == user_club),
                    Task.created_by == current_user.id
                )
            )
        else:
            user_teams = list(AuthorizationService.get_user_team_roles(db, current_user).keys())
            user_events = list(AuthorizationService.get_user_event_roles(db, current_user).keys())
            volunteer_id = current_user.volunteer_profile.id if current_user.volunteer_profile else None

            conditions = [Task.created_by == current_user.id]
            if user_teams:
                conditions.append(Task.team_id.in_(user_teams))
            if user_events:
                conditions.append(Task.event_id.in_(user_events))
            if volunteer_id:
                conditions.append(Task.assignments.any(TaskAssignment.volunteer_id == volunteer_id))

            q = q.filter(or_(*conditions))

    return q.offset(skip).limit(limit).all()


@router.post("/", response_model=schemas.Task)
def create_task(
    *,
    db: Session = Depends(deps.get_db),
    task_in: schemas.TaskCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Create a new task with team and event scoping."""
    if task_in.team_id:
        AuthorizationService.require_permission(
            db, current_user, "task.create",
            scope_type="TEAM", scope_id=task_in.team_id,
            detail=f"Permission denied: Cannot create task for team #{task_in.team_id}"
        )
    elif task_in.event_id:
        AuthorizationService.require_permission(
            db, current_user, "task.create",
            scope_type="EVENT", scope_id=task_in.event_id,
            detail=f"Permission denied: Cannot create task for event #{task_in.event_id}"
        )
    else:
        AuthorizationService.require_permission(
            db, current_user, "task.create",
            detail="Permission denied: Cannot create task"
        )

    task = Task(
        event_id=task_in.event_id,
        team_id=task_in.team_id,
        created_by=current_user.id,
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
    db.flush()

    # Assign volunteers if provided
    if task_in.owner_ids:
        AuthorizationService.require_permission(
            db, current_user, "task.assign", resource=task,
            detail="Permission denied: Cannot assign volunteers to task"
        )
        is_leader = AuthorizationService.is_club_leader(db, current_user)
        event_roles = AuthorizationService.get_user_event_roles(db, current_user)
        is_event_coord = task.event_id in event_roles

        for vol_id in task_in.owner_ids:
            vol = db.query(Volunteer).filter(Volunteer.id == vol_id).first()
            if not vol:
                raise HTTPException(status_code=404, detail=f"Volunteer #{vol_id} not found")

            # Team boundary check if non-leader and non-event-coordinator
            if not is_leader and not is_event_coord and task.team_id:
                is_member = db.query(TeamMembership).filter(
                    TeamMembership.team_id == task.team_id,
                    TeamMembership.user_id == vol.user_id
                ).first()
                if not is_member:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot assign task: Volunteer #{vol_id} is not in this team"
                    )

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
    """Get a single task by ID with authorization verification."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    AuthorizationService.require_permission(
        db, current_user, "task.view", resource=task,
        detail="Permission denied: Cannot view this task"
    )
    return task


@router.put("/{task_id}", response_model=schemas.Task)
def update_task(
    *,
    db: Session = Depends(deps.get_db),
    task_id: int,
    task_in: schemas.TaskUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Update a task. Allows team members to update status of their assigned tasks."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_in.model_dump(exclude_unset=True)

    # Check if only updating status
    is_status_only = set(update_data.keys()) == {"status"}
    if is_status_only:
        if not AuthorizationService.can(db, current_user, "task.status.update", resource=task):
            AuthorizationService.require_permission(
                db, current_user, "task.update", resource=task,
                detail="Permission denied: Cannot update task status"
            )
    else:
        AuthorizationService.require_permission(
            db, current_user, "task.update", resource=task,
            detail="Permission denied: Cannot update this task"
        )

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
    """Delete a task. Requires task.delete permission (Team Members denied)."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    AuthorizationService.require_permission(
        db, current_user, "task.delete", resource=task,
        detail="Permission denied: Team Members cannot delete tasks"
    )

    # Clean up dependent task relationships and escalations
    from app.models.escalation import TaskEscalation
    from app.models.task import TaskDependency, TaskComment, TaskAssignment

    db.query(TaskEscalation).filter(TaskEscalation.task_id == task.id).delete(synchronize_session=False)
    db.query(TaskAssignment).filter(TaskAssignment.task_id == task.id).delete(synchronize_session=False)
    db.query(TaskDependency).filter(
        (TaskDependency.dependent_task_id == task.id) | (TaskDependency.prerequisite_task_id == task.id)
    ).delete(synchronize_session=False)
    db.query(TaskComment).filter(TaskComment.task_id == task.id).delete(synchronize_session=False)
    db.query(Task).filter(Task.parent_id == task.id).update({Task.parent_id: None}, synchronize_session=False)

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
    """Assign a volunteer to a task with cross-team boundary checks."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    AuthorizationService.require_permission(
        db, current_user, "task.assign", resource=task,
        detail="Permission denied: Cannot assign volunteers to this task"
    )

    volunteer = db.query(Volunteer).filter(Volunteer.id == volunteer_id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Volunteer not found")

    if not AuthorizationService.can_assign_task(db, current_user, task_id, volunteer_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Cannot assign this volunteer to this task."
        )

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
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    AuthorizationService.require_permission(
        db, current_user, "task.assign", resource=task,
        detail="Permission denied: Cannot unassign volunteers from this task"
    )

    assignment = db.query(TaskAssignment).filter(
        TaskAssignment.task_id == task_id,
        TaskAssignment.volunteer_id == volunteer_id
    ).first()
    if assignment:
        db.delete(assignment)
        db.commit()
    db.refresh(task)
    return task
