from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

# --- Action Item Schemas ---
class MeetingActionItemBase(BaseModel):
    raw_text: Optional[str] = None
    title: str
    description: Optional[str] = None
    suggested_owner_name: Optional[str] = None
    resolved_volunteer_id: Optional[int] = None
    suggested_due_date: Optional[datetime] = None
    due_date_raw: Optional[str] = None
    priority: str = "MEDIUM"
    confidence: float = 0.85
    status: str = "PENDING"
    applied_task_id: Optional[int] = None


class MeetingActionItemCreate(MeetingActionItemBase):
    meeting_id: int


class MeetingActionItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    suggested_owner_name: Optional[str] = None
    resolved_volunteer_id: Optional[int] = None
    suggested_due_date: Optional[datetime] = None
    due_date_raw: Optional[str] = None
    priority: Optional[str] = None
    confidence: Optional[float] = None
    status: Optional[str] = None
    applied_task_id: Optional[int] = None


class MeetingActionItemRead(MeetingActionItemBase):
    id: int
    meeting_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Meeting Schemas ---
class MeetingBase(BaseModel):
    title: str
    date: Optional[datetime] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = []
    raw_notes: Optional[str] = None
    transcript: Optional[str] = None


class MeetingCreate(MeetingBase):
    event_id: int


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[datetime] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    raw_notes: Optional[str] = None
    transcript: Optional[str] = None


class MeetingRead(MeetingBase):
    id: int
    event_id: int
    created_at: datetime
    updated_at: datetime
    action_items: List[MeetingActionItemRead] = []

    model_config = ConfigDict(from_attributes=True)


# --- AI Extraction & Review Flow ---
class ExtractedActionItemDetail(BaseModel):
    title: str
    raw_text: str
    owner: Optional[str] = None
    due_date_raw: Optional[str] = None
    suggested_due_date: Optional[datetime] = None
    confidence: float
    resolved_volunteer_id: Optional[int] = None
    resolved_volunteer_name: Optional[str] = None


class ActionItemExtractionResponse(BaseModel):
    meeting_id: int
    extracted_count: int
    action_items: List[MeetingActionItemRead]


class ResolvedReferenceItem(BaseModel):
    action_item_id: int
    raw_text: str
    owner_reference: str
    matched_volunteer_id: Optional[int] = None
    matched_volunteer_name: Optional[str] = None
    match_confidence: float
    existing_task_conflict: Optional[str] = None


class ApplyActionItemsResponse(BaseModel):
    applied_count: int
    created_tasks: List[Dict[str, Any]]
