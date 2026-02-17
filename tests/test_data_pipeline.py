from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from altitude_warning.data.contract import FEATURE_COLUMNS, PROCESSED_COLUMNS, RAW_TELEMETRY_COLUMNS, RAW_WEATHER_COLUMNS
from altitude_warning.data.pipeline import run_data_pipeline


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_run_data_pipeline_writes_expected_files(tmp_path: Path) -> None:
    outputs = run_data_pipeline(base_dir=tmp_path, duration_seconds=120)

    assert outputs["raw_telemetry"].exists()
    assert outputs["raw_weather"].exists()
    assert outputs["processed"].exists()
    assert outputs["features"].exists()


def test_raw_data_shapes_and_schemas(tmp_path: Path) -> None:
    outputs = run_data_pipeline(base_dir=tmp_path, duration_seconds=120)

    telemetry_rows = _read_rows(outputs["raw_telemetry"])
    weather_rows = _read_rows(outputs["raw_weather"])

    assert len(telemetry_rows) == 240  # 2 drones x 120 seconds
    assert len(weather_rows) == 240
    assert list(telemetry_rows[0].keys()) == RAW_TELEMETRY_COLUMNS
    assert list(weather_rows[0].keys()) == RAW_WEATHER_COLUMNS



def test_processed_derivations_and_feature_targets(tmp_path: Path) -> None:
    outputs = run_data_pipeline(base_dir=tmp_path, duration_seconds=120)

    processed_rows = _read_rows(outputs["processed"])
    feature_rows = _read_rows(outputs["features"])

    assert len(processed_rows) == 240
    assert len(feature_rows) == 240
    assert list(processed_rows[0].keys()) == PROCESSED_COLUMNS
    assert list(feature_rows[0].keys()) == FEATURE_COLUMNS

    first = processed_rows[0]
    ceiling = float(first["ceiling_ft"])
    altitude = float(first["altitude_ft"])
    margin = float(first["altitude_margin_to_ceiling_ft"])
    weather_stress = float(first["weather_stress_factor"])

    assert round(ceiling - altitude, 3) == round(margin, 3)
    assert 0.0 <= weather_stress <= 1.0

    # Verify a sampled target relationship in the feature set.
    sampled = feature_rows[50]
    predicted = float(sampled["predicted_altitude_ft_8s"])
    sampled_ceiling = float(sampled["ceiling_ft"])
    sampled_target = int(sampled["ceiling_cross_within_8s"])
    assert sampled_target == (1 if predicted > sampled_ceiling else 0)



def test_drones_have_distinct_start_times(tmp_path: Path) -> None:
    outputs = run_data_pipeline(base_dir=tmp_path, duration_seconds=120)
    telemetry_rows = _read_rows(outputs["raw_telemetry"])

    first_by_drone: dict[str, datetime] = {}
    for row in telemetry_rows:
        drone = row["drone_id"]
        if drone not in first_by_drone:
            first_by_drone[drone] = datetime.fromisoformat(row["timestamp_iso"].replace("Z", "+00:00"))

    assert set(first_by_drone.keys()) == {"D-2001", "D-2002"}
    delta_seconds = abs((first_by_drone["D-2002"] - first_by_drone["D-2001"]).total_seconds())
    assert delta_seconds >= 300
