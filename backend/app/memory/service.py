import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.memory.models import Memory
from app.memory.schemas import (
    MemoryCreate, MemoryUpdate, MemoryCandidate, MemoryResponse, MemoryRetrievalQuery
)
from app.memory.repository import MemoryRepository
from app.memory.guardrails import MemoryGuardrails
from app.memory.scorer import MemoryScorer
from app.memory.deduplicator import MemoryDeduplicator
from app.memory.conflict_resolver import MemoryConflictResolver
from app.memory.retriever import MemoryRetriever
from ai.rag.embeddings import generate_embedding

logger = logging.getLogger(__name__)

class MemoryService:
    """
    Central orchestration service for Long-Term Memory:
    Validation -> Scoring -> Deduplication -> Conflict Resolution -> Persistence / Retrieval.
    """

    @classmethod
    def process_candidate(
        cls,
        db: Session,
        candidate: MemoryCandidate,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Processes a single candidate memory through all verification stages.
        Returns action taken: STORE, UPDATE, or IGNORE.
        """
        content = candidate.content.strip()

        # 1. Validation & Security Guardrails
        is_valid, error_msg = MemoryGuardrails.validate_candidate(content, candidate.source)
        if not is_valid:
            logger.info(f"Memory candidate rejected by guardrails: {error_msg}")
            return {"action": "IGNORE", "reason": error_msg}

        # 2. Importance Scoring
        score = MemoryScorer.score(candidate.memory_type, content, candidate.source)
        if not MemoryScorer.is_candidate(score):
            return {"action": "IGNORE", "reason": f"Importance score {score} is below candidate threshold (0.60)"}

        # Candidate passed initial checks
        candidate.importance = score

        # Generate embedding
        embedding = generate_embedding(content)

        # Retrieve existing memories in the same scope to check duplicates & conflicts
        existing_memories, _ = MemoryRepository.list_scoped(
            db=db,
            user_id=user_id or candidate.club_id,
            club_id=candidate.club_id,
            event_id=candidate.event_id,
            limit=100
        )

        # 3. Duplicate Detection & Merging
        duplicate_match = MemoryDeduplicator.find_duplicate(content, embedding, existing_memories)
        if duplicate_match:
            existing_mem, similarity = duplicate_match
            # Merge / update existing memory: boost confidence and refresh recency
            update_in = MemoryUpdate(
                importance=max(existing_mem.importance, score),
                confidence=min(1.0, existing_mem.confidence + 0.05)
            )
            updated_obj = MemoryRepository.update(db, existing_mem, update_in, embedding)
            return {
                "action": "UPDATE",
                "id": updated_obj.id,
                "reason": f"Merged duplicate with similarity {similarity:.2f}",
                "memory": updated_obj
            }

        # 4. Conflict Resolution
        conflict_match = MemoryConflictResolver.detect_conflict(content, existing_memories)
        if conflict_match:
            conflicting_mem, reason = conflict_match
            should_override = MemoryConflictResolver.resolve(
                conflicting_mem,
                content,
                score,
                candidate.confidence,
                candidate.source
            )
            if should_override:
                # Update existing conflicting memory with new canonical preference
                update_in = MemoryUpdate(
                    content=content,
                    importance=score,
                    confidence=candidate.confidence
                )
                updated_obj = MemoryRepository.update(db, conflicting_mem, update_in, embedding)
                return {
                    "action": "UPDATE",
                    "id": updated_obj.id,
                    "reason": f"Resolved conflict: updated outdated preference ({reason})",
                    "memory": updated_obj
                }
            else:
                return {
                    "action": "IGNORE",
                    "reason": f"Conflict detected: existing high-confidence memory overrides candidate ({reason})"
                }

        # 5. Store New Canonical Memory
        obj_in = MemoryCreate(
            user_id=user_id,
            club_id=candidate.club_id,
            event_id=candidate.event_id,
            memory_type=candidate.memory_type,
            scope=candidate.scope,
            content=content,
            structured_data=candidate.structured_data,
            importance=score,
            confidence=candidate.confidence,
            source=candidate.source
        )
        new_memory = MemoryRepository.create(db, obj_in, embedding)
        return {
            "action": "STORE",
            "id": new_memory.id,
            "memory": new_memory
        }

    @classmethod
    def retrieve_relevant_memories(
        cls,
        db: Session,
        query: str,
        user_id: Optional[int] = None,
        club_id: Optional[int] = None,
        event_id: Optional[int] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieves top-K relevant memories scoped to user and club/event."""
        return MemoryRetriever.retrieve_relevant(
            db=db,
            query=query,
            user_id=user_id,
            club_id=club_id,
            event_id=event_id,
            top_k=top_k
        )
