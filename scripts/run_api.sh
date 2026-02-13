#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="src:${PYTHONPATH:-}"
python3 -m uvicorn altitude_warning.api:app --reload --port 8000
