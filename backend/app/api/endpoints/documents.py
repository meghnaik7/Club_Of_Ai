from typing import Any, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app import schemas
from app.api import deps
from app.services import document_service
from app.models.user import User
from app.models.document import DocumentCategory
from app.models.chat_history import RAGChatHistory
from ai.rag.pipeline import execute_rag_pipeline
from ai.rag.club_memory import check_plan_against_club_memory

router = APIRouter()

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}

@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    event_id: Optional[str] = Form(None),
    uploader: Optional[str] = Form("Club Lead"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Upload a new document (PDF, DOCX, TXT, MD) and chunk it with embeddings."""
    from app.services.authz import AuthorizationService
    AuthorizationService.require_permission(db, current_user, "document.upload")

    filename = file.filename or "uploaded_file"
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '.{ext}'. Allowed formats: PDF, DOCX, TXT, MD"
        )

    file_type = "TXT" if ext == "md" else ext.upper()
    doc_name = name or filename

    doc = document_service.upload_document(
        db=db,
        file_obj=file.file,
        filename=filename,
        file_type=file_type,
        name=doc_name,
        category=category,
        event_id=event_id,
        user_id=current_user.id
    )

    return {
        "id": doc.id,
        "name": doc.name or doc.filename,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "category": doc.category.value if hasattr(doc.category, "value") else str(doc.category),
        "event_id": doc.event_id,
        "uploader": doc.uploader,
        "chunk_count": len(doc.chunks),
        "created_at": doc.created_at
    }

@router.get("/")
def list_documents(
    event_id: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
) -> Any:
    """List documents with optional category or search filters."""
    docs = document_service.list_documents(db, event_id=event_id, category=category, search=search, skip=skip, limit=limit)
    items = []
    for d in docs:
        items.append({
            "id": d.id,
            "name": d.name or d.filename,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "category": d.category.value if hasattr(d.category, "value") else str(d.category),
            "event_id": d.event_id,
            "uploader": d.uploader,
            "chunk_count": len(d.chunks),
            "created_at": d.created_at
        })
    return {"items": items, "total": len(items)}

@router.get("/{document_id}")
def get_document(
    document_id: str,
    db: Session = Depends(deps.get_db),
) -> Any:
    doc = document_service.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return {
        "id": doc.id,
        "name": doc.name or doc.filename,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "category": doc.category.value if hasattr(doc.category, "value") else str(doc.category),
        "event_id": doc.event_id,
        "uploader": doc.uploader,
        "chunk_count": len(doc.chunks),
        "created_at": doc.created_at
    }

@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    from app.services.authz import AuthorizationService
    AuthorizationService.require_permission(db, current_user, "document.delete")

    success = document_service.delete_document(db, document_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return {"ok": True, "message": f"Document '{document_id}' deleted successfully."}

@router.post("/search")
def search_documents(
    query: str,
    event_id: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 5,
    db: Session = Depends(deps.get_db),
) -> Any:
    """Hybrid lexical-semantic document search with re-ranking."""
    return document_service.search_documents(db, query, event_id=event_id, category=category, limit=limit)

@router.get("/rag/history")
def get_rag_chat_history(
    event_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """Returns past asked questions and answers for the user / event."""
    query = db.query(RAGChatHistory)
    if current_user:
        query = query.filter(RAGChatHistory.user_id == current_user.id)
    if event_id:
        try:
            query = query.filter(RAGChatHistory.event_id == int(event_id))
        except ValueError:
            pass
    records = query.order_by(RAGChatHistory.created_at.asc()).limit(limit).all()
    return {
        "items": [
            {
                "id": r.id,
                "question": r.question,
                "answer": r.answer,
                "citations": r.citations or [],
                "status": r.status,
                "proposal_ids": r.proposal_ids or [],
                "event_id": r.event_id,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in records
        ],
        "total": len(records)
    }

@router.delete("/rag/history")
def clear_rag_chat_history(
    event_id: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """Clears past RAG chat history for the user."""
    query = db.query(RAGChatHistory)
    if current_user:
        query = query.filter(RAGChatHistory.user_id == current_user.id)
    if event_id:
        try:
            query = query.filter(RAGChatHistory.event_id == int(event_id))
        except ValueError:
            pass
    count = query.delete(synchronize_session=False)
    db.commit()
    return {"ok": True, "deleted_count": count}

@router.post("/ask", response_model=schemas.DocumentAskResponse)
def ask_documents(
    request: schemas.DocumentAskRequest,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """Answer question with source citations via CRAG + Self-RAG and persist turn."""
    res = document_service.ask_documents(db, request.question, request.event_id, request.category)
    try:
        ev_id = int(request.event_id) if request.event_id and str(request.event_id).isdigit() else None
        safe_citations = []
        for s in (getattr(res, "citations", None) or getattr(res, "sources", None) or []):
            safe_citations.append({
                "source": getattr(s, "source", str(s)),
                "page": getattr(s, "page_number", None),
                "section": getattr(s, "section_name", None)
            })
        history_entry = RAGChatHistory(
            user_id=current_user.id if current_user else None,
            event_id=ev_id,
            question=request.question,
            answer=res.answer,
            citations=safe_citations,
            status="COMPLETED"
        )
        db.add(history_entry)
        db.commit()
    except Exception:
        db.rollback()
    return res

@router.post("/rag/query", response_model=schemas.RAGQueryResponse)
def query_rag(
    request: schemas.RAGQueryRequest,
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> Any:
    """
    RAG query using Hybrid Retrieval, Re-ranking, Corrective RAG (CRAG) grading,
    and Self-RAG reflection to return factual answers with source citations.
    Saves question and answer into persistent history.
    """
    if not request.query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty")

    res = execute_rag_pipeline(
        db=db,
        query=request.query,
        event_id=request.event_id,
        category=request.category,
        top_k=request.top_k
    )
    try:
        ev_id = int(request.event_id) if request.event_id and str(request.event_id).isdigit() else None
        safe_citations = []
        for s in (getattr(res, "citations", None) or getattr(res, "sources", None) or []):
            safe_citations.append({
                "source": getattr(s, "source", str(s)),
                "page": getattr(s, "page_number", None),
                "section": getattr(s, "section_name", None)
            })
        history_entry = RAGChatHistory(
            user_id=current_user.id if current_user else None,
            event_id=ev_id,
            question=request.query,
            answer=res.answer,
            citations=safe_citations,
            status="COMPLETED"
        )
        db.add(history_entry)
        db.commit()
    except Exception:
        db.rollback()
    return res


@router.post("/club-memory/check-plan", response_model=schemas.ClubMemoryPlanCheckResponse)
def check_event_plan(
    request: schemas.ClubMemoryPlanCheckRequest,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Proactive Club Memory check: Compares a planned task/operation against historical
    lessons, post-mortems, and venue rules, surfacing recommendations with citations.
    """
    if not request.plan_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan text cannot be empty")

    return check_plan_against_club_memory(
        db=db,
        plan_text=request.plan_text,
        event_id=request.event_id
    )

@router.post("/{document_id}/extract-actions")
def extract_document_actions(
    document_id: str,
    db: Session = Depends(deps.get_db),
) -> Any:
    return document_service.extract_document_actions(db, document_id)

@router.post("/{document_id}/extract-decisions")
def extract_document_decisions(
    document_id: str,
    db: Session = Depends(deps.get_db),
) -> Any:
    return document_service.extract_document_decisions(db, document_id)

@router.get("/past-lessons")
def find_relevant_past_lessons(
    query: str,
    event_id: Optional[str] = None,
    db: Session = Depends(deps.get_db),
) -> Any:
    return document_service.find_relevant_past_lessons(db, query, event_id)
