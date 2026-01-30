"""Embedding generator using BGE-base-zh model."""

import logging
from typing import List

from ..config import Settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings using BGE-base-zh model via LlamaIndex."""

    def __init__(
        self,
        model_name: str = None,
        batch_size: int = None,
        device: str = None,
    ):
        """
        Initialize embedding generator.

        Args:
            model_name: HuggingFace model name (default: BAAI/bge-base-zh-v1.5)
            batch_size: Batch size for embedding generation
            device: Device to use ("auto", "cpu", "cuda", "mps")
        """
        settings = Settings()
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
        self.device = device or settings.DEVICE

        # Lazy load the model
        self._embed_model = None

    @property
    def embed_model(self):
        """Lazy load the embedding model."""
        if self._embed_model is None:
            self._embed_model = self._load_model()
        return self._embed_model

    def _load_model(self):
        """Load the embedding model."""
        try:
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        except ImportError:
            raise ImportError(
                "llama-index-embeddings-huggingface is required. "
                "Install with: pip install llama-index-embeddings-huggingface"
            )

        # Determine device
        device = self._get_device()

        logger.info(f"Loading embedding model: {self.model_name} on {device}")

        model = HuggingFaceEmbedding(
            model_name=self.model_name,
            device=device,
            embed_batch_size=self.batch_size,
        )

        logger.info(f"Model loaded successfully")
        return model

    def _get_device(self) -> str:
        """Determine the best device to use."""
        if self.device != "auto":
            return self.device

        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        except ImportError:
            return "cpu"

    def embed_texts(self, texts: List[str], show_progress: bool = True) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed
            show_progress: Whether to show progress bar

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        logger.info(f"Generating embeddings for {len(texts)} texts")

        # Use batch embedding
        embeddings = self.embed_model.get_text_embedding_batch(
            texts, show_progress=show_progress
        )

        return embeddings

    def embed_single(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector
        """
        return self.embed_model.get_text_embedding(text)

    @property
    def embedding_dim(self) -> int:
        """Get the embedding dimension."""
        settings = Settings()
        return settings.EMBEDDING_DIM
