from __future__ import annotations

import os

import pytest

from altitude_warning.policy.retriever import retrieve_policy_context
from altitude_warning.policy.weaviate_client import DEFAULT_COLLECTION, get_client


pytestmark = pytest.mark.integration


def _client_or_skip():
    try:
        client = get_client()
    except Exception as exc:  # pragma: no cover - depends on local setup
        pytest.skip(f"Weaviate client unavailable: {exc}")
    if not client.is_ready():
        client.close()
        pytest.skip("Weaviate is not running on localhost.")
    return client


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        # Keep test optional if python-dotenv is not installed.
        pass


def test_policy_collection_vector_search_returns_chunks() -> None:
    client = _client_or_skip()
    try:
        assert client.collections.exists(DEFAULT_COLLECTION), (
            f"Collection '{DEFAULT_COLLECTION}' does not exist."
        )
        collection = client.collections.get(DEFAULT_COLLECTION)

        total_count = collection.aggregate.over_all(total_count=True).total_count or 0
        assert total_count > 0, f"Collection '{DEFAULT_COLLECTION}' is empty."

        sample = collection.query.fetch_objects(limit=1, include_vector=True)
        assert sample.objects, f"No objects found in '{DEFAULT_COLLECTION}'."

        sample_obj = sample.objects[0]
        vector_map = getattr(sample_obj, "vector", None) or {}
        sample_vector = vector_map.get("default")
        assert sample_vector, "Sample object does not have a usable vector."

        # Query by a known in-collection vector should return at least itself.
        results = collection.query.near_vector(
            near_vector=sample_vector,
            limit=3,
            return_properties=["text", "source", "page"],
            return_metadata=["distance"],
        )
        assert len(results.objects) > 0, "Vector search returned 0 chunks."
    finally:
        client.close()


def test_retriever_returns_policy_snippets() -> None:
    _load_dotenv_if_available()
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    client = _client_or_skip()
    client.close()

    query = (
        "FAA Part 107 guidance for altitude limits and operational safety. "
        "Telemetry altitude_ft=280.0, vertical_speed_fps=3.5, "
        "predicted_altitude_ft=308.0, ceiling_ft=300.0."
    )
    snippets = retrieve_policy_context(query, top_k=3)

    assert len(snippets) > 0, "retrieve_policy_context() returned 0 snippets."
    first = snippets[0]
    assert first.text.strip() != ""
    assert first.source.strip() != ""
    assert first.page >= 1
