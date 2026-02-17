# FAA Altitude Early Warning Demo Guide

## Executive Summary

This document outlines the **Altitude Early Warning System** — a LangGraph-based autonomous agent that detects potential ceiling breaches in real-time and routes decisions to human operators (HITL) when confidence is insufficient.

**Key Differentiator:** Safety-critical computations (risk assessment, visibility impact) are executed via **deterministic tools**, not LLM reasoning, ensuring FAA auditability.

---

## 1. System Architecture

### Data Flow
```
Telemetry Event
    ↓
[assess_risk] → Tools: ceiling, trajectory, risk, visibility
    ↓
Risk Assessment (risk_score, confidence, predicted_altitude)
    ↓
[retrieve_policy] → Weaviate RAG (14 CFR Part 107 guidance)
    ↓
Policy Context [S1], [S2], [S3] citations
    ↓
[decide_route] → LLM routes to: hitl_review | auto_notify | monitor
    ↓
[conditional edge]
    ├─ risk > 0.8 → [hitl_approval] → operator review
    ├─ 0.6 < risk ≤ 0.8 → [auto_notify] → immediate alert
    └─ risk ≤ 0.6 → [monitor] → log without alert
    ↓
[emit_decision] → AlertDecision with trace, rationale, policy citations
    ✓ Complete trace logged to LangSmith
```

### State Machine (LangGraph)
- **6 Nodes:** assess_risk, retrieve_policy, decide_route, hitl_approval, emit_decision, handle_error
- **Conditional Edges:** Route based on risk_score and confidence thresholds
- **Error Handling:** Graceful degradation (policy retrieval fails → continue with empty context)
- **Tracing:** Full execution trace including tool calls, LLM decisions, latency

---

## 2. Tool Suite (Deterministic, FAA-Auditable)

### Tool 1: `ceiling_tool(lat, lon) → float`
**Purpose:** Retrieve ceiling altitude for the drone's current location.

**Implementation:** Deterministic lookup based on location coordinates.
- San Francisco Bay Area (lat > 37.6, lon < -122.2): **300ft** (restricted airspace)
- Default: **400ft** (standard Part 107 limit)

**FAA Value:** No API calls, no external dependencies, deterministic and repeatable.

---

### Tool 2: `trajectory_tool(current_altitude_ft, vertical_speed_fps, horizon_seconds=8) → float`
**Purpose:** Project future altitude based on current climb/descent rate.

**Formula:** `predicted_altitude = current_altitude + (vertical_speed_fps × horizon_seconds)`

**Example:**
- Current: 280ft, Climb rate: 3.5 ft/s, Horizon: 8s
- Projected: 280 + (3.5 × 8) = **308ft**

**FAA Value:** Physics-based, no black boxes, deterministic projection.

---

### Tool 3: `risk_tool(predicted_altitude_ft, ceiling_ft, vertical_speed_fps) → {risk_score, confidence}`
**Purpose:** Compute safety risk and decision confidence.

**Formula:**
```
margin_ratio = (predicted_altitude - ceiling) / ceiling
climb_factor = vertical_speed_fps / 10.0

IF projected_altitude > ceiling:
    risk_score = 0.82 + margin_ratio + 0.05×climb_factor  (breach imminent)
ELSE:
    risk_score = 0.55 + margin_ratio + 0.2×climb_factor   (safe but climbing)

confidence = 0.6 + 0.25×climb_factor  (higher climb = higher confidence in assessment)
```

**Example: Ceiling Breach (Scenario 1)**
- Predicted: 308ft, Ceiling: 300ft, Climb: 3.5 ft/s
- margin_ratio = (308 - 300) / 300 = 0.027
- climb_factor = 3.5 / 10 = 0.35
- risk_score = 0.82 + 0.027 + (0.05 × 0.35) = **0.85** (HIGH)
- confidence = 0.6 + (0.25 × 0.35) = **0.69**

**FAA Value:** Explicit formula, auditable coefficients, no LLM guessing.

---

### Tool 4: `visibility_tool(visibility_km) → {impact, confidence_reduction}`
**Purpose:** Assess environmental visibility impact on decision reliability.

**Classification:**
| Visibility | Impact | Confidence Penalty |
|-----------|--------|------------------|
| < 1.0 km | Critical | -35% |
| 1.0-3.0 km | Poor | -20% |
| 3.0-5.0 km | Marginal | -10% |
| > 5.0 km | Good | 0% |

**Example: Low Visibility (Scenario 2)**
- Visibility: 2.5 km (poor) → confidence_reduction = 0.20
- Original confidence from risk_tool: 0.70
- Adjusted confidence: 0.70 - (0.70 × 0.20) = **0.56** (below auto_notify threshold)
- **Result:** Routes to hitl_review instead of auto_notify

**FAA Value:** Environmental factors explicitly penalize confidence, forcing human review in marginal conditions.

---

## 3. Routing Rules (DECIDE_SYSTEM_PROMPT)

After risk assessment, the LLM routes decisions based on explicit thresholds:

