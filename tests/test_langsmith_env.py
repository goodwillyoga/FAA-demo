import os

import pytest
from dotenv import load_dotenv
from langsmith.client import Client


def test_langsmith_api_key_auth() -> None:
    load_dotenv()
    key = os.getenv("LANGCHAIN_API_KEY")
    if not key:
        pytest.skip("LANGCHAIN_API_KEY not set")

    client = Client()
    try:
        response = client.request_with_retries("GET", "/sessions", params={"limit": 1})
    except Exception as exc:  # pragma: no cover - network/env specific
        pytest.fail(f"LangSmith auth request failed: {exc}")

    assert response.status_code == 200
