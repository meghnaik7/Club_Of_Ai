from typing import Any, List, Optional, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, ConfigDict, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.api import deps
from app.models.user import User, UserRole
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.team import Club, Team, TeamMembership, ClubMembership
from app.models.event import Event, EventStatus
from app.models.task import Task, TaskStatus, TaskPriority, TaskAssignment
from app.core.config import settings
from app.services.authz import AuthorizationService

router = APIRouter()


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[Any] = None  # Accepts list of strings or comma-separated string
    availability: Optional[str] = None

    model_config = ConfigDict(extra="allow")  # To catch and reject forbidden fields manually with custom error


def get_load_status(active_task_count: int) -> str:
    low_threshold = getattr(settings, "VOLUNTEER_LOAD_LOW", 3)
    med_threshold = getattr(settings, "VOLUNTEER_LOAD_MEDIUM", 6)
    if active_task_count <= low_threshold:
        return "LOW"
    elif active_task_count <= med_threshold:
        return "MEDIUM"
    else:
        return "OVERLOADED"


def get_human_readable_permissions(role: str) -> List[str]:
    role_upper = (role or "").upper()
    if "ADMIN" in role_upper:
        return [
            "Full system administration",
            "Manage all clubs, subteams, and volunteers",
            "Appoint and remove Club Heads and SubTeam Leads",
            "Configure role permissions and security policies",
            "Manage all events, tasks, and budgets globally",
            "Access complete system audit logs and metrics"
        ]
    elif "CLUB_HEAD" in role_upper or "CLUB_LEADER" in role_upper:
        return [
            "Manage club members and volunteers",
            "Create and configure club subteams",
            "Appoint and manage SubTeam Leads",
            "Manage club events, venues, and budgets",
            "Manage club tasks and cross-team dependencies",
            "Manage and resolve club risks",
            "Escalate critical issues to System Administrator"
        ]
    elif "SUBTEAM_LEAD" in role_upper or "TEAM_LEADER" in role_upper:
        return [
            "Manage own subteam",
            "Manage subteam volunteers and workloads",
            "Create, assign, and prioritize subteam tasks",
            "Update task status and monitor deadlines",
            "Review blockers and provide technical guidance",
            "Escalate bottlenecks to Club Head"
        ]
    else:
        return [
            "View assigned tasks and deadlines",
            "Update permitted task progress (To-Do, In Progress, Done)",
            "Add task comments and completion notes",
            "Report blockers and request assistance",
            "View club announcements and event schedules"
        ]


