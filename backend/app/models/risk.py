from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class EventRisk(Base):
    __tablename__ = "event_risks"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    category = Column(String(50), nullable=False) # SCHEDULING, OWNERSHIP, DEPENDENCY, WORKLOAD, MISSING_ACTIVITY, BUDGET
    severity = Column(String(20), nullable=False, default="MEDIUM") # CRITICAL, HIGH, MEDIUM, LOW
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    root_cause = Column(Text, nullable=True)
    suggested_fix = Column(Text, nullable=True)
    status = Column(String(20), default="ACTIVE", nullable=False) # ACTIVE, RESOLVED, IGNORED
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    event = relationship("Event", back_populates="risks")
    task = relationship("Task")

    def __repr__(self):
        return f"<EventRisk {self.id}: [{self.severity}] {self.title} ({self.status})>"
