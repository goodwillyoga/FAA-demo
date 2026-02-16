# Altitude Early Warning

[![CI](https://github.com/goodwillyoga/FAA-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/goodwillyoga/FAA-demo/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

Autonomous low-altitude risk awareness for UAS operations, focused on early warning and human-governed response.

## Why This Project
Low-altitude airspace is becoming denser, and safety teams need earlier warning signals than manual monitoring can provide.
This project shows how an agentic orchestration layer can sit on top of existing data and model pipelines to produce actionable risk alerts with clear audit trails.

## What It Delivers
- Early warning of likely altitude-ceiling crossing before violation occurs.
- Stateful orchestration across risk tools and policy routing.
- Human-in-the-loop escalation path for high-risk or low-confidence decisions.
- Technical traceability for review, replay, and governance.

## System View
1. Telemetry and context data are ingested.
2. Tools project near-term trajectory and compute risk/confidence.
3. Orchestration logic routes to monitor, auto-notify, or human review.
4. Outputs are exposed via API/CLI and observable in diagrams and traces.

## Stakeholder Value
- Safety: earlier detection and faster response windows.
- Operations: consistent decision paths under load.
- Governance: transparent, inspectable decision chains.
- Evolution: architecture ready to integrate MCP/A2A-aligned services.

## Public Repository Structure
- `src/altitude_warning/`: application logic
- `data/`: raw, processed, and scenario datasets
- `diagrams/`: architecture and state visuals
- `docs/`: contributor and setup documentation
- `notebooks/`: exploratory analysis artifacts

## For Contributors
- Local setup and run instructions: `docs/PYTHON_SETUP.md`
- Data schema and assumptions: `docs/data_schema.md`
- Code comment conventions: `docs/CODE_COMMENT_GUIDELINES.md`
- FAA walkthrough narrative for simulation assumptions: `docs/simulation_setup.md`

## Weaviate Policy Index (Part 107 Study Guide)
This demo uses a single policy source for retrieval: `docs/faa_guides/remote_pilot_study_guide.pdf`.

### Docker Start
1) Start Weaviate locally:
```
bash scripts/run_weaviate.sh
```
2) Confirm it responds at `http://localhost:8080`.

### Ingest Policy PDF
Set your OpenAI key, then run ingestion:
```
export OPENAI_API_KEY=your_key
python -c "from pathlib import Path; from altitude_warning.policy.ingest import ingest_policy_pdf; print(ingest_policy_pdf(Path('docs/faa_guides/remote_pilot_study_guide.pdf')))"
```

### Ingestion Parameters (High Level)
- Embeddings: `text-embedding-3-small` (1536 dims)
- Chunking: 350-word chunks with 80-word overlap
- Collection: `PolicyChunks`
- Metadata stored per chunk: `source`, `page`, `chunk_index`

### Tests
Run Weaviate setup and ingestion tests (skips if Weaviate is not running):
```
pytest tests/test_weaviate_setup.py tests/test_policy_ingest.py
```
