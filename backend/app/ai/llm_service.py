"""
Centralized LLM Service for ClubOps AI.
Single source of truth for all LLM invocations across agents, tools, and workflows.
Orchestrates:
- Capability validation (ModelSelector)
- Circuit Breaker checks
- Primary Model invocation with Bounded Exponential Retries
- Error classification and Fallback eligibility determination
- Fallback Model selection & failover execution
- Structured Output validation (Pydantic)
- Latency & token observability logging with correlation IDs
- Secret sanitization and error masking
"""
import time
import uuid
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel, Field

from app.ai.errors import (
    AIError,
    ErrorCode,
    CircuitBreakerOpenError,
    ModelUnavailableError,
    InvalidResponseError,
    classify_exception,
)
from app.ai.circuit_breaker import circuit_breaker
from app.ai.retry import RetryPolicy, default_retry_policy
from app.ai.model_registry import ModelConfig, model_registry
from app.ai.model_selector import ModelSelector
from app.ai.fallback import FallbackCoordinator
from app.ai.response_validator import ResponseValidator
from app.guardrails.output_guard import OutputGuard
from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMResponse(BaseModel):
    """Normalized response envelope for all LLM calls."""
    content: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    model_used: str
    provider_used: str
    fallback_used: bool = False
    latency_ms: float = 0.0
    token_usage: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: str = ""
    success: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_chat_message(self) -> Any:
        """Converts to LangChain AIMessage for LangGraph compatibility."""
        from langchain_core.messages import AIMessage
        return AIMessage(
            content=self.content,
            tool_calls=self.tool_calls,
            additional_kwargs={
                "model_used": self.model_used,
                "provider_used": self.provider_used,
                "fallback_used": self.fallback_used,
                "latency_ms": self.latency_ms,
            }
        )


