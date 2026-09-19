import re
from typing import List, Optional, Tuple
from datetime import datetime, timezone
from app.memory.models import Memory

class MemoryConflictResolver:
    """
    Detects and resolves semantic contradictions between new candidate memories
    and existing memories in the same category/scope.
    """

    # Antonym / opposing preference pairs
    OPPOSING_PAIRS = [
        (r"\bconcise\b", r"\bdetailed\b"),
        (r"\bshort\b", r"\blong\b"),
        (r"\bbrief\b", r"\bthorough\b"),
        (r"\bexplicit\b", r"\bimplicit\b"),
        (r"\brequire[s]?\b", r"\boptional\b"),
        (r"\ballow[s]?\b", r"\bprohibit[s]?\b"),
        (r"\benable[s]?\b", r"\bdisable[s]?\b"),
        (r"\balways\b", r"\bnever\b"),
    ]

    @classmethod
    def detect_conflict(cls, new_content: str, existing_memories: List[Memory]) -> Optional[Tuple[Memory, str]]:
        """
        Detects if new_content directly contradicts an existing memory.
        Returns the conflicting existing Memory and conflict reason if found.
        """
        new_lower = new_content.lower()

        for mem in existing_memories:
            old_lower = mem.content.lower()

            for pat_a, pat_b in cls.OPPOSING_PAIRS:
                has_a_in_new = bool(re.search(pat_a, new_lower))
                has_b_in_new = bool(re.search(pat_b, new_lower))
                has_a_in_old = bool(re.search(pat_a, old_lower))
                has_b_in_old = bool(re.search(pat_b, old_lower))

                # If new has A and old has B (or vice-versa) on similar subject matter
                if (has_a_in_new and has_b_in_old) or (has_b_in_new and has_a_in_old):
                    # Check subject matter overlap (e.g. both talk about "responses", "tasks", "deadlines")
                    words_new = set(re.findall(r"\w+", new_lower))
                    words_old = set(re.findall(r"\w+", old_lower))
                    overlap = words_new.intersection(words_old)
                    # Filter out generic stop words
                    meaningful_overlap = [w for w in overlap if len(w) > 3 and w not in ("user", "prefers", "likes")]
                    if meaningful_overlap:
                        return mem, f"Contradiction detected regarding {', '.join(meaningful_overlap)}"

        return None

    @classmethod
    def resolve(
        cls,
        conflicting_memory: Memory,
        new_content: str,
        new_importance: float,
        new_confidence: float,
        source: str = "conversation"
    ) -> bool:
        """
        Decides whether new memory should update/supersede existing conflicting memory.
        Returns True if the existing memory should be replaced/updated.
        """
        # Explicit user statements or high-confidence new inputs override older preferences
        if source in ("explicit_user_input", "user_profile"):
            return True

        # If new confidence is equal or higher, the recency principle applies
        if new_confidence >= conflicting_memory.confidence:
            return True

        # High confidence existing rule not superseded by weak evidence
        return False
