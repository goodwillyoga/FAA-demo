# Day-0 Analysis Prompt (Revised)

## Objective
You are a systems architect with FAA/UAS domain expertise. Evaluate **four candidate use cases** and recommend **one** for a stakeholder reference that best shows the **breadth and depth of an agentic AI solution** while remaining feasible to build within the stated timeline.

## Candidate Use Cases
1. **Low-Altitude UAS Traffic Management (UTM) & Safe Integration**
   - Real-time coordination for drone operations (typically below 400 ft), including conflict mitigation and risk management.
2. **UAS Facility Maps & Altitude Authorization Guidance**
   - Use FAA UAS Facility Maps and LAANC-related altitude ceilings to assess where operations can be auto-authorized vs. require further review.
3. **Remote ID Telemetry & Real-Time Positioning**
   - Ingest and operationalize Remote ID telemetry (location, altitude, velocity, unique ID) for situational awareness.
4. **Information-Centric NAS Integration (Manned + Unmanned)**
   - Fuse drone and manned-aircraft data to support a shared operational picture and automated conflict detection aligned with FAA’s long-term vision.

## What to Deliver
1. **Rank all 4 use cases (1 = best) with reasoning for each**.
2. For each use case, provide:
   - Problem value to FAA (safety, scalability, operational relevance)
   - Technical complexity (data ingestion, integration, modeling, orchestration)
   - Data readiness (availability, quality, timeliness)
   - reference feasibility (build effort, dependency risk, explainability)
   - Agentic AI depth (autonomous data gathering, tool use, reasoning, recommendations)
3. **Select one recommended use case** and defend it clearly.
4. Provide a **Day-0 to reference blueprint** for the recommended option:
   - MVP scope
   - Agent roles/workflows
   - Required data sources (e.g., Remote ID-like telemetry, facility maps, weather, ADS-B where applicable)
   - Key analytics (intrusion risk, altitude compliance, conflict likelihood)
   - Dashboard views and alerting behavior
   - Risks, assumptions, and mitigations
5. Include a short **executive narrative** suitable for FAA stakeholders.

## Evaluation Criteria (Use This Scoring)
Score each use case from 1-5 on:
- FAA mission alignment
- Safety impact
- Agentic AI breadth (multi-step autonomous workflow)
- Agentic AI depth (quality of reasoning and recommendations)
- Implementation feasibility within timeline
- Data accessibility and integration risk
- reference clarity for non-technical stakeholders

Provide a weighted recommendation with these default weights unless overridden:
- FAA mission alignment: 20%
- Safety impact: 20%
- Feasibility: 20%
- Agentic breadth/depth combined: 25%
- Data readiness: 10%
- reference clarity: 5%

## Constraints
- Safety-first framing.
- Emphasize operational realism over speculative capability.
- Clearly separate what is production-realistic vs. reference-simulated.
- Do not provide legal/regulatory advice; focus on architecture and decision support.

## Expected Output Format
1. Decision summary (recommended use case + why)
2. Ranking table (all 4 use cases)
3. Detailed reasoning by use case
4. Day-0 implementation plan for recommended use case
5. Open risks and required stakeholder decisions
