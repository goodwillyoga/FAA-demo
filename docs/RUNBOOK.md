# Runbook

This runbook tracks the end-to-end steps for the FAA altitude early warning demo.

## 📋 For FAA Stakeholders & Demo Attendees
**Start here:** [FAA_DEMO_GUIDE.md](FAA_DEMO_GUIDE.md) — Complete system overview, tool specifications, test scenarios, and results.

---

## Setup (One-Time)

### Quick Start
Run this script to configure everything in one go:
```
source scripts/demo_faa_setup.sh
```

This sets up:
- Bash history formatting (HISTTIMEFORMAT fix)
- Project directory
- Python venv activation
- OpenAI API key
- Logging infrastructure

---

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
- Verified locally on 2026-02-16.

## 5) Run FAA Demo Scenarios (Main Event!)
Execute all 5 test scenarios with live LLM calls:
```
pytest tests/test_orchestrator_scenario_sweep.py -v
```

**Output:** Baseline CSV file in `outputs/scenario_sweep_baseline_YYYYMMDDTHHMMSSZ.csv` with decision routes, risk scores, policy chunks retrieved, and latencies for all 5 scenarios.

**Expected Results:** 5/5 PASSED
- Scenario 1 (HIGH - ceiling breach + wind): route=hitl_review | auto_notify ✅
- Scenario 2 (HIGH - narrow margin + poor visibility): route=hitl_review ✅
- Scenario 3 (HIGH - very close to ceiling + extreme wind): route=hitl_review | auto_notify ✅
- Scenario 4 (MEDIUM - steady climb, good conditions): route=monitor | auto_notify ✅
- Scenario 5 (LOW - stable flight): route=monitor ✅

### Run Single Scenario
```
pytest tests/test_orchestrator_scenario_sweep.py::test_scenario_sweep_with_live_llm[data/scenarios/feature1_highriskceilingbreach_gustywind.json-HIGH-expected_route_in0] -v -s
```

## 6) EDA Notebook (Optional)
Open the notebook and run all cells:
- notebooks/01_data_eda.ipynb

## 7) Orchestrator Baseline (gpt-4o)
Run the baseline scenario and write results to `outputs/baseline_results.json`:
```
source scripts/set_openai_key.sh
python scripts/run_orchestrator_baseline.py
```
Notes:
- Ensure Weaviate is running and the policy guide is ingested if policy retrieval is enabled.

---

## Troubleshooting

### "HISTTIMEFORMAT: unbound variable" error
Run: `source scripts/demo_faa_setup.sh` to fix shell configuration.

### Weaviate not responding
```
# Check if running
docker ps | grep weaviate

# Restart
bash scripts/run_weaviate.sh
```

### Policy ingestion failed
```
# Check OpenAI key
echo $OPENAI_API_KEY

# Re-ingest
bash scripts/ingest_policy.sh
```

---

## Next Steps
- Deploy operator dashboard (Streamlit)
- Async HITL with approval timeout
- Real weather/ceiling APIs (production)
