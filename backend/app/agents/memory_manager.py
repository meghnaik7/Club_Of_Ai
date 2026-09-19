import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.memory.extractor import MemoryExtractor
from app.memory.service import MemoryService
from app.memory.schemas import MemoryCandidate

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Dedicated agentic memory manager for ClubOps AI.
    Runs pre-turn retrieval to inject scoped memories into context,
    and post-turn extraction to store stable, high-value facts into Long-Term Memory.
    """

    @classmethod
    def get_scoped_memory_context(
        cls,
        db: Session,
        query: str,
        user_id: Optional[int] = None,
        club_id: Optional[int] = None,
        event_id: Optional[int] = None,
        top_k: int = 4
    ) -> str:
        """
        Retrieves relevant long-term memories and formats them as a prompt injection block.
        Returns empty string if no relevant memories exist.
        """
        memories = MemoryService.retrieve_relevant_memories(
            db=db,
            query=query,
            user_id=user_id,
            club_id=club_id,
            event_id=event_id,
            top_k=top_k
        )
        if not memories:
            return ""

        formatted_lines = [
            "\n[LONG-TERM MEMORY CONTEXT - Scoped & Verified Facts]"
        ]
        for m in memories:
            formatted_lines.append(f"• [{m['memory_type']}] {m['content']} (confidence: {m['confidence']})")
        formatted_lines.append("[END OF MEMORY CONTEXT]\n")

        return "\n".join(formatted_lines)

    @classmethod
    def process_turn(
        cls,
        db: Session,
        user_message: str,
        assistant_message: Optional[str] = None,
        user_id: Optional[int] = None,
        event_id: Optional[int] = None,
        club_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Post-interaction hook: Extracts, validates, deduplicates, and resolves conflicts
        for candidate long-term memories.
        """
        results = []
        candidates: List[MemoryCandidate] = MemoryExtractor.extract_candidates(
            user_message=user_message,
            assistant_message=assistant_message,
            event_id=event_id,
            club_id=club_id
        )

        for candidate in candidates:
            try:
                res = MemoryService.process_candidate(
                    db=db,
                    candidate=candidate,
                    user_id=user_id
                )
                results.append(res)
            except Exception as e:
                logger.error(f"Error processing memory candidate '{candidate.content[:30]}': {e}")

        return results
