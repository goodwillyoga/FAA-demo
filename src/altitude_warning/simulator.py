from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from altitude_warning.models import TelemetryEvent


def default_scenario_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "scenarios" / "feature1_altitude_breach.json"


def load_scenario_events(path: Path) -> list[TelemetryEvent]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    events = []
    for event in payload.get("events", []):
        events.append(
            TelemetryEvent(
                drone_id=event["drone_id"],
                lat=event["lat"],
                lon=event["lon"],
                altitude_ft=event["altitude_ft"],
                vertical_speed_fps=event["vertical_speed_fps"],
                timestamp_iso=event["timestamp_iso"],
            )
        )
    return events


def generate_altitude_breach_events() -> list[TelemetryEvent]:
    """Deterministic scenario used by CLI/API when no path is supplied."""
    path = default_scenario_path()
    if path.exists():
        return load_scenario_events(path)

    now = datetime.now(UTC).isoformat()
    return [
        TelemetryEvent(
            drone_id="D-1001",
            lat=37.62,
            lon=-122.35,
            altitude_ft=280.0,
            vertical_speed_fps=3.5,
            timestamp_iso=now,
        ),
        TelemetryEvent(
            drone_id="D-1001",
            lat=37.62,
            lon=-122.35,
            altitude_ft=288.0,
            vertical_speed_fps=3.0,
            timestamp_iso=now,
        ),
    ]
