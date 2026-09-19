from typing import Any, Optional, List, Dict, Set
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.team import Club, Team, TeamMembership, ClubMembership, EventMembership, TeamRole, ClubRole, EventRole
from app.models.permission import Permission, RolePermission, UserPermission, ScopeType, PermissionEffect
from app.models.task import Task, TaskAssignment
from app.models.volunteer import Volunteer
from app.models.event import Event
from app.models.risk import EventRisk


class AuthorizationService:
    @staticmethod
    def get_role_str(user: Optional[User]) -> str:
        """Extract clean uppercase role string from user model (handling enums, strings, and aliases)."""
        if not user or not hasattr(user, "role"):
            return ""
        r = user.role
        if r is None:
            return ""
        if hasattr(r, "value"):
            s = str(r.value).upper()
        else:
            s = str(r).upper()
        if "." in s:
            s = s.split(".")[-1]
        return s

    @classmethod
    def is_admin(cls, user: Optional[User]) -> bool:
        """Check if user has system-wide administrator privileges."""
        if not user or not user.is_active:
            return False
        role_str = cls.get_role_str(user)
        return "ADMIN" in role_str

    @classmethod
    def is_club_leader(cls, db: Session, user: Optional[User], club_id: Optional[int] = None) -> bool:
        """Check if user has club-level leadership authority."""
        return cls.is_club_head(db, user, club_id=club_id)

    @classmethod
    def is_club_head(cls, db: Session, user: Optional[User], club_id: Optional[int] = None) -> bool:
        """Check if user has club-level head authority over a specific club or generally."""
        if not user or not user.is_active:
            return False
        if cls.is_admin(user):
            return True

        role_str = cls.get_role_str(user)
        if role_str in ["CLUB_HEAD", "CLUB_MANAGER", "CLUB_LEADER"]:
            if club_id is not None:
                if user.club_id is not None:
                    return user.club_id == club_id
                # Check ClubMembership record
                membership = db.query(ClubMembership).filter(
                    ClubMembership.user_id == user.id,
                    ClubMembership.club_id == club_id,
                    ClubMembership.is_active == True
                ).first()
                return membership is not None
            return True

        # Check ClubMembership table for CLUB_HEAD role
        q = db.query(ClubMembership).filter(
            ClubMembership.user_id == user.id,
            ClubMembership.is_active == True,
            ClubMembership.role.in_([ClubRole.CLUB_HEAD, ClubRole.CLUB_HEAD.value if hasattr(ClubRole.CLUB_HEAD, "value") else "CLUB_HEAD", "CLUB_LEADER"])
        )
        if club_id is not None:
            q = q.filter(ClubMembership.club_id == club_id)
        return q.first() is not None

    @classmethod
    def is_subteam_lead(cls, db: Session, user: Optional[User], subteam_id: Optional[int] = None) -> bool:
        """Check if user is a SubTeam Lead."""
        if not user or not user.is_active:
            return False
        if cls.is_admin(user):
            return True

        role_str = cls.get_role_str(user)
        if role_str in ["SUBTEAM_LEAD", "TEAM_LEADER"]:
            if subteam_id is not None:
                if user.subteam_id == subteam_id:
                    return True
                # Check lead_id on Team
                team = db.query(Team).filter(Team.id == subteam_id, Team.lead_id == user.id).first()
                if team:
                    return True
                # Check TeamMembership
                tm = db.query(TeamMembership).filter(
                    TeamMembership.user_id == user.id,
                    TeamMembership.team_id == subteam_id,
                    TeamMembership.is_active == True,
                    TeamMembership.role.in_([TeamRole.SUBTEAM_LEAD, TeamRole.SUBTEAM_LEAD.value if hasattr(TeamRole.SUBTEAM_LEAD, "value") else "SUBTEAM_LEAD", "TEAM_LEADER"])
                ).first()
                return tm is not None
            return True

        # Check Team lead_id or TeamMembership
        q = db.query(TeamMembership).filter(
            TeamMembership.user_id == user.id,
            TeamMembership.is_active == True,
            TeamMembership.role.in_([TeamRole.SUBTEAM_LEAD, TeamRole.SUBTEAM_LEAD.value if hasattr(TeamRole.SUBTEAM_LEAD, "value") else "SUBTEAM_LEAD", "TEAM_LEADER"])
        )
        if subteam_id is not None:
            q = q.filter(TeamMembership.team_id == subteam_id)
            if q.first():
                return True
            team = db.query(Team).filter(Team.id == subteam_id, Team.lead_id == user.id).first()
            return team is not None

        return q.first() is not None

    @classmethod
    def get_user_club_id(cls, db: Session, user: User) -> Optional[int]:
        """Resolves user's assigned club ID."""
        if user.club_id is not None:
            return user.club_id
        membership = db.query(ClubMembership).filter(
            ClubMembership.user_id == user.id,
            ClubMembership.is_active == True
        ).first()
        return membership.club_id if membership else None

    @classmethod
    def get_user_subteam_id(cls, db: Session, user: User) -> Optional[int]:
        """Resolves user's assigned subteam ID."""
        if user.subteam_id is not None:
            return user.subteam_id
        # Check Team where lead_id == user.id
        team_lead = db.query(Team).filter(Team.lead_id == user.id).first()
        if team_lead:
            return team_lead.id
        # Check TeamMembership
        tm = db.query(TeamMembership).filter(
            TeamMembership.user_id == user.id,
            TeamMembership.is_active == True
        ).first()
        return tm.team_id if tm else None

    @staticmethod
    def get_user_team_roles(db: Session, user: User) -> Dict[int, str]:
        """Returns dict of {team_id: role} for all active teams the user belongs to."""
        if not user:
            return {}
        memberships = db.query(TeamMembership).filter(
            TeamMembership.user_id == user.id,
            TeamMembership.is_active == True
        ).all()
        roles = {m.team_id: m.role.value if hasattr(m.role, 'value') else str(m.role) for m in memberships}

        # Also include any team where user is explicitly set as lead_id
        lead_teams = db.query(Team).filter(Team.lead_id == user.id).all()
        for lt in lead_teams:
            roles[lt.id] = TeamRole.SUBTEAM_LEAD.value

        # Also include user.subteam_id if present
        if user.subteam_id and user.subteam_id not in roles:
            role_val = TeamRole.SUBTEAM_LEAD.value if AuthorizationService.get_role_str(user) in ["SUBTEAM_LEAD", "TEAM_LEADER"] else TeamRole.VOLUNTEER.value
            roles[user.subteam_id] = role_val

        return roles

    @staticmethod
    def get_user_event_roles(db: Session, user: User) -> Dict[int, str]:
        """Returns dict of {event_id: role} for events the user is coordinated with."""
        if not user:
            return {}
        memberships = db.query(EventMembership).filter(
            EventMembership.user_id == user.id
        ).all()
        return {m.event_id: m.role.value if hasattr(m.role, 'value') else str(m.role) for m in memberships}

    # ─────────────────────────────────────────────────────────────
    # Standard Scope Checking Methods
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def can_access_club(cls, db: Session, user: User, club_id: int) -> bool:
        """Determines if user can view/access club resources."""
        if not user or not user.is_active:
            return False
        if cls.is_admin(user):
            return True
        user_club = cls.get_user_club_id(db, user)
        return user_club == club_id

    @classmethod
    def can_access_subteam(cls, db: Session, user: User, subteam_id: int) -> bool:
        """Determines if user can access a specific subteam."""
        if not user or not user.is_active:
            return False
        if cls.is_admin(user):
            return True

        subteam = db.query(Team).filter(Team.id == subteam_id).first()
        if not subteam:
            return False

        user_club = cls.get_user_club_id(db, user)
        if subteam.club_id != user_club:
            return False

        # Club Head has full visibility across all subteams in their club
        if cls.is_club_head(db, user, club_id=subteam.club_id):
            return True

        # SubTeam Lead and Volunteers can only access their own subteam
        user_team_id = cls.get_user_subteam_id(db, user)
        if user_team_id == subteam_id:
            return True

        team_roles = cls.get_user_team_roles(db, user)
        return subteam_id in team_roles

    @classmethod
    def can_access_task(cls, db: Session, user: User, task_id: int) -> bool:
        """Determines if user can view/read a task."""
        if not user or not user.is_active:
            return False
        if cls.is_admin(user):
            return True

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False

        # Check club boundary
        event = db.query(Event).filter(Event.id == task.event_id).first() if task.event_id else None
        user_club = cls.get_user_club_id(db, user)
        if event and event.club_id and user_club and event.club_id != user_club:
            return False

        if task.team_id:
            team = db.query(Team).filter(Team.id == task.team_id).first()
            if team and team.club_id and user_club and team.club_id != user_club:
                return False

        # Club head has full access to all tasks in their club
        if cls.is_club_head(db, user, club_id=user_club):
            return True

        # Creator access
        if task.created_by == user.id:
            return True

        # Assigned volunteer access
        vol = db.query(Volunteer).filter(Volunteer.user_id == user.id).first()
        if vol:
            is_assigned = db.query(TaskAssignment).filter(
                TaskAssignment.task_id == task.id,
                TaskAssignment.volunteer_id == vol.id
            ).first()
            if is_assigned:
                return True

        # Subteam scope
        if task.team_id:
            return cls.can_access_subteam(db, user, task.team_id)

        # Public event task within club (Case 1 direct volunteer)
        return True

    @classmethod
    def can_manage_task(cls, db: Session, user: User, task_id: int) -> bool:
        """Determines if user can edit, reassign, or delete a task."""
        if not user or not user.is_active:
            return False
        if cls.is_admin(user):
            return True

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False

        event = db.query(Event).filter(Event.id == task.event_id).first() if task.event_id else None
        user_club = cls.get_user_club_id(db, user)
        if event and event.club_id and user_club and event.club_id != user_club:
            return False

        if task.team_id:
            team = db.query(Team).filter(Team.id == task.team_id).first()
            if team and team.club_id and user_club and team.club_id != user_club:
                return False

        # Club Head has full management authority across their club
        if cls.is_club_head(db, user, club_id=user_club):
            return True

        # SubTeam Lead can only manage tasks within their own subteam
        if cls.is_subteam_lead(db, user):
            if task.team_id and cls.is_subteam_lead(db, user, subteam_id=task.team_id):
                return True

        # Event Coordinator
        event_roles = cls.get_user_event_roles(db, user)
        if task.event_id in event_roles and event_roles[task.event_id] == EventRole.EVENT_COORDINATOR.value:
            return True

        # Volunteers cannot manage tasks
        return False

    @classmethod
    def can_assign_task(cls, db: Session, user: User, task_id: int, volunteer_id: int) -> bool:
        """Determines if user can assign a specific volunteer to a task."""
        if not cls.can_manage_task(db, user, task_id):
            return False
        if cls.is_admin(user):
            return True

        task = db.query(Task).filter(Task.id == task_id).first()
        vol = db.query(Volunteer).filter(Volunteer.id == volunteer_id).first()
        if not task or not vol:
            return False

        user_club = cls.get_user_club_id(db, user)

        # Volunteer must belong to the same club
        vol_club = vol.club_id or (cls.get_user_club_id(db, vol.user) if vol.user else None)
        if vol_club and user_club and vol_club != user_club:
            return False

        # Club Head can assign volunteers across the club
        if cls.is_club_head(db, user, club_id=user_club):
            return True

        # SubTeam Lead can only assign volunteers from their own subteam to tasks in their subteam
        if cls.is_subteam_lead(db, user):
            if task.team_id and cls.is_subteam_lead(db, user, subteam_id=task.team_id):
                vol_team_roles = cls.get_user_team_roles(db, vol.user) if vol.user else {}
                vol_subteam = vol.subteam_id or (vol.user.subteam_id if vol.user else None)
                if task.team_id == vol_subteam or task.team_id in vol_team_roles:
                    return True
            return False

        return False

    @classmethod
    def can_manage_volunteer(cls, db: Session, user: User, volunteer_id: int) -> bool:
        """Determines if user can modify volunteer records or assignments."""
        if not user or not user.is_active:
            return False
        if cls.is_admin(user):
            return True

        vol = db.query(Volunteer).filter(Volunteer.id == volunteer_id).first()
        if not vol:
            return False

        # Volunteer can manage their own permitted profile fields
        if vol.user_id == user.id:
            return True

        user_club = cls.get_user_club_id(db, user)
        vol_club = vol.club_id or (cls.get_user_club_id(db, vol.user) if vol.user else None)
        if vol_club and user_club and vol_club != user_club:
            return False

        # Club Head can manage any volunteer in their club
        if cls.is_club_head(db, user, club_id=user_club):
            return True

        # SubTeam Lead can manage operational view/assignments of team volunteers
        if cls.is_subteam_lead(db, user):
            user_subteam = cls.get_user_subteam_id(db, user)
            vol_team_roles = cls.get_user_team_roles(db, vol.user) if vol.user else {}
            if user_subteam and (vol.subteam_id == user_subteam or user_subteam in vol_team_roles):
                return True

        return False

    @classmethod
    def can_manage_event(cls, db: Session, user: User, event_id: int) -> bool:
        """Determines if user can edit/configure an event."""
        if not user or not user.is_active:
            return False
        if cls.is_admin(user):
            return True

        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return False

        user_club = cls.get_user_club_id(db, user)
        if event.club_id and user_club and event.club_id != user_club:
            return False

        if cls.is_club_head(db, user, club_id=user_club):
            return True

        event_roles = cls.get_user_event_roles(db, user)
        return event_id in event_roles and event_roles[event_id] == EventRole.EVENT_COORDINATOR.value

    @classmethod
    def can_view_risk(cls, db: Session, user: User, risk_id: int) -> bool:
        """Determines if user can view a specific risk."""
        if not user or not user.is_active:
            return False
        if cls.is_admin(user):
            return True

        risk = db.query(EventRisk).filter(EventRisk.id == risk_id).first()
        if not risk:
            return False

        return cls.can_manage_event(db, user, risk.event_id) or (
            risk.task_id is not None and cls.can_access_task(db, user, risk.task_id)
        )

    @classmethod
    def can_apply_ai_proposal(cls, db: Session, user: User, proposal_id: int) -> bool:
        """Validates that all proposed changes inside an AI proposal are authorized for the user."""
        if not user or not user.is_active:
            return False
        if cls.is_admin(user):
            return True

        from ai.schemas.ai_proposal import AIProposal
        proposal = db.query(AIProposal).filter(AIProposal.id == proposal_id).first()
        if not proposal:
            return False

        # Only creators, Club Heads, or Admins can apply proposals
        user_club = cls.get_user_club_id(db, user)
        is_club_head = cls.is_club_head(db, user, club_id=user_club)

        for change in proposal.changes:
            entity_type = change.entity_type
            if entity_type == "Task":
                if change.entity_id:
                    if not cls.can_manage_task(db, user, change.entity_id):
                        return False
                else:
                    proposed = change.proposed_data or {}
                    team_id = proposed.get("team_id")
                    if team_id and not cls.can_access_subteam(db, user, team_id):
                        return False
            elif entity_type == "Event":
                if change.entity_id and not cls.can_manage_event(db, user, change.entity_id):
                    return False
                elif not is_club_head:
                    return False

        return True

    # ─────────────────────────────────────────────────────────────
    # Core Permission Resolution Method
    # ─────────────────────────────────────────────────────────────

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

        # ADMIN has unrestricted access across all permissions and scopes
        if cls.is_admin(user):
            return True

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

                matches_scope = (
                    ov_scope_type == ScopeType.GLOBAL.value
                    or (scope_type and ov_scope_type == scope_type and (ov.scope_id is None or ov.scope_id == scope_id))
                )
                if matches_scope:
                    if ov_effect == PermissionEffect.DENY.value:
                        return False
                    elif ov_effect == PermissionEffect.ALLOW.value:
                        return True

        # 3. Club Head authority within their club
        user_club = cls.get_user_club_id(db, user)
        if cls.is_club_head(db, user, club_id=user_club):
            # Club Head can manage anything inside their club
            # Cross-club check
            if scope_type == "CLUB" and scope_id and scope_id != user_club:
                return False

            # Check if target resource or scoped entity belongs to another club
            if isinstance(resource, Task) or (scope_type == "TASK" and scope_id):
                task = resource if isinstance(resource, Task) else db.query(Task).filter(Task.id == scope_id).first()
                if task:
                    if task.event_id:
                        ev = db.query(Event).filter(Event.id == task.event_id).first()
                        if ev and ev.club_id and user_club and ev.club_id != user_club:
                            return False
                    if task.team_id:
                        tm = db.query(Team).filter(Team.id == task.team_id).first()
                        if tm and tm.club_id and user_club and tm.club_id != user_club:
                            return False

            if isinstance(resource, Team) or (scope_type in ["TEAM", "SUBTEAM"] and scope_id):
                tm = resource if isinstance(resource, Team) else db.query(Team).filter(Team.id == scope_id).first()
                if tm and tm.club_id and user_club and tm.club_id != user_club:
                    return False

            if (hasattr(resource, '__tablename__') and resource.__tablename__ == 'events') or (scope_type == "EVENT" and scope_id):
                ev = resource if hasattr(resource, '__tablename__') and resource.__tablename__ == 'events' else db.query(Event).filter(Event.id == scope_id).first()
                if ev and ev.club_id and user_club and ev.club_id != user_club:
                    return False

            return True

        # 4. Resolve Role-Based Permissions
        team_roles = cls.get_user_team_roles(db, user)
        event_roles = cls.get_user_event_roles(db, user)

        allowed_roles = set()
        if perm_record:
            role_perms = db.query(RolePermission).filter(RolePermission.permission_id == perm_record.id).all()
            allowed_roles = {rp.role for rp in role_perms}

        # ── Resource-level checks: Task ──
        if isinstance(resource, Task) or (scope_type == "TASK" and scope_id):
            task = resource if isinstance(resource, Task) else db.query(Task).filter(Task.id == scope_id).first()
            if task:
                if permission in ["task.view", "task.status.update", "task.change_status", "task.comment", "task.comment.create"]:
                    # Check if user is volunteer assigned
                    vol = db.query(Volunteer).filter(Volunteer.user_id == user.id).first()
                    if vol:
                        is_assigned = db.query(TaskAssignment).filter(
                            TaskAssignment.task_id == task.id,
                            TaskAssignment.volunteer_id == vol.id
                        ).first() is not None
                        if is_assigned:
                            return True

                if task.created_by == user.id and permission in ["task.view", "task.update", "task.comment", "task.comment.create"]:
                    return True

                if task.team_id and task.team_id in team_roles:
                    user_team_role = team_roles[task.team_id]
                    if user_team_role in allowed_roles:
                        if user_team_role in [TeamRole.VOLUNTEER.value, "TEAM_MEMBER"] and permission in ["task.assign", "task.reassign", "task.delete", "task.create"]:
                            return False
                        return True

                if task.event_id and task.event_id in event_roles:
                    user_event_role = event_roles[task.event_id]
                    if user_event_role in allowed_roles:
                        return True

                return False

        # ── Resource-level checks: Team / SubTeam ──
        target_team_id = None
        if isinstance(resource, Team):
            target_team_id = resource.id
        elif scope_type in ["TEAM", "SUBTEAM"] and scope_id:
            target_team_id = scope_id

        if target_team_id is not None:
            if target_team_id in team_roles:
                user_team_role = team_roles[target_team_id]
                return user_team_role in allowed_roles
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
                return user_event_role in allowed_roles
            if permission == "event.view" and (len(team_roles) > 0 or len(event_roles) > 0):
                return True
            return False

        # ── General non-scoped checks ──
        if resource is not None or scope_type is not None:
            return False

        user_role_str = cls.get_role_str(user)
        if user_role_str in allowed_roles:
            return True

        all_user_roles = set(team_roles.values()) | set(event_roles.values())
        return any(r in allowed_roles for r in all_user_roles)

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
        is_admin_user = cls.is_admin(user)
        is_leader = cls.is_club_head(db, user)
        club_id = cls.get_user_club_id(db, user)
        subteam_id = cls.get_user_subteam_id(db, user)
        team_roles = cls.get_user_team_roles(db, user)
        event_roles = cls.get_user_event_roles(db, user)

        teams_data = []
        if team_roles:
            teams = db.query(Team).filter(Team.id.in_(list(team_roles.keys()))).all()
            for t in teams:
                teams_data.append({
                    "id": t.id,
                    "name": t.name,
                    "role": team_roles.get(t.id)
                })

        all_permissions = db.query(Permission).all()
        effective_perms = []
        for p in all_permissions:
            if cls.can(db, user, p.key):
                effective_perms.append(p.key)

        club_role = None
        if is_leader:
            cm = db.query(ClubMembership).filter(ClubMembership.user_id == user.id, ClubMembership.is_active == True).first()
            if cm and cm.role:
                club_role = cm.role.value if hasattr(cm.role, "value") else str(cm.role)
            else:
                club_role = "CLUB_HEAD"

        return {
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": str(user.role.value if hasattr(user.role, 'value') else user.role),
            "is_admin": is_admin_user,
            "is_club_leader": is_leader,
            "is_club_head": is_leader,
            "is_subteam_lead": cls.is_subteam_lead(db, user),
            "club_id": club_id,
            "subteam_id": subteam_id,
            "club_role": club_role,
            "teams": teams_data,
            "event_roles": [{"event_id": eid, "role": r} for eid, r in event_roles.items()],
            "permissions": effective_perms
        }
