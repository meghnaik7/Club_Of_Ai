from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Text
from datetime import datetime

from app.db.base_class import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("ai_proposals.id"), nullable=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)        # CREATE / UPDATE / DELETE
    previous_state = Column(JSON, nullable=True)   # State before change (for undo)
    new_state = Column(JSON, nullable=True)        # State after change
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
