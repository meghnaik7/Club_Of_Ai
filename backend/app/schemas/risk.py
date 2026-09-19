from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class RiskBase(BaseModel):
    category: str # SCHEDULING, OWNERSHIP, DEPENDENCY, WORKLOAD, MISSING_ACTIVITY, BUDGET
    severity: str = "MEDIUM" # CRITICAL, HIGH, MEDIUM, LOW
    title: str
    description: str
    root_cause: Optional[str] = None
    suggested_fix: Optional[str] = None
    task_id: Optional[int] = None


class RiskCreate(RiskBase):
    event_id: int


class RiskUpdate(BaseModel):
    severity: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    root_cause: Optional[str] = None
    suggested_fix: Optional[str] = None
    status: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None


class RiskRead(RiskBase):
    id: int
    event_id: int
    status: str
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskFixSuggestion(BaseModel):
    risk_id: int
    fix_type: str # REASSIGN, RESCHEDULE, CREATE_TASK, SPLIT_TASK, RESOLVE
    title: str
    explanation: str
    actionable_steps: List[str] = []
    automated_payload: Optional[Dict[str, Any]] = None


class RiskExplanation(BaseModel):
    risk_id: int
    title: str
    category: str
    severity: str
    why_it_exists: str
    underlying_conditions: List[str] = []
    potential_impact: str
    recommended_action: str


class EventRiskSummary(BaseModel):
    event_id: int
    total_active_risks: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    by_category: Dict[str, int] = {}
    risks: List[RiskRead] = []
