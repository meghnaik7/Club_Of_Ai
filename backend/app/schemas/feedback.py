from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class FeedbackCreate(BaseModel):
    proposal_id: Optional[int] = None
    event_id: Optional[int] = None
    rating: str = Field(..., description="'GOOD' (thumbs up) or 'POOR' (thumbs down)")
    feedback_type: Optional[str] = Field(
        None,
        description="Reason code: wrong_volunteer, deadline_unrealistic, missing_dependency, too_many_changes, positive_execution, other"
    )
    comment: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class FeedbackOut(BaseModel):
    id: int
    proposal_id: Optional[int] = None
    user_id: Optional[int] = None
    event_id: Optional[int] = None
    rating: str
    feedback_type: Optional[str] = None
    comment: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackAnalytics(BaseModel):
    total_feedbacks: int
    positive_count: int
    negative_count: int
    satisfaction_rate_percent: float
    proposal_acceptance_rate_percent: float
    recovery_success_rate_percent: float
    top_negative_reasons: Dict[str, int]
    recent_feedbacks: List[FeedbackOut] = Field(default_factory=list)
