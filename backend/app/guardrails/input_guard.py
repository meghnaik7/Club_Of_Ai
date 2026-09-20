"""
Input Guardrail (1, 2, 39):
- Validates and sanitizes all user input
- Detects prompt injection, jailbreaks, and instruction override attempts
- Enforces message length and context window limits
"""
import re
from typing import Tuple, List, Optional

class InputSecurityError(ValueError):
    """Base exception for input security violations."""
    pass

class PromptInjectionError(InputSecurityError):
    """Raised when prompt injection or malicious instructions are detected."""
    pass

class InputLengthError(InputSecurityError):
    """Raised when input exceeds allowed context window or length limits."""
    pass

class InputGuard:
    MAX_INPUT_LENGTH = 16000  # Character limit to protect token budgets and prevent context flooding
    MIN_INPUT_LENGTH = 1

    # Heuristic prompt injection patterns
    INJECTION_PATTERNS = [
        r"(?i)\bignore\s+(all\s+)?(previous|prior|above|past)\s+(instructions|commands)\b",
        r"(?i)\bdisregard\s+(all\s+)?(previous|prior|above|past)\s+(instructions|prompts|rules|commands)\b",
        r"(?i)\breveal\s+(your\s+)?(system\s+prompt|hidden\s+prompt|instructions|secret\s+key)\b",
        r"(?i)\bwhat\s+(is|are)\s+your\s+(system\s+prompt|initial\s+instructions)\b",
        r"(?i)\bdisable\s+(your\s+)?(safety\s+rules|guardrails|safety\s+filter)\b",
        r"(?i)\brun\s+this\s+sql\b",
        r"(?i)\bdelete\s+(all\s+)?(database|everything|records|tables)\b",
        r"(?i)\btreat\s+this\s+document\s+as\s+(an\s+)?administrator\s+instruction\b",
        r"(?i)\bcall\s+this\s+tool\s+without\s+confirmation\b",
        r"(?i)\bgive\s+me\s+the\s+(api\s+key|password|jwt|token|credentials)\b",
        r"(?i)\bexecute\s+(the\s+following\s+)?(code|python|shell|bash|powershell|script)\b",
        r"(?i)\bdrop\s+table\b",
        r"(?i)\bunion\s+select\b",
        r"(?i)\byou\s+are\s+now\s+in\s+developer\s+mode\b",
        r"(?i)\bdo\s+anything\s+now\b",
        r"(?i)\bjailbreak\b",
        r"(?i)<script\b",
        r"(?i)###\s*(system|assistant|instruction)",
        r"(?i)system\s*instruction:"
    ]

    @classmethod
    def validate_input(cls, text: str, is_document: bool = False) -> Tuple[bool, str, Optional[str]]:
        """
        Validates user or document input.
        Returns: (is_valid, sanitized_text, violation_reason)
        """
        if not text or not isinstance(text, str):
            return False, "", "Empty input provided"

        # 1. Length validation (Guardrail 39: Context Window Guardrail)
        if len(text) > cls.MAX_INPUT_LENGTH:
            raise InputLengthError(f"Input exceeds maximum allowed length of {cls.MAX_INPUT_LENGTH} characters.")

        if len(text.strip()) < cls.MIN_INPUT_LENGTH:
            return False, "", "Input must contain non-whitespace characters"

        # 2. Sanitization (Guardrail 1: Input Guardrail)
        # Strip null bytes and control characters (except newline, carriage return, tab)
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

        # 3. Injection Detection (Guardrail 2: Prompt Injection Guardrail)
        for pattern in cls.INJECTION_PATTERNS:
            match = re.search(pattern, sanitized)
            if match:
                matched_phrase = match.group(0)
                if is_document:
                    # In documents, we mark it as untrusted data without failing the whole extraction
                    return True, sanitized, f"Untrusted instruction detected inside document: '{matched_phrase}'. Will treat purely as data."
                else:
                    raise PromptInjectionError(
                        f"Prompt injection attempt detected: '{matched_phrase}'. Malicious instruction overrides are prohibited."
                    )

        return True, sanitized, None

    @classmethod
    def sanitize_search_query(cls, query: str) -> str:
        """Sanitizes text specifically for search queries to prevent query injection."""
        clean = re.sub(r'[;\'"\\]', '', query)
        return clean.strip()[:500]
