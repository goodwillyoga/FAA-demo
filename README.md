# Altitude Early Warning

[![CI](https://github.com/goodwillyoga/FAA-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/goodwillyoga/FAA-demo/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

Open-source reference implementation for low-altitude UAS risk awareness using simulated telemetry.

## Environment Setup
This project is local-first and uses a Python virtual environment in the repo root.

1. `python3 -m venv .venv`
2. `source .venv/bin/activate`
3. `python3 -m pip install --upgrade pip`
4. `python3 -m pip install -e '.[dev,api]'`

Alternative (requirements files):
1. `python3 -m pip install -r requirements-dev.txt`

## Where Things Are Defined
- `.[dev,api]` is defined in `pyproject.toml` under `[project.optional-dependencies]`.
- `make` targets are defined in `Makefile`.
- No Docker configuration is currently included (`Dockerfile` / `docker-compose.yml` are intentionally absent for now).
- `requirements.txt` and `requirements-dev.txt` are provided for contributors who prefer `pip -r`.

## Why These Commands Exist
The goal is to give contributors one consistent way to install, validate, and run the project.

| Command | Purpose |
|---|---|
| `python3 -m pip install -e '.[dev,api]'` | Installs the package in editable mode plus development tooling (`pytest`) and API runtime dependencies (`fastapi`, `uvicorn`). |
| `make test` | Runs automated tests to verify core logic before changes are merged. |
| `make run-cli` | Runs the command-line pipeline for quick functional validation and JSON output checks. |
| `make run-api` | Starts the local API server for endpoint-level validation and integration testing. |

No `.env` file is required at this stage; defaults are local and code-defined.

## Quick Start
1. `source .venv/bin/activate`
2. `python3 -m pip install -e '.[dev,api]'`
3. `make test`
4. `make run-cli`
5. `make run-api`

## Project Layout
- `src/altitude_warning/`: core package
- `data/`: raw/processed/scenario data
- `diagrams/`: architecture and state diagrams
- `specs/`: design notes, plans, and reference material
