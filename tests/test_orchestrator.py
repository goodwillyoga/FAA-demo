from langchain_core.language_models.fake import FakeListLLM

from altitude_warning.models import TelemetryEvent
from altitude_warning.orchestrator import Orchestrator


def test_orchestrator_emits_alert_for_projected_breach() -> None:
    llm = FakeListLLM(
        responses=[
            '{"predicted_altitude_ft":308.0,"ceiling_ft":300.0,"risk_score":0.85,"confidence":0.7}',
            '{"route":"auto_notify","risk_band":"HIGH","should_alert":true,"rationale":"Projected ceiling breach."}',
        ]
    )
    orch = Orchestrator(llm=llm, enable_policy_retrieval=False)
    
    # For Live test: ***use the integration test and not this unit test***
    #     remove llm parameter, ensure .env has OPENAI_API_KEY set
    #.    orch = Orchestrator(
    #               enable_policy_retrieval=True,  # Enable Weaviate policy RAG
    #               trace_enabled=True              # Enable LangSmith tracing (optional)
    #  )

    event = TelemetryEvent(
        drone_id="D-1",
        lat=37.62,
        lon=-122.35,
        altitude_ft=280.0,
        vertical_speed_fps=3.5,
        timestamp_iso="2026-02-13T00:00:00Z",
    )
    decision, assessment, policy_context, _latency_ms = orch.process_event(event)
    
    print(f"Decision: {decision}")
    print(f"\n✓ Policy context returned: {len(policy_context)} chunks")
    if policy_context:
        for chunk in policy_context[:2]:  # Print first 2
            print(f"  {chunk[:100]}...")
    print(f"Assessment: {assessment}")
        
    assert decision.status == "alerted"
    assert decision.route == "auto_notify"
    assert assessment.predicted_altitude_ft > assessment.ceiling_ft
    assert policy_context == []
