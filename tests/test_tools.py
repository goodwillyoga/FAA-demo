from altitude_warning.tools import policy_tool, risk_tool, trajectory_tool


def test_trajectory_projection_increases_with_vertical_speed() -> None:
    projected = trajectory_tool(current_altitude_ft=280.0, vertical_speed_fps=3.5, horizon_seconds=8)
    assert projected == 308.0


def test_policy_routes_high_risk_low_confidence_to_hitl() -> None:
    route, should_alert = policy_tool(risk_score=0.9, confidence=0.6)
    assert route == "hitl_review"
    assert should_alert is True


def test_risk_tool_bounds_values() -> None:
    risk, confidence = risk_tool(predicted_altitude_ft=500, ceiling_ft=300, vertical_speed_fps=20)
    assert 0.0 <= risk <= 1.0
    assert 0.0 <= confidence <= 1.0
