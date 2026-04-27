"""Embedding providers."""

from __future__ import annotations

from typing import Protocol


class Embedder(Protocol):
    """Embedding provider contract."""

    def embed_query(self, text: str) -> list[float]:
        """Embed one query string."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed many document strings."""


class OpenAIEmbedder:
    """OpenAI embeddings wrapper."""

    def __init__(self, *, api_key: str, model: str, dimensions: int) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for embeddings")

        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._dimensions = dimensions

    def embed_query(self, text: str) -> list[float]:
        """Embed one query string."""

        return self.embed_documents([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed many document strings."""

        response = self._client.embeddings.create(
            model=self._model,
            input=texts,
            dimensions=self._dimensions,
        )
        return [item.embedding for item in response.data]
