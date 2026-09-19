import re
from typing import List, Optional, Tuple
from app.memory.models import Memory
from ai.rag.embeddings import generate_embedding, cosine_similarity

class MemoryDeduplicator:
    """
    Detects and merges duplicate or semantically equivalent memories.
    Prevents fragmentation (e.g. 'User prefers concise responses' vs 'User prefers short answers').
    """

    SIMILARITY_THRESHOLD = 0.70

    SYNONYM_MAP = {
        "short": "concise",
        "brief": "concise",
        "compact": "concise",
        "answers": "responses",
        "replies": "responses",
        "thorough": "detailed",
        "comprehensive": "detailed"
    }

    @classmethod
    def _canonicalize_words(cls, text: str) -> set:
        raw_words = re.findall(r"\w+", text.lower())
        return {cls.SYNONYM_MAP.get(w, w) for w in raw_words}

    @classmethod
    def _lexical_similarity(cls, text1: str, text2: str) -> float:
        """Computes Jaccard word-set similarity with synonym canonicalization."""
        w1 = cls._canonicalize_words(text1)
        w2 = cls._canonicalize_words(text2)
        if not w1 or not w2:
            return 0.0
        intersection = len(w1.intersection(w2))
        union = len(w1.union(w2))
        return intersection / union if union > 0 else 0.0

    @classmethod
    def find_duplicate(
        cls,
        candidate_content: str,
        candidate_embedding: Optional[List[float]],
        existing_memories: List[Memory]
    ) -> Optional[Tuple[Memory, float]]:
        """
        Scans existing memories within the same scope for a semantic or lexical duplicate.
        Returns the duplicate Memory and similarity score if found above threshold.
        """
        if not candidate_embedding:
            candidate_embedding = generate_embedding(candidate_content)

        best_match: Optional[Memory] = None
        best_score = 0.0

        for mem in existing_memories:
            lexical_sim = cls._lexical_similarity(candidate_content, mem.content)
            
            # If high lexical similarity, direct duplicate
            if lexical_sim >= 0.80:
                if lexical_sim > best_score:
                    best_score = lexical_sim
                    best_match = mem
                continue

            # Check vector cosine similarity
            if mem.embedding and candidate_embedding:
                sem_sim = cosine_similarity(candidate_embedding, mem.embedding)
                combined = (sem_sim * 0.65) + (lexical_sim * 0.35)
                if combined > best_score:
                    best_score = combined
                    best_match = mem

        if best_match and best_score >= cls.SIMILARITY_THRESHOLD:
            return best_match, best_score

        return None
