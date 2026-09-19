from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    date = Column(DateTime, default=datetime.utcnow, nullable=False)
    location = Column(String(255), nullable=True)
    attendees = Column(JSON, nullable=True) # List of attendee names or details
    raw_notes = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    event = relationship("Event", backref="meetings")
    action_items = relationship("MeetingActionItem", back_populates="meeting", cascade="all, delete-orphan")


class MeetingActionItem(Base):
    __tablename__ = "meeting_action_items"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_text = Column(Text, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    suggested_owner_name = Column(String(100), nullable=True)
    resolved_volunteer_id = Column(Integer, ForeignKey("volunteers.id", ondelete="SET NULL"), nullable=True)
    suggested_due_date = Column(DateTime, nullable=True)
    due_date_raw = Column(String(100), nullable=True)
    priority = Column(String(50), default="MEDIUM", nullable=False)
    confidence = Column(Float, default=0.85, nullable=False)
    status = Column(String(50), default="PENDING", nullable=False) # PENDING, APPROVED, REJECTED, APPLIED
    applied_task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    meeting = relationship("Meeting", back_populates="action_items")
    resolved_volunteer = relationship("Volunteer")
    applied_task = relationship("Task")
