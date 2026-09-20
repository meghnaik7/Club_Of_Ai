from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base_class import Base


class AIFeedback(Base):
    """
    Stores human-in-the-loop evaluation and feedback on AI proposals, recovery plans, and actions.
    Enables closed-loop adaptive ranking, proposal acceptance tracking, and model evaluation.
    """
    __tablename__ = "ai_feedback"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("ai_proposals.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)
    
    # Rating: "GOOD" (👍) or "POOR" (👎)
    rating = Column(String, nullable=False)
    
    # Type / Categorized reason:
    # "positive_execution", "wrong_volunteer", "deadline_unrealistic",
    # "missing_dependency", "too_many_changes", "other"
    feedback_type = Column(String, nullable=True)
    
    # Optional qualitative feedback
    comment = Column(Text, nullable=True)
    
    # Arbitrary structured metadata (e.g. penalized volunteer IDs, affected task IDs)
    metadata_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    proposal = relationship("AIProposal", backref="feedbacks")
    user = relationship("User", backref="ai_feedbacks")
    event = relationship("Event", backref="ai_feedbacks")
