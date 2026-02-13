# Day-1 Execution Plan: FAA Agentic AI reference (2-Day Build)

## 1) Executive reference Concept
Build a local-first, simulated low-altitude safety system where autonomous agents ingest drone telemetry, enrich with geofence/ceiling/weather context, predict near-term risk, and issue operator alerts with human-in-the-loop (HITL) controls. The reference emphasizes auditable decision flow, measurable agent observability (latency/cost/quality), and FAA-relevant operational insights rather than production-scale completeness.

## 2) In Scope vs Out of Scope
| Area | In Scope (2 days) | Out of Scope (now) |
|---|---|---|
| Data | Simulated telemetry + synthetic weather + geofence/ceiling metadata | Live FAA/LAANC/Remote ID integrations |
| Agentic workflow | Multi-agent orchestration + retries + HITL gating | Full enterprise policy engine |
| Risk logic | Rule-based + one lightweight ML model | Advanced multi-objective optimization |
| UI | Live operator dashboard + technical trace panels | Full production design system |
| Observability | Agent traces, latency, cost proxy, quality metrics | Long-term SRE stack and on-call workflows |
| Deployment | Local MacBook runbook | Hardened cloud deployment/HA |

## 3) System Architecture and Agent Flow
## Components
- `Simulator Service`: emits telemetry events + scenario injectors (altitude breach, geofence incursion, weather surge)
- `Orchestrator Agent`: controls state machine, routing, retries, escalation, HITL checkpoints
- `Task Agents`: Ingestion, Enrichment, Risk Scoring, Recommendation, HITL, Observability
- `NoSQL Store`: event log, alert lifecycle, agent state, session history
- `Vector Store`: semantic retrieval for SOP snippets, prior incident summaries, rationale grounding
- `Dashboard App`: operator view + technical observability panel

## Event Flow
1. Simulator publishes telemetry event.
2. Orchestrator dispatches to Ingestion Agent (schema/quality checks).
3. Enrichment Agent attaches geofence, ceiling, weather features.
4. Risk Agent calculates severity and probability.
5. Recommendation Agent proposes next action and rationale.
6. Orchestrator decides: auto-notify operator or route to HITL if high-risk/low-confidence.
7. HITL action (approve/override/escalate) updates alert lifecycle.
8. Observability Agent logs traces, metrics, and outcome labels.

## 4) Feature to Stakeholder Value Mapping
| Feature | FAA Technical Value | reference Evidence |
|---|---|---|
| Altitude early warning | Proactive violation prevention | "Likely ceiling breach in 8s" alert with confidence |
| Geofence prediction | Better airspace compliance | Time-to-boundary forecast and breach countdown |
| Weather-amplified risk | Context-aware safety decisions | Risk score jump when gust scenario injected |
| Orchestrated agent routing | Robust autonomy under uncertainty | Retry/fallback + escalation trace |
| HITL approval workflow | Human governance and accountability | Approve/override actions with audit log |
| End-to-end observability | Engineering trust and operability | Agent-level latency, cost proxy, outcome metrics |

## 5) Tech Stack Decision Table
| Layer | Primary Choice (Local-First) | Why | Alternate | Tradeoff |
|---|---|---|---|---|
| Agent framework | `LangChain + LangGraph` | LangChain for tool/model abstractions; LangGraph for stateful, branching, resumable workflows | Autogen/CrewAI + custom state machine | Faster start in some cases, but less explicit graph-state control |
| Observability | `LangSmith` + local metrics (`Prometheus/Grafana` optional lightweight) | Strong agent trace UX for references; quick debugging of tool calls and paths | W&B Weave or Arize Phoenix | May be better for ML eval depth, but agent-flow UX/setup can vary |
| NoSQL | `MongoDB` (local Docker) | High-write event logging, flexible schema, alert lifecycle queries | `Redis` | Faster ephemeral state; weaker historical query ergonomics |
| Vector DB | `Qdrant` (local Docker) | Lightweight local semantic retrieval for rationale grounding | Chroma | Easy local use; typically less operational tooling than Qdrant |
| API layer | `FastAPI` | Fast local dev, async endpoints, easy integration | Flask | Simpler but less structured async patterns |
| Dashboard | `Streamlit + PyDeck/Plotly` | Fastest to deliver live map + control panels in 2 days | React + Mapbox | Better long-term UX, higher implementation time |
| Simulation | Python async generator + scenario injector | Fully controllable deterministic references | Kafka-based simulator | More realistic streaming complexity than needed in 2 days |

## 6) Why an Autonomous Orchestrator Agent Is Needed
A linear chain is insufficient for this reference because the workflow is conditional and stateful.

- Dynamic routing: high-severity events branch to HITL immediately; medium-risk events can auto-notify then monitor.
- Retry/fallback: if weather enrichment fails, orchestrator retries once, then degrades gracefully to rule-only risk mode.
- Confidence-aware policy: low-confidence recommendations require human confirmation before action.
- Lifecycle control: manages event states (`new -> assessed -> actioned -> verified -> closed`) with timestamps.
- Auditability: provides one authoritative decision timeline for FAA technical review.

Without an orchestrator, you can show inference; with an orchestrator, you show autonomous operations behavior.

## 7) Why Both NoSQL and Vector Store Are Needed
Both stores solve different problems in this architecture.

- NoSQL DB responsibilities:
  - High-throughput event ingest (`telemetry_events`)
  - Alert lifecycle (`alerts`, `status_history`)
  - Agent runtime/session state (`agent_runs`, retry metadata)
  - Time-window analytics and replay queries
