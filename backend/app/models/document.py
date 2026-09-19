from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base_class import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=True)
    name = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    category = Column(String, nullable=True, index=True)
    raw_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event = relationship("Event", backref="documents")
    uploader = relationship("User", backref="uploaded_documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    lessons = relationship("PastLesson", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)

    document = relationship("Document", back_populates="chunks")

class PastLesson(Base):
    __tablename__ = "past_lessons"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=True)
    topic = Column(String, nullable=False, index=True)
    lesson = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    impact = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="lessons")
    event = relationship("Event", backref="past_lessons")
