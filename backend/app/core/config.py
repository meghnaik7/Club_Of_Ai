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
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    
    # RAG Parameters
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    RAG_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.55

    @property
    def DATABASE_URL(self) -> str:
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            return env_url
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
