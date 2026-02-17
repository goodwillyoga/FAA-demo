import os

import pytest
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def test_openai_api_key_auth() -> None:
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        pytest.skip("OPENAI_API_KEY not set")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = ChatOpenAI(model=model, temperature=0)
    try:
        response = client.invoke("Reply with 'pong'.")
    except Exception as exc:  # pragma: no cover - network/env specific
        pytest.fail(f"OpenAI request failed: {exc}")

    print("response recvd:", response.content)
    assert response is not None
