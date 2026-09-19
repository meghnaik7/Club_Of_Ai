"""
PII / Data Privacy Guardrail (6):
- Protects personal, financial, and sensitive credential information
- Masks tokens, phone numbers, emails (where appropriate), and identity numbers
- Enforces non-discrimination in volunteer assignments (rejects protected characteristics)
"""
import re
from typing import Tuple, List

class PIIGuard:
    # Patterns for sensitive data
    PATTERNS = {
        "JWT_TOKEN": r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9._-]+\b",
        "API_KEY": r"\b(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|AIza[0-9A-Za-z-_]{35})\b",
        "PHONE_NUMBER": r"\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b",
        "AADHAAR_SSN": r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b|\b\d{3}-\d{2}-\d{4}\b",
        "PASSWORD_ASSIGNMENT": r"(?i)\bpassword\s*[:=]\s*['\"]?[^\s'\"]+['\"]?",
    }

    # Protected demographic characteristics prohibited from influencing assignments
    DISCRIMINATORY_TERMS = [
        r"(?i)\b(gender|male|female|man|woman|boy|girl)\s+(only|preference|required)\b",
        r"(?i)\b(religion|hindu|muslim|christian|sikh|jewish|caste)\s+(only|preference|required)\b",
        r"(?i)\b(race|ethnicity|white|black|asian|hispanic)\s+(only|preference|required)\b",
    ]

    @classmethod
    def sanitize_pii(cls, text: str) -> Tuple[str, List[str]]:
        """
        Scans and redacts sensitive PII from text.
        Returns: (sanitized_text, list_of_redacted_types)
        """
        if not text:
            return text, []

        redacted_types = []
        result = text

        for pii_type, pattern in cls.PATTERNS.items():
            if re.search(pattern, result):
                redacted_types.append(pii_type)
                result = re.sub(pattern, f"[REDACTED_{pii_type}]", result)

        return result, redacted_types

    @classmethod
    def check_fair_assignment(cls, criteria_text: str) -> Tuple[bool, str]:
        """
        Ensures volunteer assignment recommendations are free from discriminatory criteria.
        Guardrail 19: Prohibits demographic or protected characteristics in task allocation.
        """
        if not criteria_text:
            return True, ""

        for pattern in cls.DISCRIMINATORY_TERMS:
            match = re.search(pattern, criteria_text)
            if match:
                return False, f"Prohibited assignment criterion detected: '{match.group(0)}'. Assignments must be strictly skill and availability based."

        return True, ""
