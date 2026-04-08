"""OpenAI embedding wrapper used by the indexing pipeline."""

from __future__ import annotations

from typing import Any, Protocol

from openai import OpenAI


class Embedder(Protocol):
    """Interface implemented by embedding providers."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector for each input text."""


class OpenAIEmbedder:
    """Embedding provider backed by the OpenAI embeddings API."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        dimensions: int,
        batch_size: int,
        client: Any | None = None,
    ) -> None:
        if client is None and not api_key:
            raise ValueError("OPENAI_API_KEY is required for embedding generation")

        self._client = client or OpenAI(api_key=api_key)
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed input texts in stable batches while preserving order."""

        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            if not batch:
                continue
            response = self._client.embeddings.create(
                model=self._model,
                input=batch,
                dimensions=self._dimensions,
            )
            vectors.extend([item.embedding for item in response.data])
        return vectors
