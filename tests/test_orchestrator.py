from altitude_warning.models import TelemetryEvent
from altitude_warning.orchestrator import Orchestrator


def test_orchestrator_emits_alert_for_projected_breach() -> None:
    orch = Orchestrator()
    event = TelemetryEvent(
        drone_id="D-1",
        lat=37.62,
        lon=-122.35,
        altitude_ft=280.0,
        vertical_speed_fps=3.5,
        timestamp_iso="2026-02-13T00:00:00Z",
    )
    decision, assessment, _latency_ms = orch.process_event(event)
    assert decision.status == "alerted"
    assert assessment.predicted_altitude_ft > assessment.ceiling_ft
