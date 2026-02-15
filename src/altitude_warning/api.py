"""Optional FastAPI layer for Phase A reference.

Install extras first:
    pip install -e '.[api]'
"""

import os
from pathlib import Path

from altitude_warning.orchestrator import Orchestrator
from altitude_warning.simulator import (
        default_scenario_path,
        generate_altitude_breach_events,
        load_scenario_events,
)

try:
    from fastapi import FastAPI
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "FastAPI not installed. Run: pip install -e '.[api]'"
    ) from exc


app = FastAPI(title="Phase A Altitude Early Warning")


def _enable_tracing() -> None:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sim/inject/altitude-breach")
def inject_altitude_breach(
    include_trace: bool = False,
    scenario_path: str | None = None,
    model: str | None = None,
) -> dict[str, list[dict[str, str | float | list[dict[str, str | float]] | None]]]:
    if include_trace:
        _enable_tracing()

    orchestrator = Orchestrator(trace_enabled=include_trace, model_name=model)
    path = Path(scenario_path) if scenario_path else default_scenario_path()
    events = load_scenario_events(path) if path.exists() else generate_altitude_breach_events()

    out: list[dict[str, str | float | list[dict[str, str | float]] | None]] = []
    for event in events:
        decision, assessment, latency_ms = orchestrator.process_event(event)
        payload: dict[str, str | float | list[dict[str, str | float]] | None] = {
            "drone_id": decision.drone_id,
            "route": decision.route,
            "status": decision.status,
            "message": decision.message,
            "rationale": decision.rationale,
            "risk_score": round(decision.risk_score, 3),
            "confidence": round(decision.confidence, 3),
            "predicted_altitude_ft": round(assessment.predicted_altitude_ft, 1),
            "ceiling_ft": assessment.ceiling_ft,
            "latency_ms": round(latency_ms, 2),
        }
        if include_trace:
            payload["trace_id"] = decision.trace_id
            payload["trace"] = decision.trace
        out.append(payload)
    return {"events": out}
