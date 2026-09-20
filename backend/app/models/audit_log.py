from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Text
from datetime import datetime

from app.db.base_class import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("ai_proposals.id"), nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Backward compatibility
    action = Column(String, nullable=False)        # CREATE / UPDATE / DELETE / ASSIGN / PROMOTE / etc.
    entity_type = Column(String, nullable=False)   # task / team / member / permission / etc.
    entity_id = Column(Integer, nullable=False)
    scope_type = Column(String, nullable=True)     # GLOBAL / CLUB / TEAM / EVENT / TASK
    scope_id = Column(Integer, nullable=True)
    previous_state = Column(JSON, nullable=True)   # State before change (for undo)
    new_state = Column(JSON, nullable=True)        # State after change
    meta_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
