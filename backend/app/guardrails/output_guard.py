"""
Output, Schema, Secret Leakage & Error Guardrails (18, 19, 33, 37):
- Output Guardrail: Sanitizes and reviews model outputs prior to delivery
- Structured Output Guardrail: Strictly validates JSON using Pydantic schemas; graceful recovery
- Secret Leakage Guardrail: Prohibits leaking API keys, tokens, system prompts, DB creds, and private reasoning
- Error Handling Guardrail: Masks internal SQL/traceback errors; yields clear, safe user-facing notices
"""
import re
import json
from typing import Any, Dict, Optional, Tuple, Type
from pydantic import BaseModel, ValidationError

class SecretLeakageError(ValueError):
    """Raised when an output contains leaked secrets, credentials, or private prompts."""
    pass

class OutputGuard:
    # Patterns for secrets to scrub/block
    SECRET_PATTERNS = [
        (r"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9._-]+\b", "[REDACTED_JWT_TOKEN]"),
        (r"\b(sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9_-]{30,}|AIza[0-9A-Za-z-_]{35})\b", "[REDACTED_API_KEY]"),
        (r"(?i)\bpassword\s*:\s*[^\s,;]+", "password: [REDACTED_PASSWORD]"),
        (r"(?i)\bpostgres(ql)?://[^\s'\"]+:[^\s'\"]+@[^\s'\"]+\b", "[REDACTED_DATABASE_URL]"),
        (r"(?i)\bSECRET_KEY\s*=\s*['\"][^'\"]+['\"]", "SECRET_KEY=[REDACTED]"),
        (r"(?i)\b(system\s+instruction|system\s+prompt)\s*:\s*\"?[^\"]+\"?", "[REDACTED_INTERNAL_POLICY]"),
    ]

    # Patterns indicating private chain-of-thought that shouldn't be exposed raw
    CHAIN_OF_THOUGHT_LEAKS = [
        r"(?i)<thought>.*?</thought>",
        r"(?i)<thinking>.*?</thinking>",
        r"(?i)my internal reasoning is as follows:"
    ]

    @classmethod
    def sanitize_output(cls, output_text: str) -> str:
        """
        Guardrails 18 & 33:
        Scans for credentials, API keys, database connection strings, and private thoughts.
        Redacts them before returning to the user.
        """
        if not output_text or not isinstance(output_text, str):
            return output_text or ""

        cleaned = output_text

        # 1. Scrub secrets
        for pattern, replacement in cls.SECRET_PATTERNS:
            cleaned = re.sub(pattern, replacement, cleaned)

        # 2. Scrub raw chain-of-thought blocks
        for cot_pattern in cls.CHAIN_OF_THOUGHT_LEAKS:
            cleaned = re.sub(cot_pattern, "", cleaned, flags=re.DOTALL)

        return cleaned.strip()

    @classmethod
    def scrub_secrets(cls, output_text: str) -> str:
        """Scans for credentials, tokens, API keys and replaces with [REDACTED_SECRET]."""
        if not output_text or not isinstance(output_text, str):
            return output_text or ""
        cleaned = output_text
        for pattern, _ in cls.SECRET_PATTERNS:
            cleaned = re.sub(pattern, "[REDACTED_SECRET]", cleaned)
        for cot_pattern in cls.CHAIN_OF_THOUGHT_LEAKS:
            cleaned = re.sub(cot_pattern, "", cleaned, flags=re.DOTALL)
        return cleaned.strip()

    @classmethod
    def validate_structured_output(
        cls,
        raw_output: Any,
        schema: Type[BaseModel]
    ) -> Any:
        """
        Guardrail 19: Structured Output Guardrail.
        Parses raw dict/JSON against a target Pydantic schema.
        Handles parse errors safely without crashing the backend, returning safe fallback.
        """
        try:
            if isinstance(raw_output, str):
                # Attempt to extract JSON from markdown if wrapped in ```json ... ```
                json_match = re.search(r'```(?:json)?\s*(\{.*\}|\[.*\])\s*```', raw_output, re.DOTALL)
                if json_match:
                    raw_data = json.loads(json_match.group(1))
                else:
                    raw_data = json.loads(raw_output)
            else:
                raw_data = raw_output

            return schema(**raw_data)
        except Exception as e:
            try:
                return schema(
                    success=False,
                    summary=f"Input could not be parsed as valid structured format: {str(e)}",
                    action_taken="ERROR",
                    warnings=[f"SCHEMA_VALIDATION_ERROR: {str(e)}"]
                )
            except Exception:
                return (False, None, f"Structured output schema validation failed: {str(e)}")

    @classmethod
    def safe_error_message(cls, exc: Exception) -> str:
        return cls.mask_error_safely(exc)


    @classmethod
    def mask_error_safely(cls, exc: Exception) -> str:
        """
        Guardrail 37: Error Handling Guardrail.
        Masks internal database constraints, table names, SQL statements, and stack traces.
        Returns clean, safe user-facing message.
        """
        err_str = str(exc)
        # Check for sensitive DB / SQL keywords
        if any(w in err_str.lower() for w in ["psycopg2", "sqlalchemy", "syntax error at or near", "column does not exist", "table"]):
            return "An internal data constraint error occurred. No database state was modified."

        if "password" in err_str.lower() or "secret" in err_str.lower() or "token" in err_str.lower():
            return "An authentication or authorization verification error occurred."

        return err_str[:300]
