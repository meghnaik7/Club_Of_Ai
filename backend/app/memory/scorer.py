import re
from typing import Optional, Dict, Any

class MemoryScorer:
    """
    Evaluates importance (0.0 - 1.0) and confidence (0.0 - 1.0) of candidate facts.
    Applies deterministic heuristics to prioritize high-value, reusable organizational knowledge.
    """

    # Indicators for high-importance stable facts
    EXPLICIT_PREFERENCE_INDICATORS = [
        r"(?i)\b(?:prefers?|likes?|always|never|usually|requires?|strictly)\b",
        r"(?i)\b(?:user\s+prefers|i\s+prefer|i\s+like|i\s+always|do\s+not\s+like)\b",
        r"(?i)\b(?:concise|detailed|explicit|subtasks?|break\s+down)\b"
    ]

    PROCESS_RULE_INDICATORS = [
        r"(?i)\b(?:must\s+be|requires?\s+approval|protocol|procedure|rule|policy|mandatory)\b",
        r"(?i)\b(?:approval\s+from|signed\s+off|permission|standard\s+operating)\b"
    ]

    HISTORICAL_LESSON_INDICATORS = [
        r"(?i)\b(?:experienced\s+a\s+delay|problem|issue|failed\s+because|lesson|root\s+cause)\b",
        r"(?i)\b(?:post-mortem|postmortem|went\s+wrong|bottleneck|incident)\b"
    ]

    VOLUNTEER_SKILL_INDICATORS = [
        r"(?i)\b(?:skills?|experience\s+with|proficient|unavailable\s+on|specializes?\s+in)\b",
        r"(?i)\b(?:backend|frontend|python|design|av\s+team|logistics)\b"
    ]

    TEMPORARY_INDICATORS = [
        r"(?i)\b(?:tomorrow|yesterday|today|at\s+5pm|in\s+10\s+minutes|this\s+evening)\b",
        r"(?i)\b(?:meeting\s+right\s+now|quick\s+check|temp|test\s+task)\b"
    ]

    @classmethod
    def score(cls, memory_type: str, content: str, source: str = "conversation") -> float:
        content_lower = content.lower()
        score = 0.5 # base baseline

        # 1. Heavily penalize temporary indicators
        for pattern in cls.TEMPORARY_INDICATORS:
            if re.search(pattern, content_lower):
                score -= 0.35

        # 2. Type-specific scoring
        if memory_type in ("USER_PREFERENCE", "WORKING_PREFERENCE"):
            score = max(score, 0.70)
            for pat in cls.EXPLICIT_PREFERENCE_INDICATORS:
                if re.search(pat, content_lower):
                    score += 0.12

        elif memory_type in ("PROCESS_RULE", "IMPORTANT_DECISION"):
            score = max(score, 0.75)
            for pat in cls.PROCESS_RULE_INDICATORS:
                if re.search(pat, content_lower):
                    score += 0.12

        elif memory_type in ("EVENT_LESSON", "CLUB_KNOWLEDGE"):
            score = max(score, 0.70)
            for pat in cls.HISTORICAL_LESSON_INDICATORS:
                if re.search(pat, content_lower):
                    score += 0.15

        elif memory_type == "VOLUNTEER_KNOWLEDGE":
            score = max(score, 0.65)
            for pat in cls.VOLUNTEER_SKILL_INDICATORS:
                if re.search(pat, content_lower):
                    score += 0.15

        # 3. Explicit statement bonuses
        if source in ("explicit_user_input", "user_profile"):
            score += 0.10

        # Boundary clamping to [0.0, 1.0]
        return round(max(0.0, min(1.0, score)), 2)

    @classmethod
    def is_candidate(cls, score: float) -> bool:
        """Threshold: >= 0.60 qualifies for candidate persistence."""
        return score >= 0.60
