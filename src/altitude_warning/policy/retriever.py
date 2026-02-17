from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from langchain_openai import ChatOpenAI, OpenAIEmbeddings


logger = logging.getLogger(__name__)


def _ensure_file_logging() -> None:
    if not logger.handlers:
        logs_dir = Path(__file__).resolve().parents[3] / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(logs_dir / "policy_rerank.log")
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

from altitude_warning.policy.weaviate_client import DEFAULT_COLLECTION, get_client


@dataclass(frozen=True, slots=True)
class PolicySnippet:
    text: str
    source: str
    page: int
    score: float | None
    section_title: str | None = None
    structure: str = "body"


_ALTITUDE_TERMS = (
    "part 107",
    "107.51",
    "altitude",
    "agl",
    "ceiling",
    "maximum altitude",
)


def _keyword_boost(text: str, terms: Sequence[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term in lowered)


def retrieve_policy_context(
    query: str,
    *,
    top_k: int = 3,
    collection_name: str = DEFAULT_COLLECTION,
    embedder: OpenAIEmbeddings | None = None,
) -> list[PolicySnippet]:
    if not query.strip():
        return []

    client = get_client()
    try:
        if not client.collections.exists(collection_name):
            return []

        if embedder is None:
            embedder = OpenAIEmbeddings(model="text-embedding-3-small")

        vector = embedder.embed_query(query)
        collection = client.collections.get(collection_name)
        candidate_k = max(top_k * 3, top_k)
        result = collection.query.near_vector(
            near_vector=vector,
            limit=candidate_k,
            return_properties=["text", "source", "page", "chunk_index", "section_title", "structure"],
            return_metadata=["distance"],
        )

        snippets: list[PolicySnippet] = []
        for obj in result.objects:
            props = obj.properties or {}
            snippets.append(
                PolicySnippet(
                    text=str(props.get("text", "")),
                    source=str(props.get("source", "")),
                    page=int(props.get("page", 0) or 0),
                    score=getattr(obj.metadata, "distance", None),
                    section_title=str(props.get("section_title") or "") or None,
                    structure=str(props.get("structure") or "body") or "body",
                )
            )
        snippets.sort(
            key=lambda item: (
                -_keyword_boost(item.text, _ALTITUDE_TERMS),
                0 if item.structure == "body" else 1,
                item.score if item.score is not None else 1.0,
            )
        )
        if _should_llm_rerank() and snippets:
            _ensure_file_logging()
            candidate_count = min(len(snippets), max(top_k * 2, 6))
            reranked = _llm_rerank_snippets(query, snippets[:candidate_count])
            # keep remaining snippets after reranked list to preserve coverage
            remainder = [s for s in snippets if s not in reranked]
            snippets = reranked + remainder
        return snippets[:top_k]
    finally:
        client.close()


def _should_llm_rerank() -> bool:
    flag = os.getenv("POLICY_LLM_RERANK", "0").lower()
    return flag not in {"0", "false", ""}


def _extract_json_payload(content: str) -> str:
    cleaned = content.strip()
    if not cleaned.startswith("```"):
        return cleaned
    cleaned = cleaned[3:]
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:]
    cleaned = cleaned.lstrip()
    block_end = cleaned.find("```")
    if block_end != -1:
        cleaned = cleaned[:block_end]
    return cleaned.strip()


def _llm_rerank_snippets(query: str, snippets: Sequence[PolicySnippet]) -> list[PolicySnippet]:
    model_name = os.getenv("POLICY_RERANK_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=model_name, temperature=0)
    logger.info(
        "policy_rerank.start",
        extra={
            "model": model_name,
            "candidate_count": len(snippets),
            "query": query[:200],
        },
    )
    snippet_payload = []
    for idx, snippet in enumerate(snippets, start=1):
        text_preview = " ".join(snippet.text.split())[:800]
        snippet_payload.append(
            {
                "id": idx,
                "section": snippet.section_title or "",
                "structure": snippet.structure,
                "text": text_preview,
            }
        )

    instructions = (
        "You are ranking FAA Part 107 policy snippets for how well they answer the pilot's query.\n"
        "Given the query and snippets, assign each snippet a relevance score from 0 to 3.\n"
        "3 = directly states the applicable regulation or numeric limit;\n"
        "2 = strongly implies relevant guidance;\n"
        "1 = tangential mention; 0 = irrelevant.\n"
        "Respond with EXACT JSON ONLY (no prose): {\"scores\": [{\"id\": <snippet_id>, \"score\": <0-3>, \"reason\": \"short note\"}]}."
    )

    prompt = (
        f"Query: {query}\n"
        f"Snippets:\n" +
        "\n".join(
            f"Snippet {item['id']} [structure={item['structure']} section={item['section']}]: {item['text']}"
            for item in snippet_payload
        )
    )
    message = f"{instructions}\n\n{prompt}"

    try:
        response = llm.invoke(message)
        content = response.content if hasattr(response, "content") else str(response)
        logger.debug("policy_rerank.raw content=%s", content)
        payload = _extract_json_payload(content)
        data = json.loads(payload)
        scores = {int(entry["id"]): float(entry["score"]) for entry in data.get("scores", [])}
    except Exception:
        logger.exception("policy_rerank.failed")
        return list(snippets)

    ranked = sorted(
        enumerate(snippets, start=1),
        key=lambda pair: (
            -scores.get(pair[0], -1.0),
            pair[0],
        ),
    )
    logger.info(
        "policy_rerank.scores",
        extra={
            "scores": scores,
            "top_structure": [snippet.structure for _, snippet in ranked[:3]],
        },
    )
    return [snippet for _, snippet in ranked]
