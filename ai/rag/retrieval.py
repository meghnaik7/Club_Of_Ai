import re
from typing import List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.document import Document, DocumentChunk, DocumentCategory
from ai.rag.embeddings import generate_embedding, cosine_similarity

def retrieve_candidate_chunks(
    db: Session,
    query: str,
    event_id: Optional[Union[str, int]] = None,
    category: Optional[Union[str, DocumentCategory]] = None,
    candidate_k: int = 15
) -> List[Tuple[DocumentChunk, Document, float]]:
    """
    Retrieves initial candidate chunks using hybrid dense vector similarity
    and sparse lexical keyword overlap.
    Returns: List of tuples (chunk, document, initial_score) sorted descending.
    """
    if not query or not query.strip():
        return []

    # 1. Base query joining DocumentChunk and Document
    db_query = db.query(DocumentChunk, Document).join(Document, DocumentChunk.document_id == Document.id)

    # 2. Apply event_id scoping
    if event_id is not None:
        db_query = db_query.filter(
            or_(
                Document.event_id == event_id,
                Document.event_id == str(event_id)
            )
        )

    # 3. Apply category scoping
    if category is not None:
        cat_enum = category if isinstance(category, DocumentCategory) else None
        if cat_enum is None:
            try:
                cat_enum = DocumentCategory(category)
            except ValueError:
                cat_enum = None

        if cat_enum is not None:
            db_query = db_query.filter(Document.category == cat_enum)
        else:
            db_query = db_query.filter(Document.category == str(category))

    all_pairs = db_query.all()
    if not all_pairs:
        return []

    # 4. Generate query embedding & extract tokens
    query_vec = generate_embedding(query)
    query_tokens = set(re.findall(r'\w+', query.lower()))
    stopwords = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is", "was", "are", "were"}
    meaningful_query_tokens = [t for t in query_tokens if t not in stopwords and len(t) > 2]

    scored_candidates = []
    for chunk, doc in all_pairs:
        # A. Vector similarity
        chunk_embedding = chunk.embedding
        if not chunk_embedding:
            # Fallback: compute on the fly if not cached in DB
            chunk_embedding = generate_embedding(chunk.content)
            chunk.embedding = chunk_embedding

        sim = cosine_similarity(query_vec, chunk_embedding)

        # B. Lexical token overlap
        chunk_tokens = set(re.findall(r'\w+', chunk.content.lower()))
        matched_tokens = [t for t in meaningful_query_tokens if t in chunk_tokens]
        lexical_ratio = len(matched_tokens) / max(1, len(meaningful_query_tokens)) if meaningful_query_tokens else 0.0

        # Exact phrase bonus
        exact_bonus = 0.15 if query.lower().strip() in chunk.content.lower() else 0.0

        # Combined initial score: 65% dense vector + 25% lexical overlap + 10% exact bonus
        hybrid_score = min(1.0, (sim * 0.65) + (lexical_ratio * 0.25) + exact_bonus)
        scored_candidates.append((chunk, doc, hybrid_score))

    # Sort descending by score
    scored_candidates.sort(key=lambda x: x[2], reverse=True)
    return scored_candidates[:candidate_k]
