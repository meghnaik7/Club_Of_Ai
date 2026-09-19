import os
import shutil
import json
import uuid
import re
import logging
from typing import List, Optional, Tuple, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.models.document import Document, DocumentChunk, PastLesson, DocumentCategory
from app.services.document_parser import parse_and_chunk_document, extract_text
from ai.rag.embeddings import generate_embedding
from ai.rag.pipeline import execute_rag_pipeline, search_documents_rag
from ai.rag.club_memory import check_plan_against_club_memory

logger = logging.getLogger(__name__)

# LLM setup if Gemini is configured
genai_client = None
if settings.GEMINI_API_KEY:
    try:
        from google import genai
        genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception:
        genai_client = None

def upload_document(
    db: Session,
    file_obj,
    filename: str,
    file_type: str,
    name: str,
    category: Optional[Union[str, DocumentCategory]] = None,
    event_id: Optional[Union[str, int]] = None,
    user_id: Optional[int] = None
) -> Document:
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    doc_id = str(uuid.uuid4())
    safe_filename = f"{doc_id}_{filename}"
    file_path = os.path.join(upload_dir, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file_obj, buffer)

    file_size = os.path.getsize(file_path)

    # Parse and chunk document with metadata
    parsed_chunks = parse_and_chunk_document(
        file_path=file_path,
        file_type=file_type.upper().lstrip("."),
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP
    )

    raw_text = "\n\n".join([c.content for c in parsed_chunks]) if parsed_chunks else ""

    cat_enum = category if isinstance(category, DocumentCategory) else None
    if cat_enum is None and category:
        try:
            cat_enum = DocumentCategory(category)
        except ValueError:
            cat_enum = DocumentCategory.OTHER

    doc = Document(
        id=doc_id,
        event_id=str(event_id) if event_id is not None else None,
        name=name or filename,
        filename=filename,
        file_path=file_path,
        file_type=file_type.upper().lstrip("."),
        file_size=file_size,
        category=cat_enum or DocumentCategory.OTHER,
        raw_text=raw_text,
        uploaded_by=user_id,
        uploader=f"User #{user_id}" if user_id else "Club Lead"
    )
    db.add(doc)
    db.flush()

    for p_chunk in parsed_chunks:
        chunk_vec = generate_embedding(p_chunk.content)
        chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            chunk_index=p_chunk.chunk_index,
            content=p_chunk.content,
            page_number=p_chunk.page_number,
            section_name=p_chunk.section_name,
            token_count=p_chunk.token_count,
            embedding=chunk_vec
        )
        db.add(chunk)

    db.commit()
    db.refresh(doc)
    return doc

def list_documents(
    db: Session,
    event_id: Optional[Union[str, int]] = None,
    category: Optional[Union[str, DocumentCategory]] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Document]:
    query = db.query(Document)
    if event_id is not None:
        query = query.filter(or_(Document.event_id == event_id, Document.event_id == str(event_id)))
    if category:
        cat_enum = category if isinstance(category, DocumentCategory) else None
        if cat_enum is None:
            try:
                cat_enum = DocumentCategory(category)
            except ValueError:
                cat_enum = None
        if cat_enum:
            query = query.filter(Document.category == cat_enum)
        else:
            query = query.filter(Document.category == str(category))

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Document.name.ilike(pattern),
                Document.filename.ilike(pattern),
                Document.raw_text.ilike(pattern)
            )
        )
    return query.offset(skip).limit(limit).all()

def get_document(db: Session, document_id: Union[str, int]) -> Optional[Document]:
    return db.query(Document).filter(or_(Document.id == document_id, Document.id == str(document_id))).first()

def delete_document(db: Session, document_id: Union[str, int]) -> bool:
    doc = get_document(db, document_id)
    if not doc:
        return False
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass
    db.delete(doc)
    db.commit()
    return True

def search_documents(
    db: Session,
    query: str,
    event_id: Optional[Union[str, int]] = None,
    category: Optional[Union[str, DocumentCategory]] = None,
    limit: int = 5
) -> List[dict]:
    """Uses advanced hybrid retrieval and re-ranking from ai.rag."""
    return search_documents_rag(db, query, event_id=event_id, category=category, limit=limit)

