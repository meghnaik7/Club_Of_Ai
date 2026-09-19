import re
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.document import Document, DocumentChunk, DocumentCategory
from app.schemas.document import CitationSchema, RAGQueryResponse, CRAGEvaluation
from app.services.embeddings import generate_embedding, cosine_similarity
from app.core.config import settings

# Attempt to configure Gemini client if API key is present
genai_client = None
if settings.GEMINI_API_KEY:
    try:
        from google import genai
        genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception:
        genai_client = None

def retrieve_candidate_chunks(
    db: Session,
    query: str,
    event_id: Optional[str] = None,
    category: Optional[DocumentCategory] = None,
    top_k: int = 8
) -> List[Tuple[DocumentChunk, Document, float]]:
    """
    Retrieves candidate chunks using hybrid dense vector similarity and keyword relevance.
    Returns list of tuples: (chunk, document, similarity_score).
    """
    query_vec = generate_embedding(query)
    
    # Base query joining DocumentChunk and Document
    db_query = db.query(DocumentChunk, Document).join(Document, DocumentChunk.document_id == Document.id)
    
    if event_id:
        db_query = db_query.filter(Document.event_id == event_id)
    if category:
        db_query = db_query.filter(Document.category == category)
        
    all_chunks = db_query.all()
    if not all_chunks:
        return []

    scored_chunks = []
    query_words = set(re.findall(r'\w+', query.lower()))

    for chunk, doc in all_chunks:
        # 1. Cosine similarity of embedding
        sim = 0.0
        if chunk.embedding:
            sim = cosine_similarity(query_vec, chunk.embedding)

        # 2. Keyword overlap boost for precision
        chunk_words = set(re.findall(r'\w+', chunk.content.lower()))
        overlap = len(query_words.intersection(chunk_words))
        keyword_boost = (overlap / max(1, len(query_words))) * 0.25
        
        total_score = min(1.0, sim * 0.75 + keyword_boost)
        scored_chunks.append((chunk, doc, total_score))

    # Sort descending by total score
    scored_chunks.sort(key=lambda x: x[2], reverse=True)
    return scored_chunks[:top_k]

def grade_retrieved_documents_crag(
    query: str,
    candidates: List[Tuple[DocumentChunk, Document, float]],
    threshold: float = 0.40
) -> Tuple[List[Tuple[DocumentChunk, Document, float]], CRAGEvaluation]:
    """
    CRAG Document Relevance Grader:
    Filters out noise and irrelevant chunks before prompt construction.
    Evaluates semantic relevance to the query.
    """
    retrieved_count = len(candidates)
    relevant_chunks = []
    filtered_noise_count = 0

    query_tokens = [w for w in re.findall(r'\w+', query.lower()) if len(w) > 2]

    for chunk, doc, score in candidates:
        content_lower = chunk.content.lower()
        # Direct word match check
        matching_terms = [t for t in query_tokens if t in content_lower]
        
        # Keep chunk if semantic score exceeds threshold or has strong term matches
        if score >= threshold or (len(matching_terms) >= 2):
            relevant_chunks.append((chunk, doc, score))
        else:
            filtered_noise_count += 1

    eval_notes = f"CRAG Grader retained {len(relevant_chunks)}/{retrieved_count} chunks. Filtered {filtered_noise_count} noise chunks."
    crag_eval = CRAGEvaluation(
        retrieved_count=retrieved_count,
        relevant_count=len(relevant_chunks),
        filtered_noise_count=filtered_noise_count,
        is_grounded=len(relevant_chunks) > 0,
        evaluation_notes=eval_notes
    )

    return relevant_chunks, crag_eval

