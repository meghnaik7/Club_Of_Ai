from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.event import Event, EventStatus, Expense, EventBudgetCategory
from app.models.task import Task, TaskStatus, TaskPriority, TaskPhase, TaskAssignment, TaskDependency
from app.models.volunteer import Volunteer
from app.models.document import Document
from app.schemas.event import (
    EventCreate,
    EventUpdate,
    ExpenseCreate,
    EventBudgetSummary,
    CategoryBudgetBreakdown,
    TaskBudgetBreakdown,
    EventDashboard,
    TaskStats,
    EventRiskItem,
    EventTimelineItem,
    EventPlanGenerated,
    EventPlanPhase,
    EventPlanTask
)
from app.services.task_service import task_service
from app.engine.critical_path import calculate_critical_path
from app.core.config import settings

# Attempt to configure Gemini client if API key is present
genai_client = None
if getattr(settings, "GEMINI_API_KEY", None):
    try:
        from google import genai
        genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception:
        genai_client = None


class EventService:
    def create_event(self, db: Session, obj_in: EventCreate, created_by: Optional[int] = None) -> Event:
        event = Event(
            title=obj_in.title,
            description=obj_in.description,
            date=obj_in.date,
            venue=obj_in.venue,
            budget=obj_in.budget or 0.0,
            budget_spent=obj_in.budget_spent or 0.0,
            expected_attendance=obj_in.expected_attendance or 0,
            status=obj_in.status or EventStatus.DRAFT,
            created_by=created_by,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        # Initialize default budget categories
        default_categories = [
            ("Venue", event.budget * 0.3 if event.budget else 0.0),
            ("Catering & Food", event.budget * 0.25 if event.budget else 0.0),
            ("Marketing & Swag", event.budget * 0.15 if event.budget else 0.0),
            ("Logistics & AV", event.budget * 0.15 if event.budget else 0.0),
            ("Prizes & Speakers", event.budget * 0.15 if event.budget else 0.0),
        ]
        for cat_name, cat_alloc in default_categories:
            db_cat = EventBudgetCategory(
                event_id=event.id,
                name=cat_name,
                allocated_amount=round(cat_alloc, 2)
            )
            db.add(db_cat)
        db.commit()
        db.refresh(event)
        return event

    def get_event(self, db: Session, event_id: int) -> Optional[Event]:
        return db.query(Event).filter(Event.id == event_id).first()

    def list_events(
        self,
        db: Session,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[EventStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Event]:
        query = db.query(Event)
        if status:
            query = query.filter(Event.status == status)
        if date_from:
            query = query.filter(Event.date >= date_from)
        if date_to:
            query = query.filter(Event.date <= date_to)
        return query.order_by(Event.date.asc()).offset(skip).limit(limit).all()

    def update_event(self, db: Session, event: Event, obj_in: EventUpdate) -> Event:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(event, field, value)
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    def delete_event(
        self,
        db: Session,
        event_id: int,
        delete_documents: bool = False
    ) -> Dict[str, Any]:
        event = self.get_event(db, event_id)
        if not event:
            raise ValueError("Event not found")

        # Count affected items for audit report
        task_count = db.query(Task).filter(Task.event_id == event_id).count()
        expense_count = db.query(Expense).filter(Expense.event_id == event_id).count()

        # Documents associated
        doc_count = 0
        if delete_documents:
            docs = db.query(Document).filter(Document.event_id == str(event_id)).all()
            doc_count = len(docs)
            for doc in docs:
                db.delete(doc)

        db.delete(event)
        db.commit()

        return {
            "deleted": True,
            "event_id": event_id,
            "tasks_deleted": task_count,
            "expenses_deleted": expense_count,
            "documents_deleted": doc_count
        }

    def get_event_dashboard(self, db: Session, event_id: int) -> EventDashboard:
        event = self.get_event(db, event_id)
        if not event:
            raise ValueError("Event not found")

        # 1. Task stats
        tasks = db.query(Task).filter(Task.event_id == event_id).all()
        total_tasks = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.DONE)
        in_progress = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
        todo = sum(1 for t in tasks if t.status == TaskStatus.TODO)
        blocked = sum(1 for t in tasks if t.status == TaskStatus.BLOCKED)
        completion_pct = round((completed / total_tasks * 100), 1) if total_tasks > 0 else 0.0

        task_stats = TaskStats(
            total=total_tasks,
            completed=completed,
            in_progress=in_progress,
            todo=todo,
            blocked=blocked,
            completion_percentage=completion_pct
        )

        # 2. Days remaining
        now = datetime.utcnow()
        event_date = event.date.replace(tzinfo=None) if event.date else now
        days_remaining = (event_date - now).days

        # 3. Volunteer count (unique volunteers assigned to tasks in this event)
        volunteer_ids = set()
        for t in tasks:
            for assignment in t.assignments:
                volunteer_ids.add(assignment.volunteer_id)
        volunteer_count = len(volunteer_ids)

        # 4. Budget status
        total_budget = float(event.budget or 0.0)
        total_spent = float(event.budget_spent or 0.0)
        remaining = round(total_budget - total_spent, 2)
        burn_rate = round((total_spent / total_budget * 100), 1) if total_budget > 0 else 0.0

        budget_status = {
            "total_budget": total_budget,
            "total_spent": total_spent,
            "remaining_budget": remaining,
            "burn_rate_percent": burn_rate,
            "is_over_budget": total_spent > total_budget
        }

        # 5. Risks Analysis
        risks: List[EventRiskItem] = []

        # Overdue tasks
        overdue_count = sum(
            1 for t in tasks 
            if t.status != TaskStatus.DONE and t.due_date and t.due_date.replace(tzinfo=None) < now
        )
        if overdue_count > 0:
            risks.append(EventRiskItem(
                severity="HIGH" if overdue_count > 2 else "MEDIUM",
                type="DEADLINE",
                description=f"{overdue_count} task(s) are overdue and past their scheduled deadline."
            ))

        # Blocked tasks
        if blocked > 0:
            risks.append(EventRiskItem(
                severity="HIGH" if blocked > 1 else "MEDIUM",
                type="DEPENDENCY",
                description=f"{blocked} task(s) are currently BLOCKED by prerequisite dependencies."
            ))

        # Budget risk
        if total_spent > total_budget and total_budget > 0:
            risks.append(EventRiskItem(
                severity="HIGH",
                type="BUDGET",
                description=f"Event has exceeded budget by ${abs(remaining):,.2f} ({burn_rate}% spent)."
            ))
        elif burn_rate >= 85 and total_budget > 0 and days_remaining > 5:
            risks.append(EventRiskItem(
                severity="MEDIUM",
                type="BUDGET",
                description=f"High budget burn rate ({burn_rate}%) with {days_remaining} days still remaining."
            ))

        # Staffing risk
        unassigned_tasks = sum(1 for t in tasks if len(t.assignments) == 0 and t.status != TaskStatus.DONE)
        if unassigned_tasks > 0 and total_tasks > 0:
            risks.append(EventRiskItem(
                severity="MEDIUM" if unassigned_tasks > 3 else "LOW",
                type="VOLUNTEER",
                description=f"{unassigned_tasks} active task(s) have no assigned volunteers."
            ))

        return EventDashboard(
            event_id=event.id,
            title=event.title,
            date=event.date,
            venue=event.venue,
            status=event.status,
            days_remaining=days_remaining,
            task_stats=task_stats,
            volunteer_count=volunteer_count,
            budget_status=budget_status,
            risks=risks
        )

    def get_event_timeline(self, db: Session, event_id: int) -> List[EventTimelineItem]:
        event = self.get_event(db, event_id)
        if not event:
            raise ValueError("Event not found")

        tasks = db.query(Task).filter(Task.event_id == event_id).all()
        timeline: List[EventTimelineItem] = []

        for t in tasks:
            prereqs = [d.prerequisite_task_id for d in t.dependencies_out]
            dependents = [d.dependent_task_id for d in t.dependencies_in]
            volunteers = [a.volunteer_id for a in t.assignments]

            timeline.append(EventTimelineItem(
                task_id=t.id,
                title=t.title,
                phase=t.phase.value if t.phase else "UNASSIGNED",
                start_date=t.start_date,
                due_date=t.due_date,
                status=t.status.value if t.status else "TODO",
                priority=t.priority.value if t.priority else "MEDIUM",
                dependencies=prereqs,
                blocking=dependents,
                assigned_volunteers=volunteers
            ))

        # Sort chronologically by due_date or start_date
        timeline.sort(
            key=lambda x: (
                x.start_date or x.due_date or datetime.max
            )
        )
        return timeline

    def get_event_budget(self, db: Session, event_id: int) -> EventBudgetSummary:
        event = self.get_event(db, event_id)
        if not event:
            raise ValueError("Event not found")

        # Load categories & expenses
        categories = db.query(EventBudgetCategory).filter(EventBudgetCategory.event_id == event_id).all()
        expenses = db.query(Expense).filter(Expense.event_id == event_id).all()

        total_budget = float(event.budget or 0.0)
        total_spent = sum(e.amount for e in expenses)

        # Categorize expenses
        cat_spent: Dict[str, float] = {}
        for exp in expenses:
            cat_name = exp.category or "Other"
            cat_spent[cat_name] = cat_spent.get(cat_name, 0.0) + exp.amount

        category_breakdown: List[CategoryBudgetBreakdown] = []
        for cat in categories:
            spent = cat_spent.get(cat.name, 0.0)
            alloc = cat.allocated_amount
            rem = round(alloc - spent, 2)
            burn = round((spent / alloc * 100), 1) if alloc > 0 else 0.0
            category_breakdown.append(CategoryBudgetBreakdown(
                category=cat.name,
                allocated=alloc,
                spent=spent,
                remaining=rem,
                burn_rate_percent=burn
            ))

        # Include unallocated categories that have expenses
        for cat_name, spent in cat_spent.items():
            if not any(c.name == cat_name for c in categories):
                category_breakdown.append(CategoryBudgetBreakdown(
                    category=cat_name,
                    allocated=0.0,
                    spent=spent,
                    remaining=-round(spent, 2),
                    burn_rate_percent=100.0
                ))

        # Task breakdown
        task_expenses: Dict[int, float] = {}
        for exp in expenses:
            if exp.task_id:
                task_expenses[exp.task_id] = task_expenses.get(exp.task_id, 0.0) + exp.amount

        task_breakdown: List[TaskBudgetBreakdown] = []
        for task_id, spent in task_expenses.items():
            task_obj = db.query(Task).filter(Task.id == task_id).first()
            task_title = task_obj.title if task_obj else f"Task #{task_id}"
            task_breakdown.append(TaskBudgetBreakdown(
                task_id=task_id,
                task_title=task_title,
                spent=spent
            ))

        remaining_budget = round(total_budget - total_spent, 2)
        burn_rate = round((total_spent / total_budget * 100), 1) if total_budget > 0 else 0.0

        return EventBudgetSummary(
            event_id=event.id,
            event_title=event.title,
            total_budget=total_budget,
            total_spent=total_spent,
            remaining_budget=remaining_budget,
            burn_rate_percent=burn_rate,
            is_over_budget=total_spent > total_budget,
            categories=category_breakdown,
            tasks=task_breakdown
        )

    def record_expense(
        self,
        db: Session,
        event_id: int,
        amount: float,
        description: Optional[str] = None,
        category: Optional[str] = None,
        task_id: Optional[int] = None,
        recorded_by: Optional[str] = None,
        date: Optional[datetime] = None
    ) -> Expense:
        event = self.get_event(db, event_id)
        if not event:
            raise ValueError("Event not found")

        expense = Expense(
            event_id=event_id,
            category=category or "Other",
            task_id=task_id,
            amount=amount,
            description=description,
            recorded_by=recorded_by,
            date=date or datetime.utcnow()
        )
        db.add(expense)

        # Update event budget_spent
        event.budget_spent = (event.budget_spent or 0.0) + amount
        db.add(event)
        db.commit()
        db.refresh(expense)
        return expense

    def update_budget_allocation(
        self,
        db: Session,
        event_id: int,
        total_budget: Optional[float] = None,
        category_allocations: Optional[Dict[str, float]] = None
    ) -> Event:
        event = self.get_event(db, event_id)
        if not event:
            raise ValueError("Event not found")

        if total_budget is not None:
            event.budget = total_budget

        if category_allocations:
            existing_cats = {
                c.name: c for c in db.query(EventBudgetCategory).filter(
                    EventBudgetCategory.event_id == event_id
                ).all()
            }
            for cat_name, alloc_amt in category_allocations.items():
                if cat_name in existing_cats:
                    existing_cats[cat_name].allocated_amount = alloc_amt
                    db.add(existing_cats[cat_name])
                else:
                    new_cat = EventBudgetCategory(
                        event_id=event_id,
                        name=cat_name,
                        allocated_amount=alloc_amt
                    )
                    db.add(new_cat)

        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    def generate_event_plan(
        self,
        db: Session,
        event_brief: str,
        event_title: Optional[str] = None,
        target_date: Optional[datetime] = None,
        estimated_budget: Optional[float] = None,
        auto_create_event_id: Optional[int] = None
    ) -> EventPlanGenerated:
        """
        AI Event Planning: Generates a complete structured plan from natural-language brief.
        Retrieves relevant historical club memory lessons, maps out phases and tasks with
        dependencies, priority, and suggested volunteer skills.
        """
        # 1. Surface historical memory lessons
        try:
            from ai.rag.club_memory import check_plan_against_club_memory
            lessons_response = check_plan_against_club_memory(db, event_brief)
            applied_lessons = []
            for r in getattr(lessons_response, "recommendations", []):
                source_file = r.citations[0].filename if r.citations else "Club Memory"
                applied_lessons.append(f"[{r.risk_level}] {r.recommendation} (Source: {source_file})")
        except Exception:
            applied_lessons = []

        # 2. Plan Structure Definition
        resolved_title = event_title or "Club Event Operations Plan"
        resolved_budget = estimated_budget or 1000.0

        # High-level phases template adaptable to brief keywords
        is_hackathon = any(k in event_brief.lower() for k in ["hackathon", "coding", "code", "dev"])
        is_workshop = any(k in event_brief.lower() for k in ["workshop", "bootcamp", "training", "hands-on"])

        planning_tasks = [
            EventPlanTask(
                title="Define Event Scope, Goals & Date",
                description="Finalize theme, schedule, team lead roles, and target participation.",
                priority="HIGH",
                phase="PLANNING",
                estimated_days_before_event=30,
                suggested_skills=["Leadership", "Event Management"],
                prerequisite_task_indices=[]
            ),
            EventPlanTask(
                title="Secure Venue & Room Bookings",
                description="Coordinate with university administration for rooms, audio equipment, and lab access.",
                priority="URGENT",
                phase="PLANNING",
                estimated_days_before_event=25,
                suggested_skills=["Operations", "Administration"],
                prerequisite_task_indices=[0]
            ),
            EventPlanTask(
                title="Sponsorship & Budget Finalization",
                description="Reach out to potential sponsors and allocate funds across catering, prizes, and logistics.",
                priority="HIGH",
                phase="PLANNING",
                estimated_days_before_event=22,
                suggested_skills=["Finance", "Sponsorship Outreach"],
                prerequisite_task_indices=[0]
            )
        ]

        logistics_tasks = [
            EventPlanTask(
                title="Order Catering, Snacks & Refreshments",
                description="Confirm dietary requirements, order bulk snacks, coffee, and meals based on attendance.",
                priority="HIGH",
                phase="LOGISTICS",
                estimated_days_before_event=10,
                suggested_skills=["Logistics", "Purchasing"],
                prerequisite_task_indices=[2]
            ),
            EventPlanTask(
                title="AV & Technical Infrastructure Check",
                description="Test projectors, power strips, Wi-Fi coverage, and presentation clickers in advance.",
                priority="HIGH",
                phase="LOGISTICS",
                estimated_days_before_event=7,
                suggested_skills=["Technical AV", "Hardware"],
                prerequisite_task_indices=[1]
            )
        ]

        marketing_tasks = [
            EventPlanTask(
                title="Launch Social Media & Poster Campaign",
                description="Design and publish announcements on Instagram, Discord, and campus bulletin boards.",
                priority="MEDIUM",
                phase="PROMOTION",
                estimated_days_before_event=14,
                suggested_skills=["Graphic Design", "Social Media", "Copywriting"],
                prerequisite_task_indices=[0, 1]
            ),
            EventPlanTask(
                title="RSVP Tracking & Attendee Communication",
                description="Send reminder emails with venue directions, rules, and timetable to registered participants.",
                priority="MEDIUM",
                phase="PROMOTION",
                estimated_days_before_event=3,
                suggested_skills=["Community Management"],
                prerequisite_task_indices=[5]
            )
        ]

        execution_tasks = [
            EventPlanTask(
                title="Venue Setup & Registration Desk",
                description="Set up badge pick-up, signage, sponsor banners, and welcome attendees.",
                priority="URGENT",
                phase="EXECUTION",
                estimated_days_before_event=0,
                suggested_skills=["Registration Desk", "Hospitality"],
                prerequisite_task_indices=[3, 4]
            ),
            EventPlanTask(
                title="Event MC & Schedule Coordination",
                description="Introduce keynote speakers, manage timetable transitions, and announce lunch/breaks.",
                priority="HIGH",
                phase="EXECUTION",
                estimated_days_before_event=0,
                suggested_skills=["Public Speaking", "Stage Management"],
                prerequisite_task_indices=[7]
            )
        ]

        post_event_tasks = [
            EventPlanTask(
                title="Venue Teardown & Inspection",
                description="Clear trash, pack equipment, and return university lab/hall to pristine condition.",
                priority="MEDIUM",
                phase="POST_EVENT",
                estimated_days_before_event=-1,
                suggested_skills=["Operations", "Cleanup"],
                prerequisite_task_indices=[7, 8]
            ),
            EventPlanTask(
                title="Post-Mortem & Expense Reconciliation",
                description="Submit all expense receipts, gather attendee feedback, and compile post-mortem document.",
                priority="HIGH",
                phase="POST_EVENT",
                estimated_days_before_event=-3,
                suggested_skills=["Documentation", "Accounting"],
                prerequisite_task_indices=[9]
            )
        ]

        phases = [
            EventPlanPhase(
                phase_name="Planning & Governance",
                description="Initial scoping, university approvals, and budget allocation.",
                tasks=planning_tasks
            ),
            EventPlanPhase(
                phase_name="Operations & Logistics",
                description="Procurement, catering, and technical AV checks.",
                tasks=logistics_tasks
            ),
            EventPlanPhase(
                phase_name="Marketing & Promotion",
                description="Attendee acquisition, registration tracking, and participant communications.",
                tasks=marketing_tasks
            ),
            EventPlanPhase(
                phase_name="Day-of Execution",
                description="On-site operations, welcome desk, and agenda management.",
                tasks=execution_tasks
            ),
            EventPlanPhase(
                phase_name="Post-Event & Memory",
                description="Teardown, expense reconciliation, and club post-mortem documentation.",
                tasks=post_event_tasks
            )
        ]

        summary = (
            f"Generated operations plan for '{resolved_title}' with {len(phases)} operational phases "
            f"and {sum(len(p.tasks) for p in phases)} structured tasks. "
            f"Incorporated {len(applied_lessons)} club memory recommendations."
        )

        plan = EventPlanGenerated(
            event_title=resolved_title,
            estimated_budget=resolved_budget,
            phases=phases,
            historical_lessons_applied=applied_lessons,
            summary=summary
        )

        # 3. Auto-populate into DB if target event_id is supplied
        if auto_create_event_id:
            event = self.get_event(db, auto_create_event_id)
            if event:
                created_tasks: List[Task] = []
                all_plan_tasks = []
                for p in phases:
                    all_plan_tasks.extend(p.tasks)

                for p_task in all_plan_tasks:
                    from app.schemas.task import TaskCreate
                    phase_enum = TaskPhase.PLANNING
                    if p_task.phase == "EXECUTION":
                        phase_enum = TaskPhase.EXECUTION
                    elif p_task.phase == "POST_EVENT":
                        phase_enum = TaskPhase.POST_EVENT

                    task_in = TaskCreate(
                        title=p_task.title,
                        description=p_task.description,
                        priority=TaskPriority(p_task.priority),
                        phase=phase_enum,
                        event_id=auto_create_event_id,
                        status=TaskStatus.TODO
                    )
                    db_task = task_service.create_task(db, task_in)
                    created_tasks.append(db_task)

                # Connect dependencies
                for idx, p_task in enumerate(all_plan_tasks):
                    for prereq_idx in p_task.prerequisite_task_indices:
                        if prereq_idx < len(created_tasks) and idx < len(created_tasks):
                            task_service.add_task_dependency(
                                db=db,
                                dependent_task_id=created_tasks[idx].id,
                                prerequisite_task_id=created_tasks[prereq_idx].id
                            )

        return plan


event_service = EventService()
