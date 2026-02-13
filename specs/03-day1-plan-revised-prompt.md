# Day-1 Plan Prompt (Revised v2)

## Objective
Create a **high-impact 2-day reference plan** for FAA technical stakeholders that showcases an **agentic AI system** for low-altitude drone safety monitoring using **simulated but realistic metadata-aligned data**.  
The goal is to show autonomous reasoning, human-in-the-loop (HITL) control, and measurable observability, not a production deployment.

## Use Case Anchor
**Remote ID Telemetry & Real-Time Positioning**

Core narrative: agents ingest telemetry, enrich with airspace/weather context, predict risk (including weather-amplified risk), trigger real-time operator alerts, escalate to oversight/HITL, and provide auditable reasoning + API/tool traces.

## Planning Deliverables
Generate a Day-1/Day-2 plan that includes:
1. What we will build in 2 days (scoped MVP)
2. reference storyline and technical walkthrough
3. Local MacBook-first architecture and stack
4. Explicit framework rationale (LangChain vs LangGraph)
5. Observability/tooling choices with alternatives and tradeoffs
6. Risks, fallback options, and non-goals
7. **Story point estimation** by module (with assumptions)
8. Hour-by-hour (or block-based) execution plan

## Required MVP Features
- Simulated telemetry stream: drone_id, lat/lon, altitude, speed, heading, timestamp
- Geofencing early warning: predicted boundary breach before event
- Altitude/ceiling early warning: projected violation in next N seconds
- Weather-amplified risk: gust/wind context modifies risk score
- Real-time operator alerting UI (simulated channel)
- HITL actioning: approve / override / escalate
- Technical trace visibility: agent calls, tools, and decision steps
- Observability panel: latency, cost, accuracy proxy, alert outcomes

## Agentic Architecture Requirements
Design explicit agents and handoffs:
- **Orchestrator Agent (autonomous control-plane)**
- Ingestion Agent
- Enrichment Agent (geospatial + weather)
- Risk Scoring Agent (rules + optional ML)
- Recommendation Agent
- HITL Agent
- Observability Agent

For each agent include:
- Inputs/outputs
- Trigger conditions
- Tool/API calls
- Failure modes and fallback behavior

## Mandatory Architecture Justifications
### A) Why an autonomous Orchestrator Agent is needed
Provide concrete justification tied to reference value:
- Dynamic routing between agents based on event severity/confidence
- Retry/fallback policy when tools fail or confidence is low
- HITL gating logic for high-risk decisions
- State-aware progression (detect -> assess -> recommend -> confirm -> close)
- Centralized traceability/audit for FAA technical review

Also explain why a simple linear chain is insufficient for this reference.

### B) Why both Vector Store and NoSQL DB are needed
Provide concrete division of responsibility:
- **NoSQL DB:** high-write telemetry/events, session/agent state, alert lifecycle, TTL/event replay
- **Vector Store:** semantic retrieval for SOPs, historical incident patterns, prior recommendations, rationale grounding
- Show query examples for each and why one store cannot efficiently replace the other in this architecture
- If scope pressure arises, define a Day-1 minimal path and Day-2 expansion path

## AI/ML Requirement
Include one lightweight ML option:
- Risk likelihood classifier (violation/conflict probability), or
- Telemetry anomaly detection (jump/spoof/dropout)

If ML is risky in Day-1, provide rule-based fallback and Day-2 ML upgrade path.

## Tech Stack Requirements (Local-First)
Primary stack proposal should include:
- Agent framework: LangChain + LangGraph
- Observability: LangSmith (or equivalent if unavailable)
- Data: open-source NoSQL + open-source vector store
- Dashboard/UI: practical local tool for live map + alerts + traces
- Simulation engine: synthetic telemetry + scenario injector

## Alternatives and Tradeoff Analysis
Compare at least one alternate stack:
- LangSmith vs Weights & Biases vs Arize (agent/ML observability)
- LangGraph orchestration vs non-LangGraph orchestration
- Include pros/cons, local setup complexity, reference reliability, and explainability impact

Also address:
- Figma free-tier suitability for this reference (mockups vs live dashboard)
- If Figma is not ideal for runtime reference, propose dashboard alternatives

## Constraints
- Total timeline: 2 days
- No live FAA feeds; simulated data only
- Local MacBook preferred; AWS fallback only if blocked
- Audience: FAA technical team (expects architecture/API-level depth)
- Clearly separate simulated assumptions from production extensions

## Expected Output Format
1. Executive reference concept (1 paragraph)
2. In-scope vs out-of-scope table
3. System architecture and agent flow
4. Feature-to-stakeholder-value mapping
5. Tech stack decision table (primary + alternatives)
6. Orchestrator justification section
7. Data store justification section (Vector + NoSQL)
8. Observability/KPI plan (cost, latency, quality, HITL outcomes)
9. Story point estimate table (by feature/module)
10. Day-1 build plan and Day-2 hardening plan
11. 5-10 minute reference script
12. Risks and contingency plan

## Success Criteria
- Clear autonomous orchestration + HITL behavior
- Transparent API/tool-call reasoning and audit trail
- Live alerts for geofence + altitude + weather-amplified risk
- Observable agent metrics (cost/latency/quality) in one view
- Delivery is credible within 2 days and extensible to production
