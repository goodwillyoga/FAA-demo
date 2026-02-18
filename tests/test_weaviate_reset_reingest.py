from __future__ import annotations

import os
from pathlib import Path

import pytest

from altitude_warning.policy.ingest import ingest_policy_pdf
from altitude_warning.policy.weaviate_client import DEFAULT_COLLECTION, get_client


pytestmark = pytest.mark.integration


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        # Keep test optional if python-dotenv is not installed.
        pass


def _client_or_skip():
    try:
        client = get_client()
    except Exception as exc:  # pragma: no cover - depends on local setup
        pytest.skip(f"Weaviate client unavailable: {exc}")
    if not client.is_ready():
        client.close()
        pytest.skip("Weaviate is not running on localhost.")
    return client


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def test_reset_and_recreate_policy_collection_with_ingest() -> None:
    if not _is_truthy(os.getenv("ALLOW_WEAVIATE_RESET_TEST")):
        pytest.skip(
            "Set ALLOW_WEAVIATE_RESET_TEST=1 to run destructive reset/re-ingest test."
        )

    _load_dotenv_if_available()
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    pdf_path = Path("docs/faa_guides/remote_pilot_study_guide.pdf")
    assert pdf_path.exists(), f"Missing policy PDF: {pdf_path}"

    client = _client_or_skip()
    try:
        if client.collections.exists(DEFAULT_COLLECTION):
            client.collections.delete(DEFAULT_COLLECTION)

        ingested_count = ingest_policy_pdf(
            pdf_path,
            collection_name=DEFAULT_COLLECTION,
            client=client,
        )
        assert ingested_count > 0, "No chunks were ingested after reset."

        assert client.collections.exists(DEFAULT_COLLECTION)
        collection = client.collections.get(DEFAULT_COLLECTION)
        total_count = collection.aggregate.over_all(total_count=True).total_count or 0
        assert total_count == ingested_count
    finally:
        client.close()
