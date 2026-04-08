from types import SimpleNamespace

import pytest

from electronics_rag_assistant_backend.indexing.openai_embedder import OpenAIEmbedder


class StubEmbeddingsClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.embeddings = self

    def create(self, *, model: str, input: list[str], dimensions: int) -> SimpleNamespace:
        self.calls.append(
            {
                "model": model,
                "input": input,
                "dimensions": dimensions,
            }
        )
        return SimpleNamespace(
            data=[
                SimpleNamespace(embedding=[float(index), float(index) + 0.5])
                for index, _ in enumerate(input, start=1)
            ]
        )


def test_openai_embedder_requires_api_key_without_injected_client() -> None:
    with pytest.raises(ValueError):
        OpenAIEmbedder(
            api_key="",
            model="text-embedding-3-small",
            dimensions=1536,
            batch_size=16,
        )


def test_openai_embedder_batches_requests_and_preserves_order() -> None:
    client = StubEmbeddingsClient()
    embedder = OpenAIEmbedder(
        api_key="",
        model="text-embedding-3-small",
        dimensions=1536,
        batch_size=2,
        client=client,
    )

    vectors = embedder.embed_texts(["one", "two", "three"])

    assert client.calls == [
        {
            "model": "text-embedding-3-small",
            "input": ["one", "two"],
            "dimensions": 1536,
        },
        {
            "model": "text-embedding-3-small",
            "input": ["three"],
            "dimensions": 1536,
        },
    ]
    assert vectors == [[1.0, 1.5], [2.0, 2.5], [1.0, 1.5]]
