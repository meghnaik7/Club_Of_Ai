import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class NotificationType(str, enum.Enum):
    TASK_OVERDUE = "TASK_OVERDUE"
    TASK_OVERDUE_ESCALATION = "TASK_OVERDUE_ESCALATION"
    UNASSIGNED_TASK_OVERDUE = "UNASSIGNED_TASK_OVERDUE"


class NotificationStatus(str, enum.Enum):
    UNREAD = "UNREAD"
    READ = "READ"


class NotificationSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class EscalationLevelRole(str, enum.Enum):
    TEAM_LEAD = "TEAM_LEAD"
    HEAD = "HEAD"
    ADMIN = "ADMIN"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    volunteer_id = Column(Integer, ForeignKey("volunteers.id", ondelete="SET NULL"), nullable=True, index=True)

    notification_type = Column(String(50), nullable=False, default=NotificationType.TASK_OVERDUE.value, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), default=NotificationSeverity.WARNING.value, nullable=False)
    escalation_level = Column(String(50), nullable=False, default=EscalationLevelRole.TEAM_LEAD.value, index=True)
    status = Column(String(20), nullable=False, default=NotificationStatus.UNREAD.value, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    read_at = Column(DateTime, nullable=True)

    # Relationships
    recipient = relationship("User", foreign_keys=[recipient_id])
    event = relationship("Event", foreign_keys=[event_id])
    task = relationship("Task", foreign_keys=[task_id])
    volunteer = relationship("Volunteer", foreign_keys=[volunteer_id])

    __table_args__ = (
        UniqueConstraint(
            "task_id",
            "recipient_id",
            "notification_type",
            "escalation_level",
            name="uq_notifications_task_recipient_type_level"
        ),
    )

    def __repr__(self):
        return (
            f"<Notification id={self.id} recipient_id={self.recipient_id} "
            f"task_id={self.task_id} type={self.notification_type} level={self.escalation_level}>"
        )
