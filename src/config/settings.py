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

    # LLM settings - Three model categories
    # REASONING_MODEL: 主 Agent 推理、工具编排 (需要强推理能力)
    REASONING_MODEL: Optional[str] = None
    # GRADER_MODEL: 答案质量评分、Query 改写 (快速模型)
    GRADER_MODEL: Optional[str] = None
    # DATA_MODEL: 结构化输出 (KG/Event 提取)
    DATA_MODEL: Optional[str] = None

    # API Key settings
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # Backward compatibility aliases (deprecated)
    LLM_MODEL: Optional[str] = None
    GEMINI_MODEL: Optional[str] = None

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

        # Resolve GOOGLE_API_KEY: prefer GOOGLE_API_KEY, fallback to GEMINI_API_KEY
        if not self.GOOGLE_API_KEY:
            self.GOOGLE_API_KEY = self.GEMINI_API_KEY

        # Resolve REASONING_MODEL (main agent)
        if not self.REASONING_MODEL:
            # Fallback chain: LLM_MODEL -> GEMINI_MODEL -> default
            self.REASONING_MODEL = self.LLM_MODEL or self.GEMINI_MODEL or "gemini-2.5-flash"

        # Resolve GRADER_MODEL (fast model for grading/refinement)
        if not self.GRADER_MODEL:
            self.GRADER_MODEL = "gemini-2.5-flash"

        # Resolve DATA_MODEL (structured output for extraction)
        if not self.DATA_MODEL:
            self.DATA_MODEL = "gemini-2.5-flash"

        # Backward compatibility: LLM_MODEL points to REASONING_MODEL
        if not self.LLM_MODEL:
            self.LLM_MODEL = self.REASONING_MODEL

        return self


# Global settings instance
settings = Settings()
