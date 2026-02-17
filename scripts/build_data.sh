#!/usr/bin/env bash
set -euo pipefail
# Rebuild generated datasets from scratch by overwriting target CSV outputs.
export PYTHONPATH="src:${PYTHONPATH:-}"
python3 -m altitude_warning.data_pipeline "$@"
