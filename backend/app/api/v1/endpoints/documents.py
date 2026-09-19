import os
import uuid
import shutil
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.config import settings
from app.models.document import Document, DocumentChunk, DocumentCategory
from app.schemas.document import (
    DocumentRead,
    DocumentListResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    ClubMemoryPlanCheckRequest,
    ClubMemoryPlanCheckResponse
)
from app.services.document_parser import parse_and_chunk_document
from app.services.embeddings import generate_embedding
from app.services.rag_engine import execute_rag_pipeline
from app.services.club_memory import check_plan_against_club_memory

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    category: DocumentCategory = Form(DocumentCategory.OTHER),
    event_id: Optional[str] = Form(None),
    uploader: str = Form("Club Lead"),
    db: Session = Depends(get_db)
):
    """
    Uploads a document (PDF, DOCX, TXT), extracts text, chunks it with metadata,
    generates embeddings, and stores document and chunk records.
    """
    # 1. Validate file extension
    filename = file.filename or "uploaded_file"
    _, ext = os.path.splitext(filename)
    ext_lower = ext.lower()

    if ext_lower not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats: PDF, DOCX, TXT"
        )

    file_type = ext_lower.lstrip(".").upper()
    if file_type == "MD":
        file_type = "TXT"

    # 2. Save physical file
    doc_id = str(uuid.uuid4())
    safe_filename = f"{doc_id}_{filename}"
    saved_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    try:
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = os.path.getsize(saved_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write file to disk: {str(e)}"
        )

    # 3. Parse and chunk the document
    try:
        parsed_chunks = parse_and_chunk_document(
            file_path=saved_path,
            file_type=file_type,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
    except Exception as e:
        # Cleanup uploaded file if parsing fails
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error parsing document content: {str(e)}"
        )

    if not parsed_chunks:
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded document contains no readable text content."
        )

    # 4. Create Document DB record
    db_doc = Document(
        id=doc_id,
        event_id=event_id,
        filename=filename,
        file_path=saved_path,
        file_type=file_type,
        file_size=file_size,
        category=category,
        uploader=uploader,
        summary=f"Parsed {len(parsed_chunks)} chunks from {file_type} file."
    )
    db.add(db_doc)
    db.flush()

    # 5. Generate embeddings and save chunks
    for p_chunk in parsed_chunks:
        emb_vec = generate_embedding(p_chunk.content)
        db_chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            chunk_index=p_chunk.chunk_index,
            content=p_chunk.content,
            page_number=p_chunk.page_number,
            section_name=p_chunk.section_name,
            embedding=emb_vec,
            token_count=p_chunk.token_count
        )
        db.add(db_chunk)

    db.commit()
    db.refresh(db_doc)

    return DocumentRead(
        id=db_doc.id,
        event_id=db_doc.event_id,
        filename=db_doc.filename,
        file_type=db_doc.file_type,
        file_size=db_doc.file_size,
        category=db_doc.category,
        uploader=db_doc.uploader,
        summary=db_doc.summary,
        chunk_count=len(parsed_chunks),
        created_at=db_doc.created_at
    )

@router.get("", response_model=DocumentListResponse)
def list_documents(
    category: Optional[DocumentCategory] = Query(None),
    event_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Lists all stored documents with optional category/event filtering and search."""
    q = db.query(Document)

    if category:
        q = q.filter(Document.category == category)
    if event_id:
        q = q.filter(Document.event_id == event_id)
    if search:
        search_pattern = f"%{search.strip()}%"
        q = q.filter(or_(
            Document.filename.ilike(search_pattern),
            Document.uploader.ilike(search_pattern)
        ))

    total = q.count()
    docs = q.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()

    items = []
    for d in docs:
        items.append(DocumentRead(
            id=d.id,
            event_id=d.event_id,
            filename=d.filename,
            file_type=d.file_type,
            file_size=d.file_size,
            category=d.category,
            uploader=d.uploader,
            summary=d.summary,
            chunk_count=len(d.chunks),
            created_at=d.created_at
        ))

    return DocumentListResponse(items=items, total=total)

@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Retrieves document metadata by ID."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return DocumentRead(
        id=doc.id,
        event_id=doc.event_id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        category=doc.category,
        uploader=doc.uploader,
        summary=doc.summary,
        chunk_count=len(doc.chunks),
        created_at=doc.created_at
    )

@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Deletes a document, cascades its chunks, and removes the physical file."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Delete physical file
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass

    db.delete(doc)
    db.commit()

    return {"status": "deleted", "id": document_id, "message": f"Document '{doc.filename}' deleted successfully."}

@router.post("/rag/query", response_model=RAGQueryResponse)
def query_rag(request: RAGQueryRequest, db: Session = Depends(get_db)):
    """
    RAG query using Corrective RAG (CRAG) document grading and Self-RAG
    reflection to return factual answers with exact source citations.
    """
    if not request.query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty")

    return execute_rag_pipeline(
        db=db,
        query=request.query,
        event_id=request.event_id,
        category=request.category,
        top_k=request.top_k
    )

@router.post("/club-memory/check-plan", response_model=ClubMemoryPlanCheckResponse)
def check_event_plan(request: ClubMemoryPlanCheckRequest, db: Session = Depends(get_db)):
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
