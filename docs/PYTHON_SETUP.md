# Python Setup

This page is for contributors who want to run or develop the code locally.

## Local Environment
1. `python3 -m venv .venv`
2. `source .venv/bin/activate`
3. `python3 -m pip install --upgrade pip`
4. `python3 -m pip install -e '.[dev,api]'`

Alternative installation path:
1. `python3 -m pip install -r requirements.txt`

## Why These Commands Exist
| Command | Purpose |
|---|---|
| `python3 -m pip install -e '.[dev,api]'` | Installs project package plus development tools (`pytest`) and API runtime dependencies (`fastapi`, `uvicorn`). |
| `make test` | Runs automated tests. |
| `make run-cli` | Runs command-line pipeline with structured JSON output. |
| `make run-api` | Starts local API server for endpoint validation. |
| `make build-data` | Generates deterministic `raw`, `processed`, and `feature` CSV datasets. |

## Where Definitions Live
- Optional dependency groups: `pyproject.toml`
- Task shortcuts: `Makefile`
- Runtime helper scripts: `scripts/`
- Alternative dependency list: `requirements.txt`
- Comment-writing conventions: `docs/CODE_COMMENT_GUIDELINES.md`

## Typical Contributor Flow
1. `source .venv/bin/activate`
2. `make test`
3. `make build-data`
4. `make run-cli`
5. `make run-api`
6. Open `notebooks/01_data_eda.ipynb` for descriptive analysis.

No `.env` file is required at this stage.
