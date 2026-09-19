from langchain_core.tools import tool
from typing import Optional
from app.db.session import SessionLocal
from app.services import document_service

# For AI Tools we usually instantiate a local DB session within the tool
def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@tool
def upload_document(filepath: str, name: str, category: Optional[str] = None, event_id: Optional[int] = None) -> str:
    """Store a PDF, DOCX, or TXT document and associate it with an event/category."""
    db = SessionLocal()
    try:
        # Simplistic wrapper for AI agent usage. Real file upload goes through API endpoint.
        return f"Tool stub: Document '{name}' from {filepath} logic would trigger here."
    finally:
        db.close()

@tool
def list_documents(event_id: Optional[int] = None, category: Optional[str] = None, search: Optional[str] = None) -> list:
    """Retrieve documents associated with an event with optional category/search filters."""
    db = SessionLocal()
    try:
        docs = document_service.list_documents(db, event_id=event_id, category=category, search=search)
        return [{"id": d.id, "name": d.name, "category": d.category} for d in docs]
    finally:
        db.close()

@tool
def get_document(document_id: int) -> dict:
    """Retrieve document metadata such as name, category, event, and upload date."""
    db = SessionLocal()
    try:
        doc = document_service.get_document(db, document_id)
        if not doc:
            return {"error": "Not found"}
        return {"id": doc.id, "name": doc.name, "category": doc.category, "created_at": str(doc.created_at)}
    finally:
        db.close()

@tool
def delete_document(document_id: int) -> bool:
    """Remove a document and its associated indexed content."""
    db = SessionLocal()
    try:
        return document_service.delete_document(db, document_id)
    finally:
        db.close()

@tool
def search_documents(query: str, event_id: Optional[int] = None, category: Optional[str] = None) -> list:
    """Search uploaded documents for relevant content."""
    db = SessionLocal()
    try:
        return document_service.search_documents(db, query, event_id, category)
    finally:
        db.close()

@tool
def ask_documents(question: str, event_id: Optional[int] = None, category: Optional[str] = None) -> dict:
    """Answer a question using uploaded documents and return citations to supporting sources."""
    db = SessionLocal()
    try:
        return document_service.ask_documents(db, question, event_id, category)
    finally:
        db.close()

@tool
def extract_document_actions(document_id: int) -> list:
    """Identify decisions, action items, owners, and deadlines from a document."""
    db = SessionLocal()
    try:
        return document_service.extract_document_actions(db, document_id)
    finally:
        db.close()

@tool
def extract_document_decisions(document_id: int) -> list:
    """Identify important decisions and conclusions from a document."""
    db = SessionLocal()
    try:
        return document_service.extract_document_decisions(db, document_id)
    finally:
        db.close()

@tool
def find_relevant_past_lessons(query: str, event_id: Optional[int] = None) -> list:
    """Find relevant lessons, decisions, or previous-event information that may apply to the current event."""
    db = SessionLocal()
    try:
        lessons = document_service.find_relevant_past_lessons(db, query, event_id)
        return [{"topic": l.topic, "lesson": l.lesson, "impact": l.impact} for l in lessons]
    finally:
        db.close()
