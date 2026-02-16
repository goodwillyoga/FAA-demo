from __future__ import annotations

import pytest

from altitude_warning.policy.weaviate_client import DEFAULT_COLLECTION, ensure_policy_collection, get_client


def _client_or_skip():
    try:
        client = get_client()
    except Exception as exc:  # pragma: no cover - depends on local setup
        pytest.skip(f"Weaviate client unavailable: {exc}")
    if not client.is_ready():
        client.close()
        pytest.skip("Weaviate is not running on localhost.")
    return client


def test_weaviate_ready() -> None:
    client = _client_or_skip()
    try:
        assert client.is_ready()
    finally:
        client.close()


def test_policy_collection_setup() -> None:
    client = _client_or_skip()
    try:
        ensure_policy_collection(client, name=DEFAULT_COLLECTION, vector_dim=3)
        assert client.collections.exists(DEFAULT_COLLECTION)
        collection = client.collections.get(DEFAULT_COLLECTION)
        total_count = collection.aggregate.over_all(total_count=True).total_count
        print(f"PolicyChunks count: {total_count}")
        if total_count:
            sample = collection.query.fetch_objects(limit=3)
            for idx, obj in enumerate(sample.objects, start=1):
                text = (obj.properties.get("text") or "").strip()
                preview = " ".join(text.split())[:200]
                print(f"Sample {idx}: {preview}")
    finally:
        client.close()
