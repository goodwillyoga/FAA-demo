import json
import logging
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Sequence, TypedDict
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
from altitude_warning.policy.retriever import retrieve_policy_context
from altitude_warning.prompts import ASSESS_SYSTEM_PROMPT, DECIDE_CONTEXT_PROMPT, DECIDE_SYSTEM_PROMPT
from altitude_warning.tools import get_langchain_tools


class OrchestratorState(TypedDict):
    event: TelemetryEvent
    assessment: RiskAssessment | None
    policy_context: list[str]
    llm_decision: RouteDecision | None
    decision: AlertDecision | None
    trace: list[TraceStep]
    trace_id: str
    error: str | None
    hitl_approval_needed: bool


class Orchestrator:
    """Agentic orchestration path powered by LangGraph + LangChain."""

    _ALLOWED_RISK_BANDS = {"LOW", "MED", "HIGH"}
    _ALLOWED_ROUTES = {"auto_notify", "hitl_review", "monitor"}

    def __init__(
        self,
        llm: Any | None = None,
        trace_enabled: bool = False,
        model_name: str | None = None,
        enable_policy_retrieval: bool = True,
    ) -> None:
        self.trace_enabled = trace_enabled
        self.enable_policy_retrieval = enable_policy_retrieval
        resolved_model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm = llm or ChatOpenAI(model=resolved_model, temperature=0)
        self.tools = get_langchain_tools()
        self.tools_by_name = {tool.name: tool for tool in self.tools}
        self.llm_with_tools = self.llm.bind_tools(self.tools) if hasattr(self.llm, "bind_tools") else self.llm
        self.policy_llm_rerank = os.getenv("POLICY_LLM_RERANK", "0").lower() not in {"0", "false", ""}
        self.policy_rerank_model = os.getenv("POLICY_RERANK_MODEL", "gpt-4o-mini")
        
        # Setup logging
        self._setup_logging()
        
        self.assess_prompt = ASSESS_SYSTEM_PROMPT
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    DECIDE_SYSTEM_PROMPT,
                ),
                (
                    "human",
                    DECIDE_CONTEXT_PROMPT,
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

    def _setup_logging(self) -> None:
        """Configure logging to capture orchestrator errors and decisions."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"orchestrator_{datetime.now().strftime('%Y%m%d')}.log"
        
        self.logger = logging.getLogger(f"orchestrator.{id(self)}")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.FileHandler(log_file)
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _build_graph(self) -> Any:
        graph = StateGraph(OrchestratorState)
        
        # Add nodes
        graph.add_node("assess_risk", self._assess_risk)
        graph.add_node("retrieve_policy", self._retrieve_policy)
        graph.add_node("decide_route", self._decide_route)
        graph.add_node("hitl_approval", self._hitl_approval)
        graph.add_node("emit_decision", self._emit_decision)
        graph.add_node("handle_error", self._handle_error)
        
        # Entry point
        graph.set_entry_point("assess_risk")
        
        # Linear edges with error handling
        graph.add_edge("assess_risk", "retrieve_policy")
        graph.add_edge("retrieve_policy", "decide_route")
        
        # Conditional routing after decide_route
        graph.add_conditional_edges(
            "decide_route",
            self._route_decision,
            {
                "hitl": "hitl_approval",
                "auto": "emit_decision",
                "error": "handle_error",
            }
        )
        
        # HITL goes to emit
        graph.add_edge("hitl_approval", "emit_decision")
        
        # Terminal edges
        graph.add_edge("emit_decision", END)
        graph.add_edge("handle_error", END)
        
        return graph.compile()
    
    def _route_decision(self, state: OrchestratorState) -> str:
        """Conditional routing based on LLM decision and risk thresholds."""
        if state.get("error"):
            return "error"
        
        llm_decision = state.get("llm_decision")
        assessment = state.get("assessment")
        
        if not llm_decision or not assessment:
            return "error"
        
        # Route to HITL if:
        # 1. Route explicitly says hitl_review, OR
        # 2. High risk (>0.7) with low confidence (<0.6)
        if llm_decision.route == "hitl_review":
            return "hitl"
        
        if assessment.risk_score > 0.7 and assessment.confidence < 0.6:
            self.logger.info(
                f"Auto-routing to HITL: high_risk={assessment.risk_score:.2f}, "
                f"low_confidence={assessment.confidence:.2f}"
            )
            return "hitl"
        
        return "auto"

    def _format_policy_context(self, snippets: Sequence[str]) -> str:
        if not snippets:
            return "None available"
        return "\n".join(snippets)

    def _has_citation(self, rationale: str) -> bool:
        return "[S" in rationale

    def _retrieve_policy(self, state: OrchestratorState) -> dict[str, Any]:
        assessment = state["assessment"]
        event = state["event"]
        start = perf_counter()

        if assessment is None or not self.enable_policy_retrieval:
            trace = self._append_trace(
                state["trace"],
                "retrieve_policy",
                {"enabled": self.enable_policy_retrieval},
                {"policy_chunks": 0},
                start,
            )
            return {"policy_context": [], "trace": trace}

        query = (
            "FAA Part 107 guidance for altitude limits and operational safety. "
            f"Telemetry altitude_ft={event.altitude_ft}, vertical_speed_fps={event.vertical_speed_fps}, "
            f"predicted_altitude_ft={assessment.predicted_altitude_ft:.1f}, ceiling_ft={assessment.ceiling_ft:.1f}."
        )

        policy_context: list[str] = []
        error: str | None = None
        try:
            os.environ["POLICY_LLM_RERANK"] = "1" if self.policy_llm_rerank else "0"
            os.environ["POLICY_RERANK_MODEL"] = self.policy_rerank_model
            snippets = retrieve_policy_context(query)
            for idx, snippet in enumerate(snippets, start=1):
                text = " ".join(snippet.text.split())
                policy_context.append(
                    f"[S{idx}] [{snippet.source} p.{snippet.page}] {text}"
                )
        except Exception as exc:
            error = f"Policy retrieval failed: {type(exc).__name__}: {str(exc)}"
            self.logger.warning(error)
            # Continue with empty policy context (graceful degradation)

        trace = self._append_trace(
            state["trace"],
            "retrieve_policy",
            {"query": query},
            {"policy_chunks": len(policy_context), "error": error},
            start,
        )

        return {"policy_context": policy_context, "trace": trace}

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

    def _clamp_score(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def _guard_decision(self, decision: RouteDecision, fallback_risk_score: float) -> RouteDecision:
        risk_band = decision.risk_band if decision.risk_band in self._ALLOWED_RISK_BANDS else "MED"
        route = decision.route if decision.route in self._ALLOWED_ROUTES else "monitor"
        should_alert = bool(decision.should_alert)
        rationale = decision.rationale.strip() if decision.rationale else "Guardrail: no rationale provided."

        # Guardrail: Validate HIGH risk + no alert inconsistency
        # Route to HITL for operator review rather than silently fixing
        if risk_band == "HIGH" and not should_alert:
            route = "hitl_review"
            rationale = f"Guardrail: HIGH risk without alert routed to HITL review. {rationale}"
            self.logger.warning(
                f"Inconsistent decision detected: HIGH risk_band={risk_band} but should_alert={should_alert}. "
                f"Routing to HITL. Decision: {decision}"
            )

        if not self._has_citation(rationale):
            rationale = f"Guardrail: missing citation. {rationale}"

        if decision.risk_band != risk_band or decision.route != route:
            rationale = f"Guardrail applied. {rationale}"

        return RouteDecision(
            route=route,
            risk_band=risk_band,
            should_alert=should_alert,
            rationale=rationale,
        )

    def _assess_risk(self, state: OrchestratorState) -> dict[str, Any]:
        event = state["event"]
        start = perf_counter()

        try:
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
                    try:
                        result = tool.invoke(call["args"])
                    except Exception as exc:
                        raise RuntimeError(f"Tool invocation failed: {call['name']}") from exc
                    tool_log.append({"tool": call["name"], "args": call["args"], "result": result})
                    messages.append(
                        ToolMessage(content=json.dumps({"result": result}), tool_call_id=call["id"])
                    )
                try:
                    response = self.llm_with_tools.invoke(messages)
                except Exception as exc:
                    raise RuntimeError("LLM tool-followup failed") from exc
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
                risk_score=self._clamp_score(assessment_data.risk_score),
                confidence=self._clamp_score(assessment_data.confidence),
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
            
        except Exception as exc:
            error_msg = f"assess_risk failed: {type(exc).__name__}: {str(exc)}"
            self.logger.error(error_msg, exc_info=True)
            return {"error": error_msg}

    def _decide_route(self, state: OrchestratorState) -> dict[str, Any]:
        assessment = state["assessment"]
        event = state["event"]
        policy_context = state.get("policy_context", [])
        
        if assessment is None:
            error_msg = "Missing assessment state in decide_route"
            self.logger.error(error_msg)
            return {"error": error_msg}

        payload = {
            "altitude_ft": event.altitude_ft,
            "vertical_speed_fps": event.vertical_speed_fps,
            "predicted_altitude_ft": round(assessment.predicted_altitude_ft, 2),
            "ceiling_ft": round(assessment.ceiling_ft, 2),
            "risk_score": round(assessment.risk_score, 3),
            "confidence": round(assessment.confidence, 3),
            "policy_context": self._format_policy_context(policy_context),
        }

        start = perf_counter()
        try:
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
                
            llm_decision = self._guard_decision(llm_decision, assessment.risk_score)

            trace = self._append_trace(
                state["trace"],
                "decide_route",
                payload,
                {
                    "route": llm_decision.route,
                    "risk_band": llm_decision.risk_band,
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
            
        except Exception as exc:
            error_msg = f"decide_route failed: {type(exc).__name__}: {str(exc)}"
            self.logger.error(error_msg, exc_info=True)
            return {"error": error_msg}

    def _emit_decision(self, state: OrchestratorState) -> dict[str, Any]:
        event = state["event"]
        assessment = state["assessment"]
        llm_decision = state["llm_decision"]
        if assessment is None or llm_decision is None:
            raise ValueError("Missing decision state")


        # If HITL approval was completed, mark as complete (simulate HITL queue completion)
        hitl_approval_needed = state.get("hitl_approval_needed", True)
        if llm_decision.route == "hitl_review" and not hitl_approval_needed:
            message = (
                f"HITL approval complete. Risk score {llm_decision.risk_band}: {assessment.risk_score:.2f}. "
                f"Operator approved. Predicted: {assessment.predicted_altitude_ft:.1f}ft vs Ceiling: {assessment.ceiling_ft:.1f}ft."
            )
            status = "approved"
        elif llm_decision.route == "hitl_review":
            message = (
                f"Risk score {llm_decision.risk_band}: {assessment.risk_score:.2f}. "
                f"Routed to operator review. Predicted: {assessment.predicted_altitude_ft:.1f}ft vs Ceiling: {assessment.ceiling_ft:.1f}ft."
            )
            status = "reviewing"
        elif llm_decision.should_alert:
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
            risk_band=llm_decision.risk_band,
            risk_score=assessment.risk_score,
            confidence=assessment.confidence,
            should_alert=llm_decision.should_alert,
            rationale=llm_decision.rationale,
            trace_id=state["trace_id"] if self.trace_enabled else None,
            trace=[asdict(step) for step in trace] if self.trace_enabled else None,
        )

        return {"decision": decision, "trace": trace}

    def _hitl_approval(self, state: OrchestratorState) -> dict[str, Any]:
        """HITL approval state - simulates human review for demo purposes.
        
        In production, this would wait for operator input via API/UI.
        For demo, auto-approves with logged note.
        """
        event = state["event"]
        assessment = state["assessment"]
        llm_decision = state["llm_decision"]
        
        if assessment is None or llm_decision is None:
            raise ValueError("Missing state for HITL approval")
        
        start = perf_counter()
        
        # Log HITL checkpoint
        self.logger.info(
            f"HITL checkpoint: drone_id={event.drone_id}, "
            f"risk={assessment.risk_score:.2f}, confidence={assessment.confidence:.2f}, "
            f"route={llm_decision.route}"
        )
        
        # Simulate approval (in production, this would await operator input)
        approval_status = "approved"  # Could be: approved, rejected, escalated
        
        trace = self._append_trace(
            state["trace"],
            "hitl_approval",
            {
                "risk_score": assessment.risk_score,
                "confidence": assessment.confidence,
                "route": llm_decision.route,
            },
            {"approval_status": approval_status},
            start,
        )
        
        return {"trace": trace, "hitl_approval_needed": False}

    def _handle_error(self, state: OrchestratorState) -> dict[str, Any]:
        """Handle errors gracefully with logging and fallback decision."""
        event = state["event"]
        error_msg = state.get("error", "Unknown error")
        
        self.logger.error(
            f"Orchestrator error for drone_id={event.drone_id}: {error_msg}",
            exc_info=True
        )
        
        # Create fallback decision
        decision = AlertDecision(
            drone_id=event.drone_id,
            status="error",
            message=f"Processing error: {error_msg}. Manual review required.",
            route="hitl_review",
            risk_band="HIGH",
            risk_score=1.0,
            confidence=0.0,
            should_alert=True,
            rationale="Error recovery: escalating to human review.",
            trace_id=state["trace_id"] if self.trace_enabled else None,
            trace=[asdict(step) for step in state["trace"]] if self.trace_enabled else None,
        )
        
        return {"decision": decision}

    def get_graph_diagram(self) -> bytes:
        """Generate Mermaid diagram as PNG bytes from the compiled LangGraph state machine."""
        return self.graph.get_graph().draw_mermaid_png()

    def save_graph_diagram(self, output_path: str = "diagrams/langgraph-state-actual.png") -> str:
        """Save the LangGraph state diagram to a PNG file.
        
        Returns:
            Absolute path to the saved diagram file.
        """
        diagram_bytes = self.get_graph_diagram()
        abs_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            f.write(diagram_bytes)
        return abs_path

    def process_event(
        self, event: TelemetryEvent
    ) -> tuple[AlertDecision, RiskAssessment, list[str], float]:
        start = perf_counter()
        initial_state: OrchestratorState = {
            "event": event,
            "assessment": None,
            "policy_context": [],
            "llm_decision": None,
            "decision": None,
            "trace": [],
            "trace_id": str(uuid4()),
            "error": None,
            "hitl_approval_needed": False,
        }
        final_state = self.graph.invoke(initial_state)
        latency_ms = (perf_counter() - start) * 1000
        decision = final_state["decision"]
        assessment = final_state.get("assessment")
        policy_context = final_state.get("policy_context", [])
        if decision is None:
            raise ValueError("Missing decision output")
        return decision, assessment, policy_context, latency_ms
