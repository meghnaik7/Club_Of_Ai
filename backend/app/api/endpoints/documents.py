from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app import schemas
from app.api import deps
from app.services import document_service
from app.models.user import User

router = APIRouter()

@router.post("/upload", response_model=schemas.DocumentResponse)
def upload_document(
    file: UploadFile = File(...),
    name: str = Form(...),
    category: Optional[str] = Form(None),
    event_id: Optional[int] = Form(None),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Upload a new document."""
    ext = file.filename.split(".")[-1].lower() if file.filename else ""
    if ext not in ["pdf", "docx", "txt"]:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, or TXT allowed")
        
    doc = document_service.upload_document(
        db, file.file, file.filename, ext, name, category, event_id, current_user.id
    )
    return doc

@router.get("/", response_model=List[schemas.DocumentResponse])
def list_documents(
    event_id: Optional[int] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """List documents."""
    return document_service.list_documents(db, event_id, category, search, skip, limit)

@router.get("/{document_id}", response_model=schemas.DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    doc = document_service.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    success = document_service.delete_document(db, document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True}

@router.post("/search")
def search_documents(
    query: str,
    event_id: Optional[int] = None,
    category: Optional[str] = None,
    limit: int = 5,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    return document_service.search_documents(db, query, event_id, category, limit)

@router.post("/ask", response_model=schemas.DocumentAskResponse)
def ask_documents(
    request: schemas.DocumentAskRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    return document_service.ask_documents(db, request.question, request.event_id, request.category)

@router.post("/{document_id}/extract-actions")
def extract_document_actions(
    document_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    return document_service.extract_document_actions(db, document_id)

@router.post("/{document_id}/extract-decisions")
def extract_document_decisions(
    document_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    return document_service.extract_document_decisions(db, document_id)

@router.get("/past-lessons")
def find_relevant_past_lessons(
    query: str,
    event_id: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    return document_service.find_relevant_past_lessons(db, query, event_id)
