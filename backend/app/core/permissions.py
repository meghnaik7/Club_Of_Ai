from sqlalchemy.orm import Session
from app.models.permission import Permission, RolePermission

# Standard granular permissions
STANDARD_PERMISSIONS = {
    # Club
    "club.view": "View club information and dashboard",
    "club.update": "Update club settings and details",
    "club.manage": "Full management of club operations",

    # Teams
    "team.view": "View teams and team details",
    "team.create": "Create new teams in the club",
    "team.update": "Update team details and configuration",
    "team.delete": "Delete teams from the club",
    "team.manage": "Full management of team operations",

    # Team Members
    "team.member.view": "View members of a team",
    "team.member.add": "Add members to a team",
    "team.member.update": "Update team member details/roles",
    "team.member.remove": "Remove members from a team",

    # Team Leaders
    "team.leader.assign": "Assign a Team Leader to a team",
    "team.leader.remove": "Remove a Team Leader from a team",

    # Events
    "event.view": "View events and event details",
    "event.create": "Create new events",
    "event.update": "Update event configuration",
    "event.delete": "Delete events",

    # Tasks
    "task.view": "View tasks and task activity",
    "task.create": "Create tasks",
    "task.update": "Edit and update task details",
    "task.delete": "Delete tasks",
    "task.assign": "Assign tasks to volunteers/members",
    "task.reassign": "Reassign tasks to other volunteers/members",
    "task.status.update": "Update task progress/status",
    "task.dependency.manage": "Manage task dependencies and prerequisites",
    "task.comment.create": "Add comments to tasks",

    # Volunteers
    "volunteer.view": "View volunteer profiles and workloads",
    "volunteer.create": "Add new volunteers to the club",
    "volunteer.update": "Update volunteer information and skills",
    "volunteer.delete": "Remove volunteers from the club",
    "volunteer.assign": "Assign volunteers to roles and teams",

    # Risks
    "risk.view": "View event and team risks",
    "risk.create": "Log new risks",
    "risk.update": "Update risk assessments and mitigations",
    "risk.resolve": "Resolve and close risks",

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
    "CLUB_LEADER": list(STANDARD_PERMISSIONS.keys()),
    "EVENT_COORDINATOR": [
        "event.view", "event.update",
        "task.view", "task.create", "task.update", "task.delete", "task.assign", "task.reassign", "task.status.update", "task.dependency.manage", "task.comment.create",
        "volunteer.view", "volunteer.assign",
        "risk.view", "risk.create", "risk.update", "risk.resolve",
        "meeting.view", "meeting.create", "meeting.update", "meeting.delete",
        "document.view", "document.upload",
        "announcement.view", "announcement.create", "announcement.update", "announcement.delete",
        "ai.use", "ai.propose", "ai.apply"
    ],
    "TEAM_LEADER": [
        "team.view", "team.update",
        "team.member.view", "team.member.add", "team.member.update", "team.member.remove",
        "task.view", "task.create", "task.update", "task.assign", "task.reassign", "task.status.update", "task.dependency.manage", "task.comment.create",
        "volunteer.view",
        "event.view",
        "risk.view", "risk.create", "risk.resolve",
        "meeting.view",
        "document.view", "document.upload",
        "announcement.view",
        "ai.use", "ai.propose", "ai.apply"
    ],
    "TEAM_MEMBER": [
        "team.view",
        "team.member.view",
        "task.view", "task.status.update", "task.comment.create",
        "event.view",
        "meeting.view",
        "document.view",
        "announcement.view",
        "ai.use"
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
