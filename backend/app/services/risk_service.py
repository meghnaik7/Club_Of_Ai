from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.risk import EventRisk
from app.models.event import Event, EventStatus
from app.models.task import Task, TaskStatus, TaskPriority, TaskPhase, TaskAssignment, TaskDependency
from app.models.volunteer import Volunteer, VolunteerStatus
from app.schemas.risk import (
    RiskCreate,
    RiskUpdate,
    RiskRead,
    RiskFixSuggestion,
    RiskExplanation,
    EventRiskSummary
)
from app.engine.workload_calculator import calculate_volunteer_load
from app.engine.critical_path import calculate_critical_path


class RiskService:
    def get_risk(self, db: Session, risk_id: int) -> Optional[EventRisk]:
        return db.query(EventRisk).filter(EventRisk.id == risk_id).first()

    def list_risks(
        self,
        db: Session,
        event_id: int,
        status: Optional[str] = "ACTIVE",
        category: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[EventRisk]:
        query = db.query(EventRisk).filter(EventRisk.event_id == event_id)
        if status:
            query = query.filter(EventRisk.status == status)
        if category:
            query = query.filter(EventRisk.category == category)
        if severity:
            query = query.filter(EventRisk.severity == severity)
        return query.order_by(EventRisk.created_at.desc()).all()

    def resolve_risk(
        self,
        db: Session,
        risk_id: int,
        resolution_notes: Optional[str] = None,
        resolved_by: Optional[str] = "AI Assistant"
    ) -> EventRisk:
        risk = self.get_risk(db, risk_id)
        if not risk:
            raise ValueError(f"Risk with ID {risk_id} not found")

        risk.status = "RESOLVED"
        risk.resolved_at = datetime.utcnow()
        risk.resolved_by = resolved_by
        risk.resolution_notes = resolution_notes or "Marked resolved by operator."
        db.add(risk)
        db.commit()
        db.refresh(risk)
        return risk

    # ---------------------------------------------------------
    # 1. Specialized Detector: Unowned Tasks Near Deadline
    # ---------------------------------------------------------
    def get_unowned_tasks_near_deadline(
        self,
        db: Session,
        event_id: int,
        days_threshold: int = 7
    ) -> List[Dict[str, Any]]:
        now = datetime.utcnow()
        threshold_date = now + timedelta(days=days_threshold)

        tasks = db.query(Task).filter(
            Task.event_id == event_id,
            Task.status != TaskStatus.DONE
        ).all()

        results = []
        for t in tasks:
            if len(t.assignments) == 0:
                is_overdue = t.due_date and t.due_date < now
                is_near = t.due_date and t.due_date <= threshold_date

                if is_overdue or is_near or t.due_date is None:
                    days_left = (t.due_date - now).days if t.due_date else None
                    if is_overdue:
                        severity = "CRITICAL"
                        desc = f"Task '{t.title}' is OVERDUE by {abs(days_left)} days with no assigned volunteer!"
                    elif days_left is not None and days_left <= 2:
                        severity = "CRITICAL"
                        desc = f"Task '{t.title}' is due in {days_left} day(s) but has no assigned volunteer."
                    elif days_left is not None and days_left <= 5:
                        severity = "HIGH"
                        desc = f"Task '{t.title}' is approaching deadline ({days_left} days left) without an owner."
                    else:
                        severity = "MEDIUM"
                        desc = f"Task '{t.title}' has no owner assigned."

                    results.append({
                        "task_id": t.id,
                        "task_title": t.title,
                        "category": "OWNERSHIP",
                        "severity": severity,
                        "due_date": t.due_date.isoformat() if t.due_date else None,
                        "days_left": days_left,
                        "description": desc,
                        "root_cause": "Task was created without volunteer assignment and deadline is approaching.",
                        "suggested_fix": f"Assign a volunteer with relevant skills immediately using suggest_task_owner({t.id})."
                    })
        return results

    # ---------------------------------------------------------
    # 2. Specialized Detector: Workload & Overload Risks
    # ---------------------------------------------------------
    def get_overload_risks(self, db: Session, event_id: int) -> List[Dict[str, Any]]:
        tasks = db.query(Task).filter(
            Task.event_id == event_id,
            Task.status != TaskStatus.DONE
        ).all()

        volunteer_ids = set()
        for t in tasks:
            for a in t.assignments:
                volunteer_ids.add(a.volunteer_id)

        overload_risks = []
        for vid in volunteer_ids:
            load = calculate_volunteer_load(db, vid)
            vol = db.query(Volunteer).filter(Volunteer.id == vid).first()
            vol_name = vol.user.full_name if vol and vol.user else f"Volunteer #{vid}"

            # Check utilization
            if load.get("status") == "OVERLOADED" or load.get("utilization_percent", 0) > 100:
                overload_risks.append({
                    "volunteer_id": vid,
                    "volunteer_name": vol_name,
                    "category": "WORKLOAD",
                    "severity": "HIGH",
                    "active_tasks": load.get("active_tasks", 0),
                    "capacity_hours": load.get("capacity_hours", 10),
                    "utilization_percent": load.get("utilization_percent", 0),
                    "description": f"Volunteer '{vol_name}' is overloaded at {load.get('utilization_percent')}% capacity with {load.get('active_tasks')} active tasks.",
                    "root_cause": "Assigned task volume exceeds configured volunteer max capacity.",
                    "suggested_fix": f"Reassign one or more tasks from '{vol_name}' to another volunteer using bulk_reassign_tasks."
                })

            # Check deadline collision (multiple tasks due on the exact same date)
            assigned_tasks = [t for t in tasks if any(a.volunteer_id == vid for a in t.assignments)]
            date_counts: Dict[str, List[int]] = {}
            for at in assigned_tasks:
                if at.due_date:
                    d_str = at.due_date.strftime("%Y-%m-%d")
                    date_counts.setdefault(d_str, []).append(at.id)

            for d_str, t_ids in date_counts.items():
                if len(t_ids) > 1:
                    overload_risks.append({
                        "volunteer_id": vid,
                        "volunteer_name": vol_name,
                        "category": "WORKLOAD",
                        "severity": "MEDIUM",
                        "colliding_task_ids": t_ids,
                        "due_date": d_str,
                        "description": f"Volunteer '{vol_name}' has {len(t_ids)} tasks due on the exact same day ({d_str}).",
                        "root_cause": "Multiple deadlines scheduled for the same volunteer on identical date.",
                        "suggested_fix": "Stagger deadlines by at least 24-48 hours or share task assignments with a co-owner."
                    })

        return overload_risks

    # ---------------------------------------------------------
    # 3. Specialized Detector: Dependency Conflicts & Inversions
    # ---------------------------------------------------------
    def get_dependency_conflicts(self, db: Session, event_id: int) -> List[Dict[str, Any]]:
        tasks = db.query(Task).filter(Task.event_id == event_id).all()
        now = datetime.utcnow()
        conflicts = []

        for t in tasks:
            for dep in t.dependencies_out:
                prereq = dep.prerequisite_task
                if not prereq:
                    continue

                # 1. Timeline Inversion (Prerequisite due AFTER dependent task)
                if prereq.due_date and t.due_date and prereq.due_date > t.due_date:
                    conflicts.append({
                        "task_id": t.id,
                        "task_title": t.title,
                        "prerequisite_task_id": prereq.id,
                        "prerequisite_title": prereq.title,
                        "category": "DEPENDENCY",
                        "severity": "CRITICAL",
                        "description": (
                            f"Timeline Inversion: Prerequisite task '{prereq.title}' is due on "
                            f"{prereq.due_date.strftime('%Y-%m-%d')}, which is AFTER dependent task "
                            f"'{t.title}' due date ({t.due_date.strftime('%Y-%m-%d')})!"
                        ),
                        "root_cause": "Dependent task is scheduled to finish before its prerequisite completes.",
                        "suggested_fix": (
                            f"Reschedule '{t.title}' due date to after {prereq.due_date.strftime('%Y-%m-%d')} "
                            f"or expedite '{prereq.title}'."
                        )
                    })

                # 2. Overdue Prerequisite Blocking Active Dependent
                if prereq.status != TaskStatus.DONE and prereq.due_date and prereq.due_date < now:
                    conflicts.append({
                        "task_id": t.id,
                        "task_title": t.title,
                        "prerequisite_task_id": prereq.id,
                        "prerequisite_title": prereq.title,
                        "category": "DEPENDENCY",
                        "severity": "HIGH",
                        "description": f"Task '{t.title}' is stalled because prerequisite '{prereq.title}' is OVERDUE and incomplete.",
                        "root_cause": "Prerequisite task missed its deadline, directly impacting dependent schedule.",
                        "suggested_fix": f"Focus resources on finishing '{prereq.title}' immediately to unblock '{t.title}'."
                    })

                # 3. Blocked Prerequisite
                if prereq.status == TaskStatus.BLOCKED:
                    conflicts.append({
                        "task_id": t.id,
                        "task_title": t.title,
                        "prerequisite_task_id": prereq.id,
                        "prerequisite_title": prereq.title,
                        "category": "DEPENDENCY",
                        "severity": "HIGH",
                        "description": f"Task '{t.title}' cannot proceed because prerequisite '{prereq.title}' is explicitly BLOCKED.",
                        "root_cause": "Prerequisite task is marked as BLOCKED by team members.",
                        "suggested_fix": f"Investigate blockers on '{prereq.title}' to allow downstream progress."
                    })

        # 4. Check for Cycle / Circular Dependencies
        cpm_result = calculate_critical_path(db, event_id)
        if "error" in cpm_result and "Cycle detected" in cpm_result["error"]:
            conflicts.append({
                "category": "DEPENDENCY",
                "severity": "CRITICAL",
                "description": "Circular Dependency Cycle detected in task dependency graph! Tasks cannot be executed in linear order.",
                "root_cause": "A dependency chain loops back onto an earlier task (e.g. A -> B -> C -> A).",
                "suggested_fix": "Identify the circular link using get_task_dependencies and call remove_task_dependency to break the loop."
            })

        return conflicts

    # ---------------------------------------------------------
    # 3b. Specialized Detector: Critical Path Risks
    # ---------------------------------------------------------
    def get_critical_path_risks(self, db: Session, event_id: int) -> List[Dict[str, Any]]:
        cpm_result = calculate_critical_path(db, event_id)
        if "error" in cpm_result or not cpm_result.get("critical_task_ids"):
            return []

        now = datetime.utcnow()
        critical_task_ids = cpm_result.get("critical_task_ids", [])
        tasks = db.query(Task).filter(Task.id.in_(critical_task_ids)).all()
        task_map = {t.id: t for t in tasks}

        cp_risks = []
        for tid in critical_task_ids:
            t = task_map.get(tid)
            if not t or t.status == TaskStatus.DONE:
                continue

            # Critical path task overdue
            if t.due_date and t.due_date < now:
                days_over = (now - t.due_date).days
                cp_risks.append({
                    "task_id": t.id,
                    "task_title": t.title,
                    "category": "SCHEDULING",
                    "severity": "CRITICAL",
                    "description": f"Critical Path Delay: Task '{t.title}' is on the critical path and is OVERDUE by {days_over} day(s). Any delay directly postpones event completion.",
                    "root_cause": "Task on zero-slack critical chain missed its due date.",
                    "suggested_fix": f"Expedite '{t.title}' with highest priority or reassign extra volunteers to finish it."
                })
            # Critical path task has no owner
            elif len(t.assignments) == 0:
                cp_risks.append({
                    "task_id": t.id,
                    "task_title": t.title,
                    "category": "SCHEDULING",
                    "severity": "HIGH",
                    "description": f"Critical Path Exposure: Task '{t.title}' has no owner assigned despite being on the event critical path.",
                    "root_cause": "Key milestone task on longest sequential dependency chain is currently unassigned.",
                    "suggested_fix": f"Immediately assign a competent owner to critical path task '{t.title}'."
                })
            # Critical path task is blocked
            elif t.status == TaskStatus.BLOCKED:
                cp_risks.append({
                    "task_id": t.id,
                    "task_title": t.title,
                    "category": "SCHEDULING",
                    "severity": "CRITICAL",
                    "description": f"Critical Path Stalled: Task '{t.title}' is marked as BLOCKED on the critical path.",
                    "root_cause": "Zero-slack task is blocked by external dependencies or resources.",
                    "suggested_fix": f"Unblock '{t.title}' immediately to prevent cascading project delays."
                })

        return cp_risks

    # ---------------------------------------------------------
    # 4. Specialized Detector: Missing Activity Risks
    # ---------------------------------------------------------
    def get_missing_activity_risks(self, db: Session, event_id: int) -> List[Dict[str, Any]]:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return []

        tasks = db.query(Task).filter(Task.event_id == event_id).all()
        task_titles_lower = " ".join([t.title.lower() + " " + (t.description or "").lower() for t in tasks])

        missing_risks = []

        # Standard essential event checklist
        essential_activities = [
            {
                "keyword": ["venue", "room", "hall", "auditorium", "booking", "space"],
                "name": "Venue & Facility Booking",
                "severity": "CRITICAL",
                "suggested_title": "Confirm Venue & Room Booking with Administration",
                "suggested_desc": "Finalize venue contracts, room permissions, and campus security access.",
                "phase": "PLANNING"
            },
            {
                "keyword": ["av", "audio", "visual", "projector", "mic", "microphone", "sound"],
                "name": "AV & Sound Infrastructure Check",
                "severity": "HIGH",
                "suggested_title": "Audio/Visual & Wi-Fi Equipment Testing",
                "suggested_desc": "Test microphones, presentation clickers, cables, and network bandwidth.",
                "phase": "LOGISTICS"
            },
            {
                "keyword": ["clean", "cleanup", "teardown", "tear down", "waste", "trash"],
                "name": "Post-Event Teardown & Cleanup",
                "severity": "MEDIUM",
                "suggested_title": "Venue Teardown & Room Clearance",
                "suggested_desc": "Return equipment, clean venue hall, and conduct administrative handover.",
                "phase": "POST_EVENT"
            },
            {
                "keyword": ["post-mortem", "post mortem", "retrospective", "debrief", "feedback"],
                "name": "Club Memory & Retrospective Documentation",
                "severity": "LOW",
                "suggested_title": "Compile Event Retrospective & Post-Mortem Document",
                "suggested_desc": "Document metrics, attendance numbers, operational delays, and lessons learned into Club Memory.",
                "phase": "POST_EVENT"
            }
        ]

        # Add food check if attendance is notable
        if event.expected_attendance and event.expected_attendance >= 40:
            essential_activities.append({
                "keyword": ["food", "catering", "snack", "pizza", "lunch", "refreshment", "drink"],
                "name": "Catering & Refreshment Procurement",
                "severity": "HIGH",
                "suggested_title": "Order Event Catering & Snacks for Attendees",
                "suggested_desc": f"Order food, drinks, and dietary options for {event.expected_attendance} expected participants.",
                "phase": "LOGISTICS"
            })

        for activity in essential_activities:
            has_match = any(kw in task_titles_lower for kw in activity["keyword"])
            if not has_match:
                missing_risks.append({
                    "category": "MISSING_ACTIVITY",
                    "severity": activity["severity"],
                    "missing_domain": activity["name"],
                    "description": f"Missing Core Activity: No task found for '{activity['name']}' in event plan.",
                    "root_cause": "The event operations plan lacks standard coverage for this essential domain.",
                    "suggested_fix": f"Create task '{activity['suggested_title']}' under {activity['phase']} phase.",
                    "payload_preview": {
                        "title": activity["suggested_title"],
                        "description": activity["suggested_desc"],
                        "phase": activity["phase"],
                        "priority": "HIGH" if activity["severity"] in ("CRITICAL", "HIGH") else "MEDIUM"
                    }
                })

        return missing_risks

    # ---------------------------------------------------------
    # 5. Single Task Risk Detector
    # ---------------------------------------------------------
    def detect_task_risks(self, db: Session, task_id: int) -> List[Dict[str, Any]]:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")

        now = datetime.utcnow()
        task_risks = []

        # 1. Ownership risk
        if len(task.assignments) == 0 and task.status != TaskStatus.DONE:
            is_overdue = task.due_date and task.due_date < now
            task_risks.append({
                "category": "OWNERSHIP",
                "severity": "CRITICAL" if is_overdue else "HIGH",
                "description": f"Task '{task.title}' has no owner assigned.",
                "suggested_fix": f"Assign an available volunteer with relevant skills."
            })

        # 2. Scheduling risk
        if task.status != TaskStatus.DONE and task.due_date and task.due_date < now:
            days_over = (now - task.due_date).days
            task_risks.append({
                "category": "SCHEDULING",
                "severity": "CRITICAL",
                "description": f"Task '{task.title}' is overdue by {days_over} day(s).",
                "suggested_fix": "Reschedule deadline or allocate additional co-volunteers to complete it."
            })

        # 3. Dependency risks
        for dep in task.dependencies_out:
            prereq = dep.prerequisite_task
            if prereq:
                if prereq.due_date and task.due_date and prereq.due_date > task.due_date:
                    task_risks.append({
                        "category": "DEPENDENCY",
                        "severity": "CRITICAL",
                        "description": f"Prerequisite '{prereq.title}' is scheduled to finish after this task!",
                        "suggested_fix": f"Reschedule this task due date after {prereq.due_date.strftime('%Y-%m-%d')}."
                    })
                if prereq.status == TaskStatus.BLOCKED:
                    task_risks.append({
                        "category": "DEPENDENCY",
                        "severity": "HIGH",
                        "description": f"Prerequisite '{prereq.title}' is BLOCKED.",
                        "suggested_fix": "Resolve blockers on prerequisite task first."
                    })

        # 4. Volunteer workload risk
        for a in task.assignments:
            load = calculate_volunteer_load(db, a.volunteer_id)
            if load.get("status") == "OVERLOADED":
                vol = db.query(Volunteer).filter(Volunteer.id == a.volunteer_id).first()
                vol_name = vol.user.full_name if vol and vol.user else f"Volunteer #{a.volunteer_id}"
                task_risks.append({
                    "category": "WORKLOAD",
                    "severity": "HIGH",
                    "description": f"Assigned owner '{vol_name}' is currently OVERLOADED ({load.get('utilization_percent')}% load).",
                    "suggested_fix": f"Reassign task to an unburdened volunteer."
                })

        return task_risks

    # ---------------------------------------------------------
    # 6. Unified Orchestrator: detect_event_risks
    # ---------------------------------------------------------
    def detect_event_risks(
        self,
        db: Session,
        event_id: int,
        persist: bool = True
    ) -> EventRiskSummary:
        """
        Executes internal detector suite:
        - Unowned tasks detection
        - Overload detection
        - Dependency conflict & timeline inversion detection
        - Missing activity detection
        - Budget overruns
        Persists active risks to database for tracking and returns structured summary.
        """
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise ValueError(f"Event with ID {event_id} not found")

        # Run individual detectors
        unowned_list = self.get_unowned_tasks_near_deadline(db, event_id)
        overload_list = self.get_overload_risks(db, event_id)
        critical_path_list = self.get_critical_path_risks(db, event_id)
        dependency_list = self.get_dependency_conflicts(db, event_id)
        missing_list = self.get_missing_activity_risks(db, event_id)

        all_detected = []

        # Map unowned
        for u in unowned_list:
            all_detected.append({
                "category": u["category"],
                "severity": u["severity"],
                "title": f"Unowned Task: {u['task_title']}",
                "description": u["description"],
                "root_cause": u.get("root_cause"),
                "suggested_fix": u.get("suggested_fix"),
                "task_id": u.get("task_id")
            })

        # Map overload
        for o in overload_list:
            all_detected.append({
                "category": o["category"],
                "severity": o["severity"],
                "title": f"Volunteer Overload: {o['volunteer_name']}",
                "description": o["description"],
                "root_cause": o.get("root_cause"),
                "suggested_fix": o.get("suggested_fix"),
                "task_id": o.get("colliding_task_ids", [None])[0] if "colliding_task_ids" in o else None
            })

        # Map critical path risks
        for cp in critical_path_list:
            all_detected.append({
                "category": cp["category"],
                "severity": cp["severity"],
                "title": f"Critical Path: {cp['task_title']}",
                "description": cp["description"],
                "root_cause": cp.get("root_cause"),
                "suggested_fix": cp.get("suggested_fix"),
                "task_id": cp.get("task_id")
            })

        # Map dependencies
        for d in dependency_list:
            all_detected.append({
                "category": d["category"],
                "severity": d["severity"],
                "title": f"Dependency Conflict: {d.get('task_title', 'Graph Cycle')}",
                "description": d["description"],
                "root_cause": d.get("root_cause"),
                "suggested_fix": d.get("suggested_fix"),
                "task_id": d.get("task_id")
            })

        # Map missing activities
        for m in missing_list:
            all_detected.append({
                "category": m["category"],
                "severity": m["severity"],
                "title": f"Missing Activity: {m['missing_domain']}",
                "description": m["description"],
                "root_cause": m.get("root_cause"),
                "suggested_fix": m.get("suggested_fix"),
                "task_id": None
            })

        # Check budget overrun
        if event.budget and event.budget_spent and event.budget_spent > event.budget:
            over_amount = round(event.budget_spent - event.budget, 2)
            all_detected.append({
                "category": "BUDGET",
                "severity": "HIGH",
                "title": "Budget Overrun Warning",
                "description": f"Event expenses (${event.budget_spent:,.2f}) exceed total allocated budget (${event.budget:,.2f}) by ${over_amount:,.2f}.",
                "root_cause": "Recorded spending has outpaced the allocated event budget limit.",
                "suggested_fix": "Request budget top-up or freeze discretionary expense categories.",
                "task_id": None
            })

        persisted_risks: List[EventRisk] = []
        if persist:
            # Query existing active risks to avoid duplicate rows
            existing_active = db.query(EventRisk).filter(
                EventRisk.event_id == event_id,
                EventRisk.status == "ACTIVE"
            ).all()
            existing_signatures = {(r.category, r.title) for r in existing_active}

            for item_data in all_detected:
                sig = (item_data["category"], item_data["title"])
                if sig not in existing_signatures:
                    db_risk = EventRisk(
                        event_id=event_id,
                        task_id=item_data.get("task_id"),
                        category=item_data["category"],
                        severity=item_data["severity"],
                        title=item_data["title"],
                        description=item_data["description"],
                        root_cause=item_data.get("root_cause"),
                        suggested_fix=item_data.get("suggested_fix"),
                        status="ACTIVE"
                    )
                    db.add(db_risk)
                    persisted_risks.append(db_risk)
            db.commit()

        # Fetch current active risks for return
        active_risks = db.query(EventRisk).filter(
            EventRisk.event_id == event_id,
            EventRisk.status == "ACTIVE"
        ).all()

        by_cat = {}
        for r in active_risks:
            by_cat[r.category] = by_cat.get(r.category, 0) + 1

        crit_count = sum(1 for r in active_risks if r.severity == "CRITICAL")
        high_count = sum(1 for r in active_risks if r.severity == "HIGH")
        med_count = sum(1 for r in active_risks if r.severity == "MEDIUM")
        low_count = sum(1 for r in active_risks if r.severity == "LOW")

        return EventRiskSummary(
            event_id=event_id,
            total_active_risks=len(active_risks),
            critical_count=crit_count,
            high_count=high_count,
            medium_count=med_count,
            low_count=low_count,
            by_category=by_cat,
            risks=[RiskRead.model_validate(r) for r in active_risks]
        )

    # ---------------------------------------------------------
    # 7. Explain Risk
    # ---------------------------------------------------------
    def explain_risk(self, db: Session, risk_id: int) -> RiskExplanation:
        risk = self.get_risk(db, risk_id)
        if not risk:
            raise ValueError(f"Risk with ID {risk_id} not found")

        underlying = []
        if risk.root_cause:
            underlying.append(risk.root_cause)

        if risk.category == "OWNERSHIP":
            impact = "The task will likely miss its deadline because no single individual is accountable for its execution."
            rec = "Assign an available volunteer with appropriate skills immediately."
            underlying.append("Task was scheduled without an owner assignment.")
        elif risk.category == "WORKLOAD":
            impact = "The assigned volunteer may experience burnout, deliver lower quality, or miss critical deadlines."
            rec = "Rebalance tasks across other team members or stagger the deadlines."
            underlying.append("Volunteer capacity exceeded 100% or multiple deadlines collided on the same date.")
        elif risk.category == "DEPENDENCY":
            impact = "Downstream tasks and day-of execution will be stalled, creating ripple delays across the entire event."
            rec = "Fix timeline date order or remove the circular blocker."
            underlying.append("Prerequisite task either has an impossible date sequence, is overdue, or is blocked.")
        elif risk.category == "MISSING_ACTIVITY":
            impact = "The event may face administrative shutdown, logistical failures, or poor attendee experience."
            rec = "Generate the missing task and assign an operational owner."
            underlying.append("Essential event activity domain has no representation in the task board.")
        else:
            impact = "Financial shortfall requiring emergency out-of-pocket funding or cancellation of event activities."
            rec = "Review and trim variable expenses."
            underlying.append("Actual spending has exceeded planned budget allocation.")

        return RiskExplanation(
            risk_id=risk.id,
            title=risk.title,
            category=risk.category,
            severity=risk.severity,
            why_it_exists=risk.description,
            underlying_conditions=underlying,
            potential_impact=impact,
            recommended_action=rec
        )

    # ---------------------------------------------------------
    # 8. Suggest Risk Fix
    # ---------------------------------------------------------
    def suggest_risk_fix(self, db: Session, risk_id: int) -> RiskFixSuggestion:
        risk = self.get_risk(db, risk_id)
        if not risk:
            raise ValueError(f"Risk with ID {risk_id} not found")

        fix_type = "RESOLVE"
        title = f"Fix for: {risk.title}"
        steps = []
        payload = None

        if risk.category == "OWNERSHIP" and risk.task_id:
            fix_type = "REASSIGN"
            title = "Assign Available Volunteer"
            steps = [
                f"Query volunteer skills matching Task #{risk.task_id}.",
                "Select a volunteer with lowest current workload utilization.",
                f"Call assign_task({risk.task_id}, [volunteer_id])."
            ]
            payload = {"action": "assign_task", "task_id": risk.task_id, "suggested_tool": "suggest_task_owner"}

        elif risk.category == "WORKLOAD":
            fix_type = "REASSIGN"
            title = "Rebalance Volunteer Task Load"
            steps = [
                "Identify unburdened co-volunteers in the club.",
                "Redistribute 1-2 tasks to volunteers with capacity under 70%.",
                "Stagger identical deadlines by 2 business days."
            ]
            payload = {"action": "bulk_reassign_tasks", "suggested_tool": "bulk_reassign_tasks"}

        elif risk.category == "DEPENDENCY":
            fix_type = "RESCHEDULE"
            title = "Correct Chronological Dependency Chain"
            steps = [
                "Inspect prerequisite and dependent task dates.",
                "Push dependent task start/due dates at least 24 hours after prerequisite completion.",
                "Notify task owners of revised schedule."
            ]
            payload = {"action": "update_task", "task_id": risk.task_id, "suggested_tool": "update_task"}

        elif risk.category == "MISSING_ACTIVITY":
            fix_type = "CREATE_TASK"
            title = "Create Missing Operational Task"
            steps = [
                f"Create task for the missing domain ({risk.title}).",
                "Assign to domain lead with appropriate phase and priority.",
                "Establish dependencies with adjacent operational phases."
            ]
            payload = {"action": "create_task", "event_id": risk.event_id, "suggested_tool": "create_task"}

        return RiskFixSuggestion(
            risk_id=risk.id,
            fix_type=fix_type,
            title=title,
            explanation=risk.suggested_fix or "Address the root cause to mitigate the risk.",
            actionable_steps=steps,
            automated_payload=payload
        )


risk_service = RiskService()
