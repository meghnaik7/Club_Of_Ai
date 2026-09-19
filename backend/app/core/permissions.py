from sqlalchemy.orm import Session
from app.models.permission import Permission, RolePermission

# Standard granular permissions
STANDARD_PERMISSIONS = {
    # Club
    "club.view": "View club information and dashboard",
    "club.update": "Update club settings and details",
    "club.manage": "Full management of club operations",
    "club.manage_members": "Manage club members and assignments",

    # SubTeams / Teams
    "subteam.view": "View subteams and subteam details",
    "subteam.create": "Create new subteams in the club",
    "subteam.update": "Update subteam details and configuration",
    "subteam.delete": "Delete subteams from the club",
    "subteam.manage": "Full management of subteam operations",
    "subteam.manage_members": "Add or remove members from a subteam",
    "subteam.assign_lead": "Appoint or remove a SubTeam Lead",

    # Legacy team aliases
    "team.view": "View teams and team details",
    "team.create": "Create new teams in the club",
    "team.update": "Update team details and configuration",
    "team.delete": "Delete teams from the club",
    "team.manage": "Full management of team operations",
    "team.member.view": "View members of a team",
    "team.member.add": "Add members to a team",
    "team.member.update": "Update team member details/roles",
    "team.member.remove": "Remove members from a team",
    "team.leader.assign": "Assign a Team Leader to a team",
    "team.leader.remove": "Remove a Team Leader from a team",

    # Tasks
    "task.view": "View tasks and task activity",
    "task.create": "Create tasks",
    "task.update": "Edit and update task details",
    "task.delete": "Delete tasks",
    "task.assign": "Assign tasks to volunteers/members",
    "task.reassign": "Reassign tasks to other volunteers/members",
    "task.change_status": "Change task status/progress",
    "task.status.update": "Update task progress/status",
    "task.comment": "Add task comments and progress notes",
    "task.comment.create": "Add comments to tasks",
    "task.manage_dependencies": "Manage task dependencies and prerequisites",
    "task.dependency.manage": "Manage task dependencies and prerequisites",

    # Volunteers
    "volunteer.view": "View volunteer profiles and workloads",
    "volunteer.create": "Add new volunteers to the club",
    "volunteer.update": "Update volunteer information and skills",
    "volunteer.delete": "Remove volunteers from the club",
    "volunteer.manage": "Manage volunteer status and assignments",
    "volunteer.assign": "Assign volunteers to roles and teams",
    "volunteer.assign_tasks": "Assign tasks to volunteers",

    # Events
    "event.view": "View events and event details",
    "event.create": "Create new events",
    "event.update": "Update event configuration",
    "event.delete": "Delete events",

    # Risks
    "risk.view": "View event and team risks",
    "risk.create": "Log new risks",
    "risk.update": "Update risk assessments and mitigations",
    "risk.manage": "Manage risk assessments and assign mitigations",
    "risk.resolve": "Resolve and close risks",
    "risk.escalate": "Escalate risk to higher authority",

    # Meetings
    "meeting.view": "View meetings and action items",
    "meeting.create": "Schedule new meetings",
    "meeting.update": "Update meeting details and notes",
    "meeting.delete": "Cancel/delete meetings",

    # Documents
    "document.view": "View and read club documents",
    "document.upload": "Upload new documents",
    "document.delete": "Delete documents",

    # Announcements
    "announcement.view": "View announcements",
    "announcement.create": "Draft and broadcast announcements",
    "announcement.update": "Edit announcements",
    "announcement.delete": "Delete announcements",

    # AI
    "ai.use": "Interact with AI assistant and view authorized insights",
    "ai.propose": "Ask AI to generate proposals for tasks/events",
    "ai.apply": "Apply authorized AI proposals",
    "ai.undo": "Revert authorized AI actions",

    # Audit
    "audit.view": "View system audit logs and history",
}

