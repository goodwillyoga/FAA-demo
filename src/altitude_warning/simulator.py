from datetime import UTC, datetime

from altitude_warning.models import TelemetryEvent


def generate_altitude_breach_events() -> list[TelemetryEvent]:
    """Deterministic Phase A scenario for testing/reference."""
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
