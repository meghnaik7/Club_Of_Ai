from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator
from app.models.event import EventStatus


# --- Expense Schemas ---
class ExpenseBase(BaseModel):
    category: Optional[str] = None
    amount: float
    description: Optional[str] = None
    recorded_by: Optional[str] = None
    task_id: Optional[int] = None
    date: Optional[datetime] = None


class ExpenseCreate(ExpenseBase):
    event_id: int


class ExpenseRead(ExpenseBase):
    id: int
    event_id: int
    date: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Budget Category Schemas ---
class BudgetCategoryBase(BaseModel):
    name: str
    allocated_amount: float = 0.0


class BudgetCategoryCreate(BudgetCategoryBase):
    event_id: int


class BudgetCategoryRead(BudgetCategoryBase):
    id: int
    event_id: int
    model_config = ConfigDict(from_attributes=True)


# --- Event Schemas ---
def _normalize_datetime(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, str):
        v_clean = v.strip().replace(" ", "T")
        try:
            dt = datetime.fromisoformat(v_clean.replace("Z", "+00:00"))
            return dt.replace(tzinfo=None)
        except Exception:
            return v
    elif isinstance(v, datetime) and v.tzinfo is not None:
        return v.replace(tzinfo=None)
    return v


class EventBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[datetime] = None
    venue: Optional[str] = None
    budget: Optional[float] = 0.0
    budget_spent: Optional[float] = 0.0
    expected_attendance: Optional[int] = 0
    status: Optional[EventStatus] = EventStatus.DRAFT

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, v: Any) -> Any:
        return _normalize_datetime(v)


class EventCreate(EventBase):
    title: str
    date: datetime


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[datetime] = None
    venue: Optional[str] = None
    budget: Optional[float] = None
    budget_spent: Optional[float] = None
    expected_attendance: Optional[int] = None
    status: Optional[EventStatus] = None

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, v: Any) -> Any:
        return _normalize_datetime(v)


class EventInDBBase(EventBase):
    id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class Event(EventInDBBase):
    budget_categories: List[BudgetCategoryRead] = []
    expenses: List[ExpenseRead] = []


# --- Event Budget Summary ---
class CategoryBudgetBreakdown(BaseModel):
    category: str
    allocated: float
    spent: float
    remaining: float
    burn_rate_percent: float


class TaskBudgetBreakdown(BaseModel):
    task_id: int
    task_title: str
    spent: float


class EventBudgetSummary(BaseModel):
    event_id: int
    event_title: str
    total_budget: float
    total_spent: float
    remaining_budget: float
    burn_rate_percent: float
    is_over_budget: bool
    categories: List[CategoryBudgetBreakdown] = []
    tasks: List[TaskBudgetBreakdown] = []


# --- Event Dashboard & Analytics ---
class TaskStats(BaseModel):
    total: int
    completed: int
    in_progress: int
    todo: int
    blocked: int
    completion_percentage: float


class EventRiskItem(BaseModel):
    severity: str # HIGH, MEDIUM, LOW
    type: str # DEADLINE, BUDGET, VOLUNTEER, DEPENDENCY
    description: str


class EventDashboard(BaseModel):
    event_id: int
    title: str
    date: datetime
    venue: Optional[str] = None
    status: EventStatus
    days_remaining: int
    task_stats: TaskStats
    volunteer_count: int
    budget_status: Dict[str, Any]
    risks: List[EventRiskItem] = []


# --- Event Timeline / Gantt ---
class EventTimelineItem(BaseModel):
    task_id: int
    title: str
    phase: Optional[str] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    status: str
    priority: str
    dependencies: List[int] = [] # prerequisite task ids
    blocking: List[int] = [] # dependent task ids
    assigned_volunteers: List[int] = []


# --- AI Event Plan Generation ---
class EventPlanTask(BaseModel):
    title: str
    description: str
    priority: str = "MEDIUM"
    phase: str
    estimated_days_before_event: int
    suggested_skills: List[str] = []
    prerequisite_task_indices: List[int] = [] # indices of other tasks in the plan


class EventPlanPhase(BaseModel):
    phase_name: str
    description: str
    tasks: List[EventPlanTask] = []


class EventPlanGenerated(BaseModel):
    event_title: str
    estimated_budget: float
    phases: List[EventPlanPhase] = []
    historical_lessons_applied: List[str] = []
    summary: str
