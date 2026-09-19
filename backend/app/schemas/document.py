from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models.document import DocumentCategory

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
