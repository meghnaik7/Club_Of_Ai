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
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    club = relationship("Club", foreign_keys=[club_id])
    creator = relationship("User", backref="created_events")
    tasks = relationship("Task", backref="event", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="event", cascade="all, delete-orphan")
    budget_categories = relationship("EventBudgetCategory", back_populates="event", cascade="all, delete-orphan")
    risks = relationship("EventRisk", back_populates="event", cascade="all, delete-orphan")
    meetings = relationship("Meeting", back_populates="event", cascade="all, delete-orphan")
    escalations = relationship("TaskEscalation", back_populates="event", cascade="all, delete-orphan")
    event_memberships = relationship("EventMembership", back_populates="event", cascade="all, delete-orphan")


class EventBudgetCategory(Base):
    __tablename__ = "event_budget_categories"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    allocated_amount = Column(Float, default=0.0, nullable=False)

    event = relationship("Event", back_populates="budget_categories")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(100), nullable=True) # e.g., Venue, Catering, Marketing, Logistics, Prizes
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Float, nullable=False)
    description = Column(String(255), nullable=True)
    recorded_by = Column(String(100), nullable=True)
    date = Column(DateTime, default=datetime.utcnow, nullable=False)

    event = relationship("Event", back_populates="expenses")
    task = relationship("Task")
