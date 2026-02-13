import json

from altitude_warning.orchestrator import Orchestrator
from altitude_warning.simulator import generate_altitude_breach_events


def main() -> None:
    orchestrator = Orchestrator()
    for event in generate_altitude_breach_events():
        decision, assessment, latency_ms = orchestrator.process_event(event)
        print(
            json.dumps(
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
        )


if __name__ == "__main__":
    main()
