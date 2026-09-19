import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models.event import Event
from app.models.task import Task, TaskAssignment, TaskStatus
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.user import User
from app.models.announcement import Announcement
from app.models.document import Document
try:
    from ai.schemas.ai_proposal import AIProposal, ProposalStatus
except ImportError:
    AIProposal, ProposalStatus = None, None

logger = logging.getLogger(__name__)

def get_event_context(db: Session, event_id: int) -> Dict[str, Any]:
    """Returns important event information for the AI in a single structured payload."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"error": f"Event with ID {event_id} not found"}

    # Query tasks for this event
    tasks = db.query(Task).filter(Task.event_id == event_id).all()
    task_status_counts = {"TODO": 0, "IN_PROGRESS": 0, "DONE": 0, "BLOCKED": 0}
    for t in tasks:
        st = t.status.value if hasattr(t.status, "value") else str(t.status)
        if st in task_status_counts:
            task_status_counts[st] += 1

    # Query assigned volunteers
    volunteers = (
        db.query(Volunteer)
        .join(TaskAssignment)
        .join(Task)
        .filter(Task.event_id == event_id)
        .distinct()
        .all()
    )

    # Query announcements
    announcements = (
        db.query(Announcement)
        .filter(Announcement.event_id == event_id)
        .order_by(Announcement.created_at.desc())
        .limit(5)
        .all()
    )

    # Query documents
    documents = (
        db.query(Document)
        .filter(or_(Document.event_id == event_id, Document.event_id == str(event_id)))
        .limit(5)
        .all()
    )

    return {
        "event_id": event.id,
        "title": event.title,
        "description": event.description or "",
        "date": event.date.strftime("%Y-%m-%d %H:%M:%S") if event.date else "TBD",
        "venue": event.venue or "Unspecified Venue",
        "budget": event.budget or 0.0,
        "expected_attendance": event.expected_attendance or 0,
        "status": event.status.value if hasattr(event.status, "value") else str(event.status),
        "task_metrics": {
            "total_tasks": len(tasks),
            "status_breakdown": task_status_counts
        },
        "assigned_volunteers": [
            {
                "id": v.id,
                "name": v.user.full_name if v.user else f"Volunteer #{v.id}",
                "skills": v.skills
            }
            for v in volunteers
        ],
        "recent_announcements": [
            {"id": a.id, "title": a.title, "status": a.status}
            for a in announcements
        ],
        "attached_documents": [
            {
                "id": d.id,
                "name": d.name or d.filename,
                "category": d.category.value if hasattr(d.category, "value") else str(d.category) if d.category else None
            }
            for d in documents
        ]
    }

def get_task_context(db: Session, task_id: int) -> Dict[str, Any]:
    """Returns task + dependencies + owners + subtasks."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return {"error": f"Task with ID {task_id} not found"}

    event = db.query(Event).filter(Event.id == task.event_id).first()
    assignments = db.query(TaskAssignment).filter(TaskAssignment.task_id == task.id).all()
    assigned_volunteers = []
    for a in assignments:
        vol = a.volunteer
        if vol:
            assigned_volunteers.append({
                "volunteer_id": vol.id,
                "name": vol.user.full_name if vol.user else f"Volunteer #{vol.id}",
                "email": vol.user.email if vol.user else ""
            })

    return {
        "task_id": task.id,
        "event_id": task.event_id,
        "event_title": event.title if event else "Unknown Event",
        "title": task.title,
        "description": task.description or "",
        "status": task.status.value if hasattr(task.status, "value") else str(task.status),
        "assigned_volunteers": assigned_volunteers,
        "is_assigned": len(assigned_volunteers) > 0
    }

def get_volunteer_context(db: Session, volunteer_id: int) -> Dict[str, Any]:
    """Returns volunteer skills + availability + workload."""
    volunteer = db.query(Volunteer).filter(Volunteer.id == volunteer_id).first()
    if not volunteer:
        return {"error": f"Volunteer with ID {volunteer_id} not found"}

    # Fetch active tasks
    active_assignments = (
        db.query(TaskAssignment)
        .join(Task)
        .filter(
            TaskAssignment.volunteer_id == volunteer.id,
            Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])
        )
        .all()
    )

    completed_assignments = (
        db.query(TaskAssignment)
        .join(Task)
        .filter(
            TaskAssignment.volunteer_id == volunteer.id,
            Task.status == TaskStatus.DONE
        )
        .all()
    )

    active_tasks = [
        {"id": a.task.id, "title": a.task.title, "status": a.task.status.value if hasattr(a.task.status, "value") else str(a.task.status)}
        for a in active_assignments if a.task
    ]

    skills_list = [s.strip() for s in (volunteer.skills or "").split(",") if s.strip()]

    return {
        "volunteer_id": volunteer.id,
        "name": volunteer.user.full_name if volunteer.user else f"Volunteer #{volunteer.id}",
        "email": volunteer.user.email if volunteer.user else "",
        "skills": skills_list,
        "availability": volunteer.availability or "Not specified",
        "status": volunteer.status.value if hasattr(volunteer.status, "value") else str(volunteer.status),
        "workload": {
            "active_tasks_count": len(active_tasks),
            "completed_tasks_count": len(completed_assignments),
            "active_tasks": active_tasks
        }
    }

