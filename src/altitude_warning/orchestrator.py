import json
import os
from dataclasses import asdict
from time import perf_counter
from typing import Any, TypedDict
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from altitude_warning.models import (
    AlertDecision,
    LLMAssessment,
    RiskAssessment,
    RouteDecision,
    TelemetryEvent,
    TraceStep,
)
from altitude_warning.tools import get_langchain_tools


class OrchestratorState(TypedDict):
    event: TelemetryEvent
    assessment: RiskAssessment | None
    llm_decision: RouteDecision | None
    decision: AlertDecision | None
    trace: list[TraceStep]
    trace_id: str


class Orchestrator:
    """Agentic orchestration path powered by LangGraph + LangChain."""

    def __init__(self, llm: Any | None = None, trace_enabled: bool = False, model_name: str | None = None) -> None:
        self.trace_enabled = trace_enabled
        resolved_model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm = llm or ChatOpenAI(model=resolved_model, temperature=0)
        self.tools = get_langchain_tools()
        self.tools_by_name = {tool.name: tool for tool in self.tools}
        self.llm_with_tools = self.llm.bind_tools(self.tools) if hasattr(self.llm, "bind_tools") else self.llm
        self.assess_prompt = (
            "You are an FAA safety agent. Use tools to compute ceiling and projected altitude. "
            "Then compute risk score and confidence yourself based on those values and the telemetry. "
            "Call tools as needed. When done, respond ONLY with a JSON object: "
            "{\"predicted_altitude_ft\": number, \"ceiling_ft\": number, "
            "\"risk_score\": number, \"confidence\": number}."
        )
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an FAA safety agent. Decide the next route for a drone safety event. "
                    "Return a JSON object with: route (auto_notify | hitl_review | monitor), "
                    "should_alert (true/false), and rationale (short).",
                ),
                (
                    "human",
                    "Telemetry: altitude_ft={altitude_ft}, vertical_speed_fps={vertical_speed_fps}. "
                    "Projection: predicted_altitude_ft={predicted_altitude_ft}, ceiling_ft={ceiling_ft}. "
                    "Risk: risk_score={risk_score}, confidence={confidence}.",
                ),
            ]
        )
        self.use_structured_output = True
        try:
            self.chain = self.prompt | self.llm.with_structured_output(RouteDecision)
        except NotImplementedError:
            self.use_structured_output = False
            self.chain = self.prompt | self.llm
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        graph = StateGraph(OrchestratorState)
        graph.add_node("assess_risk", self._assess_risk)
        graph.add_node("decide_route", self._decide_route)
        graph.add_node("emit_decision", self._emit_decision)
        graph.add_edge("assess_risk", "decide_route")
        graph.add_edge("decide_route", "emit_decision")
        graph.add_edge("emit_decision", END)
        graph.set_entry_point("assess_risk")
        return graph.compile()

    def _append_trace(
        self,
        trace: list[TraceStep],
        name: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        start: float,
    ) -> list[TraceStep]:
        if not self.trace_enabled:
            return trace
        duration_ms = (perf_counter() - start) * 1000
        return [
            *trace,
            TraceStep(name=name, inputs=inputs, outputs=outputs, duration_ms=round(duration_ms, 2)),
        ]

    def _assess_risk(self, state: OrchestratorState) -> dict[str, Any]:
        event = state["event"]
        start = perf_counter()

        messages: list[Any] = [
            SystemMessage(content=self.assess_prompt),
            HumanMessage(
                content=(
                    "Telemetry: altitude_ft={altitude_ft}, vertical_speed_fps={vertical_speed_fps}, "
                    "lat={lat}, lon={lon}."
                ).format(
                    altitude_ft=event.altitude_ft,
                    vertical_speed_fps=event.vertical_speed_fps,
                    lat=event.lat,
                    lon=event.lon,
                )
            ),
        ]

        response = self.llm_with_tools.invoke(messages)
        messages.append(response)
        tool_log: list[dict[str, Any]] = []

        for _ in range(4):
            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                break
            for call in tool_calls:
                tool = self.tools_by_name.get(call["name"])
                if tool is None:
                    raise ValueError(f"Unknown tool requested: {call['name']}")
                result = tool.invoke(call["args"])
                tool_log.append({"tool": call["name"], "args": call["args"], "result": result})
                messages.append(
                    ToolMessage(content=json.dumps({"result": result}), tool_call_id=call["id"])
                )
            response = self.llm_with_tools.invoke(messages)
            messages.append(response)

        content = response.content if hasattr(response, "content") else response
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM assessment response is not valid JSON: {content}") from exc

        assessment_data = LLMAssessment.model_validate(payload)
        assessment = RiskAssessment(
            predicted_altitude_ft=assessment_data.predicted_altitude_ft,
            ceiling_ft=assessment_data.ceiling_ft,
            risk_score=assessment_data.risk_score,
            confidence=assessment_data.confidence,
        )

        trace = self._append_trace(
            state["trace"],
            "assess_risk",
            {
                "altitude_ft": event.altitude_ft,
                "vertical_speed_fps": event.vertical_speed_fps,
                "lat": event.lat,
                "lon": event.lon,
            },
            {
                "predicted_altitude_ft": round(assessment.predicted_altitude_ft, 2),
                "ceiling_ft": round(assessment.ceiling_ft, 2),
                "risk_score": round(assessment.risk_score, 3),
                "confidence": round(assessment.confidence, 3),
                "tool_calls": tool_log,
            },
            start,
        )

        return {"assessment": assessment, "trace": trace}

    def _decide_route(self, state: OrchestratorState) -> dict[str, Any]:
        assessment = state["assessment"]
        event = state["event"]
        if assessment is None:
            raise ValueError("Missing assessment state")

        payload = {
            "altitude_ft": event.altitude_ft,
            "vertical_speed_fps": event.vertical_speed_fps,
            "predicted_altitude_ft": round(assessment.predicted_altitude_ft, 2),
            "ceiling_ft": round(assessment.ceiling_ft, 2),
            "risk_score": round(assessment.risk_score, 3),
            "confidence": round(assessment.confidence, 3),
        }

        start = perf_counter()
        raw_decision = self.chain.invoke(payload)
        if self.use_structured_output:
            llm_decision = raw_decision
        else:
            content = raw_decision.content if hasattr(raw_decision, "content") else raw_decision
            try:
                decision_payload = json.loads(content)
            except json.JSONDecodeError as exc:
                raise ValueError(f"LLM routing response is not valid JSON: {content}") from exc
            llm_decision = RouteDecision.model_validate(decision_payload)
        trace = self._append_trace(
            state["trace"],
            "decide_route",
            payload,
            {
                "route": llm_decision.route,
                "should_alert": llm_decision.should_alert,
                "rationale": llm_decision.rationale,
            },
            start,
        )

        updated_assessment = RiskAssessment(
            predicted_altitude_ft=assessment.predicted_altitude_ft,
            ceiling_ft=assessment.ceiling_ft,
            risk_score=assessment.risk_score,
            confidence=assessment.confidence,
            route=llm_decision.route,
            should_alert=llm_decision.should_alert,
        )

        return {"assessment": updated_assessment, "llm_decision": llm_decision, "trace": trace}

    def _emit_decision(self, state: OrchestratorState) -> dict[str, Any]:
        event = state["event"]
        assessment = state["assessment"]
        llm_decision = state["llm_decision"]
        if assessment is None or llm_decision is None:
            raise ValueError("Missing decision state")

        if llm_decision.should_alert:
            eta_seconds = 8
            message = (
                f"Likely ceiling breach in {eta_seconds}s: projected {assessment.predicted_altitude_ft:.1f}ft "
                f"vs ceiling {assessment.ceiling_ft:.1f}ft"
            )
            status = "alerted"
        else:
            message = "No alert: drone remains within projected ceiling."
            status = "monitoring"

        start = perf_counter()
        trace = self._append_trace(
            state["trace"],
            "emit_decision",
            {
                "route": llm_decision.route,
                "should_alert": llm_decision.should_alert,
            },
            {"status": status},
            start,
        )

        decision = AlertDecision(
            drone_id=event.drone_id,
            status=status,
            message=message,
            route=llm_decision.route,
            risk_score=assessment.risk_score,
            confidence=assessment.confidence,
            rationale=llm_decision.rationale,
            trace_id=state["trace_id"] if self.trace_enabled else None,
            trace=[asdict(step) for step in trace] if self.trace_enabled else None,
        )

        return {"decision": decision, "trace": trace}

    def process_event(self, event: TelemetryEvent) -> tuple[AlertDecision, RiskAssessment, float]:
        start = perf_counter()
        initial_state: OrchestratorState = {
            "event": event,
            "assessment": None,
            "llm_decision": None,
            "decision": None,
            "trace": [],
            "trace_id": str(uuid4()),
        }
        final_state = self.graph.invoke(initial_state)
        latency_ms = (perf_counter() - start) * 1000
        decision = final_state["decision"]
        assessment = final_state["assessment"]
        if decision is None or assessment is None:
            raise ValueError("Missing decision output")
        return decision, assessment, latency_ms
