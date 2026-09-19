"""
Model Registry for ClubOps AI.
Loads credentials, models, and capability policies dynamically from environment configuration.
Provides unified model instantiation for Gemini, OpenAI, OpenRouter, and Mock offline clients.
"""
import os
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

try:
    from app.core.config import settings
except ImportError:
    from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class ModelConfig(BaseModel):
    """Configuration and capability profile for an AI model."""
    name: str
    provider: str  # "gemini", "openai", "openrouter", "mock"
    model: str
    api_key: str = ""
    base_url: Optional[str] = None
    temperature: float = 0.2
    timeout: float = 30.0
    max_retries: int = 2
    supports_tools: bool = True
    supports_structured_output: bool = True
    context_window: int = 128000

    def is_configured(self) -> bool:
        """Returns True if the model has a valid provider and credentials (or is mock)."""
        if self.provider == "mock":
            return True
        return bool(self.api_key and not self.api_key.startswith("your-"))


class ModelRegistry:
    """
    Central registry of configured AI models.
    """

    def __init__(self):
        self._models: Dict[str, ModelConfig] = {}
        self.reload_from_settings()

    def reload_from_settings(self) -> None:
        """Reloads primary, fallback, and secondary model definitions from settings."""
        self._models.clear()

        # 1. Primary Model
        primary_provider = getattr(settings, "PRIMARY_LLM_PROVIDER", getattr(settings, "LLM_PROVIDER", "openrouter")).lower()
        primary_model = getattr(settings, "PRIMARY_LLM_MODEL", getattr(settings, "LLM_MODEL", "openai/gpt-4o-mini"))
        primary_key = getattr(settings, "PRIMARY_LLM_API_KEY", "") or getattr(settings, "OPENROUTER_API_KEY", "") or getattr(settings, "AZURE_OPENAI_API_KEY", "") or getattr(settings, "OPENAI_API_KEY", "")
        if not primary_key and primary_provider in ("gemini", "google"):
            primary_key = getattr(settings, "GEMINI_API_KEY", "")
        if "azure" in primary_provider:
            primary_base_url = getattr(settings, "AZURE_OPENAI_ENDPOINT", None)
        elif primary_provider == "openrouter":
            primary_base_url = getattr(settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        else:
            primary_base_url = None

        self._models["primary"] = ModelConfig(
            name="primary",
            provider=primary_provider,
            model=primary_model,
            api_key=primary_key,
            base_url=primary_base_url,
            timeout=float(getattr(settings, "LLM_TIMEOUT", 30.0)),
            max_retries=int(getattr(settings, "MAX_RETRIES", 2)),
            supports_tools=True,
            supports_structured_output=True,
        )

        # 2. Fallback Model
        fallback_provider = getattr(settings, "FALLBACK_LLM_PROVIDER", "openrouter").lower()
        fallback_model = getattr(settings, "FALLBACK_LLM_MODEL", getattr(settings, "OPENROUTER_MODEL", "openai/gpt-4o-mini"))
        fallback_key = getattr(settings, "FALLBACK_LLM_API_KEY", "") or getattr(settings, "OPENROUTER_API_KEY", "") or getattr(settings, "AZURE_OPENAI_API_KEY", "") or getattr(settings, "OPENAI_API_KEY", "")
        if "azure" in fallback_provider:
            fallback_base_url = getattr(settings, "AZURE_OPENAI_ENDPOINT", None)
        elif fallback_provider == "openrouter":
            fallback_base_url = getattr(settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        else:
            fallback_base_url = None

        self._models["fallback"] = ModelConfig(
            name="fallback",
            provider=fallback_provider,
            model=fallback_model,
            api_key=fallback_key,
            base_url=fallback_base_url,
            timeout=float(getattr(settings, "LLM_TIMEOUT", 30.0)),
            max_retries=int(getattr(settings, "MAX_RETRIES", 2)),
            supports_tools=True,
            supports_structured_output=True,
        )

        # 3. Secondary Fallback Model (e.g. OpenRouter or alternative)
        sec_provider = getattr(settings, "FALLBACK_SECONDARY_PROVIDER", "openrouter").lower()
        sec_model = getattr(settings, "FALLBACK_SECONDARY_MODEL", "openai/gpt-4o-mini")
        sec_key = getattr(settings, "FALLBACK_SECONDARY_API_KEY", "") or getattr(settings, "OPENROUTER_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")

        self._models["secondary"] = ModelConfig(
            name="secondary",
            provider=sec_provider,
            model=sec_model,
            api_key=sec_key,
            base_url=getattr(settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1") if sec_provider == "openrouter" else None,
            timeout=float(getattr(settings, "LLM_TIMEOUT", 30.0)),
            max_retries=int(getattr(settings, "MAX_RETRIES", 2)),
            supports_tools=True,
            supports_structured_output=True,
        )

        # 4. Mock / Offline Model (Always available for tests & offline fallback)
        self._models["mock"] = ModelConfig(
            name="mock",
            provider="mock",
            model="clubops-mock-v1",
            api_key="mock-key-valid",
            timeout=5.0,
            max_retries=0,
            supports_tools=True,
            supports_structured_output=True,
        )

    def register(self, config: ModelConfig) -> None:
        """Dynamically registers or overrides a model configuration."""
        self._models[config.name] = config

    def get(self, name: str) -> Optional[ModelConfig]:
        """Retrieves model configuration by name."""
        return self._models.get(name)

    def list_models(self) -> Dict[str, ModelConfig]:
        """Lists all registered model configurations."""
        return dict(self._models)


# Global registry instance
model_registry = ModelRegistry()
