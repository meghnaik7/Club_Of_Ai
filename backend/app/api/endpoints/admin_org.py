from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User, UserRole
from app.models.team import Club, Team
from app.services.authz import AuthorizationService
from app.services.org_service import OrganizationService

router = APIRouter()


class AssignHeadRequest(BaseModel):
    user_id: int
    reason: Optional[str] = None


class AssignRoleRequest(BaseModel):
    role: str
    club_id: Optional[int] = None
    subteam_id: Optional[int] = None
    reason: Optional[str] = None


class AssignClubRequest(BaseModel):
    club_id: int
    reason: Optional[str] = None


class AssignSubTeamRequest(BaseModel):
    subteam_id: int
    role: Optional[str] = "VOLUNTEER"
    reason: Optional[str] = None


class UpdateOrganizationRequest(BaseModel):
    role: str
    club_id: Optional[int] = None
    subteam_id: Optional[int] = None
    reason: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Admin User Queries
# ─────────────────────────────────────────────────────────────

@router.get("/users")
def list_admin_users(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    club_id: Optional[int] = Query(None),
    role: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Lists users with their club and subteam organizational scopes."""
    if not AuthorizationService.is_admin(current_user):
        # Allow Club Head to view users in their own club
        actor_club = AuthorizationService.get_user_club_id(db, current_user)
        if not actor_club or not AuthorizationService.is_club_head(db, current_user, club_id=actor_club):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator or Club Head access required.")
        club_id = actor_club

    q = db.query(User)
    if club_id is not None:
        q = q.filter(User.club_id == club_id)
    if role is not None:
        q = q.filter(User.role == role.upper())

    users = q.offset(skip).limit(limit).all()

    result = []
    for u in users:
        club_name = u.club.name if u.club else None
        subteam_name = u.subteam.name if u.subteam else None
        result.append({
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role.value if hasattr(u.role, 'value') else str(u.role),
            "is_active": u.is_active,
            "club_id": u.club_id,
            "club_name": club_name,
            "subteam_id": u.subteam_id,
            "subteam_name": subteam_name,
        })
    return result


@router.get("/users/{user_id}")
def get_admin_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Retrieves user profile and full organizational breakdown."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if not AuthorizationService.is_admin(current_user):
        actor_club = AuthorizationService.get_user_club_id(db, current_user)
        if not actor_club or user.club_id != actor_club or not AuthorizationService.is_club_head(db, current_user, club_id=actor_club):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
        "is_active": user.is_active,
        "club_id": user.club_id,
        "club_name": user.club.name if user.club else None,
        "subteam_id": user.subteam_id,
        "subteam_name": user.subteam.name if user.subteam else None,
        "is_club_head": AuthorizationService.is_club_head(db, user),
        "is_subteam_lead": AuthorizationService.is_subteam_lead(db, user)
    }


# ─────────────────────────────────────────────────────────────
# Organization Assignment Operations
# ─────────────────────────────────────────────────────────────

@router.post("/clubs/{club_id}/assign-head")
def assign_club_head(
    club_id: int,
    payload: AssignHeadRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Appoints a user as CLUB_HEAD of the specified club (Admin only)."""
    return OrganizationService.assign_club_head(
        db=db,
        actor=current_user,
        club_id=club_id,
        target_user_id=payload.user_id,
        reason=payload.reason
    )


@router.post("/users/{user_id}/assign-role")
def assign_user_role(
    user_id: int,
    payload: AssignRoleRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Updates user role with hierarchy validation (prevents self-promotion and orphaned records)."""
    return OrganizationService.assign_user_role(
        db=db,
        actor=current_user,
        target_user_id=user_id,
        new_role=payload.role,
        club_id=payload.club_id,
        subteam_id=payload.subteam_id,
        reason=payload.reason
    )


@router.post("/users/{user_id}/assign-club")
def assign_user_club(
    user_id: int,
    payload: AssignClubRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Assigns user to a Club (Admin only for cross-club transfers)."""
    return OrganizationService.assign_user_club(
        db=db,
        actor=current_user,
        target_user_id=user_id,
        club_id=payload.club_id,
        reason=payload.reason
    )


@router.post("/users/{user_id}/assign-subteam")
def assign_user_subteam(
    user_id: int,
    payload: AssignSubTeamRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Assigns user to a SubTeam (Admin or Club Head of that club)."""
    return OrganizationService.assign_user_subteam(
        db=db,
        actor=current_user,
        target_user_id=user_id,
        subteam_id=payload.subteam_id,
        role=payload.role or "VOLUNTEER",
        reason=payload.reason
    )


@router.patch("/users/{user_id}/organization")
def update_user_organization(
    user_id: int,
    payload: UpdateOrganizationRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Atomically updates a user's role, club, and subteam assignments."""
    return OrganizationService.assign_user_role(
        db=db,
        actor=current_user,
        target_user_id=user_id,
        new_role=payload.role,
        club_id=payload.club_id,
        subteam_id=payload.subteam_id,
        reason=payload.reason
    )


@router.delete("/users/{user_id}/organization")
def remove_user_organization(
    user_id: int,
    reason: Optional[str] = Query(None),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Removes a user's organizational scope and resets them to unaffiliated volunteer."""
    return OrganizationService.remove_user_organization(
        db=db,
        actor=current_user,
        target_user_id=user_id,
        reason=reason
    )


# ─────────────────────────────────────────────────────────────
# Hierarchy Visual Tree Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/clubs/{club_id}/hierarchy")
def get_club_hierarchy(
    club_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Returns the visual hierarchy tree for a specific club."""
    if not AuthorizationService.is_admin(current_user):
        actor_club = AuthorizationService.get_user_club_id(db, current_user)
        if actor_club != club_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access hierarchy of another club.")
    return OrganizationService.get_club_hierarchy(db, club_id)


@router.get("/organization/tree")
def get_organization_tree(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Returns the system-wide hierarchy tree across all clubs (Admin only)."""
    if not AuthorizationService.is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator privilege required.")
    return OrganizationService.get_full_organization_tree(db)
