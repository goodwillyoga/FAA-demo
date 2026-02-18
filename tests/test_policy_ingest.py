from __future__ import annotations

from uuid import uuid4

import pytest

from altitude_warning.policy.ingest import ingest_texts
from altitude_warning.policy.weaviate_client import get_client


def _client_or_skip():
    try:
        client = get_client()
    except Exception as exc:  # pragma: no cover - depends on local setup
        pytest.skip(f"Weaviate client unavailable: {exc}")
    if not client.is_ready():
        client.close()
        pytest.skip("Weaviate is not running on localhost.")
    return client


def _fake_embedder(texts: list[str]) -> list[list[float]]:
    return [[float(idx + 1), 0.0, 0.5] for idx, _ in enumerate(texts)]


def test_ingest_texts_into_weaviate() -> None:
    client = _client_or_skip()
    collection_name = f"PolicyChunksTest_{uuid4().hex[:8]}"
    try:
        texts = ["Section 107.51 altitude limits.", "Section 107.23 operational limits."]
        metadata = [
            {
                "source": "unit-test",
                "page": 1,
                "chunk_index": 0,
                "section_title": "Section 107.51",
                "structure": "body",
            },
            {
                "source": "unit-test",
                "page": 2,
                "chunk_index": 1,
                "section_title": "Section 107.23",
                "structure": "body",
            },
        ]
        count = ingest_texts(
            texts,
            metadata,
            collection_name=collection_name,
            client=client,
            embedder=_fake_embedder,
        )
        assert count == 2
        assert client.collections.exists(collection_name)
    finally:
        client.close()
