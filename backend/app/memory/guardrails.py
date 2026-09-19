import re
from typing import Tuple, Optional

# Regex patterns for sensitive data & credentials
SECRET_PATTERNS = [
    re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|pwd|bearer|credential)\b\s*[:=\s]+\s*['\"]?(?:bearer\s+)?([A-Za-z0-9_\-\.]{6,})"),
    re.compile(r"(?i)\b(?:bearer\s+[A-Za-z0-9_\-\.]{10,})\b"),
    re.compile(r"\b(?:sk-[a-zA-Z0-9]{15,}|ghp_[a-zA-Z0-9]{15,}|ey[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,})\b"),
    re.compile(r"(?i)\b(password|api\s*key)\s+(?:is|was)\s+['\"]?([A-Za-z0-9_\-\.\@\$]{4,})"),
    re.compile(r"(?i)\bAWS[A-Z0-9]{16,}\b")
]

# Regex patterns for prompt injection or system control override
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)\b(?:ignore|override|bypass|forget)\s+(?:all\s+)?(?:previous|prior|system)\s+(?:instructions|prompts|rules)"),
    re.compile(r"(?i)\b(?:remember|store)\s+(?:this\s+)?(?:system\s+prompt|hidden\s+instruction|developer\s+mode)"),
    re.compile(r"(?i)\byou\s+are\s+now\s+(?:in\s+developer\s+mode|dan|unrestricted)"),
    re.compile(r"(?i)\bstore\s+everything\s+from\s+this\s+conversation\b"),
]

# Patterns for purely transient/temporary operational requests
TRANSIENT_PATTERNS = [
    re.compile(r"(?i)^(?:hi|hello|hey|good\s+morning|good\s+evening|howdy)[!\.\?]*$"),
    re.compile(r"(?i)^(?:create|add|delete|remove|show|list)\s+(?:a\s+)?(?:task|event|announcement)\s+(?:for\s+)?(?:today|tomorrow|yesterday|[0-9]{1,2}(?:st|nd|rd|th)?|\w+day)"),
    re.compile(r"(?i)^the\s+event\s+starts\s+(?:tomorrow|today|next\s+week)"),
    re.compile(r"(?i)^i\s+want\s+to\s+plan\b"),
    re.compile(r"(?i)^what\s+is\s+the\s+status\b"),
]

class MemoryGuardrails:
    """
    Validates candidate memories before persistence.
    Prevents storage of secrets, prompt injections, raw tool dumps, and transient states.
    """

    @classmethod
    def validate_candidate(cls, content: str, source: str = "conversation") -> Tuple[bool, Optional[str]]:
        if not content or not content.strip():
            return False, "Empty memory content"

        trimmed = content.strip()

        # 1. Check length boundaries
        if len(trimmed) < 5:
            return False, "Content too short to constitute a meaningful fact"
        if len(trimmed) > 1000:
            return False, "Content exceeds maximum length for a single canonical memory"

        # 2. Check for secrets, credentials, API keys, passwords
        for pattern in SECRET_PATTERNS:
            if pattern.search(trimmed):
                return False, "Rejected: Contains API key, password, or sensitive credential"

        # 3. Check for prompt injection / system instruction overrides
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(trimmed):
                return False, "Rejected: Prompt injection or system prompt tampering detected"

        # 4. Check for transient / temporary status
        for pattern in TRANSIENT_PATTERNS:
            if pattern.search(trimmed):
                return False, "Rejected: Transient or conversational small talk, not a persistent fact"

        # 5. Check for raw chain-of-thought or reasoning prefixes
        if re.search(r"(?i)^\s*(?:agent\s+thinks|thought:|thinking:|reasoning:)", trimmed):
            return False, "Rejected: Temporary agent reasoning cannot be stored as memory"

        return True, None
