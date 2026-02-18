# End-to-End Flow: UI → Orchestrator → LangGraph → LangChain (LLM + Tools)

This document explains the **runtime flow** of the FAA Altitude Warning demo from the **Streamlit UI** through the **Orchestrator** and into the **LangGraph + LangChain** execution path.

---

## 1. Entry Point: User Action in the Streamlit UI

1. User selects a scenario in the Streamlit dropdown.
2. User clicks **Analyze scenario events**.
3. The UI loads scenario telemetry events from disk.
4. The UI initializes the Orchestrator (LangGraph-based state machine).
5. The UI iterates through each telemetry event and sends it to the Orchestrator for processing.

---

## 2. UI Call into Orchestrator

For each telemetry event:

1. Streamlit calls:

   - `orchestrator.process_event(event)`

2. `process_event()` constructs the LangGraph state payload:

   - `initial_state = { event, assessment=None, policy_context=[], llm_decision=None, trace=[], ... }`

3. `process_event()` invokes the LangGraph state machine:

   - `final_state = self.graph.invoke(initial_state)`

At this point:
- **LangGraph orchestrates the workflow**
- **LangChain is used inside LangGraph nodes for model calls, tool execution, and structured outputs**

---

## 3. LangGraph Orchestration (State Machine)

The compiled LangGraph runs these nodes in order:

1. `assess_risk(state)`
2. `retrieve_policy(state)`
3. `decide_route(state)`
4. conditional route:
   - `hitl_approval(state)` OR
   - `emit_decision(state)` OR
   - `handle_error(state)`
5. END

---

## 4. Inside LangGraph Nodes: Where LangChain Runs

### Node 1: assess_risk(state)

Purpose:
- Use the LLM (with optional tool calling) to produce a **RiskAssessment**.

Key LangChain behavior:
1. Build a messages list:
   - `SystemMessage(...)`
   - `HumanMessage(...)`

2. Call the model:
   - `response = self.llm_with_tools.invoke(messages)`

3. If the model requests tools (`response.tool_calls`):
   - Run each tool:
     - `result = tool.invoke(call["args"])`
   - Append observations:
     - `ToolMessage(...)`
   - Call the LLM again with updated messages:
     - `response = self.llm_with_tools.invoke(messages)`

4. Parse the final LLM output JSON into:
   - `LLMAssessment` → `RiskAssessment`

Output written back to state:
- `assessment`
- `trace` (if enabled)

---

### Node 2: retrieve_policy(state)

Purpose:
- Retrieve policy snippets relevant to this event and assessment.

Key retrieval behavior:
1. Build a query string using:
   - altitude
   - vertical speed
   - predicted altitude
   - ceiling

2. Call policy retrieval:
   - `snippets = retrieve_policy_context(query)`

3. Format into citation-style chunks:
   - `[S1] [source p.page] ...`

Output written back to state:
- `policy_context`
- `trace` (if enabled)
- error captured and logged if retrieval fails (graceful degradation)

---

### Node 3: decide_route(state)

Purpose:
- Use structured output to produce a **RouteDecision**.

Key LangChain behavior:
1. Prepare payload:
   - telemetry fields
   - assessment fields
   - `policy_context` text block

2. Run the chain:
   - `raw_decision = self.chain.invoke(payload)`

Where `self.chain` is built as:
- `prompt | llm.with_structured_output(RouteDecision)`

3. Apply guardrails:
- validate allowed values for `risk_band` and `route`
- enforce citations in rationale
- route to HITL if inconsistent (e.g., HIGH risk but no alert)

Output written back to state:
- `llm_decision`
- updated `assessment` (now includes route + should_alert)
- `trace` (if enabled)

---

## 5. LangGraph Conditional Routing

After `decide_route`, LangGraph chooses the next node:

1. If state has error → `handle_error`
2. Else if decision route is `hitl_review` → `hitl_approval`
3. Else if (risk_score > 0.7 AND confidence < 0.6) → `hitl_approval`
4. Else → `emit_decision`

---

## 6. Output Nodes

### Node: hitl_approval(state) (demo simulation)

Purpose:
- Simulate an operator review checkpoint.

Behavior:
- Logs a HITL checkpoint
- Marks HITL approval as complete for demo purposes
- Writes back:
  - `hitl_approval_needed = False`
  - trace step

---

### Node: emit_decision(state)

Purpose:
- Produce the final **AlertDecision**.

Behavior:
- Builds status + message based on:
  - route
  - should_alert
  - assessment scores
- Attaches trace and trace_id if enabled

Output written back to state:
- `decision`

---

### Node: handle_error(state)

Purpose:
- Fail safely.

Behavior:
- Logs error
- Creates fallback decision:
  - route = `hitl_review`
  - risk_band = `HIGH`
  - should_alert = True
  - rationale indicates error recovery

Output written back to state:
- `decision`

---

## 7. Returning to the UI

1. `process_event()` returns:
   - `decision`
   - `assessment`
   - `policy_context`
   - `latency_ms`

2. Streamlit aggregates per-event outputs into:
   - Results table
   - Optional trace views
   - Optional CSV export

---

## 8. Key Takeaways
- **LangGraph orchestrates the workflow** as a state machine over `TelemetryEvent → Assessment → Policy Context → Decision`.
- **Within nodes, LangChain execute model calls, tool calling loops, and structured output parsing** to generate traceable routing decisions.