def ask_documents(
    db: Session,
    question: str,
    event_id: Optional[Union[str, int]] = None,
    category: Optional[Union[str, DocumentCategory]] = None
) -> dict:
    """Uses the full CRAG + Self-RAG pipeline from ai.rag."""
    rag_resp = execute_rag_pipeline(db, question, event_id=event_id, category=category, top_k=4)
    return {
        "answer": rag_resp.answer,
        "confidence": rag_resp.confidence,
        "citations": [
            {
                "document_id": c.document_id,
                "document_name": c.filename,
                "chunk_id": f"{c.document_id}_{c.chunk_index}",
                "excerpt": c.snippet,
                "page_number": c.page_number
            }
            for c in rag_resp.citations
        ],
        "crag_eval": rag_resp.crag_eval.model_dump()
    }

def extract_document_actions(db: Session, document_id: Union[str, int]) -> List[dict]:
    doc = get_document(db, document_id)
    if not doc or not doc.raw_text:
        return []

    if genai_client and settings.GEMINI_API_KEY:
        prompt = f"""Extract all action items, tasks, delegated owners, and deadlines from the following document text.
Return strictly a JSON array of objects with keys: "action", "owner", "deadline", "priority", "context".

Text:
{doc.raw_text[:4000]}

JSON:"""
        try:
            res = genai_client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt
            )
            if res and res.text:
                json_match = re.search(r'\[.*\]', res.text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
        except Exception as e:
            logger.error(f"Action extraction error: {e}")

    # Fallback heuristic rule-based extraction
    actions = []
    lines = doc.raw_text.split("\n")
    for line in lines:
        line_clean = line.strip()
        if any(line_clean.lower().startswith(p) for p in ["action:", "- [ ]", "todo:", "task:"]) or any(w in line_clean.lower() for w in ["will handle", "assigned to", "responsible for"]):
            actions.append({
                "action": line_clean,
                "owner": "Volunteer / Lead",
                "deadline": "Before Event",
                "priority": "MEDIUM",
                "context": doc.name or doc.filename
            })
    if not actions:
        actions.append({
            "action": f"Review {doc.name or doc.filename} for pending requirements",
            "owner": "Event Lead",
            "deadline": "TBD",
            "priority": "LOW",
            "context": doc.name or doc.filename
        })
    return actions

def extract_document_decisions(db: Session, document_id: Union[str, int]) -> List[dict]:
    doc = get_document(db, document_id)
    if not doc or not doc.raw_text:
        return []

    if genai_client and settings.GEMINI_API_KEY:
        prompt = f"""Extract important decisions, resolutions, and conclusions from the text.
Return strictly a JSON array of objects with keys: "decision", "rationale", "impact", "date_or_context".

Text:
{doc.raw_text[:4000]}

JSON:"""
        try:
            res = genai_client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt
            )
            if res and res.text:
                json_match = re.search(r'\[.*\]', res.text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
        except Exception as e:
            logger.error(f"Decision extraction error: {e}")

    decisions = []
    lines = doc.raw_text.split("\n")
    for line in lines:
        line_clean = line.strip()
        if any(w in line_clean.lower() for w in ["agreed to", "decided to", "approved", "finalized", "decision:"]):
            decisions.append({
                "decision": line_clean,
                "rationale": "Team consensus during planning",
                "impact": "Operational milestone",
                "date_or_context": doc.name or doc.filename
            })
    if not decisions:
        decisions.append({
            "decision": f"Policy established in {doc.name or doc.filename}",
            "rationale": "Documented in club operations record",
            "impact": "Standard operating procedure",
            "date_or_context": doc.name or doc.filename
        })
    return decisions

def find_relevant_past_lessons(
    db: Session,
    query: str,
    event_id: Optional[Union[str, int]] = None
) -> List[dict]:
    """Finds past lessons from PastLesson records and historical post-mortems via RAG."""
    # 1. PastLesson table search
    db_query = db.query(PastLesson)
    if event_id is not None:
        db_query = db_query.filter(or_(PastLesson.event_id == event_id, PastLesson.event_id == str(event_id)))
    lessons = db_query.filter(or_(PastLesson.topic.ilike(f"%{query}%"), PastLesson.lesson.ilike(f"%{query}%"))).limit(10).all()

    out = [
        {
            "id": l.id,
            "topic": l.topic,
            "lesson": l.lesson,
            "impact": l.impact or "Operational",
            "category": l.category or "POST_MORTEM"
        }
        for l in lessons
    ]

    if not out:
        # Fallback to RAG search over historical documents
        rag_chunks = search_documents_rag(db, query, category=DocumentCategory.POST_MORTEM, limit=3)
        for idx, r in enumerate(rag_chunks, start=1):
            out.append({
                "id": idx,
                "topic": r["section_name"] or r["filename"],
                "lesson": r["content"][:200] + "...",
                "impact": f"Retrieved from {r['filename']}",
                "category": r["category"]
            })

    return out
