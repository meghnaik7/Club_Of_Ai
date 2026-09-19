"""
Pydantic Schemas for AI Guardrails, Tool Validation, Proposals & Output Envelopes.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class CreateTaskSchema(BaseModel):
    title: str = Field(..., min_length=2, max_length=200, description="Task title")
    event_id: int = Field(..., gt=0, description="Target event ID")
    description: Optional[str] = Field(None, max_length=2000)
    assigned_to_id: Optional[int] = Field(None, gt=0)
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = Field("MEDIUM", pattern="^(LOW|MEDIUM|HIGH|URGENT)$")
    status: Optional[str] = Field("TODO", pattern="^(TODO|IN_PROGRESS|BLOCKED|COMPLETED|CANCELLED)$")

    @field_validator("due_date")
    @classmethod
    def validate_dates(cls, due_date, info):
        start_date = info.data.get("start_date")
        if start_date and due_date and due_date < start_date:
            raise ValueError(f"due_date ({due_date}) cannot be earlier than start_date ({start_date})")
        return due_date

class UpdateTaskSchema(BaseModel):
    task_id: int = Field(..., gt=0)
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    assigned_to_id: Optional[int] = Field(None, gt=0)
    status: Optional[str] = Field(None, pattern="^(TODO|IN_PROGRESS|BLOCKED|COMPLETED|CANCELLED)$")
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None

class AssignTaskSchema(BaseModel):
    task_id: int = Field(..., gt=0)
    volunteer_id: int = Field(..., gt=0)

class DependencySchema(BaseModel):
    task_id: int = Field(..., gt=0)
    depends_on_id: int = Field(..., gt=0)

    @field_validator("depends_on_id")
    @classmethod
    def check_self_dependency(cls, v, info):
        task_id = info.data.get("task_id")
        if task_id and v == task_id:
            raise ValueError(f"Self-dependency detected: Task {task_id} cannot depend on itself.")
        return v

class CreateEventSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    budget: Optional[float] = Field(0.0, ge=0.0)

    @field_validator("end_date")
    @classmethod
    def validate_event_dates(cls, end_date, info):
        start_date = info.data.get("start_date")
        if start_date and end_date and end_date < start_date:
            raise ValueError(f"end_date ({end_date}) cannot be earlier than start_date ({start_date})")
        return end_date

class AIProposalItem(BaseModel):
    entity_type: str = Field(..., description="Target table / model name, e.g. Task, Event")
    entity_id: Optional[int] = None
    action: str = Field(..., pattern="^(CREATE|UPDATE|DELETE)$")
    previous_data: Dict[str, Any] = Field(default_factory=dict)
    proposed_data: Dict[str, Any] = Field(default_factory=dict)
    explanation: str = Field(..., min_length=3)

class ProposalDiffPreview(BaseModel):
    proposal_id: int
    intent: str
    items_count: int
    is_bulk: bool
    requires_human_confirmation: bool
    diffs: List[Dict[str, Any]]

class AIStructuredOutput(BaseModel):
    success: bool
    summary: str
    action_taken: str = Field("NONE", pattern="^(NONE|EXECUTED_READ|PROPOSAL_STAGED|ERROR)$")
    citations: List[str] = Field(default_factory=list)
    confidence_score: float = Field(1.0, ge=0.0, le=1.0)
    proposal_id: Optional[int] = None
    data: Optional[Any] = None
    warnings: List[str] = Field(default_factory=list)
