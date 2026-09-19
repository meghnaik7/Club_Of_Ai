import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class EscalationLevel(str, enum.Enum):
    NONE = "NONE"
    CANDIDATE = "CANDIDATE"
    TEAM_LEADER = "TEAM_LEADER"
    MAIN_LEADER = "MAIN_LEADER"

class EscalationStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"

class TaskEscalation(Base):
    __tablename__ = "task_escalations"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    
    level = Column(String(50), nullable=False, default=EscalationLevel.NONE.value, index=True)
    status = Column(String(50), nullable=False, default=EscalationStatus.PENDING.value, index=True)
    
    rule_triggered = Column(String(100), nullable=True)
    reason = Column(Text, nullable=False)
    is_critical_path = Column(Boolean, default=False, nullable=False)
    
    # Notification audit & idempotency tracking
    team_leader_notified_at = Column(DateTime, nullable=True)
    main_leader_notified_at = Column(DateTime, nullable=True)
    notification_count = Column(Integer, default=0, nullable=False)
    
    # Acknowledgment & Resolution tracking
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_note = Column(Text, nullable=True)
    
    # Scheduled promotion if unresolved
    next_escalation_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    task = relationship("Task", backref="escalations")
    event = relationship("Event", backref="task_escalations")
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])

    def __repr__(self):
        return f"<TaskEscalation id={self.id} task_id={self.task_id} level={self.level} status={self.status}>"
