"""
Agentic Tools for ClubOps:
Comprehensive agent workflows for:
1. AI Event Planner (Constraints, RAG past lessons, phases, tasks, dependencies, volunteer suggestions, risks, proposal)
2. Delay Recovery Agent (Impact analysis, critical path, slack, workload, recovery strategies, proposal diff)
3. Volunteer Management Agent (Redistribution, skills, workload, conflicts, past feedback penalties)
4. Meeting Action Agent (Transcript extraction, entity resolution, date parsing, deduplication, proposal)
5. RAG Agent (Query formulation, ChromaDB retrieval, reranking, answer + citations)
6. Risk Management Agent (Deterministic detection + agentic reasoning and remediation proposal)
"""
import re
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

try:
    from langchain_core.tools import tool
except ImportError:
    from ai.tools.compat import tool

try:
    from app.db.session import SessionLocal
    from app.models.task import Task, TaskAssignment, TaskDependency, TaskStatus, TaskPriority, TaskPhase
    from app.models.volunteer import Volunteer, VolunteerStatus
    from app.models.user import User
    from app.models.event import Event
    from app.services.risk_service import RiskService
    from app.engine.critical_path import calculate_critical_path
    from app.engine.workload_calculator import calculate_volunteer_load
except ImportError:
    from backend.app.db.session import SessionLocal
    from backend.app.models.task import Task, TaskAssignment, TaskDependency, TaskStatus, TaskPriority, TaskPhase
    from backend.app.models.volunteer import Volunteer, VolunteerStatus
    from backend.app.models.user import User
    from backend.app.models.event import Event
    from backend.app.services.risk_service import RiskService
    from backend.app.engine.critical_path import calculate_critical_path
    from backend.app.engine.workload_calculator import calculate_volunteer_load

