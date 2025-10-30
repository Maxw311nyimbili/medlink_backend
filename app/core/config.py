# Environment settings
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-key.json"
    FIREBASE_KEY_BASE64: Optional[str] = None

    # Weaviate
    WEAVIATE_URL: str = "http://weaviate:8080"

    # Groq (changed from Ollama)
    GROQ_API_KEY: Optional[str] = None

    # CORS
    ALLOWED_ORIGINS: str = "*"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra env vars without error


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()