"""
Capability-Aware Model Selector.
Selects and validates compatible models for primary and fallback execution,
ensuring required features (tool calling, structured output schemas, context length)
are verified before dispatching requests.
"""
import logging
from typing import Optional, List
from app.ai.model_registry import ModelConfig, model_registry
from app.ai.errors import CapabilityMismatchError, ModelUnavailableError

logger = logging.getLogger(__name__)


class ModelSelector:
    """
    Selects primary and fallback models adhering to capability policies.
    """

    @classmethod
    def validate_capabilities(
        cls,
        config: ModelConfig,
        require_tools: bool = False,
        require_structured_output: bool = False,
    ) -> None:
        """
        Validates whether a model configuration satisfies required execution capabilities.
        Raises CapabilityMismatchError if incompatible.
        """
        if require_tools and not config.supports_tools:
            raise CapabilityMismatchError(
                model_name=config.model,
                required_capability="tool_calling"
            )

        if require_structured_output and not config.supports_structured_output:
            raise CapabilityMismatchError(
                model_name=config.model,
                required_capability="structured_output"
            )

    @classmethod
    def select_primary(
        cls,
        require_tools: bool = False,
        require_structured_output: bool = False,
    ) -> ModelConfig:
        """
        Selects the primary model configuration and verifies capability requirements.
        """
        primary = model_registry.get("primary")
        if not primary:
            raise ModelUnavailableError("No primary model is registered.")

        # If primary has no API key and mock is available, we allow mock in testing/offline
        if not primary.is_configured():
            mock_model = model_registry.get("mock")
            fallback_model = model_registry.get("fallback")
            if fallback_model and fallback_model.is_configured():
                logger.info(f"Primary model unconfigured, selecting fallback '{fallback_model.name}' as primary.")
                cls.validate_capabilities(fallback_model, require_tools, require_structured_output)
                return fallback_model
            elif mock_model:
                logger.info("No external LLM credentials configured. Defaulting to mock offline model.")
                return mock_model

        cls.validate_capabilities(primary, require_tools, require_structured_output)
        return primary

    @classmethod
    def select_fallback(
        cls,
        primary_config: ModelConfig,
        require_tools: bool = False,
        require_structured_output: bool = False,
        preferred_fallback: Optional[str] = None,
    ) -> ModelConfig:
        """
        Selects a compatible fallback model distinct from the failed primary model.
        Evaluates 'fallback', then 'secondary', then 'mock' as offline safety net.
        """
        candidate_names: List[str] = []
        if preferred_fallback:
            candidate_names.append(preferred_fallback)
        candidate_names.extend(["fallback", "secondary", "mock"])

        for name in candidate_names:
            config = model_registry.get(name)
            if not config:
                continue

            # Avoid re-using identical failed model/provider
            if config.provider == primary_config.provider and config.model == primary_config.model and config.name == primary_config.name:
                continue

            # Verify capabilities
            try:
                cls.validate_capabilities(config, require_tools, require_structured_output)
            except CapabilityMismatchError:
                logger.debug(f"Candidate fallback '{name}' rejected due to capability mismatch.")
                continue

            # Check configuration
            if config.is_configured():
                logger.info(
                    f"Selected fallback model '{config.name}' (provider: {config.provider}, model: {config.model}) "
                    f"for failed primary '{primary_config.name}'."
                )
                return config

        # If no external fallback configured, use mock
        mock = model_registry.get("mock")
        if mock:
            cls.validate_capabilities(mock, require_tools, require_structured_output)
            return mock

        raise ModelUnavailableError(
            f"No compatible fallback model could be found supporting required capabilities "
            f"(tools={require_tools}, structured={require_structured_output})."
        )