```plaintext
IF risk_score > 0.8:
    route = "hitl_review"  # High risk, escalate to human operator
    should_alert = true

ELSE IF risk_score > 0.6 AND confidence >= 0.75:
    route = "auto_notify"  # Clear violation, high confidence
    should_alert = true

ELSE:
    route = "monitor"      # Low risk, continue monitoring
    should_alert = false
```

**Decision Rationale:** Includes citation tags [S1], [S2] from policy context (Weaviate retrieval).

---

## 4. Policy Integration (Weaviate RAG)

**Data Source:** 25 PolicyChunks ingested from FAA Part 107 Study Guide (14 CFR 107.19, altitude limits, operational safety).

**Retrieval Flow:**
1. Query Weaviate with telemetry context: altitude, ceiling, visibility, risk factors
2. Return top-3 relevant policy snippets with semantic reranking
3. Embed [S1], [S2], [S3] tags in decision rationale

**Example Decision with Citations:**
```
Route: hitl_review
Rationale: "Projected altitude 308ft exceeds ceiling 300ft, violating 14 CFR 107.19 altitude 
limit guidelines [S1]. Poor visibility 2.5 km reduces confidence below auto-alert threshold. 
Escalating to human review per operational safety protocols [S2]."
```

---

## 5. Test Scenarios (5 FAA-Guided Cases)

All scenarios use **gpt-4o-mini** with live LLM calls. Test data embedded in scenario JSON files under `data/scenarios/`.

### Scenario 1: HIGH RISK - Ceiling Breach with Gusty Wind
**File:** `feature1_highriskceilingbreach_gustywind.json`
- Drone ID: D-0001
- Altitude: 280→288ft
- Ceiling: 300ft (12-20ft margin)
- Vertical Speed: 3.5 ft/s
- Wind: 3.58-3.65 m/s (gusty), Visibility: 9.9+ km
- **Expected Route:** hitl_review | auto_notify
- **Expected Risk Score:** ~0.82+
- **Status:** ✅ PASSED

**Rationale:** Clear ceiling breach imminent, high confidence in assessment despite wind.

---

### Scenario 2: HIGH RISK - Narrow Margin + Poor Visibility
**File:** `feature1_highrisklow_ceiling_poorvisibility.json`
- Drone ID: D-0002
- Altitude: 280→289ft
- Ceiling: 300ft (11-20ft margin)
- Vertical Speed: 3.2 ft/s (faster climb)
- Wind: 4.47-4.92 m/s, **Visibility: 2.4-2.5 km (POOR)** ⚠️
- **Expected Route:** hitl_review (forced by poor visibility penalty)
- **Expected Risk Score:** ~0.80+
- **Confidence Impact:** visibility_tool reduces confidence by 20% → below auto_notify threshold
- **Status:** ✅ PASSED

**Rationale:** Even with moderate risk, poor visibility forces human review (cannot see obstacles).

---

### Scenario 3: HIGH RISK - Very Close to Ceiling + Extreme Wind
**File:** `feature1_highriskrooftop_highwind.json`
- Drone ID: D-0003
- Altitude: 290→298ft
- Ceiling: 300ft (only 2-10ft margin!)
- Vertical Speed: 2.8 ft/s
- **Wind: 6.71-7.15 m/s, Gust: 8.94-9.37 m/s (EXTREME)** ⚠️
- Visibility: 8.2-8.5 km (good)
- **Expected Route:** hitl_review | auto_notify
- **Expected Risk Score:** ~0.85+
- **Status:** ✅ PASSED

**Rationale:** Extreme wind at rooftop altitude reduces control authority. Operator must assess manual override feasibility.

---

### Scenario 4: MEDIUM RISK - Steady Climb, Good Conditions
**File:** `feature1_mediumrisk_steady_climb.json`
- Drone ID: D-0001
- Altitude: 260→272ft
- Ceiling: 400ft (128-140ft margin to breach)
- Vertical Speed: 1.5 ft/s (slow climb)
- Wind: 0.82-0.89 m/s (calm), Visibility: 10.0 km (excellent)
- **Expected Route:** monitor | auto_notify
- **Expected Risk Score:** ~0.60-0.70
- **Status:** ✅ PASSED

**Rationale:** Adequate safety margin with favorable conditions. Monitoring sufficient; no immediate alert.

---

### Scenario 5: LOW RISK - Stable Flight
**File:** `feature1_lowrisk_stable_flight.json`
- Drone ID: D-0001
- Altitude: 150→148ft (stable, slight descent)
- Ceiling: 400ft (250ft+ margin)
- Vertical Speed: 0 ft/s (horizontal flight)
- Wind: 0.45-0.50 m/s (calm), Visibility: 15.0 km (excellent)
- **Expected Route:** monitor
- **Expected Risk Score:** ~0.50 (LOW)
- **Status:** ✅ PASSED

**Rationale:** Well within ceiling, zero climb risk. Passive monitoring only.

---

## 6. Decision Trace & Logging

