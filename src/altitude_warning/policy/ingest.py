from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Callable, Iterable, Sequence

from langchain_openai import OpenAIEmbeddings
from pypdf import PdfReader
from weaviate.collections.classes.data import DataObject

from altitude_warning.policy.weaviate_client import DEFAULT_COLLECTION, ensure_policy_collection, get_client


@dataclass(frozen=True, slots=True)
class PolicyChunk:
    text: str
    source: str
    page: int
    chunk_index: int
    section_title: str | None = None
    structure: str = "body"


_SECTION_PATTERN = re.compile(r"^(chapter|appendix|section)\\b", re.IGNORECASE)


def _guess_section_title(text: str) -> str | None:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _SECTION_PATTERN.match(line):
            return line
        if line.isupper() and 4 <= len(line) <= 80:
            return line
    return None


def _detect_structure_label(text: str) -> str:
    lowered = text.lower()
    if "table of contents" in lowered:
        return "toc"
    leading = lowered[:200]
    if leading.startswith("appendix") or leading.startswith("appendices"):
        return "appendix"
    if " appendix" in leading:
        return "appendix"
    if "acr" in lowered and "definition" in lowered:
        return "reference"
    if "glossary" in lowered:
        return "reference"
    return "body"


def load_pdf_pages(path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(path))
    pages: list[tuple[int, str]] = []
    for idx, page in enumerate(reader.pages, start=1):
        pages.append((idx, page.extract_text() or ""))
    return pages


def chunk_text(text: str, chunk_size: int = 350, overlap: int = 80) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(0, end - overlap)
    return chunks


def build_chunks(pages: Iterable[tuple[int, str]], source: str) -> list[PolicyChunk]:
    chunks: list[PolicyChunk] = []
    chunk_index = 0
    for page_number, text in pages:
        for chunk in chunk_text(text):
            chunks.append(
                PolicyChunk(
                    text=chunk,
                    source=source,
                    page=page_number,
                    chunk_index=chunk_index,
                    section_title=_guess_section_title(chunk),
                    structure=_detect_structure_label(chunk),
                )
            )
            chunk_index += 1
    return chunks


def _embed_texts(
    embedder: OpenAIEmbeddings | Callable[[Sequence[str]], list[list[float]]],
    texts: Sequence[str],
) -> list[list[float]]:
    if hasattr(embedder, "embed_documents"):
        return embedder.embed_documents(list(texts))
    return embedder(list(texts))


def ingest_texts(
    texts: Sequence[str],
    metadata: Sequence[dict[str, object]],
    *,
    collection_name: str = DEFAULT_COLLECTION,
    client: object | None = None,
    embedder: OpenAIEmbeddings | Callable[[Sequence[str]], list[list[float]]] | None = None,
) -> int:
    if not texts:
        return 0
    close_client = False
    if client is None:
        client = get_client()
        close_client = True
    if embedder is None:
        embedder = OpenAIEmbeddings(model="text-embedding-3-small")
    try:
        vectors = _embed_texts(embedder, texts)
        ensure_policy_collection(client, name=collection_name, vector_dim=len(vectors[0]))
        collection = client.collections.get(collection_name)

        objects = [
            DataObject(
                properties={
                    "text": text,
                    **meta,
                },
                vector=vector,
            )
            for text, meta, vector in zip(texts, metadata, vectors, strict=True)
        ]

        collection.data.insert_many(objects=objects)
        return len(objects)
    finally:
        if close_client:
            client.close()


def ingest_policy_pdf(
    path: Path,
    *,
    collection_name: str = DEFAULT_COLLECTION,
    client: object | None = None,
    embedder: OpenAIEmbeddings | Callable[[Sequence[str]], list[list[float]]] | None = None,
) -> int:
    pages = load_pdf_pages(path)
    chunks = build_chunks(pages, source=str(path))
    texts = [chunk.text for chunk in chunks]
    metadata = [
        {
            "source": chunk.source,
            "page": chunk.page,
            "chunk_index": chunk.chunk_index,
            "section_title": chunk.section_title or "",
            "structure": chunk.structure,
        }
        for chunk in chunks
    ]
    return ingest_texts(
        texts,
        metadata,
        collection_name=collection_name,
        client=client,
        embedder=embedder,
    )
