import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class RAGChatHistory(Base):
    __tablename__ = "rag_chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    citations = Column(JSON, nullable=True) # List of sources or chunk references
    status = Column(String(50), default="COMPLETED")
    proposal_ids = Column(JSON, nullable=True) # Proposals linked to this answer
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    user = relationship("User", backref="chat_histories")
    event = relationship("Event", backref="rag_chat_histories")

    def __repr__(self):
        return f"<RAGChatHistory id={self.id} user={self.user_id} q='{self.question[:30]}...'>"
