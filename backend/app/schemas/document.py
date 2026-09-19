from typing import Optional, List, Union
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.document import DocumentCategory

class DocumentBase(BaseModel):
    name: Optional[str] = None
    category: Optional[Union[str, DocumentCategory]] = None
    event_id: Optional[Union[int, str]] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[Union[str, DocumentCategory]] = None

class DocumentResponse(DocumentBase):
    id: Union[str, int]
    filename: str
    file_type: str
    file_size: int
    summary: Optional[str] = None
    uploaded_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class DocumentCitation(BaseModel):
    document_id: Union[int, str]
    document_name: str
    chunk_id: Optional[Union[int, str]] = None
    excerpt: str
    page_number: Optional[int] = None

class DocumentAskRequest(BaseModel):
    question: str
    event_id: Optional[Union[int, str]] = None
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
    document_id: Union[int, str]
    document_name: str
    actions: List[DocumentActionItem]

class DocumentDecisionItem(BaseModel):
    decision: str
    rationale: Optional[str] = None
    impact: Optional[str] = None
    date_or_context: Optional[str] = None

class DocumentDecisionsResponse(BaseModel):
    document_id: Union[int, str]
    document_name: str
    decisions: List[DocumentDecisionItem]

class PastLessonItem(BaseModel):
    id: int
    document_id: Optional[Union[int, str]] = None
    event_id: Optional[Union[int, str]] = None
    topic: str
    lesson: str
    category: Optional[str] = None
    impact: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class PastLessonsResponse(BaseModel):
    query: Optional[str] = None
    lessons: List[PastLessonItem]

# RAG and Memory schemas from origin/megh
class DocumentChunkRead(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    section_name: Optional[str] = None
    token_count: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DocumentRead(BaseModel):
    id: str
    event_id: Optional[str] = None
    filename: str
    file_type: str
    file_size: int
    category: DocumentCategory
    uploader: str
    summary: Optional[str] = None
    chunk_count: int = 0
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DocumentListResponse(BaseModel):
    items: List[DocumentRead]
    total: int

class CitationSchema(BaseModel):
    document_id: str
    filename: str
    category: str
    page_number: Optional[int] = None
    section_name: Optional[str] = None
    chunk_index: int
    snippet: str
    relevance_score: float

class CRAGEvaluation(BaseModel):
    retrieved_count: int
    relevant_count: int
    filtered_noise_count: int
    is_grounded: bool
    evaluation_notes: str

class RAGQueryRequest(BaseModel):
    query: str
    event_id: Optional[str] = None
    category: Optional[DocumentCategory] = None
    top_k: int = 5

class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    confidence: float
    citations: List[CitationSchema]
    crag_eval: CRAGEvaluation

class ClubMemoryPlanCheckRequest(BaseModel):
    plan_text: str
    event_id: Optional[str] = None

class ClubMemoryLessonRecommendation(BaseModel):
    lesson: str
    historical_context: str
    recommendation: str
    risk_level: str # LOW, MEDIUM, HIGH
    citations: List[CitationSchema]

class ClubMemoryPlanCheckResponse(BaseModel):
    plan_text: str
    surfaced_lessons_count: int
    recommendations: List[ClubMemoryLessonRecommendation]
    overall_risk_assessment: str
