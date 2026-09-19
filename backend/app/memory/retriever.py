import math
import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.memory.models import Memory
from ai.rag.embeddings import generate_embedding, cosine_similarity

class MemoryRetriever:
    """
    Retrieves and ranks relevant long-term memories using strict multi-tenant scoping
    and a hybrid scoring function:
    final_score = semantic_sim * 0.45 + importance * 0.25 + recency * 0.15 + scope_match * 0.15
    """

    @classmethod
    def _compute_recency_score(cls, created_at: datetime) -> float:
        """Decays linearly over 90 days from 1.0 down to 0.2."""
        now = datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        days_old = max(0.0, (now - created_at).total_seconds() / 86400.0)
        return max(0.2, 1.0 - (days_old / 90.0))

    @classmethod
    def retrieve_relevant(
        cls,
        db: Session,
        query: str,
        user_id: Optional[int] = None,
        club_id: Optional[int] = None,
        event_id: Optional[int] = None,
        top_k: int = 5,
        min_score: float = 0.35
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid memory retrieval strictly scoped to the authorized context.
        """
        if not query or not query.strip():
            return []

        # 1. Scope-based isolation filter
        # User scope matches user_id
        # Club scope matches club_id
        # Event scope matches event_id
        scope_clauses = []
        if user_id is not None:
            scope_clauses.append(Memory.user_id == user_id)
        if club_id is not None:
            scope_clauses.append(Memory.club_id == club_id)
        if event_id is not None:
            scope_clauses.append(Memory.event_id == event_id)

        if not scope_clauses:
            # If no context provided, restrict to unowned global public memories only
            memories = db.query(Memory).filter(
                Memory.user_id.is_(None),
                Memory.club_id.is_(None),
                Memory.event_id.is_(None)
            ).all()
        else:
            memories = db.query(Memory).filter(or_(*scope_clauses)).all()

        if not memories:
            return []

        # 2. Query embedding
        query_embedding = generate_embedding(query)

        scored_results: List[Tuple[Memory, float, float]] = []

        for mem in memories:
            # Check expiration
            if mem.expires_at:
                now_utc = datetime.now(timezone.utc)
                exp = mem.expires_at.replace(tzinfo=timezone.utc) if mem.expires_at.tzinfo is None else mem.expires_at
                if exp < now_utc:
                    continue

            # Semantic similarity
            sem_sim = 0.0
            if mem.embedding and query_embedding:
                sem_sim = cosine_similarity(query_embedding, mem.embedding)

            # Lexical keyword overlap
            q_words = set(re.findall(r"\w+", query.lower()))
            m_words = set(re.findall(r"\w+", mem.content.lower()))
            meaningful_overlap = [w for w in q_words.intersection(m_words) if len(w) > 3 and w not in ("user", "club", "event", "prefer", "prefers")]

            # Scope match bonus: exact event match = 1.0, user match = 0.95, club match = 0.85
            scope_match = 0.5
            if event_id and mem.event_id == event_id:
                scope_match = 1.0
            elif user_id and mem.user_id == user_id:
                scope_match = 0.95
            elif club_id and mem.club_id == club_id:
                scope_match = 0.85

            # Gating: If both semantic similarity is low and there is no keyword overlap, the memory is off-topic
            sim_floor = 0.12 if scope_match >= 0.9 else 0.25
            if sem_sim < sim_floor and not meaningful_overlap:
                continue

            # Importance
            imp = mem.importance

            # Recency
            rec = cls._compute_recency_score(mem.updated_at or mem.created_at)

            # Hybrid score: heavily weight topical relevance (similarity)
            final_score = (sem_sim * 0.50) + (imp * 0.20) + (rec * 0.15) + (scope_match * 0.15)

            if final_score >= min_score:
                scored_results.append((mem, final_score, sem_sim))

        # Sort descending by final score
        scored_results.sort(key=lambda x: x[1], reverse=True)
        top_matches = scored_results[:top_k]

        return [
            {
                "id": m.id,
                "memory_type": m.memory_type,
                "scope": m.scope,
                "content": m.content,
                "importance": m.importance,
                "confidence": m.confidence,
                "final_score": round(score, 3),
                "semantic_similarity": round(sim, 3),
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m, score, sim in top_matches
        ]
