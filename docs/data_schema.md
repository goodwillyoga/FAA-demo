# Data Schema

I use this schema to keep data generation, transformation, and model features consistent and reviewable.

## Where Data Code Lives
I keep dataset files in `data/`, and I keep data-processing Python code in `src/altitude_warning/data/`.

## Generation Scope
- I generate data for `2` drones: `D-2001`, `D-2002`.
- I generate `120` seconds per drone at `1 Hz` cadence.
- I intentionally offset drone start times to simulate asynchronous operations.

## Raw Telemetry (`data/raw/telemetry.csv`)
| Column | Meaning |
|---|---|
| `event_id` | I use this as the unique identifier for each telemetry record. |
| `drone_id` | I use this to identify which drone emitted the record. |
| `timestamp_iso` | I use this UTC timestamp to place each record on a precise timeline. |
| `lat` | I use latitude to locate the drone north/south in degrees. |
| `lon` | I use longitude to locate the drone east/west in degrees. |
| `altitude_ft` | I use altitude in feet to measure vertical position above reference level. |
| `vertical_speed_fps` | I use vertical speed (feet/second) to estimate climb or descent trend. |
| `ground_speed_fps` | I use ground speed (feet/second) to represent horizontal motion rate. |
| `heading_deg` | I use heading (degrees) to represent travel direction. |
| `gps_fix_ok` | I use this quality flag (`0/1`) to indicate whether GPS fix is valid. |
| `signal_strength` | I use this quality indicator (`0-100`) to track message reliability. |
| `message_delay_ms` | I use this delay value (milliseconds) to track message timeliness. |
| `is_interpolated` | I use this flag (`0/1`) to indicate whether a point was inferred/interpolated. |

## Raw Weather (`data/raw/weather.csv`)
| Column | Meaning |
|---|---|
| `timestamp_iso` | I use this UTC timestamp to align weather with telemetry by second. |
| `wind_mps` | I use wind speed (m/s) to quantify sustained wind load. |
| `gust_mps` | I use gust speed (m/s) to quantify short-term wind spikes. |
| `wind_direction_deg` | I use wind direction (degrees) to capture directional weather effects. |
| `visibility_km` | I use visibility (km) as a simple environmental condition indicator. |

## Processed Telemetry (`data/processed/telemetry_processed.csv`)
I keep all raw telemetry fields, add weather fields, and compute these derived operational features:

| Derived Column | Meaning |
|---|---|
| `ceiling_ft` | I use this as the allowed altitude ceiling for the drone location. |
| `altitude_margin_to_ceiling_ft` | I use this to measure distance to ceiling (`ceiling_ft - altitude_ft`). |
| `weather_stress_factor` | I use this normalized score (`0..1`) to quantify wind/gust burden on risk. |
| `predicted_altitude_ft_8s` | I use this projection to estimate altitude after 8 seconds. |

Derived formulas:
- `altitude_margin_to_ceiling_ft = ceiling_ft - altitude_ft`
- `weather_stress_factor = clamp(0.6*(wind_mps/12.0) + 0.4*(gust_mps/18.0), 0, 1)`
- `predicted_altitude_ft_8s = altitude_ft + vertical_speed_fps*8`

## Feature Dataset (`data/processed/ceiling_risk_features.csv`)
I prepare these model-ready fields for scoring and analysis:

| Feature/Target | Meaning |
|---|---|
| `drone_id` | I use this to group feature rows by drone. |
| `timestamp_iso` | I use this to preserve time alignment for feature rows. |
| `altitude_ft` | I use current altitude as a primary risk input. |
| `vertical_speed_fps` | I use climb/descent rate as a short-horizon predictor. |
| `ceiling_ft` | I use local ceiling as the operational constraint. |
| `altitude_margin_to_ceiling_ft` | I use margin to detect proximity risk before crossing occurs. |
| `weather_stress_factor` | I use weather burden to adjust risk sensitivity. |
| `predicted_altitude_ft_8s` | I use projected altitude to estimate near-term crossing risk. |
| `risk_score` | I use this bounded score (`0..1`) as the model/rule risk output. |
| `confidence` | I use this bounded score (`0..1`) to indicate decision certainty. |
| `route` | I use this to represent policy path (`monitor`, `auto_notify`, `hitl_review`). |
| `ceiling_cross_within_8s` | I use this binary target to label near-term crossing events. |
| `time_to_ceiling_cross_sec` | I use this target to estimate crossing lead time when crossing is expected soon. |

## Determinism
I keep generation deterministic so tests and comparisons stay reproducible across runs.
