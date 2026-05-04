"""AEGIS Application Configuration."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the .env file from the repo root (two levels above this file: backend/aegis/ → backend/ → repo root)
_ENV_FILE = Path(__file__).parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://aegis:aegis@localhost/aegis"

    # Redis / Celery
    REDIS_URL: str = "redis://:redis@localhost:6379/0"

    # MilvusDB
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530

    # Ollama LLM (used when OPENAI_API_BASE is not set)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "codellama:34b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # OpenAI-compatible LLM endpoint (overrides Ollama when set)
    OPENAI_API_BASE: str = ""
    OPENAI_API_KEY: str = "ollama"
    OPENAI_MODEL: str = ""

    # Embedding provider: ollama | openai | huggingface
    EMBEDDING_PROVIDER: str = "ollama"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    HUGGINGFACE_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # JWT Auth
    SECRET_KEY: str = "changeme-secret-key-at-least-32-chars-long!!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Reports directory
    REPORTS_DIR: str = "/tmp/aegis_reports"


settings = Settings()
