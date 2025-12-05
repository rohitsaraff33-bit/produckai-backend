"""Embedding service using sentence-transformers."""

import logging
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from apps.api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    """Service for generating text embeddings using sentence-transformers."""

    def __init__(self):
        """Initialize the embedding model."""
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        self.model = SentenceTransformer(settings.embedding_model)
        self.dimension = settings.embedding_dimension
        logger.info(f"Model loaded successfully. Dimension: {self.dimension}")

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            List of floats representing the embedding vector
        """
        # Preprocess text
        text = self._preprocess_text(text)

        # Generate embedding
        embedding = self.model.encode(text, normalize_embeddings=True)

        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        # Preprocess all texts
        processed_texts = [self._preprocess_text(text) for text in texts]

        # Generate embeddings in batch
        embeddings = self.model.encode(
            processed_texts,
            batch_size=settings.embedding_batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 100,
        )

        return embeddings.tolist()

    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score [-1, 1]
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Since embeddings are normalized, dot product = cosine similarity
        return float(np.dot(vec1, vec2))

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text before embedding.

        Args:
            text: Raw text

        Returns:
            Preprocessed text
        """
        # Basic preprocessing
        text = text.strip()

        # Truncate to reasonable length (models have max length)
        # Most sentence-transformers models support up to 512 tokens
        # which is roughly 2048 characters
        max_chars = 2048
        if len(text) > max_chars:
            text = text[:max_chars]

        return text


# Global instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
