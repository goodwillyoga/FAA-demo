#!/usr/bin/env bash
set -euo pipefail

container_name="weaviate-demo"

# Starts Weaviate locally via Docker. Key settings:
# - HTTP API: localhost:8080
# - gRPC: localhost:50051
# - Anonymous access enabled for local demo use
# - Default maximum number of results returned per query: 25
# - No built-in vectorizer (we provide embeddings explicitly)

if docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
  docker start "${container_name}" >/dev/null
else
  docker run -d --name "${container_name}" \
    -p 8080:8080 \
    -p 50051:50051 \
    -e QUERY_DEFAULTS_LIMIT=25 \
    -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
    -e DEFAULT_VECTORIZER_MODULE=none \
    -e CLUSTER_HOSTNAME=node1 \
    semitechnologies/weaviate:latest
fi

echo "Weaviate running at http://localhost:8080"
