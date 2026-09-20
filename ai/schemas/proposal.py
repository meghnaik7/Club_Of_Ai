from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class ProposalChangeOut(BaseModel):
    id: int
    entity_type: str
    entity_id: Optional[int] = None
    action: str
    proposed_data: Dict[str, Any]
    previous_data: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None

class ProposalResponse(BaseModel):
    proposal_id: int
    intent: str
    status: str
    event_plan: Optional[Any] = None
    changes: List[ProposalChangeOut] = Field(default_factory=list)

class FieldDiff(BaseModel):
    field: str
    old_value: Any = None
    new_value: Any = None
    change_type: str = Field(..., description="ADDED, MODIFIED, REMOVED, or UNCHANGED")

class EntityDiff(BaseModel):
    entity_type: str
    entity_id: Optional[int] = None
    action: str
    summary: str
    field_diffs: List[FieldDiff] = Field(default_factory=list)
    before: Optional[Dict[str, Any]] = None
    proposed: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    impact: Optional[str] = None
    confidence: Optional[str] = "HIGH"

class ProposalDiffPreview(BaseModel):
    proposal_id: int
    intent: str
    status: str
    total_changes: int
    entities_affected: List[str]
    diffs: List[EntityDiff] = Field(default_factory=list)
    overall_impact: Optional[str] = None

class AuditLogEntryOut(BaseModel):
    id: int
    proposal_id: Optional[int] = None
    entity_type: str
    entity_id: int
    action: str
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None
    timestamp: datetime
