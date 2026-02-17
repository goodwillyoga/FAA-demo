#!/usr/bin/env bash
set -euo pipefail

# Source this file to set your OpenAI API key for the current shell:
#   source scripts/set_openai_key.sh
# If a .env file exists, it will be loaded first.

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  read -r -p "Enter OPENAI_API_KEY: " OPENAI_API_KEY
  export OPENAI_API_KEY
fi

echo "OPENAI_API_KEY is set for this shell session."
