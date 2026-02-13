"""Optional FastAPI layer for Phase A reference.

Install extras first:
  pip install -e '.[api]'
"""

from altitude_warning.orchestrator import Orchestrator
from altitude_warning.simulator import generate_altitude_breach_events

try:
    from fastapi import FastAPI
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "FastAPI not installed. Run: pip install -e '.[api]'"
    ) from exc


app = FastAPI(title="Phase A Altitude Early Warning")
_orchestrator = Orchestrator()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sim/inject/altitude-breach")
def inject_altitude_breach() -> dict[str, list[dict[str, str | float]]]:
    out: list[dict[str, str | float]] = []
    for event in generate_altitude_breach_events():
        decision, assessment, latency_ms = _orchestrator.process_event(event)
        out.append(
            {
                "drone_id": decision.drone_id,
                "route": decision.route,
                "status": decision.status,
                "message": decision.message,
                "risk_score": round(decision.risk_score, 3),
                "confidence": round(decision.confidence, 3),
                "predicted_altitude_ft": round(assessment.predicted_altitude_ft, 1),
                "ceiling_ft": assessment.ceiling_ft,
                "latency_ms": round(latency_ms, 2),
            }
        )
    return {"events": out}
