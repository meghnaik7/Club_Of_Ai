from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.api import deps
from app.models.user import User
from app.models.team import Team, TeamMembership, TeamRole, Club
from app.models.audit_log import AuditLog
from app.models.task import Task
from app.services.authz import AuthorizationService

router = APIRouter()


def _format_team_response(team: Team, db: Session) -> dict:
    memberships = db.query(TeamMembership).filter(
        TeamMembership.team_id == team.id,
        TeamMembership.is_active == True
    ).all()

    members = []
    leader = None
    for m in memberships:
        u = db.query(User).filter(User.id == m.user_id).first()
        if u:
            member_dict = {
                "id": m.id,
                "user_id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "role": m.role.value if hasattr(m.role, 'value') else str(m.role),
                "joined_at": m.joined_at
            }
            members.append(member_dict)
            if member_dict["role"] == TeamRole.TEAM_LEADER.value:
                leader = member_dict

    # Calculate workload (active tasks count)
    active_tasks_count = db.query(Task).filter(
        Task.team_id == team.id,
        Task.status.in_(["TODO", "IN_PROGRESS"])
    ).count()

    return {
        "id": team.id,
        "club_id": team.club_id,
        "name": team.name,
        "description": team.description,
        "created_at": team.created_at,
        "updated_at": team.updated_at,
        "member_count": len(members),
        "leader": leader,
        "members": members,
        "active_tasks_count": active_tasks_count
    }


