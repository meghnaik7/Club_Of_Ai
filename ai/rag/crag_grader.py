import re
from typing import List, Tuple
from app.models.document import Document, DocumentChunk
from app.schemas.document import CRAGEvaluation

def grade_retrieved_documents_crag(
    query: str,
    candidates: List[Tuple[DocumentChunk, Document, float]],
    threshold: float = 0.35
) -> Tuple[List[Tuple[DocumentChunk, Document, float]], CRAGEvaluation]:
    """
    Corrective RAG (CRAG) Relevance Grader:
    Filters out noise and irrelevant chunks before answer synthesis.
    Validates semantic threshold and key concept coverage.
    """
    retrieved_count = len(candidates)
    relevant_chunks = []
    filtered_noise_count = 0

    stopwords = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is", "was", "are", "were", "what", "how", "why"}
    query_tokens = [w for w in re.findall(r'\w+', query.lower()) if w not in stopwords and len(w) > 2]

    for chunk, doc, score in candidates:
        content_lower = chunk.content.lower()
        matching_terms = [t for t in query_tokens if t in content_lower]
        term_overlap_ratio = len(matching_terms) / max(1, len(query_tokens))

        # Check for semantic relevance:
        # A chunk passes if its composite score >= threshold OR it matches >= 50% of query keywords (or at least 2 keywords)
        is_relevant = (score >= threshold) or (len(matching_terms) >= 2) or (term_overlap_ratio >= 0.5 and score >= 0.20)

        if is_relevant:
            relevant_chunks.append((chunk, doc, score))
        else:
            filtered_noise_count += 1

    is_grounded = len(relevant_chunks) > 0
    if is_grounded:
        eval_notes = f"CRAG Grader retained {len(relevant_chunks)}/{retrieved_count} relevant chunks. Filtered {filtered_noise_count} noise chunks."
    else:
        eval_notes = f"CRAG Grader found no sufficiently relevant chunks among {retrieved_count} candidates. Triggering ungrounded query protection."

    crag_eval = CRAGEvaluation(
        retrieved_count=retrieved_count,
        relevant_count=len(relevant_chunks),
        filtered_noise_count=filtered_noise_count,
        is_grounded=is_grounded,
        evaluation_notes=eval_notes
    )

    return relevant_chunks, crag_eval
