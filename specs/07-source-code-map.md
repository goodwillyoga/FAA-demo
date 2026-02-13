# 07 Source Code Map

Purpose: quick orientation for public contributors on what each source file does.

| File | Purpose |
|---|---|
| `src/altitude_warning/__init__.py` | Package marker and top-level package description. |
| `src/altitude_warning/models.py` | Typed data models for telemetry input, risk assessment output, and alert decisions. |
| `src/altitude_warning/config.py` | Central thresholds and runtime constants used by scoring and routing logic. |
| `src/altitude_warning/tools.py` | Domain tools for ceiling lookup, trajectory projection, risk scoring, and policy routing. |
| `src/altitude_warning/orchestrator.py` | Orchestration entry point that chains tools and returns decision + assessment + latency. |
| `src/altitude_warning/simulator.py` | Deterministic telemetry scenario generator used for repeatable local runs. |
| `src/altitude_warning/cli.py` | Command-line runner that executes the pipeline and prints structured JSON outputs. |
| `src/altitude_warning/api.py` | Optional FastAPI interface exposing health and simulation-injection endpoints. |

## Runtime Flow
1. `simulator.py` creates telemetry events.
2. `orchestrator.py` calls functions from `tools.py`.
3. `models.py` structures outputs.
4. `cli.py` or `api.py` publishes results for users.

## Data Notes for Contributors
These definitions keep data generation and model features consistent.

| Term | Definition | Example |
|---|---|---|
| `source_quality_flags` | Telemetry reliability indicators attached to each message to track signal/data trust. | `gps_fix_ok` (0/1), `signal_strength` (0-100), `message_delay_ms`, `is_interpolated` (0/1) |
| `altitude_margin_to_ceiling_ft` | Distance from current altitude to legal/allowed ceiling. Positive = below ceiling; negative = above ceiling. | `ceiling_ft - altitude_ft` |
| `weather_stress_factor` | Numeric weather burden score used in risk logic to quantify wind/gust pressure on safe operations. | `weather_stress = clamp(0.6*(wind_mps/wind_ref) + 0.4*(gust_mps/gust_ref), 0, 1)` |

## Initial Data Plan
- Sampling: `1 Hz` per device (aligned to FAA Remote ID timing requirement in design notes).
- Coverage: `2 drones`, `2 minutes` each, different start times.
- Layers:
  - `raw`: unjoined telemetry + weather messages
  - `processed`: cleaned/joined records with derived columns
  - `features`: model-ready table for near-term ceiling risk and time-to-threshold prediction
