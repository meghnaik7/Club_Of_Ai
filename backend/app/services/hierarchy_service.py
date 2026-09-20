import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.volunteer import Volunteer
from app.models.team import Team, TeamMembership, ClubMembership, TeamRole, ClubRole
from app.models.event import Event

logger = logging.getLogger(__name__)


class NotificationRecipients:
    """Encapsulates resolved reporting hierarchy for task notifications."""

    def __init__(
        self,
        volunteer: Optional[User] = None,
        volunteer_profile: Optional[Volunteer] = None,
        team_lead: Optional[User] = None,
        head: Optional[User] = None,
        admin: Optional[User] = None,
    ):
        self.volunteer = volunteer
        self.volunteer_profile = volunteer_profile
        self.team_lead = team_lead
        self.head = head
        self.admin = admin

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def to_dict(self) -> Dict[str, Optional[User]]:
        return {
            "volunteer": self.volunteer,
            "team_lead": self.team_lead,
            "head": self.head,
            "admin": self.admin,
        }

    def __repr__(self) -> str:
        vol_name = self.volunteer.full_name if self.volunteer else "None"
        lead_name = self.team_lead.full_name if self.team_lead else "None"
        head_name = self.head.full_name if self.head else "None"
        admin_name = self.admin.full_name if self.admin else "None"
        return (
            f"<NotificationRecipients volunteer='{vol_name}' "
            f"team_lead='{lead_name}' head='{head_name}' admin='{admin_name}'>"
        )


def get_notification_recipients(
    volunteer_id: int,
    event_id: Optional[int],
    db: Session,
    task_team_id: Optional[int] = None
) -> NotificationRecipients:
    """
    Determines the hierarchical notification recipients for a given volunteer and event:
    Volunteer → Team Lead → Club Head → System Admin (fallback).

    Follows existing database models without hardcoding IDs or inventing competing schemas.
    Safely handles missing volunteer profiles, missing team leads, inactive team leads,
    missing club heads, and unassigned hierarchies.
    """
    # 1. Resolve Volunteer Profile & User
    vol: Optional[Volunteer] = (
        db.query(Volunteer).filter(Volunteer.id == volunteer_id).first()
        or db.query(Volunteer).filter(Volunteer.user_id == volunteer_id).first()
    )

    volunteer_user: Optional[User] = None
    if vol and vol.user:
        volunteer_user = vol.user
    else:
        volunteer_user = db.query(User).filter(User.id == volunteer_id).first()

    # 2. Resolve Event and Club ID
    event: Optional[Event] = None
    if event_id:
        event = db.query(Event).filter(Event.id == event_id).first()

    effective_club_id: Optional[int] = None
    if event and event.club_id:
        effective_club_id = event.club_id
    elif vol and vol.club_id:
        effective_club_id = vol.club_id
    elif volunteer_user and volunteer_user.club_id:
        effective_club_id = volunteer_user.club_id

    # 3. Resolve SubTeam ID
    effective_subteam_id: Optional[int] = (
        (vol.subteam_id if vol else None)
        or (volunteer_user.subteam_id if volunteer_user else None)
        or task_team_id
    )

    # 4. Resolve Team Lead (Level 1)
    team_lead: Optional[User] = None
    if effective_subteam_id:
        team = db.query(Team).filter(Team.id == effective_subteam_id).first()
        if team:
            if not effective_club_id and team.club_id:
                effective_club_id = team.club_id

            # Priority 4a: Team's designated lead_id
            if team.lead_id:
                lead_candidate = db.query(User).filter(User.id == team.lead_id).first()
                if lead_candidate and lead_candidate.is_active:
                    team_lead = lead_candidate
                elif lead_candidate and not lead_candidate.is_active:
                    logger.info(
                        f"Team Lead #{lead_candidate.id} for Team #{team.id} is INACTIVE. "
                        "Skipping Team Lead and falling back to Head."
                    )

            # Priority 4b: Active user in team with SUBTEAM_LEAD / TEAM_LEADER role
            if not team_lead:
                lead_candidate = db.query(User).filter(
                    User.subteam_id == team.id,
                    User.role.in_([UserRole.SUBTEAM_LEAD, UserRole.TEAM_LEADER]),
                    User.is_active == True,
                ).first()
                if lead_candidate:
                    team_lead = lead_candidate

            # Priority 4c: Active TeamMembership lead
            if not team_lead:
                membership_lead = db.query(TeamMembership).filter(
                    TeamMembership.team_id == team.id,
                    TeamMembership.role.in_([TeamRole.SUBTEAM_LEAD, TeamRole.TEAM_LEADER]),
                    TeamMembership.is_active == True,
                ).first()
                if membership_lead and membership_lead.user and membership_lead.user.is_active:
                    team_lead = membership_lead.user

    # 5. Resolve Club Head (Level 2)
    head: Optional[User] = None
    if effective_club_id:
        # Priority 5a: Direct CLUB_HEAD / CLUB_MANAGER user in club
        head_candidate = db.query(User).filter(
            User.club_id == effective_club_id,
            User.role.in_([UserRole.CLUB_HEAD, UserRole.CLUB_MANAGER]),
            User.is_active == True,
        ).first()
        if head_candidate:
            head = head_candidate

        # Priority 5b: ClubMembership with CLUB_HEAD role
        if not head:
            cm = db.query(ClubMembership).filter(
                ClubMembership.club_id == effective_club_id,
                ClubMembership.role.in_([ClubRole.CLUB_HEAD, ClubRole.CLUB_LEADER]),
                ClubMembership.is_active == True,
            ).first()
            if cm and cm.user and cm.user.is_active:
                head = cm.user

    # Priority 5c: Event creator if they are head/admin
    if not head and event and event.created_by:
        creator = db.query(User).filter(User.id == event.created_by, User.is_active == True).first()
        if creator and creator.role in [UserRole.CLUB_HEAD, UserRole.CLUB_MANAGER, UserRole.ADMIN]:
            head = creator

    # 6. Resolve System Admin (Fallback when Head is missing)
    admin_fallback: Optional[User] = db.query(User).filter(
        User.role == UserRole.ADMIN,
        User.is_active == True,
    ).first()

    return NotificationRecipients(
        volunteer=volunteer_user,
        volunteer_profile=vol,
        team_lead=team_lead,
        head=head,
        admin=admin_fallback,
    )
