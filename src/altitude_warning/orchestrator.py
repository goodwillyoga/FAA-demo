from time import perf_counter

from altitude_warning.models import AlertDecision, RiskAssessment, TelemetryEvent
from altitude_warning.tools import ceiling_tool, policy_tool, risk_tool, trajectory_tool


class Orchestrator:
    """Phase A merged orchestrator+recommendation path for altitude warnings."""

    def process_event(self, event: TelemetryEvent) -> tuple[AlertDecision, RiskAssessment, float]:
        start = perf_counter()

        ceiling_ft = ceiling_tool(event.lat, event.lon)
        predicted_altitude_ft = trajectory_tool(event.altitude_ft, event.vertical_speed_fps)
        risk_score, confidence = risk_tool(predicted_altitude_ft, ceiling_ft, event.vertical_speed_fps)
        route, should_alert = policy_tool(risk_score, confidence)

        assessment = RiskAssessment(
            predicted_altitude_ft=predicted_altitude_ft,
            ceiling_ft=ceiling_ft,
            risk_score=risk_score,
            confidence=confidence,
            route=route,
            should_alert=should_alert,
        )

        if should_alert:
            eta_seconds = 8
            message = (
                f"Likely ceiling breach in {eta_seconds}s: projected {predicted_altitude_ft:.1f}ft "
                f"vs ceiling {ceiling_ft:.1f}ft"
            )
            status = "alerted"
        else:
            message = "No alert: drone remains within projected ceiling."
            status = "monitoring"

        decision = AlertDecision(
            drone_id=event.drone_id,
            status=status,
            message=message,
            route=route,
            risk_score=risk_score,
            confidence=confidence,
        )

        latency_ms = (perf_counter() - start) * 1000
        return decision, assessment, latency_ms
