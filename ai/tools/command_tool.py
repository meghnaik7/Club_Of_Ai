import re
import logging
from typing import Optional, Dict, Any, List
try:
    from langchain_core.tools import tool
except ImportError:
    from ai.tools.compat import tool

try:
    from app.db.session import SessionLocal
    from app.models.task import Task
    from app.models.volunteer import Volunteer
    from app.models.user import User
    from app.services import context_service
except ImportError:
    from backend.app.db.session import SessionLocal
    from backend.app.models.task import Task
    from backend.app.models.volunteer import Volunteer
    from backend.app.models.user import User
    from backend.app.services import context_service

from ai.workflows import proposal_service
from ai.schemas.ai_plan import EventPlan, GeneratedTask

logger = logging.getLogger(__name__)


def _parse_confirm_id(text: str) -> Optional[int]:
    """Check if text asks to confirm/apply an existing proposal ID."""
    match = re.search(r"\b(?:confirm|apply|approve)\s+(?:proposal|action)?\s*#?(\d+)\b", text, re.I)
    if match:
        return int(match.group(1))
    return None


def _parse_undo_id(text: str) -> Optional[int]:
    """Check if text asks to undo an existing proposal/action ID."""
    match = re.search(r"\b(?:undo|revert)\s+(?:proposal|action)?\s*#?(\d+)\b", text, re.I)
    if match:
        return int(match.group(1))
    return None


def _parse_reject_id(text: str) -> Optional[int]:
    """Check if text asks to reject an existing proposal ID."""
    match = re.search(r"\b(?:reject|cancel)\s+(?:proposal|action)?\s*#?(\d+)\b", text, re.I)
    if match:
        return int(match.group(1))
    return None


