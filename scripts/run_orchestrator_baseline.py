from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from altitude_warning.orchestrator import Orchestrator
from altitude_warning.simulator import default_scenario_path, load_scenario_events


def main() -> None:
    scenario_path = default_scenario_path()
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario not found: {scenario_path}")

    events = load_scenario_events(scenario_path)
    orchestrator = Orchestrator(model_name="gpt-4o")

    results = []
    for event in events:
        decision, assessment, policy_context, latency_ms = orchestrator.process_event(event)
        results.append(
            {
                "event": asdict(event),
                "decision": asdict(decision),
                "assessment": asdict(assessment),
                "policy_context": policy_context,
                "latency_ms": round(latency_ms, 2),
            }
        )

    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "baseline_results.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
