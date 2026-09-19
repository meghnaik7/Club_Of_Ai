import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class MemoryType(str, enum.Enum):
    USER_PREFERENCE = "USER_PREFERENCE"
    WORKING_PREFERENCE = "WORKING_PREFERENCE"
    CLUB_KNOWLEDGE = "CLUB_KNOWLEDGE"
    EVENT_LESSON = "EVENT_LESSON"
    IMPORTANT_DECISION = "IMPORTANT_DECISION"
    VOLUNTEER_KNOWLEDGE = "VOLUNTEER_KNOWLEDGE"
    PROCESS_RULE = "PROCESS_RULE"
    OTHER = "OTHER"

class MemoryScope(str, enum.Enum):
    USER = "USER"
    CLUB = "CLUB"
    EVENT = "EVENT"
    VOLUNTEER = "VOLUNTEER"

class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    club_id = Column(Integer, nullable=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True, index=True)
    
    memory_type = Column(String(50), nullable=False, default=MemoryType.OTHER.value, index=True)
    scope = Column(String(50), nullable=False, default=MemoryScope.USER.value, index=True)
    
    content = Column(Text, nullable=False)
    structured_data = Column(JSON, nullable=True)
    
    importance = Column(Float, nullable=False, default=0.5)
    confidence = Column(Float, nullable=False, default=1.0)
    source = Column(String(100), default="conversation")
    
    # Normalized vector embedding (list of floats) for semantic retrieval
    embedding = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="memories")
    event = relationship("Event", backref="memories")

    def __repr__(self):
        return f"<Memory id={self.id} type={self.memory_type} scope={self.scope} content='{self.content[:30]}...'>"
