from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


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
    route: str | None = None
    should_alert: bool | None = None


@dataclass(slots=True)
class TraceStep:
    name: str
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


class RouteDecision(BaseModel):
    route: str = Field(..., description="auto_notify | hitl_review | monitor")
    risk_band: str = Field(..., description="LOW | MED | HIGH")
    should_alert: bool
    rationale: str


class LLMAssessment(BaseModel):
    predicted_altitude_ft: float
    ceiling_ft: float
    risk_score: float
    confidence: float


@dataclass(slots=True)
class AlertDecision:
    drone_id: str
    status: str
    message: str
    route: str
    risk_band: str
    risk_score: float
    confidence: float
    rationale: str | None = None
    trace_id: str | None = None
    trace: list[dict[str, Any]] | None = None
