from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import schemas
from app.api import deps
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.user import User
from app.models.task import Task, TaskAssignment, TaskStatus
from app.core.config import settings

router = APIRouter()

def get_load_indicator(active_task_count: int) -> str:
    if active_task_count <= settings.VOLUNTEER_LOAD_LOW:
        return "LOW"
    elif active_task_count <= settings.VOLUNTEER_LOAD_MEDIUM:
        return "MEDIUM"
    else:
        return "OVERLOADED"

@router.get("/", response_model=List[schemas.VolunteerResponse])
def list_volunteers(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Retrieve all volunteers with computed load."""
    volunteers = db.query(Volunteer).offset(skip).limit(limit).all()
    
    result = []
    for vol in volunteers:
        # Calculate active tasks count
        active_count = db.query(TaskAssignment).join(Task).filter(
            TaskAssignment.volunteer_id == vol.id,
            Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])
        ).count()
        
        # Build response manually to inject computed fields
        vol_data = schemas.VolunteerResponse.model_validate(vol)
        vol_data.active_task_count = active_count
        vol_data.load_indicator = get_load_indicator(active_count)
        
        # Add user info manually for frontend display
        if vol.user:
            vol_data.user = schemas.UserInfo(
                id=vol.user.id,
                full_name=vol.user.full_name,
                email=vol.user.email
            )
        result.append(vol_data)
        
    return result

@router.get("/{volunteer_id}", response_model=schemas.VolunteerResponse)
def get_volunteer(
    volunteer_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get a specific volunteer profile."""
    vol = db.query(Volunteer).filter(Volunteer.id == volunteer_id).first()
    if not vol:
        raise HTTPException(status_code=404, detail="Volunteer not found")
        
    active_count = db.query(TaskAssignment).join(Task).filter(
        TaskAssignment.volunteer_id == vol.id,
        Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])
    ).count()
    
    vol_data = schemas.VolunteerResponse.model_validate(vol)
    vol_data.active_task_count = active_count
    vol_data.load_indicator = get_load_indicator(active_count)
    if vol.user:
        vol_data.user = schemas.UserInfo(
            id=vol.user.id,
            full_name=vol.user.full_name,
            email=vol.user.email
        )
    return vol_data

@router.get("/{volunteer_id}/tasks")
def get_volunteer_tasks(
    volunteer_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get tasks assigned to a specific volunteer."""
    vol = db.query(Volunteer).filter(Volunteer.id == volunteer_id).first()
    if not vol:
        raise HTTPException(status_code=404, detail="Volunteer not found")
        
    assignments = db.query(TaskAssignment).filter(TaskAssignment.volunteer_id == vol.id).all()
    tasks = [a.task for a in assignments if a.task]
    
    # We return raw dicts for now since TaskSchema isn't fully built out in Phase 3
    return [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status.value,
            "event_id": t.event_id
        }
        for t in tasks
    ]

@router.post("/", response_model=schemas.VolunteerResponse)
def create_volunteer(
    *,
    db: Session = Depends(deps.get_db),
    volunteer_in: schemas.VolunteerCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Create a volunteer profile."""
    # Check if user exists
    user = db.query(User).filter(User.id == volunteer_in.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Check if volunteer profile already exists
    existing = db.query(Volunteer).filter(Volunteer.user_id == volunteer_in.user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Volunteer profile already exists for this user")
        
    volunteer = Volunteer(
        user_id=volunteer_in.user_id,
        skills=volunteer_in.skills,
        availability=volunteer_in.availability,
        status=volunteer_in.status
    )
    db.add(volunteer)
    db.commit()
    db.refresh(volunteer)
    
    vol_data = schemas.VolunteerResponse.model_validate(volunteer)
    if volunteer.user:
        vol_data.user = schemas.UserInfo(
            id=volunteer.user.id,
            full_name=volunteer.user.full_name,
            email=volunteer.user.email
        )
    return vol_data

@router.put("/{volunteer_id}", response_model=schemas.VolunteerResponse)
def update_volunteer(
    *,
    db: Session = Depends(deps.get_db),
    volunteer_id: int,
    volunteer_in: schemas.VolunteerUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Update a volunteer profile."""
    volunteer = db.query(Volunteer).filter(Volunteer.id == volunteer_id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Volunteer not found")

    update_data = volunteer_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(volunteer, field, value)

    db.add(volunteer)
    db.commit()
    db.refresh(volunteer)
    
    active_count = db.query(TaskAssignment).join(Task).filter(
        TaskAssignment.volunteer_id == volunteer.id,
        Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])
    ).count()
    
    vol_data = schemas.VolunteerResponse.model_validate(volunteer)
    vol_data.active_task_count = active_count
    vol_data.load_indicator = get_load_indicator(active_count)
    if volunteer.user:
        vol_data.user = schemas.UserInfo(
            id=volunteer.user.id,
            full_name=volunteer.user.full_name,
            email=volunteer.user.email
        )
    return vol_data

@router.delete("/{volunteer_id}")
def delete_volunteer(
    *,
    db: Session = Depends(deps.get_db),
    volunteer_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Delete a volunteer profile."""
    volunteer = db.query(Volunteer).filter(Volunteer.id == volunteer_id).first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="Volunteer not found")
        
    db.delete(volunteer)
    db.commit()
    return {"ok": True}
