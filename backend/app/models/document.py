import uuid
from datetime import datetime, timezone
import enum
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class DocumentCategory(str, enum.Enum):
    POST_MORTEM = "POST_MORTEM"
    SPONSOR_DECK = "SPONSOR_DECK"
    VENUE_RULES = "VENUE_RULES"
    BUDGET = "BUDGET"
    MEETING_NOTES = "MEETING_NOTES"
    OTHER = "OTHER"

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String(100), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(50), nullable=False) # PDF, DOCX, TXT, application/pdf
    file_size = Column(Integer, default=0, nullable=False) # bytes
    category = Column(SQLEnum(DocumentCategory), nullable=False, default=DocumentCategory.OTHER, index=True)
    uploader = Column(String(100), nullable=False, default="Admin")
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    raw_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def name(self) -> str:
        return self.filename

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    lessons = relationship("PastLesson", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        cat_val = self.category.value if hasattr(self.category, "value") else str(self.category)
        return f"<Document {self.filename} ({cat_val})>"

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True) # 1-indexed page for PDFs
    section_name = Column(String(255), nullable=True) # Heading / section for DOCX / TXT
    embedding = Column(JSON, nullable=True) # Stored vector as list of floats
    token_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        return f"<DocumentChunk doc={self.document_id} idx={self.chunk_index}>"

class PastLesson(Base):
    __tablename__ = "past_lessons"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=True)
    topic = Column(String, nullable=False, index=True)
    lesson = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    impact = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="lessons")
    event = relationship("Event", backref="past_lessons")
