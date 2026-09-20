from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AnnouncementBase(BaseModel):
    title: str
    content: str
    event_id: Optional[int] = None
    target_audience: Optional[str] = None

class AnnouncementCreate(AnnouncementBase):
    variants: Optional[str] = None

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    target_audience: Optional[str] = None
    status: Optional[str] = None
    variants: Optional[str] = None

class AnnouncementResponse(AnnouncementBase):
    id: int
    status: str
    variants: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AnnouncementGenerateRequest(BaseModel):
    event_id: int
    tone: Optional[str] = "engaging"
    target_audience: Optional[str] = None
    key_highlights: Optional[List[str]] = None

class AnnouncementGenerateResponse(BaseModel):
    title: str
    content: str
    event_id: int
    event_title: str
    event_date: Optional[str] = None
    venue: Optional[str] = None

class EmailVariant(BaseModel):
    subject: str
    body: str

class InstagramVariant(BaseModel):
    caption: str
    hashtags: List[str]

class AnnouncementVariantsResponse(BaseModel):
    announcement_id: Optional[int] = None
    whatsapp: str
    email: EmailVariant
    instagram: InstagramVariant
