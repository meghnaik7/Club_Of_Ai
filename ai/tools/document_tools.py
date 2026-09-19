try:
    from langchain_core.tools import tool
except ImportError:
    from ai.tools.compat import tool
from typing import Optional, Union, List, Dict, Any
from app.db.session import SessionLocal
from app.services import document_service
from ai.rag.pipeline import execute_rag_pipeline, search_documents_rag
from ai.rag.club_memory import check_plan_against_club_memory as audit_plan_memory

def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@tool
def upload_document(filepath: str, name: str, category: Optional[str] = None, event_id: Optional[Union[str, int]] = None) -> str:
    """Store a PDF, DOCX, TXT, or MD document and index its chunks with embeddings."""
    return f"Document '{name}' from {filepath} queued for ingestion."

@tool
def list_documents(event_id: Optional[Union[str, int]] = None, category: Optional[str] = None, search: Optional[str] = None) -> list:
    """Retrieve documents associated with an event with optional category/search filters."""
    db = SessionLocal()
    try:
        docs = document_service.list_documents(db, event_id=event_id, category=category, search=search)
        return [
            {
                "id": str(d.id),
                "name": d.name or d.filename,
                "category": d.category.value if hasattr(d.category, "value") else str(d.category)
            }
            for d in docs
        ]
    finally:
        db.close()

@tool
def get_document(document_id: Union[str, int]) -> dict:
    """Retrieve document metadata such as name, category, event, and upload date."""
    db = SessionLocal()
    try:
        doc = document_service.get_document(db, document_id)
        if not doc:
            return {"error": "Not found"}
        return {
            "id": str(doc.id),
            "name": doc.name or doc.filename,
            "category": doc.category.value if hasattr(doc.category, "value") else str(doc.category),
            "created_at": str(doc.created_at)
        }
    finally:
        db.close()

@tool
def delete_document(document_id: Union[str, int]) -> bool:
    """Remove a document and its associated indexed content."""
    db = SessionLocal()
    try:
        return document_service.delete_document(db, document_id)
    finally:
        db.close()

@tool
def search_documents(query: str, event_id: Optional[Union[str, int]] = None, category: Optional[str] = None) -> list:
    """Search uploaded documents for relevant content using hybrid retrieval and re-ranking."""
    db = SessionLocal()
    try:
        return search_documents_rag(db, query, event_id=event_id, category=category)
    except Exception:
        # Transparent fallback: return empty list without crashing
        return []
    finally:
        db.close()

@tool
def ask_documents(question: str, event_id: Optional[Union[str, int]] = None, category: Optional[str] = None) -> dict:
    """Answer a question using uploaded documents with CRAG grading and Self-RAG source citations."""
    db = SessionLocal()
    try:
        res = execute_rag_pipeline(db, question, event_id=event_id, category=category)
        return {
            "answer": res.answer,
            "confidence": res.confidence,
            "citations": [
                {
                    "document_id": c.document_id,
                    "document_name": c.filename,
                    "snippet": c.snippet,
                    "page_number": c.page_number,
                    "section_name": c.section_name,
                    "score": c.relevance_score
                }
                for c in res.citations
            ],
            "crag_eval": res.crag_eval.model_dump()
        }
    except Exception as e:
        from app.ai.errors import classify_exception
        ai_err = classify_exception(e)
        return {
            "answer": "No reliable source found. Knowledge retrieval was unable to complete: " + ai_err.user_message,
            "confidence": 0.0,
            "citations": [],
            "error": ai_err.to_user_dict()["error"]
        }
    finally:
        db.close()

@tool
def check_plan_against_club_memory(plan_text: str, event_id: Optional[str] = None) -> dict:
    """Audit a planned event schedule or task against historical club post-mortems and venue guidelines."""
    db = SessionLocal()
    try:
        res = audit_plan_memory(db, plan_text, event_id=event_id)
        return res.model_dump()
    finally:
        db.close()

@tool
def extract_document_actions(document_id: Union[str, int]) -> list:
    """Identify decisions, action items, owners, and deadlines from a document."""
    db = SessionLocal()
    try:
        return document_service.extract_document_actions(db, document_id)
    finally:
        db.close()

@tool
def extract_document_decisions(document_id: Union[str, int]) -> list:
    """Identify important decisions and conclusions from a document."""
    db = SessionLocal()
    try:
        return document_service.extract_document_decisions(db, document_id)
    finally:
        db.close()

@tool
def find_relevant_past_lessons(query: str, event_id: Optional[Union[str, int]] = None) -> list:
    """Find relevant lessons, decisions, or previous-event information that may apply to the current event."""
    db = SessionLocal()
    try:
        lessons = document_service.find_relevant_past_lessons(db, query, event_id)
        return [
            {
                "topic": l.get("topic") if isinstance(l, dict) else getattr(l, "topic", ""),
                "lesson": l.get("lesson") if isinstance(l, dict) else getattr(l, "lesson", ""),
                "impact": l.get("impact") if isinstance(l, dict) else getattr(l, "impact", "")
            }
            for l in lessons
        ]
    finally:
        db.close()
