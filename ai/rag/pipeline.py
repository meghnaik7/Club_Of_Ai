from typing import Optional, Union, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.document import DocumentCategory
from app.schemas.document import RAGQueryResponse, CitationSchema, CRAGEvaluation
from ai.rag.retrieval import retrieve_candidate_chunks
from ai.rag.reranker import rerank_chunks
from ai.rag.crag_grader import grade_retrieved_documents_crag
from ai.rag.self_rag import synthesize_grounded_answer_self_rag
from ai.observability import traceable

@traceable(name="execute_rag_pipeline", run_type="retriever")
def execute_rag_pipeline(
    db: Session,
    query: str,
    event_id: Optional[Union[str, int]] = None,
    category: Optional[Union[str, DocumentCategory]] = None,
    top_k: int = 5
) -> RAGQueryResponse:
    """
    Complete end-to-end RAG pipeline:
    1. Hybrid Retrieval (Dense Vector + Keyword Overlap) -> Wide Candidate Pool
    2. Cross-Criteria Re-Ranking (Term Density + Structural Relevance + Entities)
    3. Corrective RAG (CRAG) Relevance Grader (Filters Out Noise Chunks)
    4. Top-K Retention
    5. Self-RAG Grounded Generation & Exact Citation Reflection
    """
    if not query or not query.strip():
        return RAGQueryResponse(
            query=query,
            answer="Query is empty. Please enter a specific question.",
            confidence=0.0,
            citations=[],
            crag_eval=CRAGEvaluation(
                retrieved_count=0,
                relevant_count=0,
                filtered_noise_count=0,
                is_grounded=False,
                evaluation_notes="Empty query submitted."
            )
        )

    # 1. Hybrid Retrieval (retrieve wider candidate pool)
    candidates = retrieve_candidate_chunks(
        db=db,
        query=query,
        event_id=event_id,
        category=category,
        candidate_k=max(15, top_k * 3)
    )

    if not candidates:
        return RAGQueryResponse(
            query=query,
            answer="I could not find any relevant documents or records in the club archive for this question.",
            confidence=0.0,
            citations=[],
            crag_eval=CRAGEvaluation(
                retrieved_count=0,
                relevant_count=0,
                filtered_noise_count=0,
                is_grounded=False,
                evaluation_notes="No candidate chunks retrieved matching the query or filters."
            )
        )

    # 2. Re-Ranking Strategy
    reranked_candidates = rerank_chunks(query, candidates, top_k=max(8, top_k * 2))

    # 3. Corrective RAG (CRAG) Document Grader
    relevant_chunks, crag_eval = grade_retrieved_documents_crag(query, reranked_candidates)

    # 4. Top-K retention
    final_chunks = relevant_chunks[:top_k]

    # 5. Self-RAG Grounded Generation & Reflection
    answer, citations, confidence = synthesize_grounded_answer_self_rag(query, final_chunks)

    return RAGQueryResponse(
        query=query,
        answer=answer,
        confidence=confidence,
        citations=citations,
        crag_eval=crag_eval
    )

def search_documents_rag(
    db: Session,
    query: str,
    event_id: Optional[Union[str, int]] = None,
    category: Optional[Union[str, DocumentCategory]] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Search documents using the hybrid retrieval and re-ranking pipeline,
    returning structured chunk metadata and relevance scores.
    """
    candidates = retrieve_candidate_chunks(db, query, event_id, category, candidate_k=limit * 3)
    reranked = rerank_chunks(query, candidates, top_k=limit)

    results = []
    for chunk, doc, score in reranked:
        results.append({
            "document_id": str(doc.id),
            "document_name": doc.name or doc.filename,
            "filename": doc.filename,
            "category": doc.category.value if hasattr(doc.category, "value") else str(doc.category),
            "chunk_id": str(chunk.id),
            "content": chunk.content,
            "score": round(score, 3),
            "page_number": chunk.page_number,
            "section_name": chunk.section_name
        })
    return results
