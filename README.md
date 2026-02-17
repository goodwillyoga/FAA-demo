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

## 🚀 FAA Demo: Start Here
**For a complete walkthrough of the system, 5 test scenarios, tool specifications, and routing rules, see:**
→ **[docs/FAA_DEMO_GUIDE.md](docs/FAA_DEMO_GUIDE.md)**

This guide includes:
- System architecture diagram and data flow
- **Tool suite** with deterministic risk calculations (ceiling, trajectory, risk scoring, visibility)
- **5 FAA-guided test scenarios** (HIGH/MEDIUM/LOW risk with test results)
- **Policy integration** via Weaviate RAG and 14 CFR Part 107 citations
- **HITL approval flow** and decision traces
- Quick start: run all scenarios with `pytest tests/test_orchestrator_scenario_sweep.py -v`

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
- Metadata stored per chunk: `source`, `page`, `chunk_index`, `section_title`, `structure`
	- `section_title` captures the detected heading inside the chunk so UI/reporting can show where guidance came from (we do **not** filter on it today).
	- `structure` is a lightweight tag inferred from the text (`body`, `toc`, `appendix`, `reference`) so downstream retrieval can down-rank obviously non-operational sections without hardcoding specific pages.

### Retrieval Heuristic
- `retrieve_policy_context()` still performs semantic search via Weaviate, then re-ranks the candidate snippets by two signals: (1) altitude-specific keyword hits, (2) `structure` weight (body chunks preferred; TOC/appendix/reference are penalized but still eligible if they contain the best match).
- This keeps the flow agentic—LLM still sees whatever tops the list—but reduces noisy citations from tables of contents or glossary-only chunks.
- Optional LLM re-ranker: set `POLICY_LLM_RERANK=1` (and optionally `POLICY_RERANK_MODEL=gpt-4o-mini`) in `.env` to send the top ~6 snippets plus the telemetry-aware query to a lightweight LLM judge that scores each chunk (0–3) before final ordering. Leave it at `0` to avoid extra API calls.
- When the reranker is enabled, detailed scores get logged to `logs/policy_rerank.log` (auto-created) so you can inspect which chunks were boosted or penalized.

### Tests
Run Weaviate setup and ingestion tests (skips if Weaviate is not running):
```
pytest tests/test_weaviate_setup.py tests/test_policy_ingest.py
```
