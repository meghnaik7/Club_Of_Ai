from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.db.base_class import Base


class ProposalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    UNDONE = "UNDONE"


class ProposalChangeAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class AIProposal(Base):
    __tablename__ = "ai_proposals"

    id = Column(Integer, primary_key=True, index=True)
    intent = Column(Text, nullable=False)  # The original user brief
    status = Column(Enum(ProposalStatus), default=ProposalStatus.PENDING, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    changes = relationship("AIProposalChange", back_populates="proposal", cascade="all, delete-orphan")
    creator = relationship("User", backref="proposals")


class AIProposalChange(Base):
    __tablename__ = "ai_proposal_changes"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("ai_proposals.id"), nullable=False)
    entity_type = Column(String, nullable=False)  # "Event", "Task", "Subtask"
    entity_id = Column(Integer, nullable=True)    # Null before apply; set after apply
    action = Column(Enum(ProposalChangeAction), default=ProposalChangeAction.CREATE, nullable=False)
    proposed_data = Column(JSON, nullable=False)  # The data to be applied
    previous_data = Column(JSON, nullable=True)   # Populated on apply for undo support
    explanation = Column(Text, nullable=True)     # Human-readable explanation

    proposal = relationship("AIProposal", back_populates="changes")
