from __future__ import annotations

import csv
import os
from pathlib import Path
from datetime import UTC, datetime

import pytest

from altitude_warning.orchestrator import Orchestrator
from altitude_warning.simulator import default_scenario_path, load_scenario_events


pytestmark = pytest.mark.integration


def _skip_if_no_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")


def test_orchestrator_with_real_model() -> None:
    _skip_if_no_key()
    scenario_path = default_scenario_path()
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario not found: {scenario_path}")

    events = load_scenario_events(scenario_path)
    orchestrator = Orchestrator(model_name=os.getenv("OPENAI_MODEL", "gpt-4o"))

    decision, assessment, policy_context, _latency_ms = orchestrator.process_event(events[0])
    policy_context_str = orchestrator._format_policy_context(policy_context)

    request_payload = {
        "altitude_ft": events[0].altitude_ft,
        "vertical_speed_fps": events[0].vertical_speed_fps,
        "lat": events[0].lat,
        "lon": events[0].lon,
        "policy_context": policy_context_str,
    }
    response_payload = {
        "route": decision.route,
        "risk_band": decision.risk_band,
        "risk_score": decision.risk_score,
        "confidence": decision.confidence,
        "rationale": decision.rationale,
        "predicted_altitude_ft": assessment.predicted_altitude_ft,
        "ceiling_ft": assessment.ceiling_ft,
    }

    print("LLM input:", request_payload)
    print("LLM output:", response_payload)

    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    csv_path = output_dir / f"baseline_llm_runs_with_weaviate_{stamp}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[*request_payload.keys(), *response_payload.keys()])
        writer.writeheader()
        writer.writerow({**request_payload, **response_payload})
    print(f"Saved baseline to: {csv_path}")

    assert policy_context is not None  # Should have [S1], [S2]... chunks
    assert len(policy_context) > 0, "Policy context should be retrieved with Weaviate"

    assert 0.0 <= decision.risk_score <= 1.0
    assert 0.0 <= decision.confidence <= 1.0
    assert decision.route in {"auto_notify", "hitl_review", "monitor"}
    assert decision.risk_band in {"LOW", "MED", "HIGH"}
    assert decision.rationale is not None
    assert decision.rationale.strip() != ""

    assert assessment.predicted_altitude_ft > 0
    assert assessment.ceiling_ft > 0

    if decision.route == "hitl_review":
        print(f"✓ HITL triggered: risk={decision.risk_score:.2f}, confidence={decision.confidence:.2f}")
