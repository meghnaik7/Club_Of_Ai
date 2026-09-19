"""
AI RAG (Retrieval-Augmented Generation) Module for ClubOps AI.

Architecture:
1. Hybrid Retrieval (Dense Vector + Keyword Overlap)
2. Lexical-Semantic Re-Ranking (Term Density, Structural Relevance, Entity Matching)
3. Corrective RAG (CRAG) Relevance Grader (Noise Filtering & Evaluation)
4. Self-RAG Grounded Generation (Source Citations & Factual Reflection)
5. Proactive Club Memory Auditing (Historical Post-Mortem and Rule Conflict Detection)
"""

from ai.rag.embeddings import (
    generate_embedding,
    generate_embeddings_batch,
    cosine_similarity,
)
from ai.rag.retrieval import retrieve_candidate_chunks
from ai.rag.reranker import rerank_chunks
from ai.rag.crag_grader import grade_retrieved_documents_crag
from ai.rag.self_rag import (
    synthesize_grounded_answer_self_rag,
    build_citations,
)
from ai.rag.pipeline import (
    execute_rag_pipeline,
    search_documents_rag,
)
from ai.rag.club_memory import check_plan_against_club_memory

__all__ = [
    "generate_embedding",
    "generate_embeddings_batch",
    "cosine_similarity",
    "retrieve_candidate_chunks",
    "rerank_chunks",
    "grade_retrieved_documents_crag",
    "synthesize_grounded_answer_self_rag",
    "build_citations",
    "execute_rag_pipeline",
    "search_documents_rag",
    "check_plan_against_club_memory",
]
