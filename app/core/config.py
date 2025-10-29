# Environment settings

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str

    # Weaviate
    WEAVIATE_URL: str = "http://weaviate:8080"

    # Ollama
    OLLAMA_URL: str = "http://host.docker.internal:11434"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()