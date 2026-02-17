# FAA Altitude Early Warning Demo Guide

## Executive Summary
This guide covers the system architecture, data flow, tool suite, and test scenarios for the FAA demo.

- Early warning of altitude ceiling crossing
- Human-in-the-loop escalation for high risk
- Technical traceability and auditability

## System Architecture
- Telemetry ingestion → risk tools → policy retrieval → route decision (monitor, auto_notify, hitl_review)
- Deterministic tools for risk, trajectory, visibility
- LLM for routing and rationale

## Test Scenarios
- 5 FAA-guided scenarios (HIGH/MED/LOW risk)
- Policy integration and HITL flow

## How to Run
- See CONTRIBUTING.md for setup
- Run demo UI: ./scripts/run_demo_ui.sh
- Run all scenarios: pytest tests/test_orchestrator_scenario_sweep.py -v

## More Info
- For design, see DESIGN_GUIDE.md
- For developer info, see DEVELOPER_GUIDE.md
- For runbook, see RUNBOOK.md
