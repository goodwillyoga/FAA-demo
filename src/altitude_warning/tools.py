from langchain_core.tools import tool

from altitude_warning.config import THRESHOLDS


def ceiling_tool(lat: float, lon: float) -> float:
    """Return a simple simulated ceiling in feet for the location."""
    # Keep deterministic for Phase A references.
    if lat > 37.6 and lon < -122.2:
        return 300.0
    return 400.0


def trajectory_tool(current_altitude_ft: float, vertical_speed_fps: float, horizon_seconds: int | None = None) -> float:
    horizon = horizon_seconds if horizon_seconds is not None else THRESHOLDS.horizon_seconds
    return current_altitude_ft + (vertical_speed_fps * horizon)


def risk_tool(predicted_altitude_ft: float, ceiling_ft: float, vertical_speed_fps: float) -> tuple[float, float]:
    """Return (risk_score, confidence) bounded to [0, 1]."""
    if ceiling_ft <= 0:
        return 1.0, 0.3

    margin_ratio = (predicted_altitude_ft - ceiling_ft) / ceiling_ft
    climb_factor = max(vertical_speed_fps, 0.0) / 10.0

    # Phase A intent: if projected altitude exceeds ceiling, force an early-warning level score.
    if predicted_altitude_ft > ceiling_ft:
        risk_score = max(0.0, min(1.0, 0.82 + min(0.15, margin_ratio * 2.0) + 0.05 * climb_factor))
    else:
        risk_score = max(0.0, min(1.0, 0.55 + margin_ratio + 0.2 * climb_factor))
    confidence = max(0.0, min(1.0, 0.6 + 0.25 * climb_factor))
    return risk_score, confidence


def policy_tool(risk_score: float, confidence: float) -> tuple[str, bool]:
    if risk_score >= THRESHOLDS.risk_alert_threshold:
        if confidence >= THRESHOLDS.confidence_auto_notify:
            return "auto_notify", True
        return "hitl_review", True
    return "monitor", False


@tool("ceiling_tool")
def lc_ceiling_tool(lat: float, lon: float) -> float:
    """Return a simulated ceiling in feet for the location."""
    return ceiling_tool(lat, lon)


@tool("trajectory_tool")
def lc_trajectory_tool(current_altitude_ft: float, vertical_speed_fps: float, horizon_seconds: int | None = None) -> float:
    """Project altitude forward using a fixed horizon."""
    return trajectory_tool(current_altitude_ft, vertical_speed_fps, horizon_seconds)


def get_langchain_tools() -> list:
    return [lc_ceiling_tool, lc_trajectory_tool]