class LLMService:
    """
    Centralized LLM Service with Circuit Breaker, Bounded Retries, and Fallback.
    """

    def __init__(
        self,
        retry_policy: Optional[RetryPolicy] = None,
    ):
        self.retry_policy = retry_policy or default_retry_policy

    # -------------------------------------------------------------------------
    # Core Invocation API
    # -------------------------------------------------------------------------

    def invoke(
        self,
        prompt: Union[str, List[Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[int] = None,
        event_id: Optional[int] = None,
        timeout: Optional[float] = None,
        temperature: Optional[float] = None,
        tool_name: Optional[str] = None,
    ) -> LLMResponse:
        """
        Main entry point for freeform or tool-calling LLM interactions.
        All agents and workflows must call this method.
        """
        corr_id = correlation_id or str(uuid.uuid4())
        require_tools = bool(tools)

        # 1. Select Primary Model
        primary_config = ModelSelector.select_primary(
            require_tools=require_tools,
            require_structured_output=False,
        )

        # 2. Attempt Primary Model with Circuit Breaker and Retries
        start_time = time.time()
        primary_error: Optional[AIError] = None
        total_primary_attempts = 0

        can_call_primary, cooldown = circuit_breaker.can_execute(primary_config.provider)
        if not can_call_primary:
            primary_error = CircuitBreakerOpenError(
                provider=primary_config.provider,
                cooldown_remaining=cooldown or 0.0
            )
            logger.warning(
                f"[{corr_id}] Primary provider '{primary_config.provider}' circuit is OPEN. "
                f"Skipping primary and diverting directly to fallback."
            )
        else:
            try:
                def _call_primary():
                    return self._dispatch_call(
                        config=primary_config,
                        prompt=prompt,
                        system_prompt=system_prompt,
                        tools=tools,
                        timeout=timeout,
                        temperature=temperature,
                    )

                raw_res, total_primary_attempts = self.retry_policy.execute(
                    _call_primary,
                    operation_name=f"Primary ({primary_config.provider}/{primary_config.model})"
                )
                circuit_breaker.record_success(primary_config.provider)
                latency = (time.time() - start_time) * 1000.0

                cleaned_content = OutputGuard.sanitize_output(raw_res.get("content", ""))
                return LLMResponse(
                    content=cleaned_content,
                    tool_calls=raw_res.get("tool_calls", []),
                    model_used=primary_config.model,
                    provider_used=primary_config.provider,
                    fallback_used=False,
                    latency_ms=round(latency, 2),
                    token_usage=raw_res.get("usage", {}),
                    correlation_id=corr_id,
                    success=True,
                )

            except Exception as exc:
                primary_error = classify_exception(exc)
                circuit_breaker.record_failure(primary_config.provider, exc)
                logger.warning(
                    f"[{corr_id}] Primary model failed ({primary_error.code}): {primary_error.message}. "
                    f"Checking fallback eligibility..."
                )

        # 3. Fallback Evaluation
        if not primary_error or not FallbackCoordinator.is_eligible_for_fallback(primary_error):
            logger.error(
                f"[{corr_id}] Error {primary_error.code if primary_error else 'UNKNOWN'} is not eligible for fallback. "
                f"Aborting execution."
            )
            raise primary_error

        # 4. Select and Execute Fallback Model
        fallback_config = ModelSelector.select_fallback(
            primary_config=primary_config,
            require_tools=require_tools,
            require_structured_output=False,
        )

        can_call_fallback, fb_cooldown = circuit_breaker.can_execute(fallback_config.provider)
        if not can_call_fallback:
            raise CircuitBreakerOpenError(
                provider=fallback_config.provider,
                cooldown_remaining=fb_cooldown or 0.0
            )

        fb_start_time = time.time()
        try:
            def _call_fallback():
                return self._dispatch_call(
                    config=fallback_config,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    tools=tools,
                    timeout=timeout,
                    temperature=temperature,
                )

            fb_raw_res, total_fb_attempts = self.retry_policy.execute(
                _call_fallback,
                operation_name=f"Fallback ({fallback_config.provider}/{fallback_config.model})"
            )
            circuit_breaker.record_success(fallback_config.provider)
            latency = (time.time() - fb_start_time) * 1000.0

            FallbackCoordinator.log_fallback_event(
                primary_config=primary_config,
                fallback_config=fallback_config,
                error=primary_error,
                retry_count=total_primary_attempts,
                success=True,
                correlation_id=corr_id,
                tool_name=tool_name,
            )

            cleaned_content = OutputGuard.sanitize_output(fb_raw_res.get("content", ""))
            return LLMResponse(
                content=cleaned_content,
                tool_calls=fb_raw_res.get("tool_calls", []),
                model_used=fallback_config.model,
                provider_used=fallback_config.provider,
                fallback_used=True,
                latency_ms=round(latency, 2),
                token_usage=fb_raw_res.get("usage", {}),
                correlation_id=corr_id,
                success=True,
                metadata={"primary_error": primary_error.code},
            )

        except Exception as fb_exc:
            classified_fb_err = classify_exception(fb_exc)
            circuit_breaker.record_failure(fallback_config.provider, fb_exc)
            FallbackCoordinator.log_fallback_event(
                primary_config=primary_config,
                fallback_config=fallback_config,
                error=primary_error,
                retry_count=total_primary_attempts,
                success=False,
                correlation_id=corr_id,
                tool_name=tool_name,
            )
            raise classified_fb_err

    def invoke_structured(
        self,
        prompt: Union[str, List[Any]],
        response_schema: Type[T],
        system_prompt: Optional[str] = None,
        correlation_id: Optional[str] = None,
        timeout: Optional[float] = None,
        temperature: Optional[float] = None,
    ) -> T:
        """
        Executes prompt and validates response against target Pydantic schema.
        Handles JSON parse failures, schema validation retries, and fallback.
        """
        schema_instruction = (
            f"\n\nCRITICAL: Respond ONLY with a valid JSON object matching this schema:\n"
            f"{response_schema.model_json_schema()}\nDo not include any prose outside the JSON block."
        )

        effective_sys = (system_prompt or "") + schema_instruction

        # Attempt invocation
        response = self.invoke(
            prompt=prompt,
            system_prompt=effective_sys,
            correlation_id=correlation_id,
            timeout=timeout,
            temperature=temperature or 0.1,
        )

        try:
            return ResponseValidator.validate_structured(response.content, response_schema)
        except InvalidResponseError as val_err:
            logger.warning(
                f"First structured validation failed ({val_err.message}). "
                f"Retrying structured validation with targeted repair prompt..."
            )
            # One repair attempt with the schema error
            repair_prompt = (
                f"Original output was invalid for schema '{response_schema.__name__}'.\n"
                f"Error: {val_err.message}\n"
                f"Please correct the JSON and return only the valid JSON object:"
            )
            repair_response = self.invoke(
                prompt=repair_prompt,
                system_prompt=effective_sys,
                correlation_id=correlation_id,
                timeout=timeout,
                temperature=0.0,
            )
            return ResponseValidator.validate_structured(repair_response.content, response_schema)

    # -------------------------------------------------------------------------
    # Internal Provider Dispatcher
    # -------------------------------------------------------------------------

    def _dispatch_call(
        self,
        config: ModelConfig,
        prompt: Union[str, List[Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        timeout: Optional[float] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches request to specific provider implementation (Gemini, OpenAI, OpenRouter, Mock).
        """
        eff_timeout = timeout or config.timeout
        eff_temp = temperature if temperature is not None else config.temperature

        # 1. Mock / Offline Provider
        if config.provider == "mock":
            return self._call_mock(prompt, tools)

        # 2. OpenAI / Azure / OpenRouter Provider
        if config.provider in ("openai", "openrouter", "azure", "azure_openai"):
            return self._call_openai(config, prompt, system_prompt, tools, eff_timeout, eff_temp)

        # 3. Gemini / Google Provider
        if config.provider in ("gemini", "google"):
            return self._call_gemini(config, prompt, system_prompt, tools, eff_timeout, eff_temp)

        # Unknown provider fallback to OpenAI-compatible
        return self._call_openai(config, prompt, system_prompt, tools, eff_timeout, eff_temp)

    def _call_mock(
        self,
        prompt: Union[str, List[Any]],
        tools: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Offline deterministic mock provider for testing and disconnected environments."""
        prompt_text = str(prompt)
        if "generate tasks" in prompt_text.lower() or "task plan" in prompt_text.lower():
            content = (
                '{"tasks": [{"title": "Setup Venue", "description": "Prepare stage and mics", "status": "TODO"}], '
                '"success": true, "summary": "Generated 1 task."}'
            )
        elif "{" in prompt_text and "}" in prompt_text:
            content = '{"success": true, "summary": "Mock structured response completed."}'
        else:
            content = "This is a verified response from the ClubOps AI service."

        return {
            "content": content,
            "tool_calls": [],
            "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
        }

    def _call_openai(
        self,
        config: ModelConfig,
        prompt: Union[str, List[Any]],
        system_prompt: Optional[str],
        tools: Optional[List[Any]],
        timeout: float,
        temperature: float,
    ) -> Dict[str, Any]:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage

        is_azure = (config.provider in ("azure", "azure_openai") or (config.base_url and "azure" in config.base_url.lower())) and config.provider != "openrouter"
        azure_ep = config.base_url or getattr(settings, "AZURE_OPENAI_ENDPOINT", None)

        if is_azure and azure_ep:
            from langchain_openai import AzureChatOpenAI
            llm = AzureChatOpenAI(
                azure_endpoint=azure_ep,
                api_key=config.api_key or getattr(settings, "AZURE_OPENAI_API_KEY", "") or getattr(settings, "OPENAI_API_KEY", ""),
                api_version=getattr(settings, "AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
                azure_deployment=config.model,
                temperature=temperature,
                request_timeout=timeout,
            )
        else:
            default_headers = {}
            if config.provider == "openrouter" or (config.base_url and "openrouter" in config.base_url.lower()):
                default_headers = {
                    "HTTP-Referer": "https://github.com/meghnaik7/Club_Of_Ai",
                    "X-Title": "ClubOps AI",
                }
            llm = ChatOpenAI(
                api_key=config.api_key or getattr(settings, "OPENROUTER_API_KEY", "") or "sk-mock-key-for-test",
                model=config.model,
                base_url=config.base_url or (getattr(settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1") if config.provider == "openrouter" else None),
                default_headers=default_headers or None,
                temperature=temperature,
                request_timeout=timeout,
            )

        if tools:
            llm = llm.bind_tools(tools)

        # Normalize messages
        messages: List[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        if isinstance(prompt, str):
            messages.append(HumanMessage(content=prompt))
        elif isinstance(prompt, list):
            for item in prompt:
                if isinstance(item, BaseMessage):
                    messages.append(item)
                else:
                    messages.append(HumanMessage(content=str(item)))

        res = llm.invoke(messages)

        tool_calls = []
        if hasattr(res, "tool_calls") and res.tool_calls:
            tool_calls = res.tool_calls

        usage = {}
        if hasattr(res, "response_metadata") and isinstance(res.response_metadata, dict):
            usage = res.response_metadata.get("token_usage", {})

        return {
            "content": str(res.content or ""),
            "tool_calls": tool_calls,
            "usage": usage,
        }

    def _call_gemini(
        self,
        config: ModelConfig,
        prompt: Union[str, List[Any]],
        system_prompt: Optional[str],
        tools: Optional[List[Any]],
        timeout: float,
        temperature: float,
    ) -> Dict[str, Any]:
        """Invokes Gemini using official Google GenAI SDK if available, or ChatOpenAI if mocked."""
        try:
            from google import genai
            client = genai.Client(api_key=config.api_key)
            full_prompt = (f"{system_prompt}\n\n" if system_prompt else "") + str(prompt)
            res = client.models.generate_content(
                model=config.model,
                contents=full_prompt,
            )
            return {
                "content": str(res.text or ""),
                "tool_calls": [],
                "usage": {},
            }
        except ImportError:
            # If google-genai is not imported or environment uses langchain, delegate to generic
            return self._call_openai(config, prompt, system_prompt, tools, timeout, temperature)


# Global singleton instance for centralized use
llm_service = LLMService()
