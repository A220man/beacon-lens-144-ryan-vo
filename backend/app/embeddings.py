
"""Embedding service for generating vector representations."""
import os
from functools import lru_cache
from typing import List
import httpx
import structlog

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using a local or remote model."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        api_url: str | None = None,
        dimensions: int = 384,
    ):
        self.model_name = model_name
        self.dimensions = dimensions
        self.api_url = api_url or os.getenv(
            "EMBEDDING_API_URL", "http://localhost:8001/embed"
        )
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (list of floats)
        """
        if not texts:
            return []

        try:
            response = await self.client.post(
                self.api_url,
                json={"texts": texts, "model": self.model_name},
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings", [])

            # Validate dimensions
            for emb in embeddings:
                if len(emb) != self.dimensions:
                    logger.warning(
                        "embedding_dimension_mismatch",
                        expected=self.dimensions,
                        got=len(emb),
                    )

            return embeddings
        except Exception as e:
            logger.error("embedding_failed", error=str(e))
            # Return zero vectors as fallback
            return [[0.0] * self.dimensions for _ in texts]

    async def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embeddings = await self.embed([text])
        return embeddings[0] if embeddings else []

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Get singleton embedding service instance."""
    return EmbeddingService()
