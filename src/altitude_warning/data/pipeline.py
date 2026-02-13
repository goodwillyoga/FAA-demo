"""Build deterministic raw/processed/feature datasets for local development."""

from __future__ import annotations

import argparse
import csv
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

from altitude_warning.data.contract import (
    FEATURE_COLUMNS,
    PROCESSED_COLUMNS,
    RAW_TELEMETRY_COLUMNS,
    RAW_WEATHER_COLUMNS,
)
from altitude_warning.tools import ceiling_tool, policy_tool, risk_tool, trajectory_tool


def _to_iso(ts: datetime) -> str:
    return ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clamp(value: float, lo: float, hi: float) -> float:
    # Keep computed values inside a safe numeric range.
    # Example: clamp(1.2, 0, 1) -> 1.0
    return max(lo, min(value, hi))


def weather_stress_factor(wind_mps: float, gust_mps: float, wind_ref: float = 12.0, gust_ref: float = 18.0) -> float:
    """Compute a normalized weather burden score in [0, 1]."""
    # Weight sustained wind more than gust spikes:
    # stress = 0.6 * normalized_wind + 0.4 * normalized_gust
    # Intuition: sustained wind creates persistent control/trajectory pressure,
    # while gusts are short spikes; both matter, but baseline wind is weighted higher.
    # Clamp the final value to [0, 1] for stable downstream logic.
    return _clamp(0.6 * (wind_mps / wind_ref) + 0.4 * (gust_mps / gust_ref), 0.0, 1.0)


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    # Open mode "w" intentionally overwrites previous generated outputs.
    # This keeps each pipeline run deterministic and prevents stale row carryover.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_raw_data(base_dir: Path, duration_seconds: int = 120) -> tuple[Path, Path]:
    """Generate deterministic 1 Hz telemetry and weather rows for two drones."""
    # Pseudo logic:
    # 1) Define two drone profiles with different start times and locations.
    # 2) For each second in the duration, synthesize telemetry signals.
    # 3) Build quality flags (GPS fix, interpolation, delay, signal strength).
    # 4) Generate weather at the same second-level cadence.
    # 5) Write two raw CSVs: telemetry and weather.
    raw_dir = base_dir / "raw"
    raw_telemetry_path = raw_dir / "telemetry.csv"
    raw_weather_path = raw_dir / "weather.csv"

    drone_configs = [
        {
            "drone_id": "D-2001",
            "start": datetime(2026, 2, 13, 12, 0, 0, tzinfo=UTC),
            "lat": 37.62,
            "lon": -122.35,
            "start_altitude": 228.0,
            "heading": 95.0,
        },
        {
            "drone_id": "D-2002",
            "start": datetime(2026, 2, 13, 12, 5, 0, tzinfo=UTC),
            "lat": 37.58,
            "lon": -122.18,
            "start_altitude": 186.0,
            "heading": 40.0,
        },
    ]

    telemetry_rows: list[dict[str, object]] = []
    weather_map: dict[str, dict[str, object]] = {}

    # Build each drone timeline independently so datasets reflect asynchronous flights.
    for cfg in drone_configs:
        altitude_ft = cfg["start_altitude"]
        for second in range(duration_seconds):
            ts = cfg["start"] + timedelta(seconds=second)
            ts_iso = _to_iso(ts)

            if cfg["drone_id"] == "D-2001":
                if second < 35:
                    vertical_speed_fps = 1.2
                elif second < 75:
                    vertical_speed_fps = 2.1
                else:
                    vertical_speed_fps = 3.4
            else:
                if second < 60:
                    vertical_speed_fps = 0.7
                elif second < 95:
                    vertical_speed_fps = 2.6
                else:
                    vertical_speed_fps = 1.1

            # Add smooth movement variation to avoid unrealistic constant-speed traces.
            ground_speed_fps = 14.0 + 1.8 * math.sin(second / 12.0)
            heading_deg = cfg["heading"] + 2.5 * math.sin(second / 20.0)

            # Emit occasional quality degradation events so quality filters can be tested.
            gps_fix_ok = 0 if second % 57 == 0 else 1
            is_interpolated = 0 if gps_fix_ok == 1 else 1
            signal_strength = int(_clamp(82 + 10 * math.cos(second / 16.0) - (10 if is_interpolated else 0), 20, 100))
            message_delay_ms = int(35 + (90 if is_interpolated else 0) + abs(4 * math.sin(second / 15.0)))

            telemetry_rows.append(
                {
                    "event_id": f"{cfg['drone_id']}-{second:04d}",
                    "drone_id": cfg["drone_id"],
                    "timestamp_iso": ts_iso,
                    "lat": round(cfg["lat"] + 0.0002 * math.sin(second / 18.0), 7),
                    "lon": round(cfg["lon"] + 0.0002 * math.cos(second / 18.0), 7),
                    "altitude_ft": round(altitude_ft, 2),
                    "vertical_speed_fps": round(vertical_speed_fps, 3),
                    "ground_speed_fps": round(ground_speed_fps, 3),
                    "heading_deg": round(heading_deg, 3),
                    "gps_fix_ok": gps_fix_ok,
                    "signal_strength": signal_strength,
                    "message_delay_ms": message_delay_ms,
                    "is_interpolated": is_interpolated,
                }
            )

            # Weather context follows the same second-level cadence.
            # A gust window is injected to create visible risk amplification segments.
            wind_base = 4.2 + 0.015 * second
            gust_boost = 2.1 if 65 <= second <= 95 else 0.9
            wind_mps = round(wind_base + 0.55 * math.sin(second / 10.0), 3)
            gust_mps = round(wind_mps + gust_boost + 0.35 * math.cos(second / 11.0), 3)

            weather_map[ts_iso] = {
                "timestamp_iso": ts_iso,
                "wind_mps": wind_mps,
                "gust_mps": gust_mps,
                "wind_direction_deg": round(228 + 12 * math.sin(second / 30.0), 3),
                "visibility_km": round(_clamp(9.8 - 0.01 * second + 0.15 * math.cos(second / 9.0), 6.0, 10.0), 3),
            }

            altitude_ft += vertical_speed_fps

    # Sort weather by timestamp so downstream joins are deterministic and reproducible.
    weather_rows = [weather_map[k] for k in sorted(weather_map.keys())]
    _write_csv(raw_telemetry_path, telemetry_rows, RAW_TELEMETRY_COLUMNS)
    _write_csv(raw_weather_path, weather_rows, RAW_WEATHER_COLUMNS)
    return raw_telemetry_path, raw_weather_path