- Vector store responsibilities:
  - Semantic retrieval of SOP guidance and prior incident narratives
  - Retrieval-augmented rationale generation ("similar past event" explanation)
  - Context injection for Recommendation Agent when writing action briefs

### Example queries
- NoSQL query: "Find all unresolved high-risk alerts in last 15 minutes near geofence A."
- Vector query: "Retrieve top 3 SOP/incident passages relevant to geofence incursion with high wind."

A single NoSQL store cannot do high-quality semantic similarity retrieval well; a standalone vector store is poor at lifecycle/event state queries.

## 8) Observability and KPI Plan
## Core KPIs
- Pipeline latency: p50/p95 end-to-end (ingest to alert)
- Agent latency: per-agent execution times
- Cost proxy: model tokens/tool calls per alert
- Alert quality: precision/recall against simulated ground truth labels
- HITL outcomes: approval rate, override rate, escalation rate
- Reliability: tool-call failure rate and retry recovery rate

## Minimum Observability Views
- Trace view: per-event agent graph with tool calls
- Operations panel: active alerts, unresolved count, average time-to-recommend
- Quality panel: confusion matrix snapshot from scenario runs
- Governance panel: HITL decisions with rationale and operator notes

## 9) Story Point Estimate (2-Day reference Scope)
Assumption: 1 story point ~= 1.5-2 focused engineering hours for this reference.

| Module | Story Points | Notes |
|---|---:|---|
| Project scaffolding + local run scripts | 2 | Repo structure, env config, make targets |
| Telemetry simulator + scenario injector | 4 | Includes altitude/geofence/weather scenario toggles |
| Orchestrator graph + state transitions | 5 | Branching, retries, escalation |
| Ingestion + enrichment agents | 4 | Schema checks + feature joins |
| Risk scoring agent (rules + ML stub) | 4 | Includes risk score outputs |
| Recommendation + HITL agent flow | 4 | Approve/override/escalate controls |
| NoSQL + vector integration | 3 | Minimal schemas and retrieval |
| Dashboard (map, alerts, trace panels) | 5 | Operator + technical tabs |
| Observability instrumentation | 3 | Traces, latency, cost proxy |
| reference fixtures + script + dry run | 2 | Deterministic run and backup recording |
| **Total** | **36 SP** | Aggressive but feasible for focused 2-day build |

## 10) Day-1 and Day-2 Build Plan
## Day-1 (Build Core Loop)
- Block 1 (2-3h): setup repo/runtime, env vars, local DB containers
- Block 2 (2h): telemetry simulator + scenario definitions
- Block 3 (2h): LangGraph orchestrator skeleton + agent interfaces
- Block 4 (2h): ingestion/enrichment agents + geofence/ceiling logic
- Block 5 (1-2h): rule-based risk scoring + alert object schema

Day-1 exit criteria:
- End-to-end pipeline runs for at least one scenario
- Alert generated and persisted with traceable state transitions

## Day-2 (Polish + Observability + reference)
- Block 1 (2h): recommendation + HITL approval/override paths
- Block 2 (2h): dashboard tabs (map, alerts, traces, metrics)
- Block 3 (1-2h): weather amplification + optional ML anomaly detector
- Block 4 (1h): KPI computation + quality metrics from simulated labels
- Block 5 (1-2h): dry runs, failure-path reference, backup recording

Day-2 exit criteria:
- Three scenarios reliably presentation-ready (altitude, geofence, weather)
- HITL and observability visible in UI
- 5-10 minute script executable without manual patching

## 11) reference Script (5-10 Minutes)
1. Open system overview: show architecture and agent graph.
2. Start telemetry simulation for normal traffic.
3. Inject geofence incursion scenario -> show predicted breach alert.
4. Inject altitude climb scenario -> show "breach in N seconds" warning.
5. Inject weather gust scenario -> show risk score amplification.
6. Show orchestrator branching to HITL for high-risk low-confidence case.
7. Operator approves/overrides recommendation.
8. Open trace panel: show tool/API calls and rationale chain.
9. Open KPI panel: latency, cost proxy, quality snapshot.
10. Close with roadmap: live feed integration and production hardening.

## 12) Risks and Contingencies
| Risk | Impact | Mitigation |
|---|---|---|
| UI complexity overruns | reference instability | Keep Streamlit tabs simple; prioritize alerts + trace panels |
| ML model underperforms | Confusing quality story | Default to rules baseline; present ML as optional enhancement |
| Observability setup friction | Lost technical credibility | Pre-wire minimal traces first; add richer panels after core loop |
| Store integration delays | Pipeline blockers | Start with NoSQL only; add vector retrieval in Day-2 |
| Local environment issues | Build delay | Keep Docker compose minimal; prepare AWS fallback path |

## 13) Figma and Dashboard Recommendation
- Figma free tier is suitable for mockups/storyboarding and stakeholder discussion.
- For live reference runtime, use Streamlit (or similar) since Figma is not an execution dashboard.
- Practical approach: create 1-2 Figma frames for "future polished UX" and run the live reference in Streamlit.

## 14) Minimal API Endpoints to Expose in reference
- `POST /sim/start` start scenario stream
- `POST /sim/inject/{scenario}` inject event type
- `GET /alerts/active` list active alerts
- `POST /hitl/{alert_id}/decision` approve/override/escalate
- `GET /metrics/summary` latency/cost/quality snapshot
- `GET /traces/{event_id}` agent/tool execution chain

This endpoint layer helps FAA technical reviewers inspect system behavior beyond UI-only storytelling.
