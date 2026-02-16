import argparse
import json
import os
from pathlib import Path

from altitude_warning.orchestrator import Orchestrator
from altitude_warning.simulator import (
    default_scenario_path,
    generate_altitude_breach_events,
    load_scenario_events,
)


def _enable_tracing() -> None:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the altitude early warning CLI demo.")
    parser.add_argument(
        "--scenario",
        default=str(default_scenario_path()),
        help="Path to a scenario JSON file.",
    )
    parser.add_argument("--trace", action="store_true", help="Include trace details in output.")
    parser.add_argument("--model", default=None, help="Override the default LLM model name.")
    args = parser.parse_args()

    if args.trace:
        _enable_tracing()

    orchestrator = Orchestrator(trace_enabled=args.trace, model_name=args.model)
    scenario_path = Path(args.scenario)
    events = load_scenario_events(scenario_path) if scenario_path.exists() else generate_altitude_breach_events()

    for event in events:
        decision, assessment, latency_ms = orchestrator.process_event(event)
        payload = {
            "drone_id": decision.drone_id,
            "route": decision.route,
            "status": decision.status,
            "message": decision.message,
            "risk_band": decision.risk_band,
            "rationale": decision.rationale,
            "risk_score": round(decision.risk_score, 3),
            "confidence": round(decision.confidence, 3),
            "predicted_altitude_ft": round(assessment.predicted_altitude_ft, 1),
            "ceiling_ft": assessment.ceiling_ft,
            "latency_ms": round(latency_ms, 2),
        }
        if args.trace:
            payload["trace_id"] = decision.trace_id
            payload["trace"] = decision.trace
        print(json.dumps(payload))


if __name__ == "__main__":
    main()
