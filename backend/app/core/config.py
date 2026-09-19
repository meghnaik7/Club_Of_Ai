import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables early so os.environ is populated for all AI/agent runtimes
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")

class Settings(BaseSettings):
    PROJECT_NAME: str = "ClubOps AI"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Postgres Database Configuration
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "your_password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "clubops_ai"
    
    # Secret Key & Tokens
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Volunteer Load Thresholds
    VOLUNTEER_LOAD_LOW: int = 3
    VOLUNTEER_LOAD_MEDIUM: int = 6
    
    # Upload Storage for Documents
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    
    # LLM & Embedding Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openrouter")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")

    # OpenRouter Settings
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    
    # Azure OpenAI Settings
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "https://earlycustomers-resource.services.ai.azure.com")
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.4-mini")

    # Centralized Primary and Fallback LLM Registry Settings
    PRIMARY_LLM_PROVIDER: str = os.getenv("PRIMARY_LLM_PROVIDER", os.getenv("LLM_PROVIDER", "openrouter"))
    PRIMARY_LLM_MODEL: str = os.getenv("PRIMARY_LLM_MODEL", os.getenv("LLM_MODEL", "openai/gpt-4o-mini"))
    PRIMARY_LLM_API_KEY: str = os.getenv("PRIMARY_LLM_API_KEY", os.getenv("OPENROUTER_API_KEY", os.getenv("AZURE_OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))))
    
    FALLBACK_LLM_PROVIDER: str = os.getenv("FALLBACK_LLM_PROVIDER", "openrouter")
    FALLBACK_LLM_MODEL: str = os.getenv("FALLBACK_LLM_MODEL", os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"))
    FALLBACK_LLM_API_KEY: str = os.getenv("FALLBACK_LLM_API_KEY", os.getenv("OPENROUTER_API_KEY", os.getenv("AZURE_OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))))
    
    FALLBACK_SECONDARY_PROVIDER: str = os.getenv("FALLBACK_SECONDARY_PROVIDER", "openrouter")
    FALLBACK_SECONDARY_MODEL: str = os.getenv("FALLBACK_SECONDARY_MODEL", "openai/gpt-4o-mini")
    FALLBACK_SECONDARY_API_KEY: str = os.getenv("FALLBACK_SECONDARY_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
    
    # Timeout Settings (Seconds)
    LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "30.0"))
    TOOL_TIMEOUT: float = float(os.getenv("TOOL_TIMEOUT", "10.0"))
    DATABASE_TIMEOUT: float = float(os.getenv("DATABASE_TIMEOUT", "10.0"))
    RAG_TIMEOUT: float = float(os.getenv("RAG_TIMEOUT", "10.0"))
    TOTAL_AGENT_TIMEOUT: float = float(os.getenv("TOTAL_AGENT_TIMEOUT", "60.0"))
    
    # Agent Guardrail & Loop Limits
    MAX_AGENT_ITERATIONS: int = int(os.getenv("MAX_AGENT_ITERATIONS", "10"))
    MAX_TOOL_CALLS: int = int(os.getenv("MAX_TOOL_CALLS", "15"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "2"))
    
    # LangSmith / Observability Settings
    LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "true")
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "ClubOps-AI")
    LANGCHAIN_ENDPOINT: str = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    LANGSMITH_TRACING: str = os.getenv("LANGSMITH_TRACING", "true")
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "ClubOps-AI")
    LANGSMITH_ENDPOINT: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    
    # RAG Parameters
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    RAG_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.55

    # LangSmith / Observability Settings
    LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "true")
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "ClubOps-AI")
    LANGCHAIN_ENDPOINT: str = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    LANGSMITH_TRACING: str = os.getenv("LANGSMITH_TRACING", "true")
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "ClubOps-AI")
    LANGSMITH_ENDPOINT: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

    DATABASE_URL: str = ""
    
    # LangGraph PostgreSQL Checkpointer Cloud Settings
    CHECKPOINTER_ENABLED: bool = True
    CHECKPOINTER_DATABASE_URL: str = ""
    CHECKPOINTER_POOL_MIN_SIZE: int = 1
    CHECKPOINTER_POOL_MAX_SIZE: int = 20
    CHECKPOINTER_POOL_TIMEOUT: float = 10.0

    def model_post_init(self, __context: object) -> None:
        env_url = os.getenv("DATABASE_URL") or self.DATABASE_URL
        if env_url and "${" not in env_url:
            self.DATABASE_URL = env_url
        else:
            # Build postgresql connection string from components
            user = self.POSTGRES_USER or "postgres"
            pwd = self.POSTGRES_PASSWORD or "your_password"
            host = self.POSTGRES_HOST or "localhost"
            port = self.POSTGRES_PORT or "5432"
            db_name = self.POSTGRES_DB or "clubops_ai"
            self.DATABASE_URL = f"postgresql://{user}:{pwd}@{host}:{port}/{db_name}"
        # Checkpointer URL defaults to DATABASE_URL if not explicitly overridden
        cp_url = os.getenv("CHECKPOINTER_DATABASE_URL") or self.CHECKPOINTER_DATABASE_URL
        if cp_url and "${" not in cp_url:
            self.CHECKPOINTER_DATABASE_URL = cp_url
        else:
            self.CHECKPOINTER_DATABASE_URL = self.DATABASE_URL
        # Ensure LangSmith / LangChain tracing environment variables are populated in os.environ
        api_key = self.LANGCHAIN_API_KEY or self.LANGSMITH_API_KEY or os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
        if api_key:
            project_name = self.LANGCHAIN_PROJECT or self.LANGSMITH_PROJECT or "ClubOps-AI"
            endpoint = self.LANGCHAIN_ENDPOINT or self.LANGSMITH_ENDPOINT or "https://api.smith.langchain.com"
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = api_key
            os.environ["LANGCHAIN_PROJECT"] = project_name
            os.environ["LANGCHAIN_ENDPOINT"] = endpoint
            os.environ["LANGSMITH_TRACING"] = "true"
            os.environ["LANGSMITH_API_KEY"] = api_key
            os.environ["LANGSMITH_PROJECT"] = project_name
            os.environ["LANGSMITH_ENDPOINT"] = endpoint
    
    model_config = SettingsConfigDict(
        env_file=[str(BASE_DIR / ".env"), str(BASE_DIR.parent / ".env")],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
