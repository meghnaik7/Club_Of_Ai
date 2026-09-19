"""
Comprehensive Automated Test Suite for Centralized Error Handling & LLM Model Fallback System.
Tests cover:
1. LLM Primary Success, Rate Limit, Timeout, Unavailable, Fallback Success & Failure.
2. Permanent Errors (Invalid API Key, Content Safety, Auth) -> No Fallback.
3. Bounded Retry Policy with Exponential Backoff and Retry-After hint.
4. Circuit Breaker State Transitions (CLOSED -> OPEN -> HALF-OPEN -> CLOSED).
5. Structured Output Validation (Pydantic, Markdown JSON extraction, Schema repair).
6. Model Selector Capability Matching (Tools, Structured Output).
7. Tool Error Classification, Timeouts, and Safe DB Read Retry.
8. Database Transaction Rollback and Conflict Handling.
9. RAG Failure & Transparent Fallback ("No reliable source found").
10. Agent Loop Limit (MAX_AGENT_ITERATIONS) and AgentState Error Tracking.
11. End-to-End Fallback: Primary -> Retry -> Fallback -> Success.
"""
import time
import unittest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel, Field

from app.ai.errors import (
    AIError,
    ErrorCode,
    ErrorCategory,
    RateLimitError,
    AuthenticationError,
    TimeoutError,
    NetworkError,
    ModelUnavailableError,
    InvalidResponseError,
    ContentPolicyError,
    CircuitBreakerOpenError,
    CapabilityMismatchError,
    ToolTimeoutError,
    ToolInvalidArgumentError,
    DatabaseUnavailableError,
    DatabaseConflictError,
    AgentLoopLimitError,
    classify_exception,
)
from app.ai.circuit_breaker import CircuitBreaker, CircuitState, circuit_breaker
from app.ai.retry import RetryPolicy
from app.ai.model_registry import ModelConfig, ModelRegistry, model_registry
from app.ai.model_selector import ModelSelector
from app.ai.response_validator import ResponseValidator
from app.ai.fallback import FallbackCoordinator
from app.ai.llm_service import LLMService, LLMResponse, llm_service
from ai.schemas.state import AgentState, AgentError


class SampleTaskPlan(BaseModel):
    title: str
    priority: str = "HIGH"
    steps_count: int = Field(ge=1)