def _handle_assignment_command(
    db,
    command: str,
    event_id: Optional[int],
    user_id: Optional[int],
    auto_confirm: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Handle natural-language assignment commands such as:
    'Assign all unowned tasks due this week to Arjun' or 'Assign task 2 to Arjun'
    Following the pipeline: Context/List -> Create Proposal -> Diff Preview -> (Confirm -> Apply)
    """
    cmd_lower = command.lower()
    if "assign" not in cmd_lower:
        return None

    # Find volunteer target name
    # e.g. "assign ... to Arjun"
    to_match = re.search(r"\bto\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b", command, re.I)
    target_name = to_match.group(1).strip() if to_match else None
    if not target_name:
        return None

    # Search volunteer
    matched_volunteers = context_service.search_volunteers(db=db, query=target_name, limit=1)
    if not matched_volunteers:
        return {
            "status": "ERROR",
            "message": f"Could not find any volunteer matching name '{target_name}'."
        }
    volunteer = matched_volunteers[0]
    volunteer_id = volunteer["id"]
    volunteer_name = volunteer["name"]

    # Determine tasks to assign
    tasks_to_assign = []
    # Check if a specific task ID is mentioned, e.g. "task 3"
    task_id_match = re.search(r"\btask\s+#?(\d+)\b", command, re.I)
    if task_id_match:
        tid = int(task_id_match.group(1))
        t = db.query(Task).filter(Task.id == tid).first()
        if t:
            tasks_to_assign.append(t)
    elif "all unowned" in cmd_lower or "all unassigned" in cmd_lower or "unassigned tasks" in cmd_lower or "unowned tasks" in cmd_lower:
        # Query unassigned tasks
        query = db.query(Task)
        if event_id:
            query = query.filter(Task.event_id == event_id)
        all_tasks = query.all()
        for t in all_tasks:
            # check if assignments exist
            if not t.assignments:
                tasks_to_assign.append(t)
    else:
        # Search relevant tasks
        query = db.query(Task)
        if event_id:
            query = query.filter(Task.event_id == event_id)
        tasks_to_assign = query.limit(5).all()

    if not tasks_to_assign:
        return {
            "status": "COMPLETED",
            "message": f"No unassigned tasks found matching the criteria."
        }

    # Check authorization scoping
    try:
        from app.services.authz import AuthorizationService
        from app.models.team import TeamMembership
    except ImportError:
        from backend.app.services.authz import AuthorizationService
        from backend.app.models.team import TeamMembership

    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    authorized_tasks = []
    unauthorized_tasks = []
    unauthorized_by_team: Dict[str, int] = {}

    for t in tasks_to_assign:
        can_assign = AuthorizationService.can(db, user, "task.assign", resource=t) if user else True
        if can_assign and user and not AuthorizationService.is_club_leader(db, user) and t.team_id:
            vol_user_id = volunteer.get("user_id")
            if not vol_user_id:
                vol_obj = db.query(Volunteer).filter(Volunteer.id == volunteer_id).first()
                vol_user_id = vol_obj.user_id if vol_obj else None
            if vol_user_id:
                is_mem = db.query(TeamMembership).filter(
                    TeamMembership.team_id == t.team_id,
                    TeamMembership.user_id == vol_user_id
                ).first()
                if not is_mem:
                    can_assign = False

        if can_assign:
            authorized_tasks.append(t)
        else:
            unauthorized_tasks.append(t)
            team_name = t.team.name if t.team else "General / Other"
            unauthorized_by_team[team_name] = unauthorized_by_team.get(team_name, 0) + 1

    if not authorized_tasks:
        if unauthorized_tasks:
            breakdown_str = ", ".join(f"{tname}: {cnt}" for tname, cnt in unauthorized_by_team.items())
            return {
                "status": "FORBIDDEN",
                "message": f"Found {len(tasks_to_assign)} unowned task(s), but you do not have authority to assign them ({breakdown_str}). Only the respective Team Leaders or the Club Leader can assign these tasks."
            }
        return {
            "status": "COMPLETED",
            "message": "No unassigned tasks found matching the criteria."
        }

    # Stage changes in AIProposal for authorized tasks ONLY
    changes = []
    for t in authorized_tasks:
        changes.append({
            "entity_type": "TASK",
            "entity_id": t.id,
            "action": "UPDATE",
            "proposed_data": {
                "volunteer_id": volunteer_id,
                "volunteer_name": volunteer_name
            },
            "previous_data": {
                "volunteer_id": None
            },
            "explanation": f"Assign task '{t.title}' to {volunteer_name} (ID: {volunteer_id})."
        })

    intent = f"Assign {len(authorized_tasks)} task(s) to {volunteer_name}"
    proposal_resp = proposal_service.create_proposal(
        db=db,
        user_id=user_id,
        intent=intent,
        changes=changes
    )
    proposal_id = proposal_resp.proposal_id

    # Preview action diff
    diff = proposal_service.preview_action_diff(db=db, proposal_id=proposal_id)

    # Build clear informative feedback for the user
    if unauthorized_tasks:
        breakdown_str = ", ".join(f"{tname}: {cnt}" for tname, cnt in unauthorized_by_team.items())
        auth_team_names = set(t.team.name for t in authorized_tasks if t.team)
        auth_teams_str = ", ".join(auth_team_names) if auth_team_names else "authorized scope"
        feedback_msg = (
            f"Found {len(tasks_to_assign)} unowned tasks. You have authority to manage {len(authorized_tasks)} tasks "
            f"in the {auth_teams_str}. Staged proposal #{proposal_id} for those {len(authorized_tasks)} tasks. "
            f"The remaining {len(unauthorized_tasks)} tasks belong to other teams ({breakdown_str}) "
            f"and require their respective Team Leaders or the Club Leader to assign."
        )
    else:
        feedback_msg = f"Staged proposal #{proposal_id} to {intent}. Please review the diff and confirm to apply to production."

    if auto_confirm:
        apply_resp = proposal_service.apply_proposal(db=db, proposal_id=proposal_id, user_id=user_id)
        return {
            "status": "APPLIED",
            "proposal_id": proposal_id,
            "intent": intent,
            "message": f"Proposal #{proposal_id} applied successfully: {intent}.",
            "applied_changes": len(apply_resp.changes),
            "diff": diff.model_dump()
        }

    return {
        "status": "AWAITING_CONFIRMATION",
        "proposal_id": proposal_id,
        "intent": intent,
        "tasks_affected": [t.id for t in authorized_tasks],
        "diff_preview": diff.model_dump(),
        "requires_confirmation": True,
        "message": feedback_msg
    }


def _handle_planning_command(
    db,
    command: str,
    event_id: Optional[int],
    user_id: Optional[int],
    auto_confirm: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Handle natural-language plan creation such as:
    'Generate tasks for Hackathon 2026' or 'Create event plan for AI Summit'
    Following the pipeline: Propose Plan -> Diff Preview -> (Confirm -> Apply)
    """
    cmd_lower = command.lower()
    if not any(k in cmd_lower for k in ["generate task", "create task", "plan event", "create plan", "tasks for"]):
        return None

    # Extract event title or name
    event_title = "Upcoming Club Event"
    title_match = re.search(r"(?:for|event)\s+([A-Za-z0-9\s]+?)(?:$|\.|\band\b)", command, re.I)
    if title_match:
        event_title = title_match.group(1).strip()

    # Generate task definitions
    tasks = [
        GeneratedTask(
            title=f"Initial Planning & Scope - {event_title}",
            description="Define objectives, venue requirements, and timeline.",
            phase="PRE_EVENT",
            priority="HIGH",
            estimated_duration_hours=6
        ),
        GeneratedTask(
            title=f"Logistics & Equipment Setup - {event_title}",
            description="Arrange sound system, projector, seating, and signage.",
            phase="PRE_EVENT",
            priority="MEDIUM",
            estimated_duration_hours=4
        ),
        GeneratedTask(
            title=f"Marketing & Registrations - {event_title}",
            description="Promote on social media and manage participant sign-ups.",
            phase="PRE_EVENT",
            priority="HIGH",
            estimated_duration_hours=5
        ),
        GeneratedTask(
            title=f"Live Event Operations - {event_title}",
            description="Coordinate schedule, guest speakers, and volunteer shifts.",
            phase="EVENT_DAY",
            priority="HIGH",
            estimated_duration_hours=8
        ),
        GeneratedTask(
            title=f"Post-Event Cleanup & Retrospective - {event_title}",
            description="Collect feedback, settle budget, and pack venue equipment.",
            phase="POST_EVENT",
            priority="MEDIUM",
            estimated_duration_hours=3
        )
    ]
    event_plan = EventPlan(event_title=event_title, tasks=tasks)
    intent = f"Generate event plan with 5 structured tasks for '{event_title}'"

    proposal_resp = proposal_service.create_proposal(
        db=db,
        user_id=user_id,
        intent=intent,
        event_plan=event_plan
    )
    proposal_id = proposal_resp.proposal_id
    diff = proposal_service.preview_action_diff(db=db, proposal_id=proposal_id)

    if auto_confirm:
        apply_resp = proposal_service.apply_proposal(db=db, proposal_id=proposal_id, user_id=user_id)
        return {
            "status": "APPLIED",
            "proposal_id": proposal_id,
            "intent": intent,
            "message": f"Proposal #{proposal_id} applied: Event and tasks created in production.",
            "applied_changes": len(apply_resp.changes),
            "diff": diff.model_dump()
        }

    return {
        "status": "AWAITING_CONFIRMATION",
        "proposal_id": proposal_id,
        "intent": intent,
        "diff_preview": diff.model_dump(),
        "requires_confirmation": True,
        "message": f"Proposed event plan #{proposal_id} generated for '{event_title}' with {len(tasks)} tasks. Please review the diff preview and confirm to commit to production."
    }


@tool
def execute_command(
    command: str,
    active_event_id: Optional[int] = None,
    user_id: Optional[int] = None,
    confirm_proposal_id: Optional[int] = None,
    auto_confirm: bool = False,
    thread_id: Optional[str] = None,
    club_id: Optional[int] = None
) -> Dict[str, Any]:

    """
    Interpret a user's natural-language command and determine which tools/actions are required.
    Supports context queries, volunteer/task search, proposal creation with diff preview,
    and user confirmation before state application.
    """
    db = SessionLocal()
    try:
        cmd_trimmed = command.strip()

        # 1. Handle Explicit Confirmation / Apply Proposal
        target_confirm_id = confirm_proposal_id or _parse_confirm_id(cmd_trimmed)
        if target_confirm_id:
            apply_resp = proposal_service.apply_proposal(
                db=db,
                proposal_id=target_confirm_id,
                user_id=user_id
            )
            audit_log = proposal_service.get_action_audit_log(db=db, proposal_id=target_confirm_id)
            return {
                "status": "APPLIED",
                "proposal_id": target_confirm_id,
                "message": f"Proposal #{target_confirm_id} successfully confirmed and applied to production.",
                "applied_changes": len(apply_resp.changes),
                "audit_entries": len(audit_log)
            }

        # 2. Handle Explicit Undo
        undo_id = _parse_undo_id(cmd_trimmed)
        if undo_id:
            undo_resp = proposal_service.undo_proposal(
                db=db,
                proposal_id=undo_id,
                user_id=user_id
            )
            return {
                "status": "UNDONE",
                "proposal_id": undo_id,
                "message": f"Proposal #{undo_id} has been reverted using the audit log.",
                "changes_reverted": len(undo_resp.changes)
            }

        # 3. Handle Explicit Reject
        reject_id = _parse_reject_id(cmd_trimmed)
        if reject_id:
            reject_resp = proposal_service.reject_proposal(db=db, proposal_id=reject_id)
            return {
                "status": "REJECTED",
                "proposal_id": reject_id,
                "message": f"Proposal #{reject_id} marked as rejected without modifying production state."
            }

        # 4. Handle Read-Only Context Retrieval
        cmd_lower = cmd_trimmed.lower()
        if "summary" in cmd_lower and ("project" in cmd_lower or "event" in cmd_lower or "overall" in cmd_lower):
            summary = context_service.get_project_summary(db=db, event_id=active_event_id)
            return {
                "status": "COMPLETED",
                "type": "PROJECT_SUMMARY",
                "result": summary,
                "message": f"Retrieved project summary: {summary.get('active_tasks')} active tasks, {summary.get('completion_rate_percent')}% complete."
            }

        if ("next" in cmd_lower or "upcoming" in cmd_lower) and "event" in cmd_lower:
            next_ev = context_service.get_next_event(db=db)
            title = next_ev.get("title", "Upcoming Event")
            venue = next_ev.get("venue", "Campus Auditorium")
            date_str = next_ev.get("formatted_date", "Date TBD")
            days_until = next_ev.get("days_until", 0)
            attendance = next_ev.get("expected_attendance", 0)
            budget = next_ev.get("budget", 0.0)
            total_tasks = next_ev.get("total_tasks", 0)

            days_text = f"in {days_until} days" if days_until > 0 else "approaching soon"
            msg = (
                f"📅 The next event is **{title}**, scheduled {days_text} on **{date_str}**.\n\n"
                f"• **Venue**: {venue}\n"
                f"• **Expected Attendance**: {attendance} attendees\n"
                f"• **Budget Allocated**: ₹{budget:,.2f}\n"
                f"• **Active Tasks**: {total_tasks} operations tasks\n"
                f"• **Description**: {next_ev.get('description', '')}"
            )
            return {
                "status": "COMPLETED",
                "type": "NEXT_EVENT_DETAILS",
                "result": next_ev,
                "message": msg
            }

        if "context" in cmd_lower and "event" in cmd_lower:
            eid_match = re.search(r"event\s+#?(\d+)", cmd_trimmed, re.I)
            eid = int(eid_match.group(1)) if eid_match else active_event_id
            if eid:
                ctx = context_service.get_event_context(db=db, event_id=eid)
                return {
                    "status": "COMPLETED",
                    "type": "EVENT_CONTEXT",
                    "result": ctx,
                    "message": f"Retrieved event context for '{ctx.get('title')}'."
                }

        if "search volunteer" in cmd_lower or "find volunteer" in cmd_lower or "search volunteers" in cmd_lower:
            query = re.sub(r"(?i)(search|find)\s+volunteers?\s*(for|who|with)?", "", cmd_trimmed).strip()
            volunteers = context_service.search_volunteers(db=db, query=query or "python")
            return {
                "status": "COMPLETED",
                "type": "VOLUNTEER_SEARCH",
                "query": query,
                "result": volunteers,
                "message": f"Found {len(volunteers)} matching volunteer(s)."
            }

        if "search task" in cmd_lower or "find task" in cmd_lower or "search tasks" in cmd_lower:
            query = re.sub(r"(?i)(search|find)\s+tasks?\s*(for|about|with)?", "", cmd_trimmed).strip()
            tasks = context_service.search_tasks(db=db, query=query, event_id=active_event_id)
            return {
                "status": "COMPLETED",
                "type": "TASK_SEARCH",
                "query": query,
                "result": tasks,
                "message": f"Found {len(tasks)} matching task(s)."
            }

        # 5. Handle Task Assignment Commands (AI Proposal Lifecycle)
        assignment_result = _handle_assignment_command(
            db=db,
            command=cmd_trimmed,
            event_id=active_event_id,
            user_id=user_id,
            auto_confirm=auto_confirm
        )
        if assignment_result:
            return assignment_result

        # 6. Handle Planning / Event Generation Commands (AI Proposal Lifecycle)
        planning_result = _handle_planning_command(
            db=db,
            command=cmd_trimmed,
            event_id=active_event_id,
            user_id=user_id,
            auto_confirm=auto_confirm
        )
        if planning_result:
            return planning_result

        # 7. Fallback to LangGraph Agent Supervisor
        try:
            from ai.workflows.ai_controller import run_ai_command
            agent_result = run_ai_command(
                user_id=user_id or 1,
                command=cmd_trimmed,
                active_event_id=active_event_id,
                thread_id=thread_id,
                club_id=club_id
            )
            return {
                "status": "COMPLETED",
                "type": "AGENT_RESPONSE",
                "result": agent_result,
                "message": agent_result.get("response", "Command processed."),
                "thread_id": agent_result.get("thread_id"),
                "active_event_name": agent_result.get("active_event_name")
            }

        except Exception as e:
            logger.warning(f"Agent execution error: {e}")
            return {
                "status": "PROCESSED",
                "command": cmd_trimmed,
                "message": f"Command received and interpreted: '{cmd_trimmed}'. No state changes required."
            }
    finally:
        db.close()
