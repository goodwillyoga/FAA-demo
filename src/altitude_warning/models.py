from dataclasses import dataclass


@dataclass(slots=True)
class TelemetryEvent:
    drone_id: str
    lat: float
    lon: float
    altitude_ft: float
    vertical_speed_fps: float
    timestamp_iso: str


@dataclass(slots=True)
class RiskAssessment:
    predicted_altitude_ft: float
    ceiling_ft: float
    risk_score: float
    confidence: float
    route: str
    should_alert: bool


@dataclass(slots=True)
class AlertDecision:
    drone_id: str
    status: str
    message: str
    route: str
    risk_score: float
    confidence: float
