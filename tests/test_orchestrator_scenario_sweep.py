"""Integration test: scenario sweeps with live LLM calls and calibrated assertions."""

from __future__ import annotations

import csv
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from altitude_warning.orchestrator import Orchestrator
from altitude_warning.simulator import load_scenario_events


pytestmark = pytest.mark.integration


def _skip_if_no_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")


@pytest.mark.parametrize(
    "scenario_file,expected_risk_category,expected_route_in",
    [
        (
            "data/scenarios/feature1_highriskceilingbreach_gustywind.json",
            "HIGH",
            {"hitl_review", "auto_notify"},  # Both acceptable for HIGH risk
        ),
        (
            "data/scenarios/feature1_highrisklow_ceiling_poorvisibility.json",
            "HIGH",
            {"hitl_review"},  # Poor visibility should force HITL
        ),
        (
            "data/scenarios/feature1_highriskrooftop_highwind.json",
            "HIGH",
            {"hitl_review", "auto_notify"},
        ),
        (
            "data/scenarios/feature1_mediumrisk_steady_climb.json",
            "MEDIUM",
            {"monitor", "auto_notify"},  # Medium can be monitor or auto
        ),
        (
            "data/scenarios/feature1_lowrisk_stable_flight.json",
            "LOW",
            {"monitor"},  # Low risk should monitor, not alert
        ),
    ],
)
def test_scenario_sweep_with_live_llm(
    scenario_file: str,
    expected_risk_category: str,
    expected_route_in: set[str],
) -> None:
    """Test orchestrator on 5 FAA-guided scenarios with real LLM."""
    _skip_if_no_key()

    scenario_path = Path(scenario_file)
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario not found: {scenario_path}")

    events = load_scenario_events(scenario_path)
    orchestrator = Orchestrator(
        enable_policy_retrieval=True,
        trace_enabled=True,
        model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )

    # Process first event from scenario
    event = events[0]
    decision, assessment, policy_context, latency_ms = orchestrator.process_event(event)

    # Assertions calibrated for live API calls (ranges, not exact values)
    print(f"\n{'='*70}")
    print(f"Scenario: {scenario_file}")
    print(f"Risk Category (Expected): {expected_risk_category}")
    print(f"Route: {decision.route} (expected in {expected_route_in})")
    print(f"Risk Score: {assessment.risk_score:.2f}, Confidence: {assessment.confidence:.2f}")
    print(f"Policy Context: {len(policy_context)} chunks retrieved")
    print(f"Latency: {latency_ms:.0f}ms")
    print(f"Decision: {decision.status} | Message: {decision.message}")
    if decision.route == "hitl_review":
        print(f"✓ HITL triggered for human review")
    print(f"{'='*70}\n")

    # Assertions
    assert 0.0 <= decision.risk_score <= 1.0, "Risk score out of range"
    assert 0.0 <= decision.confidence <= 1.0, "Confidence out of range"
    assert decision.route in expected_route_in, f"Route {decision.route} not in {expected_route_in}"
    assert decision.risk_band in {"LOW", "MED", "HIGH"}, "Invalid risk_band"
    assert decision.rationale is not None, "Rationale missing"
    assert decision.rationale.strip() != "", "Rationale empty"

    # Policy context assertions
    assert policy_context is not None, "Policy context should not be None"
    assert len(policy_context) > 0, "Policy context should be retrieved (Weaviate working)"

    # Risk assessment assertions
    assert assessment.predicted_altitude_ft > 0, "Predicted altitude invalid"
    assert assessment.ceiling_ft > 0, "Ceiling invalid"

    # Latency sanity check (should be <30 seconds for local + API calls)
    assert latency_ms < 30000, f"Latency {latency_ms}ms exceeds 30 seconds"

    # Save to baseline CSV
    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    csv_path = output_dir / f"scenario_sweep_baseline_{stamp}.csv"

    with csv_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "scenario_id",
                "risk_category",
                "drone_id",
                "altitude_ft",
                "ceiling_ft",
                "vertical_speed_fps",
                "wind_mps",
                "gust_mps",
                "visibility_km",
                "route",
                "risk_band",
                "risk_score",
                "confidence",
                "should_alert",
                "policy_chunks_retrieved",
                "latency_ms",
                "rationale",
            ],
        )
        if not csv_path.exists() or csv_path.stat().st_size == 0:
            writer.writeheader()
        writer.writerow(
            {
                "scenario_id": scenario_path.stem,
                "risk_category": expected_risk_category,
                "drone_id": event.drone_id,
                "altitude_ft": event.altitude_ft,
                "ceiling_ft": assessment.ceiling_ft,
                "vertical_speed_fps": event.vertical_speed_fps,
                "wind_mps": getattr(event, "wind_mps", "N/A"),
                "gust_mps": getattr(event, "gust_mps", "N/A"),
                "visibility_km": getattr(event, "visibility_km", "N/A"),
                "route": decision.route,
                "risk_band": decision.risk_band,
                "risk_score": f"{assessment.risk_score:.3f}",
                "confidence": f"{assessment.confidence:.3f}",
                "should_alert": decision.should_alert,
                "policy_chunks_retrieved": len(policy_context),
                "latency_ms": f"{latency_ms:.0f}",
                "rationale": decision.rationale[:100],  # Truncate for CSV
            }
        )

    print(f"✓ Baseline saved to: {csv_path}")
