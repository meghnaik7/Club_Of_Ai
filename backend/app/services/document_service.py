import os
import shutil
import json
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.models.document import Document, DocumentChunk, PastLesson
from app.services.document_parser import extract_text, chunk_text

# LangChain imports for basic LLM extractions
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

def get_llm():
    if settings.OPENAI_API_KEY:
        return ChatOpenAI(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)
    return None

def upload_document(
    db: Session, file_obj, filename: str, file_type: str, 
    name: str, category: Optional[str] = None, event_id: Optional[int] = None, user_id: Optional[int] = None
) -> Document:
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file_obj, buffer)
        
    file_size = os.path.getsize(file_path)
    raw_text = extract_text(file_path, file_type)
    
    doc = Document(
        event_id=event_id,
        name=name,
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        file_size=file_size,
        category=category,
        raw_text=raw_text,
        uploaded_by=user_id
    )
    db.add(doc)
    db.flush()
    
    chunks = chunk_text(raw_text)
    for i, c_text in enumerate(chunks):
        chunk = DocumentChunk(document_id=doc.id, chunk_index=i, content=c_text)
        db.add(chunk)
        
    db.commit()
    db.refresh(doc)
    return doc

def list_documents(db: Session, event_id: Optional[int] = None, category: Optional[str] = None, search: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Document]:
    query = db.query(Document)
    if event_id:
        query = query.filter(Document.event_id == event_id)
    if category:
        query = query.filter(Document.category == category)
    if search:
        query = query.filter(or_(Document.name.ilike(f"%{search}%"), Document.raw_text.ilike(f"%{search}%")))
    return query.offset(skip).limit(limit).all()

def get_document(db: Session, document_id: int) -> Optional[Document]:
    return db.query(Document).filter(Document.id == document_id).first()

def delete_document(db: Session, document_id: int) -> bool:
    doc = get_document(db, document_id)
    if not doc:
        return False
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    db.delete(doc)
    db.commit()
    return True

def search_documents(db: Session, query: str, event_id: Optional[int] = None, category: Optional[str] = None, limit: int = 5) -> List[dict]:
    # Basic ILIKE search fallback since pgvector isn't fully configured yet.
    # Searches chunks for keyword matches.
    db_query = db.query(DocumentChunk, Document).join(Document)
    if event_id:
        db_query = db_query.filter(Document.event_id == event_id)
    if category:
        db_query = db_query.filter(Document.category == category)
        
    results = db_query.filter(DocumentChunk.content.ilike(f"%{query}%")).limit(limit).all()
    
    out = []
    for chunk, doc in results:
        out.append({
            "document_id": doc.id,
            "document_name": doc.name,
            "chunk_id": chunk.id,
            "content": chunk.content,
            "score": 1.0,
            "page_number": chunk.page_number
        })
    return out

def ask_documents(db: Session, question: str, event_id: Optional[int] = None, category: Optional[str] = None) -> dict:
    search_results = search_documents(db, question, event_id, category, limit=3)
    if not search_results:
        return {"answer": "No relevant documents found.", "citations": []}
        
    context = "\n\n".join([f"Document: {r['document_name']}\nExcerpt: {r['content']}" for r in search_results])
    
    llm = get_llm()
    if llm:
        sys_msg = SystemMessage(content="You are a helpful assistant. Use the provided context to answer the user's question. Cite the Document Name in your answer.")
        user_msg = HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}")
        response = llm.invoke([sys_msg, user_msg]).content
    else:
        # Fallback offline
        response = f"Found relevant information in {len(search_results)} snippets. (LLM offline, returning excerpts)"
        
    citations = [{
        "document_id": r["document_id"],
        "document_name": r["document_name"],
        "chunk_id": r["chunk_id"],
        "excerpt": r["content"],
        "page_number": r["page_number"]
    } for r in search_results]
    
    return {"answer": response, "citations": citations}

def extract_document_actions(db: Session, document_id: int) -> List[dict]:
    doc = get_document(db, document_id)
    if not doc or not doc.raw_text:
        return []
        
    llm = get_llm()
    if llm:
        prompt = "Extract all decisions, action items, owners, and deadlines from the following document text. Return as JSON array of objects with keys: action, owner, deadline, priority, context.\n\nText:\n" + doc.raw_text[:4000]
        try:
            res = llm.invoke([HumanMessage(content=prompt)]).content
            # Basic parsing attempt (assuming LLM returns valid json array)
            if "[" in res and "]" in res:
                json_str = res[res.find("["):res.rfind("]")+1]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"Action extraction error: {e}")
            
    # Fallback mock
    return [{"action": "Extracted Action Mock (LLM unavailable/failed)", "context": doc.name}]

def extract_document_decisions(db: Session, document_id: int) -> List[dict]:
    doc = get_document(db, document_id)
    if not doc or not doc.raw_text:
        return []
        
    llm = get_llm()
    if llm:
        prompt = "Extract important decisions and conclusions from the text. Return as JSON array of objects with keys: decision, rationale, impact, date_or_context.\n\nText:\n" + doc.raw_text[:4000]
        try:
            res = llm.invoke([HumanMessage(content=prompt)]).content
            if "[" in res and "]" in res:
                json_str = res[res.find("["):res.rfind("]")+1]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"Decision extraction error: {e}")
            
    return [{"decision": "Extracted Decision Mock (LLM unavailable/failed)", "rationale": "N/A"}]

def find_relevant_past_lessons(db: Session, query: str, event_id: Optional[int] = None) -> List[PastLesson]:
    # Basic keyword search on PastLesson
    db_query = db.query(PastLesson)
    if event_id:
        db_query = db_query.filter(PastLesson.event_id == event_id)
    return db_query.filter(PastLesson.topic.ilike(f"%{query}%") | PastLesson.lesson.ilike(f"%{query}%")).limit(10).all()
