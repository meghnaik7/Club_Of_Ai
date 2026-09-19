import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

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
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    
    # Centralized Primary and Fallback LLM Registry Settings
    PRIMARY_LLM_PROVIDER: str = os.getenv("PRIMARY_LLM_PROVIDER", os.getenv("LLM_PROVIDER", "gemini"))
    PRIMARY_LLM_MODEL: str = os.getenv("PRIMARY_LLM_MODEL", os.getenv("LLM_MODEL", "gemini-1.5-flash"))
    PRIMARY_LLM_API_KEY: str = os.getenv("PRIMARY_LLM_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    
    FALLBACK_LLM_PROVIDER: str = os.getenv("FALLBACK_LLM_PROVIDER", "openai")
    FALLBACK_LLM_MODEL: str = os.getenv("FALLBACK_LLM_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    FALLBACK_LLM_API_KEY: str = os.getenv("FALLBACK_LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    
    FALLBACK_SECONDARY_PROVIDER: str = os.getenv("FALLBACK_SECONDARY_PROVIDER", "openrouter")
    FALLBACK_SECONDARY_MODEL: str = os.getenv("FALLBACK_SECONDARY_MODEL", "google/gemini-flash-1.5")
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
    
    # RAG Parameters
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    RAG_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.55

    DATABASE_URL: str = ""

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
    
    model_config = SettingsConfigDict(
        env_file=[str(BASE_DIR / ".env"), str(BASE_DIR.parent / ".env")],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
