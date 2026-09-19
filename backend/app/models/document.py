import uuid
from datetime import datetime, timezone
import enum
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

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
    file_type = Column(String(10), nullable=False) # PDF, DOCX, TXT
    file_size = Column(Integer, nullable=False) # bytes
    category = Column(SQLEnum(DocumentCategory), nullable=False, default=DocumentCategory.OTHER, index=True)
    uploader = Column(String(100), nullable=False, default="Admin")
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document {self.filename} ({self.category.value})>"

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
