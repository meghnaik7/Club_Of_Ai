from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import schemas
from app.api import deps
from app.services import announcement_service
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=schemas.AnnouncementResponse)
def create_announcement(
    announcement_in: schemas.AnnouncementCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Create an announcement draft for an event."""
    return announcement_service.create_announcement(
        db=db,
        title=announcement_in.title,
        content=announcement_in.content,
        event_id=announcement_in.event_id,
        target_audience=announcement_in.target_audience,
        user_id=current_user.id,
        variants=announcement_in.variants
    )

@router.post("/generate", response_model=schemas.AnnouncementGenerateResponse)
def generate_announcement(
    request: schemas.AnnouncementGenerateRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Generate announcement content using live event information."""
    try:
        return announcement_service.generate_announcement(
            db=db,
            event_id=request.event_id,
            tone=request.tone or "engaging",
            target_audience=request.target_audience,
            key_highlights=request.key_highlights
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/variants", response_model=schemas.AnnouncementVariantsResponse)
def generate_variants_from_content(
    content: str = Query(..., description="The content to generate variants from"),
    event_id: Optional[int] = Query(None, description="Optional associated event ID"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Generate variants for WhatsApp, email, and Instagram directly from text."""
    return announcement_service.generate_announcement_variants(
        db=db,
        content=content,
        event_id=event_id
    )

@router.post("/{announcement_id}/variants", response_model=schemas.AnnouncementVariantsResponse)
def generate_announcement_variants(
    announcement_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Generate variants for WhatsApp, email, and Instagram for an existing announcement draft."""
    announcement = announcement_service.get_announcement(db, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return announcement_service.generate_announcement_variants(
        db=db,
        content=announcement.content,
        event_id=announcement.event_id,
        announcement_id=announcement_id
    )

@router.get("/", response_model=List[schemas.AnnouncementResponse])
def list_announcements(
    event_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Retrieve previous announcements for an event."""
    return announcement_service.list_announcements(
        db=db,
        event_id=event_id,
        status=status,
        skip=skip,
        limit=limit
    )

@router.get("/{announcement_id}", response_model=schemas.AnnouncementResponse)
def get_announcement(
    announcement_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Retrieve an announcement draft."""
    announcement = announcement_service.get_announcement(db, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return announcement

@router.put("/{announcement_id}", response_model=schemas.AnnouncementResponse)
def update_announcement(
    announcement_id: int,
    announcement_in: schemas.AnnouncementUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Modify announcement content before sending/copying."""
    announcement = announcement_service.update_announcement(
        db=db,
        announcement_id=announcement_id,
        title=announcement_in.title,
        content=announcement_in.content,
        target_audience=announcement_in.target_audience,
        status=announcement_in.status,
        variants=announcement_in.variants
    )
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return announcement

@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Delete an announcement draft."""
    success = announcement_service.delete_announcement(db, announcement_id)
    if not success:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return {"ok": True, "message": "Announcement deleted successfully"}
