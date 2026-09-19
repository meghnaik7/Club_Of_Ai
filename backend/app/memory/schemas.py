from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class MemoryTypeEnum(str):
    USER_PREFERENCE = "USER_PREFERENCE"
    WORKING_PREFERENCE = "WORKING_PREFERENCE"
    CLUB_KNOWLEDGE = "CLUB_KNOWLEDGE"
    EVENT_LESSON = "EVENT_LESSON"
    IMPORTANT_DECISION = "IMPORTANT_DECISION"
    VOLUNTEER_KNOWLEDGE = "VOLUNTEER_KNOWLEDGE"
    PROCESS_RULE = "PROCESS_RULE"
    OTHER = "OTHER"

class MemoryScopeEnum(str):
    USER = "USER"
    CLUB = "CLUB"
    EVENT = "EVENT"
    VOLUNTEER = "VOLUNTEER"

class MemoryBase(BaseModel):
    memory_type: str = Field(..., description="Type of memory")
    scope: str = Field(default="USER", description="Scope of memory (USER, CLUB, EVENT, VOLUNTEER)")
    content: str = Field(..., min_length=3, description="Canonical memory statement")
    structured_data: Optional[Dict[str, Any]] = None
    importance: float = Field(default=0.7, ge=0.0, le=1.0)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    source: str = Field(default="conversation")
    club_id: Optional[int] = None
    event_id: Optional[int] = None
    expires_at: Optional[datetime] = None

class MemoryCreate(MemoryBase):
    user_id: Optional[int] = None

class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    memory_type: Optional[str] = None
    scope: Optional[str] = None
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    structured_data: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None

class MemoryResponse(MemoryBase):
    id: int
    user_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MemoryListResponse(BaseModel):
    items: List[MemoryResponse]
    total: int

class MemoryRetrievalQuery(BaseModel):
    query: str
    user_id: Optional[int] = None
    club_id: Optional[int] = None
    event_id: Optional[int] = None
    top_k: int = 5
    min_score: float = 0.35

class MemoryCandidate(BaseModel):
    memory_type: str
    scope: str = "USER"
    content: str
    structured_data: Optional[Dict[str, Any]] = None
    importance: float = 0.7
    confidence: float = 0.9
    source: str = "conversation"
    club_id: Optional[int] = None
    event_id: Optional[int] = None