def synthesize_grounded_answer_self_rag(
    query: str,
    relevant_chunks: List[Tuple[DocumentChunk, Document, float]]
) -> Tuple[str, List[CitationSchema], float]:
    """
    Self-RAG Answer Synthesizer & Reflection:
    Generates a concise factual answer strictly grounded in the relevant chunks
    and builds formal source citations with page numbers and sections.
    """
    if not relevant_chunks:
        return (
            "I could not find any relevant information in the uploaded club documents to answer this question.",
            [],
            0.0
        )

    # Build citations list
    citations: List[CitationSchema] = []
    context_blocks = []

    for idx, (chunk, doc, score) in enumerate(relevant_chunks, start=1):
        # Snippet preview (up to 200 chars)
        snippet = chunk.content.strip()
        if len(snippet) > 220:
            snippet = snippet[:220] + "..."

        citation = CitationSchema(
            document_id=doc.id,
            filename=doc.filename,
            category=doc.category.value,
            page_number=chunk.page_number,
            section_name=chunk.section_name or f"Section {chunk.chunk_index + 1}",
            chunk_index=chunk.chunk_index,
            snippet=snippet,
            relevance_score=round(score, 3)
        )
        citations.append(citation)

        page_str = f", page {chunk.page_number}" if chunk.page_number else ""
        sec_str = f", {chunk.section_name}" if chunk.section_name else ""
        context_blocks.append(
            f"[Source {idx}: {doc.filename}{page_str}{sec_str}]\n{chunk.content}"
        )

    context_str = "\n\n".join(context_blocks)

    # If Gemini API is available, invoke LLM with Self-RAG prompt
    if genai_client and settings.GEMINI_API_KEY:
        prompt = f"""You are the ClubOps AI operational assistant for a college club.
Answer the user's question accurately and concisely using ONLY the provided sources below.
Rules:
1. Ground every single claim in the sources. Do not speculate or invent facts.
2. If the sources mention delays, problems, numbers, or rules, cite them clearly.
3. Keep the answer direct, practical, and under 4-5 sentences.

Sources:
{context_str}

User Question:
{query}

Answer:"""
        try:
            response = genai_client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt
            )
            if response and response.text:
                avg_confidence = sum(c.relevance_score for c in citations) / max(1, len(citations))
                return response.text.strip(), citations, min(0.99, max(0.65, avg_confidence))
        except Exception as e:
            # Fall back to extractive synthesis
            pass

    # Deterministic extractive synthesis for local/offline execution
    # Extract the most salient sentences directly matching the query intent
    salient_sentences = []
    query_keywords = set(re.findall(r'\w+', query.lower()))

    for chunk, doc, _ in relevant_chunks[:3]:
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', chunk.content)
        for s in sentences:
            s_clean = s.strip()
            if not s_clean or len(s_clean) < 15:
                continue
            s_words = set(re.findall(r'\w+', s_clean.lower()))
            if query_keywords.intersection(s_words):
                salient_sentences.append(s_clean)
                if len(salient_sentences) >= 3:
                    break
        if len(salient_sentences) >= 4:
            break

    if salient_sentences:
        answer = " ".join(salient_sentences)
    else:
        # Use first chunk content truncated
        answer = relevant_chunks[0][0].content[:280] + "..."

    avg_confidence = sum(c.relevance_score for c in citations) / max(1, len(citations))
    return answer, citations, round(avg_confidence, 2)

def execute_rag_pipeline(
    db: Session,
    query: str,
    event_id: Optional[str] = None,
    category: Optional[DocumentCategory] = None,
    top_k: int = 5
) -> RAGQueryResponse:
    """
    Complete end-to-end RAG pipeline with CRAG grading and Self-RAG citation synthesis.
    """
    # 1. Retrieve candidates
    candidates = retrieve_candidate_chunks(db, query, event_id, category, top_k=top_k * 2)

    # 2. CRAG Document Grader
    relevant_chunks, crag_eval = grade_retrieved_documents_crag(query, candidates)

    # 3. Take top_k graded relevant chunks
    final_chunks = relevant_chunks[:top_k]

    # 4. Self-RAG Generation & Citation mapping
    answer, citations, confidence = synthesize_grounded_answer_self_rag(query, final_chunks)

    return RAGQueryResponse(
        query=query,
        answer=answer,
        confidence=confidence,
        citations=citations,
        crag_eval=crag_eval
    )
