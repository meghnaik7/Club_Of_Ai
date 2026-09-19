import re
from typing import List, Optional, Dict, Any
from app.memory.schemas import MemoryCandidate

class MemoryExtractor:
    """
    Extracts high-value, reusable candidate facts from user inputs and conversation outcomes.
    Filters out temporary conversational chatter and operational execution logs.
    """

    # Rule patterns for extraction
    PREFERENCE_PATTERNS = [
        (re.compile(r"(?i)\b(?:i\s+prefer|user\s+prefers|always\s+give\s+me)\s+([^.\n]+)"), "USER_PREFERENCE", "USER"),
        (re.compile(r"(?i)\b(?:i\s+like|i\s+want)\s+(concise|detailed|short|bulleted)\s+(?:responses?|answers?|summaries)"), "USER_PREFERENCE", "USER"),
        (re.compile(r"(?i)\b(?:tasks?\s+should\s+(?:normally\s+)?be\s+broken\s+down|prefer\s+smaller\s+subtasks?)"), "WORKING_PREFERENCE", "USER"),
        (re.compile(r"(?i)\b(?:tasks?\s+must\s+have\s+explicit\s+deadlines?|prefer\s+explicit\s+deadlines?)"), "WORKING_PREFERENCE", "USER"),
    ]

    CLUB_RULE_PATTERNS = [
        (re.compile(r"(?i)\b(?:the\s+club(?:'s)?\s+(?:events|proposals|budget|sponsorship))\s+([^.\n]+requires?\s+approval[^.\n]*)"), "PROCESS_RULE", "CLUB"),
        (re.compile(r"(?i)\b(?:for\s+the\s+current\s+club|in\s+our\s+club|club\s+policy)\s*,?\s*([^.\n]+)"), "PROCESS_RULE", "CLUB"),
        (re.compile(r"(?i)\b(?:the\s+club\s+usually\s+conducts\s+[^.\n]+in\s+[^.\n]+)"), "CLUB_KNOWLEDGE", "CLUB"),
    ]

    LESSON_PATTERNS = [
        (re.compile(r"(?i)\b(?:previous|last)\s+([a-zA-Z0-9_\s]+)\s+(?:experienced\s+a\s+delay|failed|had\s+issues?\s+because)\s+([^.\n]+)"), "EVENT_LESSON", "EVENT"),
        (re.compile(r"(?i)\b(?:lesson\s+learned|post-mortem\s+note|went\s+wrong)\s*:\s*([^.\n]+)"), "EVENT_LESSON", "EVENT"),
    ]

    VOLUNTEER_PATTERNS = [
        (re.compile(r"(?i)\b(?:volunteer\s+([A-Za-z0-9_]+)\s+(?:has\s+([^.\n]+skills?)|is\s+usually\s+unavailable\s+on\s+([^.\n]+)))"), "VOLUNTEER_KNOWLEDGE", "VOLUNTEER"),
        (re.compile(r"(?i)\b(?:assign\s+technical\s+tasks\s+to\s+volunteers\s+with\s+([^.\n]+skills?))"), "USER_PREFERENCE", "USER"),
    ]

    @classmethod
    def extract_candidates(
        cls,
        user_message: str,
        assistant_message: Optional[str] = None,
        event_id: Optional[int] = None,
        club_id: Optional[int] = None
    ) -> List[MemoryCandidate]:
        """
        Extracts structured memory candidates from interaction text.
        """
        candidates: List[MemoryCandidate] = []
        if not user_message:
            return candidates

        text = user_message.strip()

        # 1. Preferences
        for pat, mem_type, scope in cls.PREFERENCE_PATTERNS:
            match = pat.search(text)
            if match:
                content = match.group(0).strip()
                # Normalize canonical form
                if not content.lower().startswith("user prefers") and not content.lower().startswith("the club"):
                    content = f"User prefers {match.group(1).strip() if match.groups() else content}"
                candidates.append(MemoryCandidate(
                    memory_type=mem_type,
                    scope=scope,
                    content=content,
                    club_id=club_id,
                    event_id=event_id,
                    source="conversation"
                ))

        # 2. Club Rules & Process Knowledge
        for pat, mem_type, scope in cls.CLUB_RULE_PATTERNS:
            match = pat.search(text)
            if match:
                content = match.group(0).strip()
                candidates.append(MemoryCandidate(
                    memory_type=mem_type,
                    scope=scope,
                    content=content,
                    club_id=club_id,
                    event_id=event_id,
                    source="conversation"
                ))

        # 3. Lessons & Post-Mortems
        for pat, mem_type, scope in cls.LESSON_PATTERNS:
            match = pat.search(text)
            if match:
                content = match.group(0).strip()
                candidates.append(MemoryCandidate(
                    memory_type=mem_type,
                    scope=scope,
                    content=content,
                    club_id=club_id,
                    event_id=event_id,
                    source="conversation"
                ))

        # 4. Volunteer Knowledge
        for pat, mem_type, scope in cls.VOLUNTEER_PATTERNS:
            match = pat.search(text)
            if match:
                content = match.group(0).strip()
                candidates.append(MemoryCandidate(
                    memory_type=mem_type,
                    scope=scope,
                    content=content,
                    club_id=club_id,
                    event_id=event_id,
                    source="conversation"
                ))

        return candidates
