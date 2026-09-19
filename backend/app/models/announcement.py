from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base_class import Base

class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    target_audience = Column(String, nullable=True)
    status = Column(String, default="DRAFT", index=True)
    variants = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event = relationship("Event", backref="announcements")
    author = relationship("User", backref="created_announcements")
