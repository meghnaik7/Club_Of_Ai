from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ClubOps AI"
    
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "your_password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "clubops_ai"
    
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    VOLUNTEER_LOAD_LOW: int = 3
    VOLUNTEER_LOAD_MEDIUM: int = 6

    # AI / LLM settings
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    UPLOAD_DIR: str = "uploads/documents"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
