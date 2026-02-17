# Developer Guide

## Code Comment Guidelines
- Comment non-obvious logic, formulas, and domain assumptions.
- Explain both what and why for complex logic.
- Keep comments concise and close to code.

## Data Schema
- See data/raw/ and data/processed/ for CSVs.
- Telemetry: event_id, drone_id, timestamp_iso, lat, lon, altitude_ft, etc.
- Weather: timestamp_iso, wind_mps, gust_mps, wind_direction_deg, visibility_km.
- Processed: derived features for risk and prediction.

## Source Code Map
| File | Purpose |
|---|---|
| src/altitude_warning/models.py | Data models for telemetry, risk, alerts |
| src/altitude_warning/config.py | Thresholds and constants |
| src/altitude_warning/tools.py | Domain tools (ceiling, risk, policy) |
| src/altitude_warning/orchestrator.py | Orchestration logic |
| src/altitude_warning/simulator.py | Telemetry scenario generator |
| src/altitude_warning/cli.py | CLI runner |
| src/altitude_warning/api.py | FastAPI interface |
| src/altitude_warning/data/contract.py | Dataset schema contracts |
| src/altitude_warning/data/pipeline.py | Data pipeline |

## Developer Setup
- See CONTRIBUTING.md for environment and install steps.

---
For more, see docs/DEMO_GUIDE.md and docs/RUNBOOK.md.
