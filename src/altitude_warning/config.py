from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Thresholds:
    horizon_seconds: int = 8
    risk_alert_threshold: float = 0.80
    confidence_auto_notify: float = 0.75


THRESHOLDS = Thresholds()
