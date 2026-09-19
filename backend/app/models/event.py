from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.db.base_class import Base


class EventStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    date = Column(DateTime, nullable=False)
    venue = Column(String, nullable=True)
    budget = Column(Float, default=0.0)
    budget_spent = Column(Float, default=0.0)
    expected_attendance = Column(Integer, default=0)
    status = Column(Enum(EventStatus), default=EventStatus.DRAFT, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", backref="created_events")
