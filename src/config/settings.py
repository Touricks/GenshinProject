"""Configuration settings for the ingestion pipeline."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """Pipeline configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from .env
    )

    # Qdrant settings
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_URL: Optional[str] = None  # Alternative: full URL like http://localhost:6333
    COLLECTION_NAME: str = "genshin_story"

    # Embedding settings
    EMBEDDING_MODEL: str = "BAAI/bge-base-zh-v1.5"
    EMBEDDING_DIM: int = 768
    EMBEDDING_BATCH_SIZE: int = 64
    DEVICE: str = "auto"  # "auto", "cpu", "cuda", "mps"

    # Reranker settings
    RERANKER_MODEL: str = "jinaai/jina-reranker-v2-base-multilingual"
    RERANKER_TOP_K: int = 5

    # LLM settings (for Agent)
    # 支持两种命名方式: LLM_MODEL/GEMINI_MODEL, GOOGLE_API_KEY/GEMINI_API_KEY
    LLM_MODEL: Optional[str] = None
    GEMINI_MODEL: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # Grader/Refiner 使用轻量模型 (速度优先)
    GRADER_MODEL: Optional[str] = None

    # Chunking settings
    MAX_CHUNK_SIZE: int = 1500
    MIN_CHUNK_SIZE: int = 200
    CHUNK_OVERLAP: int = 100

    # Data paths
    DATA_DIR: Path = Path("Data")

    # Incremental indexing
    VECTOR_TRACKING_FILE: Path = Path(".cache/vector/tracking.json")

    @model_validator(mode="after")
    def resolve_settings(self):
        """Resolve settings with fallbacks and aliases."""
        # Parse QDRANT_URL into host and port if provided
        if self.QDRANT_URL:
            url = self.QDRANT_URL.replace("http://", "").replace("https://", "")
            if ":" in url:
                host, port = url.split(":")
                self.QDRANT_HOST = host
                self.QDRANT_PORT = int(port)
            else:
                self.QDRANT_HOST = url

        # Resolve LLM_MODEL: prefer LLM_MODEL, fallback to GEMINI_MODEL
        if not self.LLM_MODEL:
            self.LLM_MODEL = self.GEMINI_MODEL or "gemini-2.5-flash"

        # Resolve GOOGLE_API_KEY: prefer GOOGLE_API_KEY, fallback to GEMINI_API_KEY
        if not self.GOOGLE_API_KEY:
            self.GOOGLE_API_KEY = self.GEMINI_API_KEY

        # Resolve GRADER_MODEL: default to gemini-2.5-flash for speed
        if not self.GRADER_MODEL:
            self.GRADER_MODEL = "gemini-2.5-flash"

        return self


# Global settings instance
settings = Settings()