@router.get("/", response_model=List[schemas.Team])
def list_teams(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """List all teams visible to the current user."""
    AuthorizationService.require_permission(db, current_user, "team.view")
    teams = db.query(Team).all()
    return [_format_team_response(t, db) for t in teams]


@router.post("/", response_model=schemas.Team, status_code=status.HTTP_201_CREATED)
def create_team(
    team_in: schemas.TeamCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Create a new team (Club Leader only)."""
    AuthorizationService.require_permission(db, current_user, "team.create", scope_type="CLUB")

    team = Team(
        name=team_in.name,
        description=team_in.description,
        club_id=team_in.club_id
    )
    db.add(team)
    db.commit()
    db.refresh(team)

    # Audit log
    db.add(AuditLog(
        actor_id=current_user.id,
        user_id=current_user.id,
        action="CREATE",
        entity_type="team",
        entity_id=team.id,
        scope_type="TEAM",
        scope_id=team.id,
        new_state={"name": team.name, "description": team.description}
    ))
    db.commit()

    return _format_team_response(team, db)


@router.get("/{team_id}", response_model=schemas.Team)
def get_team(
    team_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get team details."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    AuthorizationService.require_permission(db, current_user, "team.view", resource=team, scope_type="TEAM", scope_id=team_id)
    return _format_team_response(team, db)


@router.put("/{team_id}", response_model=schemas.Team)
def update_team(
    team_id: int,
    team_in: schemas.TeamUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Update team details."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    AuthorizationService.require_permission(db, current_user, "team.update", resource=team, scope_type="TEAM", scope_id=team_id)

    prev_state = {"name": team.name, "description": team.description}
    if team_in.name is not None:
        team.name = team_in.name
    if team_in.description is not None:
        team.description = team_in.description

    db.commit()
    db.refresh(team)

    db.add(AuditLog(
        actor_id=current_user.id,
        user_id=current_user.id,
        action="UPDATE",
        entity_type="team",
        entity_id=team.id,
        scope_type="TEAM",
        scope_id=team.id,
        previous_state=prev_state,
        new_state={"name": team.name, "description": team.description}
    ))
    db.commit()

    return _format_team_response(team, db)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Delete team (Club Leader only)."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    AuthorizationService.require_permission(db, current_user, "team.delete", resource=team, scope_type="TEAM", scope_id=team_id)

    db.add(AuditLog(
        actor_id=current_user.id,
        user_id=current_user.id,
        action="DELETE",
        entity_type="team",
        entity_id=team.id,
        scope_type="TEAM",
        scope_id=team.id,
        previous_state={"name": team.name}
    ))
    db.delete(team)
    db.commit()


# ── Team Members ──

@router.get("/{team_id}/members", response_model=List[schemas.TeamMemberResponse])
def list_team_members(
    team_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """List members of a team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    AuthorizationService.require_permission(db, current_user, "team.member.view", resource=team, scope_type="TEAM", scope_id=team_id)
    resp = _format_team_response(team, db)
    return resp["members"]


@router.post("/{team_id}/members", response_model=schemas.TeamMemberResponse, status_code=status.HTTP_201_CREATED)
def add_team_member(
    team_id: int,
    member_in: schemas.TeamMemberAdd,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Add a member to a team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    user_to_add = db.query(User).filter(User.id == member_in.user_id).first()
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User not found")

    AuthorizationService.require_permission(db, current_user, "team.member.add", resource=team, scope_type="TEAM", scope_id=team_id)

    # Check if already a member
    membership = db.query(TeamMembership).filter(
        TeamMembership.team_id == team_id,
        TeamMembership.user_id == member_in.user_id
    ).first()

    target_role = TeamRole.TEAM_MEMBER
    if member_in.role == TeamRole.TEAM_LEADER.value:
        # Assigning a leader requires team.leader.assign permission
        AuthorizationService.require_permission(db, current_user, "team.leader.assign", resource=team, scope_type="TEAM", scope_id=team_id)
        target_role = TeamRole.TEAM_LEADER

    if membership:
        membership.is_active = True
        membership.role = target_role
    else:
        membership = TeamMembership(
            team_id=team_id,
            user_id=member_in.user_id,
            role=target_role
        )
        db.add(membership)

    db.commit()
    db.refresh(membership)

    db.add(AuditLog(
        actor_id=current_user.id,
        user_id=current_user.id,
        action="ADD_MEMBER",
        entity_type="team_membership",
        entity_id=membership.id,
        scope_type="TEAM",
        scope_id=team.id,
        new_state={"user_id": user_to_add.id, "team_id": team.id, "role": str(target_role)}
    ))
    db.commit()

    return {
        "id": membership.id,
        "user_id": user_to_add.id,
        "full_name": user_to_add.full_name,
        "email": user_to_add.email,
        "role": membership.role.value if hasattr(membership.role, 'value') else str(membership.role),
        "joined_at": membership.joined_at
    }


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(
    team_id: int,
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Remove a member from a team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    membership = db.query(TeamMembership).filter(
        TeamMembership.team_id == team_id,
        TeamMembership.user_id == user_id,
        TeamMembership.is_active == True
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    # If removing a Team Leader, check team.leader.remove
    if membership.role == TeamRole.TEAM_LEADER:
        AuthorizationService.require_permission(db, current_user, "team.leader.remove", resource=team, scope_type="TEAM", scope_id=team_id)
    else:
        AuthorizationService.require_permission(db, current_user, "team.member.remove", resource=team, scope_type="TEAM", scope_id=team_id)

    db.add(AuditLog(
        actor_id=current_user.id,
        user_id=current_user.id,
        action="REMOVE_MEMBER",
        entity_type="team_membership",
        entity_id=membership.id,
        scope_type="TEAM",
        scope_id=team.id,
        previous_state={"user_id": user_id, "role": str(membership.role)}
    ))
    membership.is_active = False
    db.commit()


# ── Team Leaders ──

@router.post("/{team_id}/leaders", response_model=schemas.TeamMemberResponse)
def assign_team_leader(
    team_id: int,
    leader_in: schemas.TeamLeaderAssign,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Assign or promote a member to Team Leader (Club Leader only)."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    user_to_promote = db.query(User).filter(User.id == leader_in.user_id).first()
    if not user_to_promote:
        raise HTTPException(status_code=404, detail="User not found")

    AuthorizationService.require_permission(db, current_user, "team.leader.assign", resource=team, scope_type="TEAM", scope_id=team_id)

    # Demote existing leader if any
    existing_leaders = db.query(TeamMembership).filter(
        TeamMembership.team_id == team_id,
        TeamMembership.role == TeamRole.TEAM_LEADER,
        TeamMembership.is_active == True
    ).all()
    for el in existing_leaders:
        el.role = TeamRole.TEAM_MEMBER

    membership = db.query(TeamMembership).filter(
        TeamMembership.team_id == team_id,
        TeamMembership.user_id == leader_in.user_id
    ).first()

    if membership:
        membership.is_active = True
        membership.role = TeamRole.TEAM_LEADER
    else:
        membership = TeamMembership(
            team_id=team_id,
            user_id=leader_in.user_id,
            role=TeamRole.TEAM_LEADER
        )
        db.add(membership)

    db.commit()
    db.refresh(membership)

    db.add(AuditLog(
        actor_id=current_user.id,
        user_id=current_user.id,
        action="ASSIGN_LEADER",
        entity_type="team_membership",
        entity_id=membership.id,
        scope_type="TEAM",
        scope_id=team.id,
        new_state={"user_id": user_to_promote.id, "team_id": team.id, "role": "TEAM_LEADER"}
    ))
    db.commit()

    return {
        "id": membership.id,
        "user_id": user_to_promote.id,
        "full_name": user_to_promote.full_name,
        "email": user_to_promote.email,
        "role": TeamRole.TEAM_LEADER.value,
        "joined_at": membership.joined_at
    }


@router.delete("/{team_id}/leaders/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_leader(
    team_id: int,
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Demote a Team Leader back to Member (Club Leader only)."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    AuthorizationService.require_permission(db, current_user, "team.leader.remove", resource=team, scope_type="TEAM", scope_id=team_id)

    membership = db.query(TeamMembership).filter(
        TeamMembership.team_id == team_id,
        TeamMembership.user_id == user_id,
        TeamMembership.role == TeamRole.TEAM_LEADER,
        TeamMembership.is_active == True
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Team Leader membership not found")

    membership.role = TeamRole.TEAM_MEMBER
    db.add(AuditLog(
        actor_id=current_user.id,
        user_id=current_user.id,
        action="REMOVE_LEADER",
        entity_type="team_membership",
        entity_id=membership.id,
        scope_type="TEAM",
        scope_id=team.id,
        previous_state={"user_id": user_id, "role": "TEAM_LEADER"},
        new_state={"user_id": user_id, "role": "TEAM_MEMBER"}
    ))
    db.commit()
