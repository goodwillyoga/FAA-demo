#!/usr/bin/env bash
set -e
export HISTTIMEFORMAT="%Y-%m-%d %H:%M:%S "
cd "/Users/poojasingh/Documents/2026 AI/2026-FAA"
source .venv/bin/activate
#pip install -r requirements.txt
source scripts/set_openai_key.sh
source scripts/enable_logging.sh