def build_processed_data(base_dir: Path, raw_telemetry_path: Path, raw_weather_path: Path) -> Path:
    """Join raw telemetry/weather and compute derived operational fields."""
    processed_dir = base_dir / "processed"
    processed_path = processed_dir / "telemetry_processed.csv"

    weather_lookup: dict[str, dict[str, str]] = {}
    # Build O(1) weather lookup by timestamp for stable second-level joins.
    with raw_weather_path.open("r", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            weather_lookup[row["timestamp_iso"]] = row

    processed_rows: list[dict[str, object]] = []
    # Enrich each telemetry record with weather and operational risk context.
    with raw_telemetry_path.open("r", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            ts = row["timestamp_iso"]
            weather = weather_lookup[ts]

            lat = float(row["lat"])
            lon = float(row["lon"])
            altitude_ft = float(row["altitude_ft"])
            vertical_speed_fps = float(row["vertical_speed_fps"])
            wind_mps = float(weather["wind_mps"])
            gust_mps = float(weather["gust_mps"])

            # Derived fields are designed for both operations monitoring and model features.
            ceiling_ft = ceiling_tool(lat, lon)
            margin_ft = ceiling_ft - altitude_ft
            predicted_altitude_ft_8s = trajectory_tool(altitude_ft, vertical_speed_fps, horizon_seconds=8)
            weather_stress = weather_stress_factor(wind_mps, gust_mps)

            processed_rows.append(
                {
                    **row,
                    "wind_mps": wind_mps,
                    "gust_mps": gust_mps,
                    "wind_direction_deg": float(weather["wind_direction_deg"]),
                    "visibility_km": float(weather["visibility_km"]),
                    "ceiling_ft": round(ceiling_ft, 3),
                    "altitude_margin_to_ceiling_ft": round(margin_ft, 3),
                    "weather_stress_factor": round(weather_stress, 4),
                    "predicted_altitude_ft_8s": round(predicted_altitude_ft_8s, 3),
                }
            )

    _write_csv(processed_path, processed_rows, PROCESSED_COLUMNS)
    return processed_path


def build_feature_data(base_dir: Path, processed_path: Path) -> Path:
    """Create model-ready feature dataset from processed operational rows."""
    processed_dir = base_dir / "processed"
    features_path = processed_dir / "ceiling_risk_features.csv"

    feature_rows: list[dict[str, object]] = []
    # Convert enriched operations rows into model-ready features and training labels.
    with processed_path.open("r", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            altitude_ft = float(row["altitude_ft"])
            vertical_speed_fps = float(row["vertical_speed_fps"])
            ceiling_ft = float(row["ceiling_ft"])
            predicted_altitude_ft_8s = float(row["predicted_altitude_ft_8s"])
            weather_stress = float(row["weather_stress_factor"])

            # Weather-adjusted climb rate makes windy intervals more risk-sensitive.
            adjusted_vertical_speed = vertical_speed_fps + (2.0 * weather_stress)
            risk_score, confidence = risk_tool(predicted_altitude_ft_8s, ceiling_ft, adjusted_vertical_speed)
            route, _ = policy_tool(risk_score, confidence)

            # Binary target for classification-style evaluation.
            cross_within_8s = 1 if predicted_altitude_ft_8s > ceiling_ft else 0

            if adjusted_vertical_speed <= 0 or altitude_ft >= ceiling_ft:
                time_to_ceiling_cross_sec = ""
            else:
                # Time-to-cross target for lead-time analysis and ranking.
                ttc = (ceiling_ft - altitude_ft) / adjusted_vertical_speed
                time_to_ceiling_cross_sec = round(ttc, 3) if 0 <= ttc <= 8 else ""

            feature_rows.append(
                {
                    "drone_id": row["drone_id"],
                    "timestamp_iso": row["timestamp_iso"],
                    "altitude_ft": round(altitude_ft, 3),
                    "vertical_speed_fps": round(vertical_speed_fps, 3),
                    "ceiling_ft": round(ceiling_ft, 3),
                    "altitude_margin_to_ceiling_ft": round(float(row["altitude_margin_to_ceiling_ft"]), 3),
                    "weather_stress_factor": round(weather_stress, 4),
                    "predicted_altitude_ft_8s": round(predicted_altitude_ft_8s, 3),
                    "risk_score": round(risk_score, 4),
                    "confidence": round(confidence, 4),
                    "route": route,
                    "ceiling_cross_within_8s": cross_within_8s,
                    "time_to_ceiling_cross_sec": time_to_ceiling_cross_sec,
                }
            )

    _write_csv(features_path, feature_rows, FEATURE_COLUMNS)
    return features_path


def run_data_pipeline(base_dir: Path, duration_seconds: int = 120) -> dict[str, Path]:
    raw_telemetry, raw_weather = generate_raw_data(base_dir=base_dir, duration_seconds=duration_seconds)
    processed = build_processed_data(base_dir=base_dir, raw_telemetry_path=raw_telemetry, raw_weather_path=raw_weather)
    features = build_feature_data(base_dir=base_dir, processed_path=processed)
    return {
        "raw_telemetry": raw_telemetry,
        "raw_weather": raw_weather,
        "processed": processed,
        "features": features,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build raw/processed/feature datasets.")
    parser.add_argument("--base-dir", default="data", help="Output base data directory")
    parser.add_argument("--duration-seconds", type=int, default=120, help="Per-drone generation duration in seconds")
    args = parser.parse_args()

    outputs = run_data_pipeline(base_dir=Path(args.base_dir), duration_seconds=args.duration_seconds)
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