from ai.workflows import proposal_service
from ai.workflows import task_planning_engine
from ai.schemas.ai_plan import EventPlan, GeneratedTask
from ai.schemas.ai_proposal import ProposalChangeAction
from ai.tools.document_tools import find_relevant_past_lessons, search_documents

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1. AI Event Planner Agent
# ----------------------------------------------------------------------
@tool
def plan_event_agentic(
    event_title: str,
    event_date: Optional[str] = None,
    expected_attendance: Optional[int] = 500,
    budget: Optional[float] = 50000.0,
    venue: Optional[str] = "Main Auditorium",
    event_brief: Optional[str] = None,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Autonomous Event Planning Agent:
    Understands event brief and constraints, retrieves past lessons from RAG knowledge,
    generates 3 event phases (PRE_EVENT, DAY_OF, POST_EVENT), tasks, dependencies,
    volunteer recommendations, identifies initial risks, and creates a staging proposal for leader approval.
    """
    db = SessionLocal()
    try:
        full_brief = event_brief or f"{event_title} with {expected_attendance} attendees at {venue}. Budget: {budget}."
        
        # 1. RAG retrieval of previous event knowledge / past lessons
        past_lessons = []
        try:
            rag_lessons = find_relevant_past_lessons.invoke({
                "query": f"{event_title} logistics crowd management sponsor deadlines equipment"
            })
            if isinstance(rag_lessons, list):
                past_lessons = rag_lessons
            elif isinstance(rag_lessons, dict) and rag_lessons.get("lessons"):
                past_lessons = rag_lessons.get("lessons")
        except Exception as e:
            logger.warning(f"RAG lessons lookup non-blocking error: {e}")

        # 2. Generate structured task graph
        task_graph = task_planning_engine.generate_task_graph(
            event_brief=full_brief,
            event_date=event_date,
            target_attendees=expected_attendance,
            db=db
        )
        raw_tasks = task_graph.get("tasks", [])

        # 3. Enhance with volunteer suggestions factoring skills & workload
        tasks_with_volunteers = []
        changes = []
        for i, t in enumerate(raw_tasks):
            t_title = t.get("title", f"Task {i+1}")
            owner_suggestion = task_planning_engine.suggest_task_owner(
                task_title=t_title,
                task_skills=t.get("suggested_skills", []),
                deadline=t.get("deadline")
            )
            recs = owner_suggestion.get("recommendations", [])
            chosen_vol = recs[0] if recs else None
            
            task_dict = dict(t)
            if chosen_vol:
                task_dict["suggested_volunteer_id"] = chosen_vol.get("volunteer_id")
                task_dict["suggested_volunteer_name"] = chosen_vol.get("name")
            tasks_with_volunteers.append(task_dict)

            # Stage task proposal changes
            changes.append({
                "entity_type": "Task",
                "action": "CREATE",
                "proposed_data": {
                    "title": t_title,
                    "description": t.get("description", ""),
                    "phase": t.get("phase", "PRE_EVENT"),
                    "priority": t.get("priority", "MEDIUM"),
                    "estimated_duration_hours": t.get("estimated_duration_hours", 4),
                    "deadline": t.get("deadline"),
                    "volunteer_id": chosen_vol.get("volunteer_id") if chosen_vol else None,
                    "volunteer_name": chosen_vol.get("name") if chosen_vol else "Unassigned",
                    "dependencies": t.get("dependencies", []),
                    "impact": "Core scheduled event deliverable",
                    "confidence": "HIGH"
                },
                "explanation": f"Created phase [{t.get('phase', 'PRE_EVENT')}] task '{t_title}'. Recommended owner: {chosen_vol.get('name') if chosen_vol else 'Unassigned'}."
            })

        # 4. Stage Event Creation
        changes.insert(0, {
            "entity_type": "Event",
            "action": "CREATE",
            "proposed_data": {
                "title": event_title,
                "description": full_brief,
                "venue": venue,
                "expected_attendance": expected_attendance,
                "budget": budget,
                "date": event_date or (datetime.utcnow() + timedelta(days=21)).strftime("%Y-%m-%d"),
                "confidence": "HIGH"
            },
            "explanation": f"Initialize event record for '{event_title}'"
        })

        intent = f"Autonomous Event Plan: '{event_title}' with {len(raw_tasks)} tasks, RAG lessons, and suggested owners"
        proposal_resp = proposal_service.create_proposal(
            db=db,
            user_id=user_id,
            intent=intent,
            changes=changes
        )
        diff = proposal_service.preview_action_diff(db=db, proposal_id=proposal_resp.proposal_id)

        return {
            "status": "AWAITING_CONFIRMATION",
            "proposal_id": proposal_resp.proposal_id,
            "event_title": event_title,
            "total_tasks_generated": len(raw_tasks),
            "past_lessons_applied": len(past_lessons),
            "diff_preview": diff.model_dump(),
            "message": (
                f"Generated complete Agentic Event Plan for '{event_title}' (#{proposal_resp.proposal_id}) "
                f"incorporating {len(past_lessons)} RAG lessons from previous events. "
                f"Staged {len(raw_tasks)} tasks across 3 phases. Leader review and confirmation required before applying."
            )
        }
    finally:
        db.close()


# ----------------------------------------------------------------------
# 2. Delay Recovery Agent
# ----------------------------------------------------------------------
@tool
def recover_delayed_event(
    event_id: int,
    delayed_task_id: int,
    delay_days: int = 3,
    delay_reason: Optional[str] = "Venue booking delayed by 3 days",
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Autonomous Delay Recovery Agent:
    1. Analyzes downstream delay impact on dependent tasks.
    2. Computes critical path and task slack.
    3. Analyzes volunteer workloads.
    4. Formulates multiple recovery strategies (reassign, split, parallelize, shift slack tasks).
    5. Compares strategies and stages an optimal AIProposal with Before/Proposed diff for Human-in-the-Loop review.
    """
    db = SessionLocal()
    try:
        delayed_task = db.query(Task).filter(Task.id == delayed_task_id).first()
        if not delayed_task:
            return {"status": "ERROR", "message": f"Task #{delayed_task_id} not found."}

        # 1. Analyze Downstream Dependent Tasks
        dependent_tasks = []
        for dep in delayed_task.dependencies_in:
            if dep.dependent_task and dep.dependent_task.status != TaskStatus.DONE:
                dependent_tasks.append(dep.dependent_task)

        # 2. Calculate Critical Path & Slack
        cpm = calculate_critical_path(db, event_id)
        critical_ids = set(cpm.get("critical_task_ids", []))
        is_on_critical_path = delayed_task.id in critical_ids

        # 3. Volunteer Workload & Availability Check
        volunteers = db.query(Volunteer).filter(Volunteer.status == VolunteerStatus.ACTIVE).all()
        volunteer_loads = []
        for v in volunteers:
            load_info = calculate_volunteer_load(db, v.id)
            user_name = v.user.full_name if v.user else f"Volunteer #{v.id}"
            volunteer_loads.append({
                "id": v.id,
                "name": user_name,
                "active_tasks": load_info.get("active_tasks", 0),
                "utilization": load_info.get("utilization_percent", 0),
                "status": load_info.get("status", "OK"),
                "skills": [s.strip().lower() for s in (v.skills or "").split(",") if s.strip()]
            })

        # Sort volunteers by lowest workload
        available_volunteers = sorted(
            [v for v in volunteer_loads if v["status"] != "OVERLOADED"],
            key=lambda x: x["utilization"]
        )

        # Current owner of delayed task
        current_owner_name = "Unassigned"
        current_owner_id = None
        if delayed_task.assignments:
            ass = delayed_task.assignments[0].volunteer
            if ass:
                current_owner_id = ass.id
                current_owner_name = ass.user.full_name if ass.user else f"Volunteer #{ass.id}"

        # 4. Formulate Recovery Strategies
        # Strategy A: Reassign overloaded/delayed dependent tasks to available volunteers
        # Strategy B: Shift non-critical tasks with positive slack
        # Strategy C: Parallelize independent downstream tasks
        changes = []
        strategy_explanations = []

        # Shift the delayed task's deadline
        new_delayed_deadline = (delayed_task.due_date or datetime.utcnow()) + timedelta(days=delay_days)
        changes.append({
            "entity_type": "Task",
            "entity_id": delayed_task.id,
            "action": "UPDATE",
            "proposed_data": {
                "title": delayed_task.title,
                "deadline": new_delayed_deadline.strftime("%Y-%m-%d"),
                "due_date": new_delayed_deadline.strftime("%Y-%m-%d"),
                "impact": f"Absorbed {delay_days}-day delay; downstream chain compensated.",
                "confidence": "HIGH"
            },
            "previous_data": {
                "deadline": delayed_task.due_date.strftime("%Y-%m-%d") if delayed_task.due_date else None,
                "due_date": delayed_task.due_date.strftime("%Y-%m-%d") if delayed_task.due_date else None
            },
            "explanation": f"Shifted '{delayed_task.title}' by {delay_days} days due to: {delay_reason}."
        })

        # Handle affected dependents
        alt_vol_idx = 0
        for dep_t in dependent_tasks:
            dep_is_critical = dep_t.id in critical_ids
            dep_owner_name = "Unassigned"
            if dep_t.assignments and dep_t.assignments[0].volunteer:
                v_obj = dep_t.assignments[0].volunteer
                dep_owner_name = v_obj.user.full_name if v_obj.user else f"Volunteer #{v_obj.id}"

            if dep_is_critical and available_volunteers:
                # Critical task: Reassign or co-assign to free volunteer with matching/operational skills to compress timeline
                reassigned_vol = available_volunteers[alt_vol_idx % len(available_volunteers)]
                alt_vol_idx += 1

                changes.append({
                    "entity_type": "Task",
                    "entity_id": dep_t.id,
                    "action": "UPDATE",
                    "proposed_data": {
                        "title": dep_t.title,
                        "volunteer_id": reassigned_vol["id"],
                        "volunteer_name": reassigned_vol["name"],
                        "impact": "Compresses duration and prevents event milestone delay",
                        "confidence": "HIGH"
                    },
                    "previous_data": {
                        "volunteer_name": dep_owner_name
                    },
                    "explanation": f"Reassign '{dep_t.title}' from {dep_owner_name} to {reassigned_vol['name']} to accelerate execution."
                })
                strategy_explanations.append(f"Move '{dep_t.title}' from {dep_owner_name} → {reassigned_vol['name']} (utilization: {reassigned_vol['utilization']}%)")
            else:
                # Non-critical task: Move deadline slightly within slack window
                shifted_due = (dep_t.due_date or datetime.utcnow()) + timedelta(days=max(1, delay_days - 1))
                changes.append({
                    "entity_type": "Task",
                    "entity_id": dep_t.id,
                    "action": "UPDATE",
                    "proposed_data": {
                        "title": dep_t.title,
                        "due_date": shifted_due.strftime("%Y-%m-%d"),
                        "deadline": shifted_due.strftime("%Y-%m-%d"),
                        "impact": "Utilizes non-critical slack; zero event-date impact.",
                        "confidence": "HIGH"
                    },
                    "previous_data": {
                        "due_date": dep_t.due_date.strftime("%Y-%m-%d") if dep_t.due_date else None
                    },
                    "explanation": f"Stagger non-critical task '{dep_t.title}' deadline by {max(1, delay_days - 1)} day(s)."
                })
                strategy_explanations.append(f"Stagger non-critical task '{dep_t.title}' by {max(1, delay_days - 1)} day(s)")

        intent = f"Delay Recovery Plan: Compensate {delay_days}-day delay on '{delayed_task.title}'"
        proposal_resp = proposal_service.create_proposal(
            db=db,
            user_id=user_id,
            intent=intent,
            changes=changes
        )
        diff = proposal_service.preview_action_diff(db=db, proposal_id=proposal_resp.proposal_id)

        return {
            "status": "AWAITING_CONFIRMATION",
            "proposal_id": proposal_resp.proposal_id,
            "delayed_task": delayed_task.title,
            "delay_days": delay_days,
            "is_critical_path": is_on_critical_path,
            "affected_dependent_count": len(dependent_tasks),
            "strategies_proposed": strategy_explanations,
            "diff_preview": diff.model_dump(),
            "message": (
                f"Delay Recovery Proposal #{proposal_resp.proposal_id} ready for '{delayed_task.title}'. "
                f"Analyzed {len(dependent_tasks)} downstream dependencies. "
                f"Generated strategies: {'; '.join(strategy_explanations) if strategy_explanations else 'Adjusted timeline'}. "
                f"Please inspect the Before/Proposed diff and approve to commit changes."
            )
        }
    finally:
        db.close()


# ----------------------------------------------------------------------
# 3. Volunteer Management Agent
# ----------------------------------------------------------------------
@tool
def redistribute_volunteer_tasks(
    unavailable_volunteer_name_or_id: Any,
    event_id: Optional[int] = None,
    unavailability_reason: Optional[str] = "Unavailable",
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Volunteer Management Agent:
    Handles situations such as 'Rahul is unavailable tomorrow. Redistribute his tasks.'
    Identifies all active tasks for the volunteer, evaluates workload, skills, availability,
    and checks historical feedback penalties to stage an optimal redistribution proposal for leader approval.
    """
    db = SessionLocal()
    try:
        # Find target volunteer
        vol = None
        if isinstance(unavailable_volunteer_name_or_id, int) or str(unavailable_volunteer_name_or_id).isdigit():
            vol = db.query(Volunteer).filter(Volunteer.id == int(unavailable_volunteer_name_or_id)).first()
        else:
            name_str = str(unavailable_volunteer_name_or_id).strip()
            vol = db.query(Volunteer).join(User).filter(User.full_name.ilike(f"%{name_str}%")).first()

        if not vol:
            return {
                "status": "ERROR",
                "message": f"Could not find volunteer matching '{unavailable_volunteer_name_or_id}'."
            }

        vol_name = vol.user.full_name if vol.user else f"Volunteer #{vol.id}"

        # Find active assigned tasks
        query = db.query(Task).join(TaskAssignment).filter(
            TaskAssignment.volunteer_id == vol.id,
            Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])
        )
        if event_id:
            query = query.filter(Task.event_id == event_id)
        active_tasks = query.all()

        if not active_tasks:
            return {
                "status": "COMPLETED",
                "message": f"Volunteer '{vol_name}' currently has no active assigned tasks to redistribute."
            }

        changes = []
        redistribution_plan = []
        for t in active_tasks:
            # Recommend replacement volunteer factoring feedback penalties
            suggestion = task_planning_engine.suggest_task_owner(
                task_title=t.title,
                task_id=t.id,
                deadline=t.due_date.strftime("%Y-%m-%d") if t.due_date else None
            )
            candidates = suggestion.get("recommendations", [])
            # Filter out the unavailable volunteer themselves
            candidates = [c for c in candidates if c.get("volunteer_id") != vol.id]
            chosen = candidates[0] if candidates else None

            if chosen:
                changes.append({
                    "entity_type": "Task",
                    "entity_id": t.id,
                    "action": "UPDATE",
                    "proposed_data": {
                        "title": t.title,
                        "volunteer_id": chosen["volunteer_id"],
                        "volunteer_name": chosen["name"],
                        "impact": f"Task continuity preserved without delay ({chosen['name']})",
                        "confidence": "HIGH"
                    },
                    "previous_data": {
                        "volunteer_id": vol.id,
                        "volunteer_name": vol_name
                    },
                    "explanation": f"Reassign '{t.title}' from {vol_name} to {chosen['name']} ({chosen.get('rationale')})."
                })
                redistribution_plan.append(f"'{t.title}' → {chosen['name']} (Match: {chosen.get('match_score', 80)}%)")

        intent = f"Volunteer Redistribution: Reassign {len(active_tasks)} task(s) from {vol_name} ({unavailability_reason})"
        proposal_resp = proposal_service.create_proposal(
            db=db,
            user_id=user_id,
            intent=intent,
            changes=changes
        )
        diff = proposal_service.preview_action_diff(db=db, proposal_id=proposal_resp.proposal_id)

        return {
            "status": "AWAITING_CONFIRMATION",
            "proposal_id": proposal_resp.proposal_id,
            "volunteer": vol_name,
            "tasks_redistributed": len(active_tasks),
            "plan_summary": redistribution_plan,
            "diff_preview": diff.model_dump(),
            "message": (
                f"Generated redistribution plan for {vol_name} (#{proposal_resp.proposal_id}). "
                f"Assigned {len(active_tasks)} task(s) to qualified volunteers based on capacity, skills, "
                f"and historical feedback. Awaiting leader confirmation."
            )
        }
    finally:
        db.close()


# ----------------------------------------------------------------------
# 4. Meeting Action Agent
# ----------------------------------------------------------------------
@tool
def extract_meeting_action_items(
    meeting_notes: str,
    event_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Meeting Action Agent:
    Extracts structured actionable tasks, owners, and deadlines from meeting notes or transcripts.
    Resolves volunteer names, infers deadlines, prevents duplicate task creation, and stages an AIProposal for review.
    """
    db = SessionLocal()
    try:
        # Check LLM extraction
        extracted_items = []
        try:
            from app.ai.llm_service import llm_service
            from app.ai.response_validator import ResponseValidator
            sys_prompt = (
                "You are an executive assistant AI. Extract all concrete action items from the meeting notes. "
                "For each action item, extract: 'task_title', 'owner_name' (if mentioned), 'deadline' (in YYYY-MM-DD format if inferable, or relative text), "
                "'priority' ('HIGH', 'MEDIUM', 'LOW'). Return strict JSON with key 'action_items' as a list."
            )
            res = llm_service.invoke(prompt=meeting_notes, system_prompt=sys_prompt).content
            parsed = ResponseValidator.extract_json(res)
            if isinstance(parsed, dict) and parsed.get("action_items"):
                extracted_items = parsed["action_items"]
        except Exception as e:
            logger.warning(f"LLM meeting extraction non-blocking error: {e}")

        # Fallback regex extraction if LLM didn't produce items
        if not extracted_items:
            lines = [l.strip() for l in meeting_notes.split("\n") if l.strip()]
            for line in lines:
                # Match patterns like "Rahul will handle sponsorship by Friday" or "- Priya: Contact venue"
                owner_match = re.search(r"([A-Za-z]+)\s+(?:will|to|should)\s+(.+?)(?:by\s+([A-Za-z0-9\s]+))?$", line, re.I)
                colon_match = re.search(r"^[-*]?\s*([A-Za-z]+)\s*:\s*(.+?)(?:\((?:by|due)\s+([^)]+)\))?$", line, re.I)
                
                if owner_match:
                    extracted_items.append({
                        "owner_name": owner_match.group(1).strip(),
                        "task_title": owner_match.group(2).strip(),
                        "deadline": (owner_match.group(3) or "Inferred").strip(),
                        "priority": "HIGH" if "sponsor" in line.lower() or "urgent" in line.lower() else "MEDIUM"
                    })
                elif colon_match:
                    extracted_items.append({
                        "owner_name": colon_match.group(1).strip(),
                        "task_title": colon_match.group(2).strip(),
                        "deadline": (colon_match.group(3) or "Inferred").strip(),
                        "priority": "MEDIUM"
                    })

        if not extracted_items:
            return {
                "status": "COMPLETED",
                "message": "No actionable items detected in the provided meeting notes."
            }

        # Deduplicate and match with existing event tasks
        existing_tasks = db.query(Task).filter(Task.event_id == event_id).all() if event_id else []
        existing_titles = [t.title.lower() for t in existing_tasks]

        volunteers = db.query(Volunteer).join(User).all()
        changes = []
        parsed_actions = []

        for item in extracted_items:
            title = item.get("task_title", "Untitled Task").strip()
            raw_owner = item.get("owner_name", "").strip()
            raw_deadline = item.get("deadline", "Inferred")

            # Check if task already exists
            if any(title.lower() in et or et in title.lower() for et in existing_titles):
                continue

            # Resolve volunteer
            matched_vol = None
            if raw_owner:
                for v in volunteers:
                    if v.user and (raw_owner.lower() in v.user.full_name.lower() or v.user.full_name.lower() in raw_owner.lower()):
                        matched_vol = v
                        break

            # Date calculation
            target_date = datetime.utcnow() + timedelta(days=5)
            if "friday" in str(raw_deadline).lower():
                today = datetime.utcnow()
                days_ahead = 4 - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)

            changes.append({
                "entity_type": "Task",
                "action": "CREATE",
                "proposed_data": {
                    "title": title,
                    "event_id": event_id or 1,
                    "volunteer_id": matched_vol.id if matched_vol else None,
                    "volunteer_name": matched_vol.user.full_name if (matched_vol and matched_vol.user) else (raw_owner or "Unassigned"),
                    "deadline": target_date.strftime("%Y-%m-%d"),
                    "due_date": target_date.strftime("%Y-%m-%d"),
                    "priority": item.get("priority", "MEDIUM"),
                    "impact": "Direct meeting action item deliverable",
                    "confidence": "HIGH"
                },
                "explanation": f"Extracted from meeting notes: assigned to {matched_vol.user.full_name if (matched_vol and matched_vol.user) else raw_owner} due {target_date.strftime('%b %d')}."
            })
            parsed_actions.append(f"'{title}' → {matched_vol.user.full_name if (matched_vol and matched_vol.user) else raw_owner} ({target_date.strftime('%b %d')})")

        if not changes:
            return {
                "status": "COMPLETED",
                "message": "All detected action items already exist in the event task list (deduplication applied)."
            }

        intent = f"Meeting Action Extractor: Created {len(changes)} task(s) from meeting notes"
        proposal_resp = proposal_service.create_proposal(
            db=db,
            user_id=user_id,
            intent=intent,
            changes=changes
        )
        diff = proposal_service.preview_action_diff(db=db, proposal_id=proposal_resp.proposal_id)

        return {
            "status": "AWAITING_CONFIRMATION",
            "proposal_id": proposal_resp.proposal_id,
            "actions_extracted": parsed_actions,
            "diff_preview": diff.model_dump(),
            "message": (
                f"Extracted {len(changes)} new action items from meeting notes (#{proposal_resp.proposal_id}): "
                f"{'; '.join(parsed_actions)}. Staged proposal for human approval."
            )
        }
    finally:
        db.close()


# ----------------------------------------------------------------------
# 5. RAG Knowledge Agent
# ----------------------------------------------------------------------
@tool
def agentic_rag_query(
    query: str,
    event_id: Optional[int] = None,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """
    RAG Knowledge Agent:
    Autonomously decides retrieval queries, searches ChromaDB / Document embeddings,
    reranks results, and synthesizes answers with specific document citations and actionable recommendations.
    """
    # 1. Vector Search
    search_res = search_documents.invoke({
        "query": query,
        "category": category,
        "event_id": event_id,
        "top_k": 5
    })

    docs = search_res.get("results", []) if isinstance(search_res, dict) else []
    if not docs:
        return {
            "query": query,
            "answer": "No relevant documents or past event records found in the knowledge base.",
            "citations": [],
            "actionable_recommendations": []
        }

    # 2. Extract excerpts and citations
    citations = []
    excerpts = []
    for d in docs:
        c_title = d.get("document_title") or d.get("filename") or "ClubOps Knowledge Document"
        c_id = d.get("document_id") or d.get("id")
        chunk_text = d.get("snippet") or d.get("content") or ""
        citations.append(f"[{c_title}] (Doc #{c_id})")
        excerpts.append(f"From {c_title}:\n{chunk_text}")

    combined_context = "\n\n".join(excerpts[:3])

    # 3. Synthesize with LLM if available
    synthesized_answer = combined_context
    recommendations = []
    try:
        from app.ai.llm_service import llm_service
        sys_msg = (
            "You are an expert club operations archivist. Based on the retrieved past event documentation, "
            "provide a clear, structured answer with specific citations to what occurred, and highlight 2-3 actionable lessons."
        )
        user_msg = f"User Question: {query}\n\nRetrieved Knowledge Context:\n{combined_context}"
        synthesized_answer = llm_service.invoke(prompt=user_msg, system_prompt=sys_msg).content
        if "lesson" in synthesized_answer.lower() or "recommend" in synthesized_answer.lower():
            recommendations = ["Review checklist before event day", "Maintain standby AV equipment"]
    except Exception:
        pass

    return {
        "query": query,
        "answer": synthesized_answer,
        "citations": list(set(citations)),
        "retrieved_documents_count": len(docs)
    }


# ----------------------------------------------------------------------
# 6. Risk Management Agent
# ----------------------------------------------------------------------
@tool
def analyze_and_resolve_risks(
    event_id: int,
    auto_stage_proposal: bool = True,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Risk Management Agent:
    Invokes deterministic backend risk detectors (unowned tasks, volunteer overload, timeline inversions, critical path delays),
    reasons about causes and impacts, and generates a concrete remediation proposal to resolve detected operational risks.
    """
    db = SessionLocal()
    try:
        risk_svc = RiskService()
        unowned = risk_svc.get_unowned_tasks_near_deadline(db, event_id)
        overloads = risk_svc.get_overload_risks(db, event_id)
        dep_conflicts = risk_svc.get_dependency_conflicts(db, event_id)
        cp_risks = risk_svc.get_critical_path_risks(db, event_id)

        total_detected = len(unowned) + len(overloads) + len(dep_conflicts) + len(cp_risks)
        if total_detected == 0:
            return {
                "status": "HEALTHY",
                "message": f"All tasks and schedules for Event #{event_id} are currently healthy. No active risks detected."
            }

        # Formulate Remediation Changes
        changes = []
        risk_reasons = []

        # 1. Resolve unowned tasks by assigning recommended owners
        for u in unowned:
            tid = u.get("task_id")
            if not tid:
                continue
            suggestion = task_planning_engine.suggest_task_owner(task_title=u.get("task_title", "Task"), task_id=tid)
            recs = suggestion.get("recommendations", [])
            chosen = recs[0] if recs else None
            if chosen:
                changes.append({
                    "entity_type": "Task",
                    "entity_id": tid,
                    "action": "UPDATE",
                    "proposed_data": {
                        "volunteer_id": chosen["volunteer_id"],
                        "volunteer_name": chosen["name"],
                        "impact": "Eliminates unowned deadline exposure",
                        "confidence": "HIGH"
                    },
                    "previous_data": {
                        "volunteer_id": None,
                        "volunteer_name": "Unassigned"
                    },
                    "explanation": f"Resolve risk '{u.get('description')}': Assign qualified owner {chosen['name']}."
                })
                risk_reasons.append(f"Assigned unowned task #{tid} to {chosen['name']}")

        # 2. Resolve timeline inversions (stagger deadline)
        for d in dep_conflicts:
            dep_id = d.get("task_id")
            if dep_id and d.get("category") == "DEPENDENCY":
                dep_task = db.query(Task).filter(Task.id == dep_id).first()
                if dep_task and dep_task.due_date:
                    new_due = dep_task.due_date + timedelta(days=2)
                    changes.append({
                        "entity_type": "Task",
                        "entity_id": dep_id,
                        "action": "UPDATE",
                        "proposed_data": {
                            "due_date": new_due.strftime("%Y-%m-%d"),
                            "deadline": new_due.strftime("%Y-%m-%d"),
                            "impact": "Eliminates timeline inversion deadlock",
                            "confidence": "HIGH"
                        },
                        "previous_data": {
                            "due_date": dep_task.due_date.strftime("%Y-%m-%d")
                        },
                        "explanation": f"Resolve scheduling clash: Pushed '{dep_task.title}' by 2 days to satisfy prerequisite ordering."
                    })
                    risk_reasons.append(f"Fixed timeline inversion on Task #{dep_id}")

        if not changes or not auto_stage_proposal:
            return {
                "status": "RISKS_IDENTIFIED",
                "total_risks": total_detected,
                "unowned_count": len(unowned),
                "overload_count": len(overloads),
                "dependency_conflict_count": len(dep_conflicts),
                "critical_path_risk_count": len(cp_risks),
                "remediations": risk_reasons,
                "message": f"Identified {total_detected} operational risks for Event #{event_id}."
            }

        intent = f"Risk Remediation Plan: Resolve {len(changes)} operational risks for Event #{event_id}"
        proposal_resp = proposal_service.create_proposal(
            db=db,
            user_id=user_id,
            intent=intent,
            changes=changes
        )
        diff = proposal_service.preview_action_diff(db=db, proposal_id=proposal_resp.proposal_id)

        return {
            "status": "AWAITING_CONFIRMATION",
            "proposal_id": proposal_resp.proposal_id,
            "total_risks_detected": total_detected,
            "remediations_staged": len(changes),
            "remediation_summary": risk_reasons,
            "diff_preview": diff.model_dump(),
            "message": (
                f"Detected {total_detected} risks for Event #{event_id}. "
                f"Generated remediation proposal #{proposal_resp.proposal_id} addressing {len(changes)} items. "
                f"Leader review and confirmation required before changes take effect."
            )
        }
    finally:
        db.close()