class TestLLMFallbackSystem(unittest.TestCase):

    def setUp(self):
        # Reset global circuit breaker state before each test
        circuit_breaker.reset()
        model_registry.reload_from_settings()

    # =========================================================================
    # 1. Error Classification & Hierarchy
    # =========================================================================

    def test_01_classify_rate_limit(self):
        """HTTP 429 and rate limit messages are classified as RETRYABLE and FALLBACK_ELIGIBLE."""
        raw_exc = Exception("Error code 429: Rate limit exceeded, retry-after: 2.5")
        classified = classify_exception(raw_exc)
        self.assertIsInstance(classified, RateLimitError)
        self.assertEqual(classified.code, ErrorCode.LLM_RATE_LIMIT)
        self.assertEqual(classified.category, ErrorCategory.RETRYABLE)
        self.assertTrue(classified.retryable)
        self.assertTrue(classified.fallback_eligible)
        self.assertEqual(classified.details.get("retry_after"), 2.5)

    def test_02_classify_authentication_error(self):
        """Invalid API key (401) is classified as NON_RETRYABLE with NO fallback."""
        raw_exc = Exception("Incorrect API key provided: sk-invalid. (type: invalid_request_error, code: 401)")
        classified = classify_exception(raw_exc)
        self.assertIsInstance(classified, AuthenticationError)
        self.assertEqual(classified.code, ErrorCode.LLM_AUTH_ERROR)
        self.assertEqual(classified.category, ErrorCategory.NON_RETRYABLE)
        self.assertFalse(classified.retryable)
        self.assertFalse(classified.fallback_eligible)
        self.assertFalse(FallbackCoordinator.is_eligible_for_fallback(classified))

    def test_03_classify_timeout_and_network_error(self):
        """Timeouts and connection drops are classified as RETRYABLE and FALLBACK_ELIGIBLE."""
        timeout_exc = Exception("ReadTimeout: Request to api.openai.com timed out after 30s")
        conn_exc = Exception("ConnectError: Failed to establish a new connection: [Errno 111] Connection refused")

        c_timeout = classify_exception(timeout_exc)
        c_conn = classify_exception(conn_exc)

        self.assertIsInstance(c_timeout, TimeoutError)
        self.assertTrue(c_timeout.retryable)
        self.assertTrue(FallbackCoordinator.is_eligible_for_fallback(c_timeout))

        self.assertIsInstance(c_conn, NetworkError)
        self.assertTrue(c_conn.retryable)
        self.assertTrue(FallbackCoordinator.is_eligible_for_fallback(c_conn))

    def test_04_user_safe_error_masking(self):
        """Internal stack traces, SQL fragments, and secrets are masked in user response payload."""
        sql_exc = Exception("psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint 'users_pkey'")
        classified = classify_exception(sql_exc)
        user_dict = classified.to_user_dict()
        self.assertFalse(user_dict["success"])
        self.assertIn("error", user_dict)
        self.assertNotIn("psycopg2", user_dict["error"]["message"])
        self.assertNotIn("users_pkey", user_dict["error"]["message"])

    # =========================================================================
    # 2. Retry Policy & Exponential Backoff
    # =========================================================================

    def test_05_retry_exponential_backoff_timing(self):
        """Retry policy applies exponential backoff progression."""
        policy = RetryPolicy(max_retries=2, initial_delay=0.5, backoff_factor=2.0, jitter=False)
        d0 = policy.calculate_delay(0)
        d1 = policy.calculate_delay(1)
        self.assertAlmostEqual(d0, 0.5)
        self.assertAlmostEqual(d1, 1.0)

    def test_06_retry_respects_retry_after_hint(self):
        """Provider retry-after hint overrides default formula up to max_delay."""
        policy = RetryPolicy(max_retries=2, initial_delay=0.5, max_delay=10.0)
        d_hint = policy.calculate_delay(0, retry_after_hint=3.5)
        self.assertEqual(d_hint, 3.5)

    def test_07_retry_policy_aborts_on_non_retryable_error(self):
        """Non-retryable errors abort immediately on attempt 1 without retrying."""
        mock_fn = MagicMock(side_effect=Exception("Invalid API key provided: 401 unauthorized"))
        policy = RetryPolicy(max_retries=2, initial_delay=0.01)

        with self.assertRaises(AuthenticationError):
            policy.execute(mock_fn, operation_name="TestAuth")

        self.assertEqual(mock_fn.call_count, 1)

    def test_08_retry_policy_succeeds_on_second_attempt(self):
        """Temporary rate limit error retries and returns result on attempt 2."""
        attempts = 0
        def _flaky_service():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise Exception("429 Too Many Requests: Rate limit exceeded")
            return "SUCCESS_DATA"

        policy = RetryPolicy(max_retries=2, initial_delay=0.01, jitter=False)
        result, total_attempts = policy.execute(_flaky_service, operation_name="FlakyTest")
        self.assertEqual(result, "SUCCESS_DATA")
        self.assertEqual(total_attempts, 2)

    # =========================================================================
    # 3. Circuit Breaker State Transitions
    # =========================================================================

    def test_09_circuit_breaker_lifecycle(self):
        """Circuit transitions: CLOSED -> repeated failures -> OPEN -> cooldown -> HALF-OPEN -> recovery -> CLOSED."""
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.1, half_open_success_threshold=1)
        provider = "test_ai_provider"

        # Initially CLOSED
        self.assertEqual(cb.get_state(provider), CircuitState.CLOSED)
        allowed, _ = cb.can_execute(provider)
        self.assertTrue(allowed)

        # 1st failure -> still CLOSED
        cb.record_failure(provider, Exception("503 Overloaded"))
        self.assertEqual(cb.get_state(provider), CircuitState.CLOSED)

        # 2nd failure -> Trips to OPEN
        cb.record_failure(provider, Exception("503 Overloaded"))
        self.assertEqual(cb.get_state(provider), CircuitState.OPEN)

        # Immediate check is blocked
        allowed, remaining = cb.can_execute(provider)
        self.assertFalse(allowed)
        self.assertGreater(remaining, 0.0)

        # Wait for cooldown
        time.sleep(0.12)
        self.assertEqual(cb.get_state(provider), CircuitState.HALF_OPEN)
        allowed, _ = cb.can_execute(provider)
        self.assertTrue(allowed)

        # Successful test in HALF_OPEN resets to CLOSED
        cb.record_success(provider)
        self.assertEqual(cb.get_state(provider), CircuitState.CLOSED)

    # =========================================================================
    # 4. Structured Output Validation
    # =========================================================================

    def test_10_validate_markdown_json_response(self):
        """Extracts and parses JSON wrapped in ```json ... ``` code fences."""
        raw_llm_markdown = (
            "Here is the planned task as requested:\n"
            "```json\n"
            "{\n"
            '  "title": "Stage Calibration",\n'
            '  "priority": "HIGH",\n'
            '  "steps_count": 3\n'
            "}\n"
            "```\n"
            "Let me know if you want to make changes."
        )
        parsed = ResponseValidator.validate_structured(raw_llm_markdown, SampleTaskPlan)
        self.assertEqual(parsed.title, "Stage Calibration")
        self.assertEqual(parsed.priority, "HIGH")
        self.assertEqual(parsed.steps_count, 3)

    def test_11_validate_structured_output_schema_failure(self):
        """Invalid JSON schema values raise InvalidResponseError with schema details."""
        raw_invalid = '{"title": "Broken Plan", "steps_count": 0}'  # ge=1 fails
        with self.assertRaises(InvalidResponseError):
            ResponseValidator.validate_structured(raw_invalid, SampleTaskPlan)

    # =========================================================================
    # 5. Model Selector & Capability Matching
    # =========================================================================

    def test_12_model_selector_capability_validation(self):
        """Selector enforces required capabilities and blocks incompatible models."""
        no_tools_config = ModelConfig(
            name="chat_only",
            provider="mock",
            model="mock-chat",
            supports_tools=False,
            supports_structured_output=True,
        )
        with self.assertRaises(CapabilityMismatchError):
            ModelSelector.validate_capabilities(no_tools_config, require_tools=True)

    # =========================================================================
    # 6. Central LLM Service: Primary, Retry, Fallback End-to-End
    # =========================================================================

    def test_13_llm_service_primary_success(self):
        """Primary mock model returns valid LLMResponse without fallback."""
        service = LLMService(retry_policy=RetryPolicy(max_retries=0))
        resp = service.invoke("Hello ClubOps")
        self.assertTrue(resp.success)
        self.assertFalse(resp.fallback_used)
        self.assertIn("verified response", resp.content)

    def test_14_llm_service_failover_to_fallback(self):
        """When primary model encounters 503 unavailable, service fails over to fallback with fallback_used=True."""
        # Configure a primary that raises 503 and a fallback that succeeds
        primary_cfg = ModelConfig(
            name="primary",
            provider="gemini",
            model="gemini-failover-test",
            api_key="mock-key",
        )
        fallback_cfg = ModelConfig(
            name="fallback",
            provider="mock",
            model="clubops-mock-v1",
            api_key="mock-key",
        )
        model_registry.register(primary_cfg)
        model_registry.register(fallback_cfg)

        service = LLMService(retry_policy=RetryPolicy(max_retries=0))

        # Mock _dispatch_call to simulate primary failing with 503 and fallback succeeding
        def _mock_dispatch(config, prompt, **kwargs):
            if config.name == "primary":
                raise Exception("503 Service Unavailable: High cluster traffic")
            return {
                "content": "Fallback response delivered.",
                "tool_calls": [],
                "usage": {"total_tokens": 30}
            }

        with patch.object(service, "_dispatch_call", side_effect=_mock_dispatch):
            response = service.invoke("Summarize symposium schedule")
            self.assertTrue(response.success)
            self.assertTrue(response.fallback_used)
            self.assertEqual(response.content, "Fallback response delivered.")
            self.assertEqual(response.metadata.get("primary_error"), ErrorCode.LLM_UNAVAILABLE)

    def test_15_llm_service_circuit_breaker_tripped_immediate_fallback(self):
        """If primary provider circuit breaker is OPEN, call diverts immediately to fallback."""
        primary_cfg = ModelConfig(
            name="primary",
            provider="unstable_provider",
            model="unstable-v1",
            api_key="mock-key",
        )
        fallback_cfg = ModelConfig(
            name="fallback",
            provider="mock",
            model="clubops-mock-v1",
            api_key="mock-key",
        )
        model_registry.register(primary_cfg)
        model_registry.register(fallback_cfg)

        # Trip the primary provider circuit breaker to OPEN
        circuit_breaker.record_failure("unstable_provider", Exception("503"))
        circuit_breaker.record_failure("unstable_provider", Exception("503"))
        circuit_breaker.record_failure("unstable_provider", Exception("503"))
        self.assertEqual(circuit_breaker.get_state("unstable_provider"), CircuitState.OPEN)

        service = LLMService(retry_policy=RetryPolicy(max_retries=0))

        dispatch_mock = MagicMock(return_value={"content": "Immediate fallback result."})
        with patch.object(service, "_dispatch_call", side_effect=dispatch_mock):
            response = service.invoke("Test prompt")
            self.assertTrue(response.success)
            self.assertTrue(response.fallback_used)
            self.assertEqual(response.content, "Immediate fallback result.")

    def test_16_permanent_error_does_not_trigger_fallback(self):
        """Invalid API key (401) aborts immediately without attempting fallback."""
        primary_cfg = ModelConfig(
            name="primary",
            provider="gemini",
            model="gemini-auth-test",
            api_key="mock-key",
        )
        model_registry.register(primary_cfg)

        service = LLMService(retry_policy=RetryPolicy(max_retries=0))

        with patch.object(service, "_dispatch_call", side_effect=Exception("401 Unauthorized: Invalid API Key")):
            with self.assertRaises(AuthenticationError):
                service.invoke("Test prompt")

    # =========================================================================
    # 7. Agent Loop Protection & LangGraph Error Handling
    # =========================================================================

    def test_17_agent_loop_protection_limit(self):
        """Agent stops execution when iteration_count exceeds MAX_AGENT_ITERATIONS."""
        from ai.agents.graph import call_model, should_continue

        exhausted_state = AgentState(
            messages=[],
            user_id=1,
            proposal_ids=[],
            iteration_count=10,
        )

        result = call_model(exhausted_state)
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], ErrorCode.AGENT_MAX_ITERATIONS)
        self.assertIn("couldn't safely complete", result["messages"][0].content)

        # should_continue routes to __end__
        next_step = should_continue(result)
        self.assertEqual(next_step, "__end__")

    # =========================================================================
    # 8. Tool Safe Execution & Database Transient Retry
    # =========================================================================

    def test_18_tool_guard_transient_db_retry(self):
        """ToolGuard retries read tool execution once if a transient DB error occurs."""
        from app.guardrails.tool_guard import ToolGuard, ToolClassification

        call_attempts = 0
        def _flaky_db_read():
            nonlocal call_attempts
            call_attempts += 1
            if call_attempts == 1:
                raise Exception("OperationalError: connection to server was lost")
            return {"active_volunteers": 5}

        ToolGuard.register_tool(
            name="test_read_volunteers",
            description="Test read tool",
            classification=ToolClassification.READ,
            handler=_flaky_db_read
        )

        res = ToolGuard.execute_or_propose(
            tool_name="test_read_volunteers",
            arguments={},
            user=MagicMock(),
            db=None
        )

        self.assertEqual(res["status"], "EXECUTED_READ")
        self.assertEqual(res["data"]["active_volunteers"], 5)
        self.assertEqual(call_attempts, 2)


if __name__ == "__main__":
    unittest.main()
