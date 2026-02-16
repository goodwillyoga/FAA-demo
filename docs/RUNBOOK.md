# Runbook

This runbook tracks the end-to-end steps for the local demo workflow.

## 1) Build Data Artifacts (Raw -> Processed -> Features)
Generate deterministic datasets for two drones:
```
python -m altitude_warning.data.pipeline --base-dir data
```
Expected outputs:
- data/raw/telemetry.csv
- data/raw/weather.csv
- data/processed/telemetry_processed.csv
- data/processed/ceiling_risk_features.csv

## 2) Start Weaviate (Docker)
Start the local Weaviate container:
```
bash scripts/run_weaviate.sh
```
Verify:
- http://localhost:8080

## 3) Ingest FAA Policy Study Guide
Set your key and ingest the Part 107 study guide:
```
export OPENAI_API_KEY=your_key
```
Or use the helper script (sets the key for the current shell):
```
source scripts/set_openai_key.sh
```
Then ingest:
```
bash scripts/ingest_policy.sh
```

### Enable Verbose Logging (Optional)
To capture retriever/LLM rerank logs, export the logging level before running tests:
```
source scripts/enable_logging.sh
```
Then run the desired pytest or CLI command in the same shell.

## 4) Run Setup Tests (Optional)
```
pytest tests/test_weaviate_setup.py tests/test_policy_ingest.py
```
Notes:
- Use `-s` if you want to see printed chunk counts and previews.
- Verified locally on 2026-02-15.

## 5) EDA Notebook (Optional)
Open the notebook and run all cells:
- notebooks/01_data_eda.ipynb

## 6) Orchestrator Baseline (gpt-4o)
Run the baseline scenario and write results to `outputs/baseline_results.json`:
```
source scripts/set_openai_key.sh
python scripts/run_orchestrator_baseline.py
```
Notes:
- Ensure Weaviate is running and the policy guide is ingested if policy retrieval is enabled.

## 7) Next Steps (Keep Updated)
- Wire the minimal dashboard
- Update this runbook as new steps are added
