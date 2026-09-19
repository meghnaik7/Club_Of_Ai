import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.team import Club, Team, TeamMembership, ClubMembership, TeamRole, ClubRole
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.audit_log import AuditLog
from app.services.authz import AuthorizationService

logger = logging.getLogger(__name__)


class OrganizationService:
    @staticmethod
    def _log_org_audit(
        db: Session,
        actor_id: int,
        target_user_id: int,
        action: str,
        previous_state: Dict[str, Any],
        new_state: Dict[str, Any],
        reason: Optional[str] = None
    ) -> AuditLog:
        """Creates an immutable AuditLog record for organizational changes."""
        audit = AuditLog(
            proposal_id=None,
            entity_type="Organization",
            entity_id=target_user_id,
            action=action,
            previous_state=previous_state,
            new_state=new_state,
            user_id=actor_id,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit)
        return audit

    @classmethod
    def assign_club_head(
        cls,
        db: Session,
        actor: User,
        club_id: int,
        target_user_id: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assigns target user as CLUB_HEAD of the specified club.
        Only ADMIN has authority to assign Club Heads.
        """
        if not AuthorizationService.is_admin(actor):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only System Administrators can appoint or change Club Heads."
            )

        club = db.query(Club).filter(Club.id == club_id).first()
        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Club #{club_id} not found.")

        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User #{target_user_id} not found.")

        prev_state = {
            "role": str(target_user.role.value if hasattr(target_user.role, 'value') else target_user.role),
            "club_id": target_user.club_id,
            "subteam_id": target_user.subteam_id,
        }

        # Clear any prior SubTeam lead assignment if user was leading a team
        if target_user.subteam_id:
            prior_team = db.query(Team).filter(Team.id == target_user.subteam_id, Team.lead_id == target_user.id).first()
            if prior_team:
                prior_team.lead_id = None

        target_user.role = UserRole.CLUB_HEAD
        target_user.club_id = club_id
        target_user.subteam_id = None  # Club heads manage entire club, clear subteam

        # Ensure ClubMembership record
        existing_cm = db.query(ClubMembership).filter(
            ClubMembership.club_id == club_id,
            ClubMembership.user_id == target_user.id
        ).first()
        if existing_cm:
            existing_cm.role = ClubRole.CLUB_HEAD
            existing_cm.is_active = True
        else:
            db.add(ClubMembership(club_id=club_id, user_id=target_user.id, role=ClubRole.CLUB_HEAD))

        # Update volunteer profile if exists
        vol = db.query(Volunteer).filter(Volunteer.user_id == target_user.id).first()
        if vol:
            vol.club_id = club_id
            vol.subteam_id = None

        new_state = {
            "role": "CLUB_HEAD",
            "club_id": club_id,
            "subteam_id": None,
            "reason": reason or "Club Head appointed by Admin"
        }

        cls._log_org_audit(db, actor.id, target_user.id, "CLUB_HEAD_ASSIGNED", prev_state, new_state, reason)
        db.commit()
        db.refresh(target_user)

        return {
            "success": True,
            "message": f"Successfully assigned {target_user.full_name} as Club Head of {club.name}.",
            "user": {
                "id": target_user.id,
                "full_name": target_user.full_name,
                "email": target_user.email,
                "role": "CLUB_HEAD",
                "club_id": club_id,
                "club_name": club.name
            }
        }

    @classmethod
    def assign_user_role(
        cls,
        db: Session,
        actor: User,
        target_user_id: int,
        new_role: str,
        club_id: Optional[int] = None,
        subteam_id: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Changes user's role while strictly enforcing hierarchy invariants and preventing self-promotion.
        """
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User #{target_user_id} not found.")

        normalized_role = new_role.upper().strip()
        is_actor_admin = AuthorizationService.is_admin(actor)

        # 1. Invariant: Prevent self-promotion
        if actor.id == target_user.id and not is_actor_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security violation: Self-promotion is strictly prohibited."
            )

        # 2. Invariant: Only ADMIN can assign ADMIN or CLUB_HEAD
        if normalized_role in ["ADMIN", "CLUB_HEAD", "CLUB_MANAGER", "CLUB_LEADER"]:
            if not is_actor_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied: Only Administrators can appoint Club Heads or Administrators."
                )

        # 3. Club Head authority boundaries
        if not is_actor_admin:
            actor_club = AuthorizationService.get_user_club_id(db, actor)
            target_club = club_id or target_user.club_id
            if not actor_club or target_club != actor_club:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied: Club Heads can only manage users within their own club."
                )
            if not AuthorizationService.is_club_head(db, actor, club_id=actor_club):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied: Insufficient privileges to change user roles."
                )

        effective_club_id = club_id or target_user.club_id
        effective_subteam_id = subteam_id

        # 4. Invariant: Role Transition Rules
        if normalized_role in ["SUBTEAM_LEAD", "TEAM_LEADER"]:
            if not effective_subteam_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Validation error: A user cannot be assigned as SUBTEAM_LEAD without specifying a SubTeam."
                )
            subteam = db.query(Team).filter(Team.id == effective_subteam_id).first()
            if not subteam:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"SubTeam #{effective_subteam_id} not found.")
            if effective_club_id and subteam.club_id != effective_club_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Validation error: SubTeam #{effective_subteam_id} belongs to Club #{subteam.club_id}, not Club #{effective_club_id}."
                )
            effective_club_id = subteam.club_id
            subteam.lead_id = target_user.id

        elif normalized_role in ["CLUB_HEAD", "CLUB_MANAGER"]:
            if not effective_club_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Validation error: A Club Head must belong to a valid Club."
                )
            effective_subteam_id = None  # Clear subteam

        elif normalized_role in ["VOLUNTEER", "TEAM_MEMBER"]:
            if effective_subteam_id:
                subteam = db.query(Team).filter(Team.id == effective_subteam_id).first()
                if not subteam:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"SubTeam #{effective_subteam_id} not found.")
                if effective_club_id and subteam.club_id != effective_club_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Validation error: Volunteer cannot belong to a SubTeam from another Club."
                    )
                effective_club_id = subteam.club_id

        prev_state = {
            "role": str(target_user.role.value if hasattr(target_user.role, 'value') else target_user.role),
            "club_id": target_user.club_id,
            "subteam_id": target_user.subteam_id,
        }

        # Apply mapped role enum
        if normalized_role in ["ADMIN"]:
            target_user.role = UserRole.ADMIN
        elif normalized_role in ["CLUB_HEAD", "CLUB_MANAGER", "CLUB_LEADER"]:
            target_user.role = UserRole.CLUB_HEAD
        elif normalized_role in ["SUBTEAM_LEAD", "TEAM_LEADER"]:
            target_user.role = UserRole.SUBTEAM_LEAD
        else:
            target_user.role = UserRole.VOLUNTEER

        target_user.club_id = effective_club_id
        target_user.subteam_id = effective_subteam_id

        # Update volunteer profile if present
        vol = db.query(Volunteer).filter(Volunteer.user_id == target_user.id).first()
        if vol:
            vol.club_id = effective_club_id
            vol.subteam_id = effective_subteam_id

        new_state = {
            "role": str(target_user.role.value if hasattr(target_user.role, 'value') else target_user.role),
            "club_id": effective_club_id,
            "subteam_id": effective_subteam_id,
            "reason": reason
        }

        cls._log_org_audit(db, actor.id, target_user.id, "ROLE_CHANGED", prev_state, new_state, reason)
        db.commit()
        db.refresh(target_user)

        return {
            "success": True,
            "message": f"Successfully updated role for {target_user.full_name} to {target_user.role.value}.",
            "user": {
                "id": target_user.id,
                "full_name": target_user.full_name,
                "email": target_user.email,
                "role": target_user.role.value,
                "club_id": target_user.club_id,
                "subteam_id": target_user.subteam_id
            }
        }

    @classmethod
    def assign_user_club(
        cls,
        db: Session,
        actor: User,
        target_user_id: int,
        club_id: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Assigns a user to a specific club (Admin only for cross-club transfers)."""
        if not AuthorizationService.is_admin(actor):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only System Administrators can transfer users across Clubs."
            )

        club = db.query(Club).filter(Club.id == club_id).first()
        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Club #{club_id} not found.")

        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User #{target_user_id} not found.")

        prev_state = {
            "club_id": target_user.club_id,
            "subteam_id": target_user.subteam_id,
            "role": target_user.role.value
        }

        # If user was in a different club, clear their subteam to prevent cross-club invalidity
        if target_user.club_id != club_id:
            target_user.subteam_id = None

        target_user.club_id = club_id

        # Update volunteer profile
        vol = db.query(Volunteer).filter(Volunteer.user_id == target_user.id).first()
        if vol:
            vol.club_id = club_id
            if target_user.subteam_id is None:
                vol.subteam_id = None

        new_state = {
            "club_id": club_id,
            "subteam_id": target_user.subteam_id,
            "role": target_user.role.value,
            "reason": reason
        }

        cls._log_org_audit(db, actor.id, target_user.id, "USER_MOVED", prev_state, new_state, reason)
        db.commit()
        db.refresh(target_user)

        return {
            "success": True,
            "message": f"Assigned {target_user.full_name} to {club.name}.",
            "user": {
                "id": target_user.id,
                "club_id": target_user.club_id,
                "subteam_id": target_user.subteam_id
            }
        }

    @classmethod
    def assign_user_subteam(
        cls,
        db: Session,
        actor: User,
        target_user_id: int,
        subteam_id: int,
        role: str = "VOLUNTEER",
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Assigns user to a subteam (Admin or Club Head of that club)."""
        subteam = db.query(Team).filter(Team.id == subteam_id).first()
        if not subteam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"SubTeam #{subteam_id} not found.")

        if not AuthorizationService.is_admin(actor):
            if not AuthorizationService.is_club_head(db, actor, club_id=subteam.club_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the Club Head or an Admin can assign members to this SubTeam."
                )

        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User #{target_user_id} not found.")

        normalized_role = role.upper().strip()
        action_name = "SUBTEAM_LEAD_ASSIGNED" if normalized_role in ["SUBTEAM_LEAD", "TEAM_LEADER"] else "VOLUNTEER_ASSIGNED"

        prev_state = {
            "club_id": target_user.club_id,
            "subteam_id": target_user.subteam_id,
            "role": target_user.role.value
        }

        target_user.club_id = subteam.club_id
        target_user.subteam_id = subteam.id
        if normalized_role in ["SUBTEAM_LEAD", "TEAM_LEADER"]:
            target_user.role = UserRole.SUBTEAM_LEAD
            subteam.lead_id = target_user.id
        else:
            if target_user.role not in [UserRole.ADMIN, UserRole.CLUB_HEAD]:
                target_user.role = UserRole.VOLUNTEER

        # Ensure TeamMembership
        tm = db.query(TeamMembership).filter(
            TeamMembership.team_id == subteam.id,
            TeamMembership.user_id == target_user.id
        ).first()
        if tm:
            tm.role = TeamRole.SUBTEAM_LEAD if target_user.role == UserRole.SUBTEAM_LEAD else TeamRole.VOLUNTEER
            tm.is_active = True
        else:
            db.add(TeamMembership(
                team_id=subteam.id,
                user_id=target_user.id,
                role=TeamRole.SUBTEAM_LEAD if target_user.role == UserRole.SUBTEAM_LEAD else TeamRole.VOLUNTEER
            ))

        # Update volunteer profile
        vol = db.query(Volunteer).filter(Volunteer.user_id == target_user.id).first()
        if vol:
            vol.club_id = subteam.club_id
            vol.subteam_id = subteam.id

        new_state = {
            "club_id": subteam.club_id,
            "subteam_id": subteam.id,
            "role": target_user.role.value,
            "reason": reason
        }

        cls._log_org_audit(db, actor.id, target_user.id, action_name, prev_state, new_state, reason)
        db.commit()
        db.refresh(target_user)

        return {
            "success": True,
            "message": f"Assigned {target_user.full_name} to {subteam.name}.",
            "user": {
                "id": target_user.id,
                "role": target_user.role.value,
                "club_id": target_user.club_id,
                "subteam_id": target_user.subteam_id
            }
        }

    @classmethod
    def remove_user_organization(
        cls,
        db: Session,
        actor: User,
        target_user_id: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Removes a user's organizational assignments cleanly without leaving orphaned records."""
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User #{target_user_id} not found.")

        if not AuthorizationService.is_admin(actor):
            actor_club = AuthorizationService.get_user_club_id(db, actor)
            if not actor_club or target_user.club_id != actor_club or not AuthorizationService.is_club_head(db, actor, club_id=actor_club):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only Administrators or the Club Head can remove organizational assignments."
                )

        prev_state = {
            "role": target_user.role.value,
            "club_id": target_user.club_id,
            "subteam_id": target_user.subteam_id
        }

        # Clear any subteam lead reference
        teams_led = db.query(Team).filter(Team.lead_id == target_user.id).all()
        for t in teams_led:
            t.lead_id = None

        # Deactivate memberships
        db.query(TeamMembership).filter(TeamMembership.user_id == target_user.id).update({"is_active": False})
        db.query(ClubMembership).filter(ClubMembership.user_id == target_user.id).update({"is_active": False})

        target_user.role = UserRole.VOLUNTEER
        target_user.club_id = None
        target_user.subteam_id = None

        vol = db.query(Volunteer).filter(Volunteer.user_id == target_user.id).first()
        if vol:
            vol.club_id = None
            vol.subteam_id = None

        new_state = {
            "role": "VOLUNTEER",
            "club_id": None,
            "subteam_id": None,
            "reason": reason or "Removed organizational assignment"
        }

        cls._log_org_audit(db, actor.id, target_user.id, "ROLE_REMOVED", prev_state, new_state, reason)
        db.commit()

        return {
            "success": True,
            "message": f"Removed organizational assignments for {target_user.full_name}."
        }

    # ─────────────────────────────────────────────────────────────
    # Hierarchy Views & Visual Tree Data
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def get_club_hierarchy(cls, db: Session, club_id: int) -> Dict[str, Any]:
        """Returns the complete organizational hierarchy tree for a single Club."""
        club = db.query(Club).filter(Club.id == club_id).first()
        if not club:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Club #{club_id} not found.")

        # Find Club Head
        club_head_user = db.query(User).filter(
            User.club_id == club_id,
            User.role.in_([UserRole.CLUB_HEAD, "CLUB_MANAGER", "CLUB_LEADER"])
        ).first()

        if not club_head_user:
            # Fallback check ClubMembership
            cm = db.query(ClubMembership).filter(
                ClubMembership.club_id == club_id,
                ClubMembership.is_active == True,
                ClubMembership.role.in_([ClubRole.CLUB_HEAD, "CLUB_LEADER"])
            ).first()
            if cm:
                club_head_user = db.query(User).filter(User.id == cm.user_id).first()

        head_data = None
        if club_head_user:
            head_data = {
                "id": club_head_user.id,
                "full_name": club_head_user.full_name,
                "email": club_head_user.email,
                "role": "CLUB_HEAD"
            }

        # SubTeams and their members
        subteams_data = []
        teams = db.query(Team).filter(Team.club_id == club_id).all()
        for t in teams:
            lead_data = None
            if t.lead_id:
                lu = db.query(User).filter(User.id == t.lead_id).first()
                if lu:
                    lead_data = {
                        "id": lu.id,
                        "full_name": lu.full_name,
                        "email": lu.email,
                        "role": "SUBTEAM_LEAD"
                    }

            # Team volunteers
            team_members = db.query(User).filter(
                User.subteam_id == t.id,
                User.role.in_([UserRole.VOLUNTEER, "TEAM_MEMBER"])
            ).all()

            subteams_data.append({
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "lead": lead_data,
                "volunteers": [
                    {
                        "id": m.id,
                        "full_name": m.full_name,
                        "email": m.email,
                        "role": "VOLUNTEER"
                    }
                    for m in team_members if not (lead_data and m.id == lead_data["id"])
                ]
            })

        # Direct volunteers (Case 1: Belong to Club, but subteam_id is None)
        direct_volunteers = db.query(User).filter(
            User.club_id == club_id,
            User.subteam_id == None,
            User.role.in_([UserRole.VOLUNTEER, "TEAM_MEMBER"])
        ).all()

        return {
            "club_id": club.id,
            "club_name": club.name,
            "description": club.description,
            "structure_type": "CASE_2_SUBTEAMS" if len(subteams_data) > 0 else "CASE_1_DIRECT_VOLUNTEERS",
            "club_head": head_data,
            "subteams": subteams_data,
            "direct_volunteers": [
                {
                    "id": v.id,
                    "full_name": v.full_name,
                    "email": v.email,
                    "role": "VOLUNTEER"
                }
                for v in direct_volunteers
            ]
        }

    @classmethod
    def get_full_organization_tree(cls, db: Session) -> Dict[str, Any]:
        """Returns the full system organization tree across all Clubs for the Admin UI."""
        clubs = db.query(Club).all()
        clubs_tree = [cls.get_club_hierarchy(db, c.id) for c in clubs]

        # System Admins
        admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
        admin_data = [
            {"id": a.id, "full_name": a.full_name, "email": a.email, "role": "ADMIN"}
            for a in admins
        ]

        # Unassigned users
        unassigned = db.query(User).filter(
            User.club_id == None,
            User.role != UserRole.ADMIN
        ).all()
        unassigned_data = [
            {"id": u.id, "full_name": u.full_name, "email": u.email, "role": u.role.value}
            for u in unassigned
        ]

        return {
            "root": "ADMIN",
            "administrators": admin_data,
            "clubs": clubs_tree,
            "unassigned_users": unassigned_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