def get_project_summary(db: Session, event_id: Optional[int] = None) -> Dict[str, Any]:
    """Returns high-level event/project state for overall AI planning."""
    events_query = db.query(Event)
    tasks_query = db.query(Task)
    if event_id:
        events_query = events_query.filter(Event.id == event_id)
        tasks_query = tasks_query.filter(Task.event_id == event_id)

    total_events = events_query.count()
    total_tasks = tasks_query.count()
    completed_tasks = tasks_query.filter(Task.status == TaskStatus.DONE).count()
    active_tasks = tasks_query.filter(Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])).count()

    # Volunteers
    total_volunteers = db.query(Volunteer).filter(Volunteer.status == VolunteerStatus.ACTIVE).count()

    # Pending proposals
    pending_proposals = 0
    if AIProposal:
        try:
            pending_proposals = db.query(AIProposal).filter(AIProposal.status == ProposalStatus.PENDING).count()
        except Exception:
            pass

    return {
        "total_events": total_events,
        "total_tasks": total_tasks,
        "active_tasks": active_tasks,
        "completed_tasks": completed_tasks,
        "completion_rate_percent": round((completed_tasks / max(1, total_tasks)) * 100, 1),
        "active_volunteers": total_volunteers,
        "pending_ai_proposals": pending_proposals
    }

def search_tasks(
    db: Session,
    query: str,
    event_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Semantic/task search across titles and descriptions."""
    q = db.query(Task)
    if event_id:
        q = q.filter(Task.event_id == event_id)
    if status:
        q = q.filter(Task.status == status)

    if query:
        search_pattern = f"%{query.strip()}%"
        q = q.filter(or_(Task.title.ilike(search_pattern), Task.description.ilike(search_pattern)))

    tasks = q.limit(limit).all()
    return [
        {
            "id": t.id,
            "event_id": t.event_id,
            "title": t.title,
            "description": t.description or "",
            "status": t.status.value if hasattr(t.status, "value") else str(t.status)
        }
        for t in tasks
    ]

def search_volunteers(
    db: Session,
    query: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Search volunteers by natural-language requirements (skills, names, availability)."""
    q = db.query(Volunteer).join(User)
    if query:
        pattern = f"%{query.strip()}%"
        q = q.filter(
            or_(
                Volunteer.skills.ilike(pattern),
                Volunteer.availability.ilike(pattern),
                User.full_name.ilike(pattern),
                User.email.ilike(pattern)
            )
        )

    volunteers = q.limit(limit).all()
    return [
        {
            "id": v.id,
            "name": v.user.full_name if v.user else f"Volunteer #{v.id}",
            "email": v.user.email if v.user else "",
            "skills": v.skills,
            "availability": v.availability,
            "status": v.status.value if hasattr(v.status, "value") else str(v.status)
        }
        for v in volunteers
    ]

def search_event_data(
    db: Session,
    query: str,
    event_id: Optional[int] = None,
    limit: int = 15
) -> Dict[str, Any]:
    """Search across event entities (tasks, announcements, and documents)."""
    pattern = f"%{query.strip()}%"

    # 1. Search tasks
    t_query = db.query(Task).filter(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))
    if event_id:
        t_query = t_query.filter(Task.event_id == event_id)
    matched_tasks = t_query.limit(limit).all()

    # 2. Search announcements
    a_query = db.query(Announcement).filter(or_(Announcement.title.ilike(pattern), Announcement.content.ilike(pattern)))
    if event_id:
        a_query = a_query.filter(Announcement.event_id == event_id)
    matched_announcements = a_query.limit(limit).all()

    # 3. Search documents
    d_query = db.query(Document).filter(
        or_(
            Document.name.ilike(pattern),
            Document.filename.ilike(pattern),
            Document.raw_text.ilike(pattern)
        )
    )
    if event_id:
        d_query = d_query.filter(or_(Document.event_id == event_id, Document.event_id == str(event_id)))
    matched_docs = d_query.limit(limit).all()

    return {
        "query": query,
        "event_id": event_id,
        "total_results": len(matched_tasks) + len(matched_announcements) + len(matched_docs),
        "tasks": [{"id": t.id, "title": t.title, "status": str(t.status)} for t in matched_tasks],
        "announcements": [{"id": a.id, "title": a.title, "status": a.status} for a in matched_announcements],
        "documents": [
            {
                "id": d.id,
                "name": d.name or d.filename,
                "category": d.category.value if hasattr(d.category, "value") else str(d.category) if d.category else None
            }
            for d in matched_docs
        ]
    }
