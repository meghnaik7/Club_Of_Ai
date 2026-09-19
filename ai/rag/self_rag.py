import re
from typing import List, Tuple, Optional
from app.models.document import Document, DocumentChunk
from app.schemas.document import CitationSchema
from app.core.config import settings

genai_client = None
if settings.GEMINI_API_KEY:
    try:
        from google import genai
        genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception:
        genai_client = None

def build_citations(relevant_chunks: List[Tuple[DocumentChunk, Document, float]]) -> List[CitationSchema]:
    """Constructs structured citations for all retained chunks."""
    citations = []
    for chunk, doc, score in relevant_chunks:
        snippet = chunk.content.strip()
        if len(snippet) > 220:
            snippet = snippet[:220] + "..."

        cat_val = doc.category.value if hasattr(doc.category, "value") else str(doc.category) if doc.category else "GENERAL"
        sec_val = chunk.section_name or f"Section {chunk.chunk_index + 1}"

        citation = CitationSchema(
            document_id=str(doc.id),
            filename=doc.filename,
            category=cat_val,
            page_number=chunk.page_number,
            section_name=sec_val,
            chunk_index=chunk.chunk_index,
            snippet=snippet,
            relevance_score=round(score, 3)
        )
        citations.append(citation)
    return citations

def synthesize_grounded_answer_self_rag(
    query: str,
    relevant_chunks: List[Tuple[DocumentChunk, Document, float]]
) -> Tuple[str, List[CitationSchema], float]:
    """
    Self-RAG Grounded Generation & Citation Reflection:
    Produces an answer strictly rooted in the provided context and returns
    detailed source citations and a grounded confidence score.
    """
    if not relevant_chunks:
        return (
            "I could not find any relevant information in the uploaded club documents to answer this question.",
            [],
            0.0
        )

    citations = build_citations(relevant_chunks)

    # Prepare formatted context blocks
    context_blocks = []
    for idx, (chunk, doc, _) in enumerate(relevant_chunks, start=1):
        page_str = f", page {chunk.page_number}" if chunk.page_number else ""
        sec_str = f", {chunk.section_name}" if chunk.section_name else ""
        context_blocks.append(f"[Source {idx}: {doc.filename}{page_str}{sec_str}]\n{chunk.content}")

    context_str = "\n\n".join(context_blocks)

    # 1. LLM Generation if Gemini API key is configured
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
                return response.text.strip(), citations, round(min(0.99, max(0.65, avg_confidence)), 2)
        except Exception:
            pass

    # 2. Deterministic Extractive Synthesis (Offline Fallback)
    salient_sentences = []
    stopwords = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is", "was", "are", "were"}
    query_keywords = set(w for w in re.findall(r'\w+', query.lower()) if w not in stopwords and len(w) > 2)

    for chunk, doc, _ in relevant_chunks[:4]:
        sentences = re.split(r'(?<=[.!?])\s+', chunk.content)
        for s in sentences:
            s_clean = s.strip()
            if not s_clean or len(s_clean) < 15:
                continue
            s_words = set(re.findall(r'\w+', s_clean.lower()))
            overlap = query_keywords.intersection(s_words)
            if overlap:
                salient_sentences.append(s_clean)
                if len(salient_sentences) >= 3:
                    break
        if len(salient_sentences) >= 4:
            break

    if salient_sentences:
        answer = " ".join(salient_sentences)
    else:
        # If no individual sentence had high keyword overlap, use the first chunk content directly
        answer = relevant_chunks[0][0].content[:280].strip()
        if len(relevant_chunks[0][0].content) > 280:
            answer += "..."

    avg_score = sum(c.relevance_score for c in citations) / max(1, len(citations))
    confidence = round(min(0.95, max(0.50, avg_score)), 2)
    return answer, citations, confidence
