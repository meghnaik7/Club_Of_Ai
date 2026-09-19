from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class DocumentBase(BaseModel):
    name: str
    category: Optional[str] = None
    event_id: Optional[int] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None

class DocumentResponse(DocumentBase):
    id: int
    filename: str
    file_type: str
    file_size: int
    summary: Optional[str] = None
    uploaded_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DocumentCitation(BaseModel):
    document_id: int
    document_name: str
    chunk_id: Optional[int] = None
    excerpt: str
    page_number: Optional[int] = None

class DocumentAskRequest(BaseModel):
    question: str
    event_id: Optional[int] = None
    category: Optional[str] = None

class DocumentAskResponse(BaseModel):
    answer: str
    citations: List[DocumentCitation]

class DocumentActionItem(BaseModel):
    action: str
    owner: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None
    context: Optional[str] = None

class DocumentActionsResponse(BaseModel):
    document_id: int
    document_name: str
    actions: List[DocumentActionItem]

class DocumentDecisionItem(BaseModel):
    decision: str
    rationale: Optional[str] = None
    impact: Optional[str] = None
    date_or_context: Optional[str] = None

class DocumentDecisionsResponse(BaseModel):
    document_id: int
    document_name: str
    decisions: List[DocumentDecisionItem]

class PastLessonItem(BaseModel):
    id: int
    document_id: Optional[int] = None
    event_id: Optional[int] = None
    topic: str
    lesson: str
    category: Optional[str] = None
    impact: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class PastLessonsResponse(BaseModel):
    query: Optional[str] = None
    lessons: List[PastLessonItem]
