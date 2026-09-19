"""
Response Validator for ClubOps AI.
Strictly parses and validates raw LLM output against Pydantic schemas.
Supports markdown JSON block extraction, type coercion, and safe validation error reporting.
"""
import re
import json
import logging
from typing import Any, Type, TypeVar, Optional, Dict
from pydantic import BaseModel, ValidationError
from app.ai.errors import InvalidResponseError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ResponseValidator:
    """
    Parses and verifies raw and structured LLM responses.
    """

    @classmethod
    def extract_json(cls, raw_output: Any) -> Any:
        """
        Extracts JSON from raw string, code blocks, or passthrough if already a dict/list.
        """
        if isinstance(raw_output, (dict, list)):
            return raw_output

        if not isinstance(raw_output, str):
            raise InvalidResponseError(f"Expected text or dict response, got {type(raw_output).__name__}")

        text = raw_output.strip()

        # 1. Search for markdown ```json ... ``` or ``` ... ```
        block_pattern = re.search(r"```(?:json)?\s*([\{\[].*?[\}\]])\s*```", text, re.DOTALL)
        if block_pattern:
            candidate = block_pattern.group(1).strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse fenced JSON: {e}")

        # 2. Try parsing raw text directly
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 3. Search for outermost { ... } or [ ... ]
        curly_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if curly_match:
            try:
                return json.loads(curly_match.group(1))
            except json.JSONDecodeError:
                pass

        bracket_match = re.search(r"(\[.*\])", text, re.DOTALL)
        if bracket_match:
            try:
                return json.loads(bracket_match.group(1))
            except json.JSONDecodeError:
                pass

        raise InvalidResponseError(
            message=f"Output could not be parsed as valid JSON: {text[:200]}...",
            retryable=True
        )

    @classmethod
    def validate_structured(
        cls,
        raw_output: Any,
        schema: Type[T],
    ) -> T:
        """
        Validates raw output against a target Pydantic model.
        Raises InvalidResponseError on parse or schema validation failure.
        """
        parsed_json = cls.extract_json(raw_output)

        if not isinstance(parsed_json, dict):
            raise InvalidResponseError(
                message=f"Expected JSON object for schema '{schema.__name__}', got {type(parsed_json).__name__}",
                retryable=True
            )

        try:
            return schema(**parsed_json)
        except ValidationError as val_err:
            error_details = str(val_err)
            logger.warning(f"Schema validation error for '{schema.__name__}': {error_details[:200]}")
            raise InvalidResponseError(
                message=f"Schema validation failed for '{schema.__name__}': {error_details}",
                retryable=True,
                details={"validation_errors": val_err.errors()}
            )
