from __future__ import annotations

import os
from dataclasses import dataclass

import weaviate
from weaviate.classes.config import Configure, DataType, Property


DEFAULT_COLLECTION = "PolicyChunks"


@dataclass(frozen=True, slots=True)
class WeaviateConfig:
    http_host: str = "localhost"
    http_port: int = 8080
    grpc_host: str = "localhost"
    grpc_port: int = 50051


def _load_config() -> WeaviateConfig:
    http_host = os.getenv("WEAVIATE_HTTP_HOST", "localhost")
    http_port = int(os.getenv("WEAVIATE_HTTP_PORT", "8080"))
    grpc_host = os.getenv("WEAVIATE_GRPC_HOST", http_host)
    grpc_port = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))
    return WeaviateConfig(
        http_host=http_host,
        http_port=http_port,
        grpc_host=grpc_host,
        grpc_port=grpc_port,
    )


def get_client() -> weaviate.WeaviateClient:
    cfg = _load_config()
    if (
        cfg.http_host == "localhost"
        and cfg.http_port == 8080
        and cfg.grpc_host == "localhost"
        and cfg.grpc_port == 50051
    ):
        return weaviate.connect_to_local()
    return weaviate.connect_to_custom(
        http_host=cfg.http_host,
        http_port=cfg.http_port,
        http_secure=False,
        grpc_host=cfg.grpc_host,
        grpc_port=cfg.grpc_port,
        grpc_secure=False,
    )


def ensure_policy_collection(
    client: weaviate.WeaviateClient,
    name: str = DEFAULT_COLLECTION,
    vector_dim: int = 1536,
) -> None:
    if client.collections.exists(name):
        return

    client.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.none(),
        vector_index_config=Configure.VectorIndex.hnsw(),
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="source", data_type=DataType.TEXT),
            Property(name="page", data_type=DataType.INT),
            Property(name="chunk_index", data_type=DataType.INT),
        ],
    )
