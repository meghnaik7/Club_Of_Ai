from typing import Any, Optional, List, Dict
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.team import Club, Team, TeamMembership, ClubMembership, EventMembership, TeamRole, ClubRole, EventRole
from app.models.permission import Permission, RolePermission, UserPermission, ScopeType, PermissionEffect
from app.models.task import Task, TaskAssignment
from app.models.volunteer import Volunteer


class AuthorizationService:
    @staticmethod
    def is_club_leader(db: Session, user: User) -> bool:
        """Check if user has club-level leadership authority."""
        if not user or not user.is_active:
            return False
        # Check User.role directly (supports legacy CLUB_MANAGER or ADMIN)
        if user.role in [UserRole.ADMIN, UserRole.CLUB_MANAGER, "CLUB_LEADER"]:
            return True
        # Check ClubMembership table
        membership = db.query(ClubMembership).filter(
            ClubMembership.user_id == user.id,
            ClubMembership.is_active == True,
            ClubMembership.role == ClubRole.CLUB_LEADER
        ).first()
        return membership is not None

    @staticmethod
    def get_user_team_roles(db: Session, user: User) -> Dict[int, str]:
        """Returns dict of {team_id: role} for all active teams the user belongs to."""
        if not user:
            return {}
        memberships = db.query(TeamMembership).filter(
            TeamMembership.user_id == user.id,
            TeamMembership.is_active == True
        ).all()
        return {m.team_id: m.role.value if hasattr(m.role, 'value') else str(m.role) for m in memberships}

    @staticmethod
    def get_user_event_roles(db: Session, user: User) -> Dict[int, str]:
        """Returns dict of {event_id: role} for events the user is coordinated with."""
        if not user:
            return {}
        memberships = db.query(EventMembership).filter(
            EventMembership.user_id == user.id
        ).all()
        return {m.event_id: m.role.value if hasattr(m.role, 'value') else str(m.role) for m in memberships}

    @classmethod
    def can(
        cls,
        db: Session,
        user: Optional[User],
        permission: str,
        resource: Optional[Any] = None,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None
    ) -> bool:
        """
        Evaluate if user has permission over a resource/scope.
        Follows rule: ROLE != PERMISSION != SCOPE.
        Effective access = User + Role + Team/Event Scope + Explicit Overrides.
        """
        if not user or not user.is_active:
            return False

        # 1. Fetch permission record
        perm_record = db.query(Permission).filter(Permission.key == permission).first()

        # 2. Check explicit UserPermission overrides (DENY always wins)
        if perm_record:
            overrides = db.query(UserPermission).filter(
                UserPermission.user_id == user.id,
                UserPermission.permission_id == perm_record.id
            ).all()

            for ov in overrides:
                ov_scope_type = ov.scope_type.value if hasattr(ov.scope_type, 'value') else str(ov.scope_type)
                ov_effect = ov.effect.value if hasattr(ov.effect, 'value') else str(ov.effect)

                # Does override match scope?
                matches_scope = (
                    ov_scope_type == ScopeType.GLOBAL.value
                    or (scope_type and ov_scope_type == scope_type and (ov.scope_id is None or ov.scope_id == scope_id))
                )
                if matches_scope:
                    if ov_effect == PermissionEffect.DENY.value:
                        return False
                    elif ov_effect == PermissionEffect.ALLOW.value:
                        return True

        # 3. Club Leader has overarching authority across club resources
        if cls.is_club_leader(db, user):
            return True

        # 4. Resolve Role-Based Permissions
        team_roles = cls.get_user_team_roles(db, user)
        event_roles = cls.get_user_event_roles(db, user)

        # Pre-fetch role permissions for the queried permission
        allowed_roles = set()
        if perm_record:
            role_perms = db.query(RolePermission).filter(RolePermission.permission_id == perm_record.id).all()
            allowed_roles = {rp.role for rp in role_perms}

        # ── Resource-level checks: Task ──
        if isinstance(resource, Task) or (scope_type == "TASK" and scope_id):
            task = resource if isinstance(resource, Task) else db.query(Task).filter(Task.id == scope_id).first()
            if task:
                # Direct assignee permissions
                if permission in ["task.view", "task.status.update", "task.comment.create"]:
                    # Check if user is volunteer assigned
                    volunteer = db.query(Volunteer).filter(Volunteer.user_id == user.id).first()
                    if volunteer:
                        is_assigned = db.query(TaskAssignment).filter(
                            TaskAssignment.task_id == task.id,
                            TaskAssignment.volunteer_id == volunteer.id
                        ).first() is not None
                        if is_assigned:
                            return True

                # Creator permissions
                if task.created_by == user.id and permission in ["task.view", "task.update", "task.comment.create"]:
                    return True

                # Team scope check
                if task.team_id and task.team_id in team_roles:
                    user_team_role = team_roles[task.team_id]
                    if user_team_role in allowed_roles:
                        # Team Members cannot reassign, assign, or delete tasks
                        if user_team_role == TeamRole.TEAM_MEMBER.value and permission in ["task.assign", "task.reassign", "task.delete"]:
                            return False
                        return True
                    return False

                # Event scope check
                if task.event_id and task.event_id in event_roles:
                    user_event_role = event_roles[task.event_id]
                    if user_event_role in allowed_roles:
                        return True
                    return False

                # Cross-team restriction: if task has a team and user is NOT in that team, deny
                return False

        # ── Resource-level checks: Team ──
        target_team_id = None
        if isinstance(resource, Team):
            target_team_id = resource.id
        elif scope_type == "TEAM" and scope_id:
            target_team_id = scope_id

        if target_team_id is not None:
            if target_team_id in team_roles:
                user_team_role = team_roles[target_team_id]
                return user_team_role in allowed_roles
            else:
                # User has no membership in target team
                return False

        # ── Resource-level checks: Event ──
        target_event_id = None
        if hasattr(resource, '__tablename__') and resource.__tablename__ == 'events':
            target_event_id = resource.id
        elif scope_type == "EVENT" and scope_id:
            target_event_id = scope_id

        if target_event_id is not None:
            if target_event_id in event_roles:
                user_event_role = event_roles[target_event_id]
                if user_event_role in allowed_roles:
                    return True
            else:
                # User has no coordinator role on target event
                # Team leaders or members can still view event info
                if permission == "event.view" and (len(team_roles) > 0 or len(event_roles) > 0):
                    return True
            return False

        # ── General non-scoped or listing permissions ──
        # If a specific resource or scope was evaluated above and didn't grant access, deny
        if resource is not None or scope_type is not None:
            return False

        # ── General non-scoped or listing permissions ──
        # Check if user holds any role that grants this permission in general
        all_user_roles = set(team_roles.values()) | set(event_roles.values())
        if any(r in allowed_roles for r in all_user_roles):
            # Special case: team.delete or team.create can only be performed by Club Leader
            if permission in ["team.delete", "team.create", "team.leader.assign", "team.leader.remove"]:
                return False
            return True

        return False

    @classmethod
    def require_permission(
        cls,
        db: Session,
        user: Optional[User],
        permission: str,
        resource: Optional[Any] = None,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None,
        detail: Optional[str] = None
    ):
        """Raises 403 Forbidden if user lacks required permission."""
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        if not cls.can(db, user, permission, resource=resource, scope_type=scope_type, scope_id=scope_id):
            action_desc = detail or f"Permission denied for '{permission}'"
            if scope_type and scope_id:
                action_desc += f" on {scope_type.lower()} #{scope_id}"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=action_desc
            )

    @classmethod
    def get_user_authz_summary(cls, db: Session, user: User) -> Dict[str, Any]:
        """Provides full profile of user's roles, scopes, and effective permissions."""
        is_leader = cls.is_club_leader(db, user)
        team_roles = cls.get_user_team_roles(db, user)
        event_roles = cls.get_user_event_roles(db, user)

        # Retrieve team objects
        teams_data = []
        if team_roles:
            teams = db.query(Team).filter(Team.id.in_(list(team_roles.keys()))).all()
            for t in teams:
                teams_data.append({
                    "id": t.id,
                    "name": t.name,
                    "role": team_roles.get(t.id)
                })

        # Calculate effective permissions list
        all_permissions = db.query(Permission).all()
        effective_perms = []
        for p in all_permissions:
            if cls.can(db, user, p.key):
                effective_perms.append(p.key)

        return {
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "is_club_leader": is_leader,
            "club_role": "CLUB_LEADER" if is_leader else None,
            "teams": teams_data,
            "event_roles": [{"event_id": eid, "role": r} for eid, r in event_roles.items()],
            "permissions": effective_perms
        }