@router.get("/me/profile")
def get_current_user_profile(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Returns complete profile data for the authenticated user,
    including basic info, organization, workload, authorized tasks,
    events, and human-readable permissions summary.
    """
    user = current_user
    vol = user.volunteer_profile

    # 1. Skills & Availability
    raw_skills = ""
    if vol and vol.skills:
        raw_skills = vol.skills
    elif user.skills:
        raw_skills = user.skills

    skills_list = [s.strip() for s in raw_skills.split(",") if s.strip()] if raw_skills else []

    raw_availability = ""
    if vol and vol.availability:
        raw_availability = vol.availability
    elif user.availability:
        raw_availability = user.availability

    # 2. Organization Info
    club = user.club
    subteam = user.subteam

    club_head_info = None
    if club:
        head_membership = db.query(ClubMembership).filter(
            ClubMembership.club_id == club.id
        ).first()
        if head_membership and head_membership.user:
            club_head_info = {
                "id": head_membership.user.id,
                "name": head_membership.user.full_name,
                "email": head_membership.user.email
            }
        else:
            # Fallback: check user with CLUB_HEAD role in this club
            ch_user = db.query(User).filter(
                User.club_id == club.id,
                User.role == UserRole.CLUB_HEAD
            ).first()
            if ch_user:
                club_head_info = {
                    "id": ch_user.id,
                    "name": ch_user.full_name,
                    "email": ch_user.email
                }

    subteam_lead_info = None
    if subteam:
        lead_user = subteam.lead
        if not lead_user and subteam.lead_id:
            lead_user = db.query(User).filter(User.id == subteam.lead_id).first()
        if lead_user:
            subteam_lead_info = {
                "id": lead_user.id,
                "name": lead_user.full_name,
                "email": lead_user.email
            }

    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    role_display_map = {
        "ADMIN": "System Administrator",
        "CLUB_HEAD": "Club Head",
        "CLUB_LEADER": "Club Head",
        "CLUB_MANAGER": "Club Head",
        "SUBTEAM_LEAD": "SubTeam Lead",
        "TEAM_LEADER": "SubTeam Lead",
        "VOLUNTEER": "Volunteer",
        "TEAM_MEMBER": "Volunteer"
    }
    role_display = role_display_map.get(role_val, role_val.replace("_", " ").title())

    # 3. Task Scoping according to RBAC hierarchy
    now = datetime.utcnow()
    q_tasks = db.query(Task)

    if AuthorizationService.is_admin(user):
        pass  # Admin can see all tasks
    elif AuthorizationService.is_club_head(db, user, club_id=user.club_id):
        if user.club_id:
            q_tasks = q_tasks.filter(
                or_(
                    Task.event.has(Event.club_id == user.club_id),
                    Task.team.has(Team.club_id == user.club_id),
                    Task.created_by == user.id
                )
            )
    elif AuthorizationService.is_subteam_lead(db, user):
        user_team_id = user.subteam_id
        conditions = [Task.created_by == user.id]
        if user_team_id:
            conditions.append(Task.team_id == user_team_id)
        if vol:
            conditions.append(Task.assignments.any(TaskAssignment.volunteer_id == vol.id))
        q_tasks = q_tasks.filter(or_(*conditions))
    else:
        # Volunteer: Only view tasks assigned to them or created by them
        if vol:
            q_tasks = q_tasks.filter(
                or_(
                    Task.assignments.any(TaskAssignment.volunteer_id == vol.id),
                    Task.created_by == user.id
                )
            )
        else:
            q_tasks = q_tasks.filter(Task.created_by == user.id)

    all_authorized_tasks = q_tasks.order_by(Task.due_date.asc().nullslast()).all()

    # Calculate workload metrics
    if vol:
        assigned_tasks_q = db.query(Task).join(TaskAssignment).filter(
            TaskAssignment.volunteer_id == vol.id
        )
        workload_tasks = assigned_tasks_q.all()
    else:
        workload_tasks = all_authorized_tasks

    active_tasks_count = 0
    completed_tasks_count = 0
    overdue_tasks_count = 0
    blocked_tasks_count = 0
    in_progress_tasks_count = 0

    formatted_tasks = []
    for t in all_authorized_tasks:
        is_overdue = bool(t.due_date and t.due_date < now and t.status not in [TaskStatus.DONE, TaskStatus.CANCELLED])
        t_status = t.status.value if hasattr(t.status, "value") else str(t.status)
        t_priority = t.priority.value if hasattr(t.priority, "value") else str(t.priority)

        # Workload metrics
        if t in workload_tasks:
            if t_status in ["TODO", "IN_PROGRESS", "BLOCKED"]:
                active_tasks_count += 1
            if t_status == "IN_PROGRESS":
                in_progress_tasks_count += 1
            if t_status == "BLOCKED":
                blocked_tasks_count += 1
            if t_status == "DONE":
                completed_tasks_count += 1
            if is_overdue:
                overdue_tasks_count += 1

        formatted_tasks.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t_status,
            "priority": t_priority,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "is_overdue": is_overdue,
            "event_id": t.event_id,
            "event_title": t.event.title if t.event else None,
            "team_id": t.team_id,
            "team_name": t.team.name if t.team else None,
        })

    load_status = get_load_status(active_tasks_count)

    # 4. Event Information
    q_events = db.query(Event)
    if not AuthorizationService.is_admin(user):
        if user.club_id:
            q_events = q_events.filter(
                or_(Event.club_id == user.club_id, Event.club_id == None)
            )
    all_events = q_events.order_by(Event.date.desc()).all()

    user_event_ids = {t["event_id"] for t in formatted_tasks if t.get("event_id")}

    upcoming_events = []
    participated_events = []
    assigned_events = []

    for ev in all_events:
        ev_data = {
            "id": ev.id,
            "title": ev.title,
            "description": ev.description,
            "date": ev.date.isoformat() if ev.date else None,
            "venue": ev.venue,
            "status": ev.status.value if hasattr(ev.status, "value") else str(ev.status),
            "club_id": ev.club_id,
            "club_name": ev.club.name if ev.club else None
        }
        if ev.date and ev.date >= now:
            upcoming_events.append(ev_data)
        else:
            participated_events.append(ev_data)

        if ev.id in user_event_ids or ev.created_by == user.id:
            assigned_events.append(ev_data)

    # 5. Permissions
    authz_summary = AuthorizationService.get_user_authz_summary(db, user)
    granular_permissions = authz_summary.get("permissions", [])
    human_readable_perms = get_human_readable_permissions(role_val)

    # 6. Build Comprehensive Response
    return {
        "basic_info": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone or "",
            "username": user.username or (user.email.split("@")[0] if user.email else ""),
            "avatar_url": user.avatar_url or "",
            "bio": user.bio or "",
            "account_status": "ACTIVE" if user.is_active else "INACTIVE",
            "is_active": user.is_active,
            "joined_date": user.created_at.isoformat() if user.created_at else None,
        },
        "organization": {
            "role": role_val,
            "role_display": role_display,
            "club_id": user.club_id,
            "club_name": club.name if club else None,
            "club_description": club.description if club else None,
            "subteam_id": user.subteam_id,
            "subteam_name": subteam.name if subteam else None,
            "subteam_description": subteam.description if subteam else None,
            "club_head_info": club_head_info,
            "subteam_lead_info": subteam_lead_info,
        },
        "skills": skills_list,
        "availability": raw_availability or "Not specified",
        "workload": {
            "active_tasks": active_tasks_count,
            "in_progress_tasks": in_progress_tasks_count,
            "blocked_tasks": blocked_tasks_count,
            "completed_tasks": completed_tasks_count,
            "overdue_tasks": overdue_tasks_count,
            "total_tasks": len(workload_tasks),
            "load_status": load_status,
            "max_capacity": vol.max_capacity if vol else 10,
        },
        "tasks": formatted_tasks,
        "events": {
            "upcoming": upcoming_events[:5],
            "participated": participated_events[:5],
            "assigned": assigned_events[:5],
        },
        "permissions": {
            "human_readable": human_readable_perms,
            "granular_keys": granular_permissions,
        }
    }


@router.patch("/me/profile")
async def update_current_user_profile(
    request: Request,
    payload: ProfileUpdateRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Updates permitted personal profile information only.
    Strictly forbids and rejects attempts to modify role, club_id, subteam_id,
    permissions, or admin status.
    """
    # 1. Intercept raw request JSON to inspect for forbidden fields
    try:
        raw_json = await request.json()
    except Exception:
        raw_json = {}

    forbidden_fields = ["role", "club_id", "subteam_id", "is_admin", "admin", "permissions", "is_active"]
    attempted_forbidden = [f for f in forbidden_fields if f in raw_json]
    if attempted_forbidden:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unauthorized field modification: {', '.join(attempted_forbidden)} cannot be altered via profile update."
        )

    user = current_user

    # 2. Update allowed personal attributes on User
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.username is not None:
        user.username = payload.username.strip()
    if payload.phone is not None:
        user.phone = payload.phone.strip()
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url.strip()
    if payload.bio is not None:
        user.bio = payload.bio.strip()

    # Skills formatting (can be list or string)
    formatted_skills = None
    if payload.skills is not None:
        if isinstance(payload.skills, list):
            formatted_skills = ", ".join([str(s).strip() for s in payload.skills if str(s).strip()])
        else:
            formatted_skills = str(payload.skills).strip()
        user.skills = formatted_skills

    if payload.availability is not None:
        user.availability = payload.availability.strip()

    # 3. Synchronize with Volunteer profile if it exists
    vol = user.volunteer_profile
    if vol:
        if formatted_skills is not None:
            vol.skills = formatted_skills
        if payload.availability is not None:
            vol.availability = payload.availability.strip()

    db.commit()
    db.refresh(user)

    # Return updated profile
    return get_current_user_profile(db=db, current_user=user)