# Role to Permission mapping
DEFAULT_ROLE_PERMISSIONS = {
    "ADMIN": list(STANDARD_PERMISSIONS.keys()),
    "CLUB_HEAD": list(STANDARD_PERMISSIONS.keys()),
    "CLUB_LEADER": list(STANDARD_PERMISSIONS.keys()),
    "SUBTEAM_LEAD": [
        "subteam.view", "subteam.update", "subteam.manage_members",
        "team.view", "team.update", "team.member.view", "team.member.add", "team.member.update", "team.member.remove",
        "task.view", "task.create", "task.update", "task.assign", "task.reassign", "task.change_status", "task.status.update", "task.manage_dependencies", "task.dependency.manage", "task.comment", "task.comment.create",
        "volunteer.view", "volunteer.assign_tasks",
        "event.view",
        "risk.view", "risk.create", "risk.manage", "risk.resolve", "risk.escalate",
        "meeting.view", "meeting.create", "meeting.update",
        "document.view", "document.upload",
        "announcement.view",
        "ai.use", "ai.propose", "ai.apply"
    ],
    "TEAM_LEADER": [
        "subteam.view", "subteam.update", "subteam.manage_members",
        "team.view", "team.update", "team.member.view", "team.member.add", "team.member.update", "team.member.remove",
        "task.view", "task.create", "task.update", "task.assign", "task.reassign", "task.change_status", "task.status.update", "task.dependency.manage", "task.comment.create",
        "volunteer.view", "volunteer.assign_tasks",
        "event.view",
        "risk.view", "risk.create", "risk.manage", "risk.resolve", "risk.escalate",
        "meeting.view",
        "document.view", "document.upload",
        "announcement.view",
        "ai.use", "ai.propose", "ai.apply"
    ],
    "VOLUNTEER": [
        "subteam.view", "team.view", "team.member.view",
        "task.view", "task.change_status", "task.status.update", "task.comment", "task.comment.create",
        "volunteer.view", "volunteer.update",
        "event.view",
        "risk.view", "risk.escalate",
        "meeting.view",
        "document.view",
        "announcement.view",
        "ai.use"
    ],
    "TEAM_MEMBER": [
        "subteam.view", "team.view", "team.member.view",
        "task.view", "task.change_status", "task.status.update", "task.comment", "task.comment.create",
        "volunteer.view", "volunteer.update",
        "event.view",
        "risk.view", "risk.escalate",
        "meeting.view",
        "document.view",
        "announcement.view",
        "ai.use"
    ],
    "EVENT_COORDINATOR": [
        "event.view", "event.update",
        "task.view", "task.create", "task.update", "task.delete", "task.assign", "task.reassign", "task.change_status", "task.status.update", "task.manage_dependencies", "task.dependency.manage", "task.comment", "task.comment.create",
        "volunteer.view", "volunteer.assign", "volunteer.assign_tasks",
        "risk.view", "risk.create", "risk.update", "risk.manage", "risk.resolve", "risk.escalate",
        "meeting.view", "meeting.create", "meeting.update", "meeting.delete",
        "document.view", "document.upload",
        "announcement.view", "announcement.create", "announcement.update", "announcement.delete",
        "ai.use", "ai.propose", "ai.apply"
    ]
}

ROLE_PERMISSIONS = DEFAULT_ROLE_PERMISSIONS
SYSTEM_PERMISSIONS = STANDARD_PERMISSIONS


def seed_permissions(db: Session):
    """Seed standard permissions and default role mappings into the database."""
    # 1. Insert permissions
    perm_objects = {}
    for key, desc in STANDARD_PERMISSIONS.items():
        perm = db.query(Permission).filter(Permission.key == key).first()
        if not perm:
            perm = Permission(key=key, description=desc)
            db.add(perm)
            db.flush()
        perm_objects[key] = perm

    # 2. Insert role mappings
    for role, perm_keys in DEFAULT_ROLE_PERMISSIONS.items():
        for key in perm_keys:
            perm = perm_objects.get(key)
            if perm:
                existing = db.query(RolePermission).filter(
                    RolePermission.role == role,
                    RolePermission.permission_id == perm.id
                ).first()
                if not existing:
                    db.add(RolePermission(role=role, permission_id=perm.id))

    db.commit()
