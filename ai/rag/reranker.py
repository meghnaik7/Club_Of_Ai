import re
from typing import List, Tuple
from app.models.document import Document, DocumentChunk

def compute_term_density(query_terms: List[str], text: str) -> float:
    """Calculates term density and co-occurrence proximity of query tokens."""
    if not query_terms or not text:
        return 0.0
    text_lower = text.lower()
    total_matches = sum(1 for term in query_terms if term in text_lower)
    token_ratio = total_matches / len(query_terms)

    # Bigram proximity check
    bigram_matches = 0
    if len(query_terms) >= 2:
        for i in range(len(query_terms) - 1):
            bigram = f"{query_terms[i]} {query_terms[i+1]}"
            if bigram in text_lower:
                bigram_matches += 1
        bigram_bonus = (bigram_matches / (len(query_terms) - 1)) * 0.3
    else:
        bigram_bonus = 0.0

    return min(1.0, (token_ratio * 0.7) + bigram_bonus)

def compute_structural_relevance(query_terms: List[str], chunk: DocumentChunk) -> float:
    """Computes bonus if chunk's section or document title contains query keywords."""
    score = 0.0
    section_lower = (chunk.section_name or "").lower()
    for term in query_terms:
        if term in section_lower:
            score += 0.25
    return min(1.0, score)

def compute_entity_matches(query: str, text: str) -> float:
    """Checks for exact numerical and proper noun matches (hours, amounts, dates, codes)."""
    # Look for numbers with units or isolated numbers
    numbers_query = re.findall(r'\b\d+(?:\.\d+)?(?:\s*(?:hours?|hrs?|mins?|days?|pm|am|auditorium|hall|rs|inr))?\b', query.lower())
    if not numbers_query:
        return 0.0
    text_lower = text.lower()
    matched = sum(1 for n in numbers_query if n in text_lower)
    return matched / len(numbers_query)

def rerank_chunks(
    query: str,
    candidates: List[Tuple[DocumentChunk, Document, float]],
    top_k: int = 8
) -> List[Tuple[DocumentChunk, Document, float]]:
    """
    Applies multi-criteria re-ranking across candidate chunks:
    - Initial hybrid retrieval score (0.40)
    - Term density and proximity (0.35)
    - Structural heading relevance (0.15)
    - Entity and numerical match precision (0.10)
    Returns: Re-ranked candidate list sorted descending.
    """
    if not candidates:
        return []

    query_clean = query.lower()
    stopwords = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is", "was", "are", "were", "what", "how", "why", "when", "did", "does"}
    query_tokens = [w for w in re.findall(r'\w+', query_clean) if w not in stopwords and len(w) > 2]

    reranked = []
    for chunk, doc, initial_score in candidates:
        density_score = compute_term_density(query_tokens, chunk.content)
        structural_score = compute_structural_relevance(query_tokens, chunk)
        entity_score = compute_entity_matches(query, chunk.content)

        # Re-ranked composite score
        final_score = (
            (initial_score * 0.40) +
            (density_score * 0.35) +
            (structural_score * 0.15) +
            (entity_score * 0.10)
        )
        final_score = round(min(1.0, max(0.0, final_score)), 4)
        reranked.append((chunk, doc, final_score))

    # Sort descending by re-ranked score
    reranked.sort(key=lambda x: x[2], reverse=True)
    return reranked[:top_k]
