from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.api import deps
from app.models.event import Event
from app.models.user import User

router = APIRouter()


@router.post("/", response_model=schemas.Event)
def create_event(
    *,
    db: Session = Depends(deps.get_db),
    event_in: schemas.EventCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Create a new event."""
    from app.services.authz import AuthorizationService
    AuthorizationService.require_permission(db, current_user, "event.create")

    user_club = AuthorizationService.get_user_club_id(db, current_user)
    event_club = getattr(event_in, "club_id", None) or user_club

    event = Event(
        title=event_in.title,
        description=event_in.description,
        date=event_in.date,
        venue=event_in.venue,
        budget=event_in.budget,
        budget_spent=event_in.budget_spent,
        expected_attendance=event_in.expected_attendance,
        status=event_in.status,
        created_by=current_user.id,
        club_id=event_club
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/", response_model=List[schemas.Event])
def list_events(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Retrieve all events scoped by club."""
    from app.services.authz import AuthorizationService
    q = db.query(Event)
    if not AuthorizationService.is_admin(current_user):
        user_club = AuthorizationService.get_user_club_id(db, current_user)
        if user_club:
            q = q.filter((Event.club_id == user_club) | (Event.club_id == None))
    events = q.offset(skip).limit(limit).all()
    return events



@router.get("/{event_id}", response_model=schemas.Event)
def get_event(
    *,
    db: Session = Depends(deps.get_db),
    event_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get a single event by ID with club scoping."""
    from app.services.authz import AuthorizationService
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not AuthorizationService.is_admin(current_user):
        user_club = AuthorizationService.get_user_club_id(db, current_user)
        if event.club_id and user_club and event.club_id != user_club:
            raise HTTPException(status_code=403, detail="Permission denied: Event belongs to another club")
    return event


@router.put("/{event_id}", response_model=schemas.Event)
def update_event(
    *,
    db: Session = Depends(deps.get_db),
    event_id: int,
    event_in: schemas.EventUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Update an event with management permission verification."""
    from app.services.authz import AuthorizationService
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not AuthorizationService.can_manage_event(db, current_user, event_id):
        raise HTTPException(status_code=403, detail="Permission denied: Cannot manage this event")

    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}")
def delete_event(
    *,
    db: Session = Depends(deps.get_db),
    event_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Delete an event (Admin or Club Head within their club only)."""
    from app.services.authz import AuthorizationService
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not AuthorizationService.is_admin(current_user):
        user_club = AuthorizationService.get_user_club_id(db, current_user)
        if not AuthorizationService.is_club_head(db, current_user, club_id=event.club_id) or (event.club_id and user_club != event.club_id):
            raise HTTPException(status_code=403, detail="Permission denied: Cannot delete this event")

    db.delete(event)
    db.commit()
    return {"ok": True}
