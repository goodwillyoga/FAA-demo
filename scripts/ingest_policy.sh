#!/usr/bin/env bash
set -euo pipefail

# Ingest the Part 107 study guide into Weaviate.
# Uses OPENAI_API_KEY from the environment (or .env if sourced earlier).

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${repo_root}/src:${PYTHONPATH:-}"

if [[ -f "${repo_root}/.env" ]]; then
	set -a
	# shellcheck disable=SC1090
	source "${repo_root}/.env"
	set +a
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
	echo "OPENAI_API_KEY is not set. Run: source scripts/set_openai_key.sh" >&2
	exit 1
fi

python - <<'PY'
from pathlib import Path
from altitude_warning.policy.ingest import ingest_policy_pdf

count = ingest_policy_pdf(Path('docs/faa_guides/remote_pilot_study_guide.pdf'))
print(count)
PY
