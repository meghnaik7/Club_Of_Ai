from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class EscalationLevelEnum(str):
    NONE = "NONE"
    CANDIDATE = "CANDIDATE"
    TEAM_LEADER = "TEAM_LEADER"
    MAIN_LEADER = "MAIN_LEADER"

class EscalationStatusEnum(str):
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"

class EscalationResult(BaseModel):
    task_id: int
    task_title: str
    event_id: int
    escalation_required: bool
    reason: str
    escalation_level: str
    escalation_status: str
    rule_triggered: Optional[str] = None
    is_critical_path: bool = False
    team_leader_notified: bool = False
    main_leader_notified: bool = False
    notification_count: int = 0
    next_escalation_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class EscalationConfig(BaseModel):
    HOURS_BEFORE_DUE: int = Field(default=24, description="Hours before due date to flag high/critical tasks (Rule 1)")
    TEAM_LEADER_ESCALATION_MINUTES: int = Field(default=60, description="Minutes unresolved before escalating to Main Leader (Rule 3)")
    CRITICAL_PATH_ESCALATION_MINUTES: int = Field(default=30, description="Minutes critical path task remains unresolved before Main Leader escalation (Rule 5)")

class EscalationAcknowledgeRequest(BaseModel):
    note: Optional[str] = None

class EscalationResolveRequest(BaseModel):
    resolution_note: str = Field(..., min_length=2, description="Reason or note explaining resolution")

class EscalationManualPromoteRequest(BaseModel):
    reason: Optional[str] = None

class EscalationCancelRequest(BaseModel):
    reason: Optional[str] = None