Each decision includes a complete execution trace:

```json
{
  "decision": {
    "drone_id": "D-0001",
    "route": "hitl_review",
    "risk_band": "HIGH",
    "risk_score": 0.85,
    "confidence": 0.69,
    "should_alert": true,
    "status": "alerted",
    "message": "Likely ceiling breach in 8s: projected 308ft vs ceiling 300ft",
    "rationale": "Projected altitude 308ft exceeds ceiling 300ft..."
  },
  "trace": [
    {
      "name": "assess_risk",
      "inputs": {...event telemetry...},
      "outputs": {
        "predicted_altitude_ft": 308.0,
        "ceiling_ft": 300.0,
        "risk_score": 0.85,
        "confidence": 0.69,
        "tool_calls": [
          {"tool": "ceiling_tool", "args": {...}, "result": 300.0},
          {"tool": "trajectory_tool", "args": {...}, "result": 308.0},
          {"tool": "risk_tool", "args": {...}, "result": {...}},
          {"tool": "visibility_tool", "args": {...}, "result": {...}}
        ]
      },
      "duration_ms": 2600.0
    },
    {
      "name": "retrieve_policy",
      "inputs": {"query": "FAA Part 107 guidance..."},
      "outputs": {...3 policy chunks with [S1] [S2] [S3] tags...},
      "duration_ms": 1500.0
    },
    {
      "name": "decide_route",
      "inputs": {"risk_score": 0.85, "confidence": 0.69, ...},
      "outputs": {"route": "hitl_review", "should_alert": true, ...},
      "duration_ms": 800.0
    },
    {
      "name": "hitl_approval",
      "inputs": {"route": "hitl_review", ...},
      "outputs": {"approval_status": "approved"},
      "duration_ms": 200.0
    },
    {
      "name": "emit_decision",
      "outputs": {"status": "alerted"},
      "duration_ms": 50.0
    }
  ],
  "latency_ms": 5150.0
}
```

**Logging:** File-based logs in `logs/orchestrator_YYYYMMDD.log` + LangSmith traces (if `LANGCHAIN_API_KEY` set).

---

## 7. HITL Approval Flow

**Trigger Condition:** `route == "hitl_review"` (risk > 0.8 or risk > 0.7 & confidence < 0.65)

**Current Implementation (Demo):** Auto-approves with log checkpoint.
```python
INFO orchestrator: HITL checkpoint: drone_id=D-0001, risk=0.85, confidence=0.69, route=hitl_review
```

**Production Implementation (Future):** 
- Queue decision to operator dashboard
- Wait for human approval (timeout: 30s)
- Log operator decision + timestamp
- If timeout: escalate to supervisor

---

## 8. Running the Demo

### Setup
```bash
source scripts/demo_faa_setup.sh
```

### Test All 5 Scenarios
```bash
pytest tests/test_orchestrator_scenario_sweep.py -v
```

**Output:** Baseline CSV file in `outputs/scenario_sweep_baseline_YYYYMMDDTHHMMSSZ.csv`

Example row:
```
scenario_id,risk_category,route,risk_score,confidence,should_alert,policy_chunks_retrieved,latency_ms
feature1_highrisklow_ceiling_poorvisibility,HIGH,hitl_review,0.81,0.58,True,3,7500
```

### Test Individual Scenario
```bash
pytest tests/test_orchestrator_scenario_sweep.py::test_scenario_sweep_with_live_llm[data/scenarios/feature1_highriskceilingbreach_gustywind.json-HIGH-expected_route_in0] -v -s
```

---

## 9. Key Design Decisions

| Decision | Rationale | FAA Value |
|----------|-----------|-----------|
| **Tools over LLM reasoning** | Deterministic safety calculations | Auditable, repeatable, no black boxes |
| **Weaviate RAG for policy** | Cited guidance in rationale | Traceability to 14 CFR Part 107 |
| **HITL approval for risk > 0.8** | Human operator as final arbiter | Safety redundancy, operator authority |
| **Visibility penalty via tool** | Environmental factors explicit | Marginal conditions don't mask poor decisions |
| **8-second horizon** | Typical drone reaction time | Realistic early warning window |
| **Deterministic ceiling tool** | No API dependencies | Repeatable for demos |

---

## 10. Future Enhancements

1. **Real Weather APIs** (NOAA, FAA) for ceiling/visibility
2. **Operator Dashboard** (Streamlit) with real-time alerts + HITL queue
3. **Async HITL** with approval timeout and escalation
4. **Wind Safety Margin Tool** (headwind/tailwind impact on control)
5. **Multi-drone coordination** (airspace conflict detection)
6. **Regulatory compliance audit** (trace-to-CFR mappings)

---

## Questions?

Contact: Pooja Singh  
Technical review: [docs/PYTHON_SETUP.md](PYTHON_SETUP.md) | [docs/data_schema.md](data_schema.md)  
Architecture: [diagrams/langgraph-state-flow.mmd](../diagrams/langgraph-state-flow.mmd)
