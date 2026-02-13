"""Schema contracts for raw, processed, and feature datasets."""

from __future__ import annotations

# Raw telemetry schema at 1 Hz cadence.
RAW_TELEMETRY_COLUMNS = [
    "event_id",  # Unique identifier for a telemetry record.
    "drone_id",  # Drone identifier.
    "timestamp_iso",  # Event timestamp in UTC ISO-8601 format.
    "lat",  # Latitude in decimal degrees.
    "lon",  # Longitude in decimal degrees.
    "altitude_ft",  # Current altitude in feet.
    "vertical_speed_fps",  # Vertical speed in feet per second.
    "ground_speed_fps",  # Horizontal speed over ground in feet per second.
    "heading_deg",  # Movement heading in degrees.
    "gps_fix_ok",  # GPS fix quality flag (1 valid, 0 invalid).
    "signal_strength",  # Signal quality indicator (0-100).
    "message_delay_ms",  # Message delay in milliseconds.
    "is_interpolated",  # Interpolation flag (1 inferred point, 0 direct measurement).
]

# Weather schema aligned by timestamp.
RAW_WEATHER_COLUMNS = [
    "timestamp_iso",  # Weather timestamp in UTC ISO-8601 format.
    "wind_mps",  # Sustained wind speed in meters per second.
    "gust_mps",  # Gust speed in meters per second.
    "wind_direction_deg",  # Wind direction in degrees.
    "visibility_km",  # Visibility in kilometers.
]

# Processed schema extends raw telemetry with weather + derived fields.
PROCESSED_COLUMNS = [
    *RAW_TELEMETRY_COLUMNS,
    "wind_mps",  # Joined sustained wind speed.
    "gust_mps",  # Joined gust speed.
    "wind_direction_deg",  # Joined wind direction.
    "visibility_km",  # Joined visibility.
    "ceiling_ft",  # Allowed altitude ceiling for location.
    "altitude_margin_to_ceiling_ft",  # Distance to ceiling: ceiling_ft - altitude_ft.
    "weather_stress_factor",  # Normalized weather burden score (0..1).
    "predicted_altitude_ft_8s",  # Projected altitude after 8 seconds.
]

# Feature schema used for model training/evaluation and risk analytics.
FEATURE_COLUMNS = [
    "drone_id",  # Drone identifier.
    "timestamp_iso",  # Feature timestamp.
    "altitude_ft",  # Current altitude.
    "vertical_speed_fps",  # Vertical speed.
    "ceiling_ft",  # Local ceiling.
    "altitude_margin_to_ceiling_ft",  # Current margin to ceiling.
    "weather_stress_factor",  # Weather burden score (0..1).
    "predicted_altitude_ft_8s",  # 8-second altitude projection.
    "risk_score",  # Computed risk score (0..1).
    "confidence",  # Confidence score (0..1).
    "route",  # Decision path: monitor, auto_notify, or hitl_review.
    "ceiling_cross_within_8s",  # Binary label for projected crossing in 8 seconds.
    "time_to_ceiling_cross_sec",  # Estimated crossing time in seconds when applicable.
]

# Human-readable schema dictionary for docs and UI tooltips.
COLUMN_DESCRIPTIONS = {
    "event_id": "Unique identifier for each telemetry record.",
    "drone_id": "Identifier for the drone that produced the record.",
    "timestamp_iso": "UTC timestamp in ISO-8601 format.",
    "lat": "Latitude in decimal degrees.",
    "lon": "Longitude in decimal degrees.",
    "altitude_ft": "Current altitude in feet.",
    "vertical_speed_fps": "Vertical speed in feet per second.",
    "ground_speed_fps": "Horizontal speed over ground in feet per second.",
    "heading_deg": "Travel direction in degrees.",
    "gps_fix_ok": "GPS quality flag (1=valid fix, 0=invalid fix).",
    "signal_strength": "Signal quality score from 0 to 100.",
    "message_delay_ms": "Delay between measurement and message processing in milliseconds.",
    "is_interpolated": "Flag showing whether a point is inferred (1) or directly measured (0).",
    "wind_mps": "Sustained wind speed in meters per second.",
    "gust_mps": "Gust speed in meters per second.",
    "wind_direction_deg": "Wind direction in degrees.",
    "visibility_km": "Visibility in kilometers.",
    "ceiling_ft": "Allowed altitude ceiling for the given location.",
    "altitude_margin_to_ceiling_ft": "Distance to ceiling computed as ceiling_ft minus altitude_ft.",
    "weather_stress_factor": "Normalized weather burden score in the range 0 to 1.",
    "predicted_altitude_ft_8s": "Projected altitude eight seconds after current timestamp.",
    "risk_score": "Risk output score in the range 0 to 1.",
    "confidence": "Confidence output score in the range 0 to 1.",
    "route": "Policy route selected by decision logic.",
    "ceiling_cross_within_8s": "Binary target indicating projected ceiling crossing in eight seconds.",
    "time_to_ceiling_cross_sec": "Projected seconds to ceiling crossing when crossing is expected soon.",
}
