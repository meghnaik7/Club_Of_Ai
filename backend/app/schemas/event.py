from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.event import EventStatus


class EventBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[datetime] = None
    venue: Optional[str] = None
    budget: Optional[float] = 0.0
    budget_spent: Optional[float] = 0.0
    expected_attendance: Optional[int] = 0
    status: Optional[EventStatus] = EventStatus.DRAFT


class EventCreate(EventBase):
    title: str
    date: datetime


class EventUpdate(EventBase):
    pass


class EventInDBBase(EventBase):
    id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class Event(EventInDBBase):
    pass
