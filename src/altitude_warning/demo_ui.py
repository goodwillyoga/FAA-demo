"""Streamlit demo UI for sUAS Altitude Warning System.

Real-time altitude risk assessment for small Unmanned Aircraft Systems (sUAS)
operating under 14 CFR Part 107. Runs process_event() directly through LangGraph orchestrator.
"""

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st

from altitude_warning.orchestrator import Orchestrator
from altitude_warning.simulator import load_scenario_events


def get_scenarios_dir() -> Path:
    """Return path to scenarios directory."""
    return Path(__file__).resolve().parents[2] / "data" / "scenarios"


def list_scenario_files() -> list[tuple[str, Path]]:
    """Return list of (display_name, file_path) tuples for available scenarios."""
    scenarios_dir = get_scenarios_dir()
    
    # Map filenames to friendly display names
    scenario_files = [
        ("Altitude Breach (moderate climb)", "feature1_altitude_breach.json"),
        ("Ceiling Breach + Gusty Wind", "feature1_highriskceilingbreach_gustywind.json"),
        ("Low Ceiling + Poor Visibility", "feature1_highrisklow_ceiling_poorvisibility.json"),
        ("Rooftop Operations + High Wind", "feature1_highriskrooftop_highwind.json"),
        ("Steady Climb (safe margin)", "feature1_mediumrisk_steady_climb.json"),
        ("Stable Flight (low risk)", "feature1_lowrisk_stable_flight.json"),
    ]
    
    return [
        (display_name, scenarios_dir / filename)
        for display_name, filename in scenario_files
        if (scenarios_dir / filename).exists()
    ]


def load_scenario_metadata(path: Path) -> dict:
    """Load scenario JSON and extract metadata."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    
    return {
        "description": data.get("description", "No description available"),
        "event_count": len(data.get("events", [])),
        "risk_category": data.get("risk_category", "UNKNOWN"),
        "scenario_id": data.get("scenario_id", path.stem),
    }


def format_scenario_name(scenario_id: str) -> str:
    """Format scenario ID to readable name with proper whitespace and structure.
    
    Examples:
        'feature1_altitude_breach' → 'Altitude Breach'
        'feature1_highriskceilingbreach_gustywind' → 'High Risk – Ceiling Breach + Gusty Wind'
        'feature1_highrisklow_ceiling_poorvisibility' → 'High Risk – Low Ceiling + Poor Visibility'
    """
    # Direct mapping for non-standard scenarios (concatenated compound words)
    scenario_mappings = {
        "feature1_altitude_breach": "Altitude Breach",
        "feature1_highriskceilingbreach_gustywind": "High Risk – Ceiling Breach + Gusty Wind",
        "feature1_highrisklow_ceiling_poorvisibility": "High Risk – Low Ceiling + Poor Visibility",
        "feature1_highriskrooftop_highwind": "High Risk – Rooftop Operations + High Wind",
        "feature1_mediumrisk_steady_climb": "Medium Risk – Steady Climb",
        "feature1_lowrisk_stable_flight": "Low Risk – Stable Flight",
    }
    
    if scenario_id in scenario_mappings:
        return scenario_mappings[scenario_id]
    
    # Fallback: standard underscore-based formatting
    name = scenario_id.replace("feature1_", "").replace("_", " ").title()
    return name


def process_scenario(scenario_path: Path, progress_callback=None, enable_retrieval: bool = False) -> list[dict[str, Any]]:
    """Process all events in a scenario through the orchestrator.
    
    Args:
        scenario_path: Path to scenario JSON file
        progress_callback: Optional callback function(event_num, total, message) for UI updates
        enable_retrieval: Whether to enable Weaviate policy retrieval and LLM reranking
    
    Returns:
        List of result dictionaries containing decision, assessment, and trace data
    """
    # Enable trace to capture tool calls
    orchestrator = Orchestrator(trace_enabled=True, enable_policy_retrieval=enable_retrieval)
    events = load_scenario_events(scenario_path)
    
    results = []
    for idx, event in enumerate(events, start=1):
        if progress_callback:
            progress_callback(idx, len(events), f"Processing Event {idx}/{len(events)}: {event.drone_id}")
        
        decision, assessment, _policy_context, latency_ms = orchestrator.process_event(event)
        results.append({
            "event": event,
            "decision": decision,
            "assessment": assessment,
            "latency_ms": latency_ms,
        })
    
    return results


def is_langsmith_enabled() -> bool:
    """Check if LangSmith API is configured via LangChain environment variables."""
    return bool(os.getenv("LANGCHAIN_API_KEY"))


def get_trace_statistics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract aggregated trace statistics from all results."""
    if not results:
        return {}
    
    all_steps = []
    step_timings = {}
    
    for result in results:
        decision = result["decision"]
        if not decision.trace:
            continue
        for step in decision.trace:
            step_name = step.get("name", "unknown")
            duration_ms = step.get("duration_ms", 0)
            all_steps.append((step_name, duration_ms))
            
            if step_name not in step_timings:
                step_timings[step_name] = []
            step_timings[step_name].append(duration_ms)
    
    # Calculate aggregate stats
    stats = {
        "total_events": len(results),
        "total_steps": len(all_steps),
        "total_latency_ms": sum(r["latency_ms"] for r in results),
        "step_timings": step_timings,
        "step_average_timings": {
            step: sum(timings) / len(timings)
            for step, timings in step_timings.items()
        },
    }
    
    return stats


def render_trace_analysis_tab(results: list[dict[str, Any]], show_langsmith: bool = False) -> None:
    """Render comprehensive trace analysis tab with response design patterns.
    
    Args:
        results: List of processed event results
        show_langsmith: Whether to display LangSmith integration section
    """
    if not results:
        st.info("No results available. Process a scenario first.")
        return
    
    # Summary cards section
    st.markdown("### 📊 Execution Summary")
    
    stats = get_trace_statistics(results)
    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    
    with summary_col1:
        st.metric(
            "Total Events",
            stats["total_events"],
            help="Number of telemetry snapshots processed"
        )
    
    with summary_col2:
        st.metric(
            "Total Steps",
            stats["total_steps"],
            help="Total LangGraph node executions across all events"
        )
    
    with summary_col3:
        total_latency = stats["total_latency_ms"]
        st.metric(
            "Total Latency",
            f"{total_latency:.2f} ms",
            help="Combined latency for all events"
        )
    
    with summary_col4:
        avg_per_event = total_latency / stats["total_events"]
        st.metric(
            "Avg per Event",
            f"{avg_per_event:.2f} ms",
            help="Average latency per telemetry event"
        )
    
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### ⏱️ Step-wise Performance")
    
    if stats["step_average_timings"]:
        step_names = list(stats["step_average_timings"].keys())
        step_avgs = list(stats["step_average_timings"].values())
        
        # Create latency breakdown visualization
        col_viz, col_details = st.columns([2, 1])
        
        with col_viz:
            # Bar chart for latency breakdown
            step_data = {
                step: stats["step_average_timings"][step]
                for step in sorted(step_names, 
                                   key=lambda x: stats["step_average_timings"][x], 
                                   reverse=True)
            }
            
            # Simple visualization with columns
            st.markdown("**Average Time per Step (across all events)**")
            for step_name, avg_time in step_data.items():
                percentage = (avg_time / sum(step_data.values())) * 100
                col_step, col_bar = st.columns([2, 8])
                with col_step:
                    st.caption(step_name)
                with col_bar:
                    st.progress(percentage / 100.0)
                    st.caption(f"{avg_time:.2f} ms ({percentage:.1f}%)")
        
        with col_details:
            st.markdown("**Step Invocations**")
            for step_name in sorted(step_names):
                invocations = len(stats["step_timings"].get(step_name, []))
                min_time = min(stats["step_timings"].get(step_name, [0]))
                max_time = max(stats["step_timings"].get(step_name, [0]))
                st.metric(
                    step_name,
                    f"{invocations}x",
                    f"min: {min_time:.1f}ms, max: {max_time:.1f}ms",
                    label_visibility="collapsed"
                )
    
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 🔍 Detailed Trace Timeline")
    
    for idx, result in enumerate(results, start=1):
        decision = result["decision"]
        event = result["event"]
        
        with st.expander(f"Event {idx}: {event.drone_id} @ {event.timestamp_iso}", expanded=False):
            if decision.trace:
                trace_items = []
                cumulative_ms = 0
                
                for step in decision.trace:
                    step_name = step.get("name", "unknown")
                    duration_ms = step.get("duration_ms", 0)
                    cumulative_ms += duration_ms
                    
                    # Step emojis
                    step_emojis = {
                        "assess_risk": "📝",
                        "retrieve_policy": "🔍",
                        "decide_route": "🤖",
                        "hitl_approval": "👤",
                        "emit_decision": "✓",
                    }
                    emoji = step_emojis.get(step_name, "🔧")
                    
                    # Timeline item with bar
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.caption(f"{emoji} **{step_name}**")
                    with col2:
                        st.caption(f"{cumulative_ms:.0f}ms total")
                    with col3:
                        st.caption(f"+{duration_ms:.2f}ms")
            else:
                st.caption("No trace data")
    
    st.markdown("<hr style='margin: 0.15rem 0;'>", unsafe_allow_html=True)
    
    # LangSmith integration section
    if show_langsmith and is_langsmith_enabled():
        st.markdown("### 🔗 LangSmith Integration")
        st.info(
            "✅ LangSmith API is connected. LangGraph runs are automatically logged to your LangSmith project.\n\n"
            "View detailed traces at: https://smith.langchain.com/",
            icon="ℹ️"
        )
        st.markdown(
            "**What's being tracked:**\n"
            "- All LangGraph node executions (assess_risk, retrieve_policy, decide_route, emit_decision)\n"
            "- Tool calls and outputs (ceiling_tool, trajectory_tool, risk_tool, visibility_tool)\n"
            "- LLM inputs and responses\n"
            "- Full execution timings and error logs"
        )


def render_tool_trace(decision: Any) -> None:
    """Render tool call trace with calculations and formulas as collapsible sections."""
    if not decision.trace:
        st.caption("No trace data available")
        return
    
    # Map step names to emojis
    step_emojis = {
        "assess_risk": "📝",
        "retrieve_policy": "🔍",
        "decide_route": "🤖",
        "hitl_approval": "👤",
        "emit_decision": "✓",
    }
    
    for step in decision.trace:
        step_name = step.get("name", "unknown")
        inputs = step.get("inputs", {})
        outputs = step.get("outputs", {})
        duration_ms = step.get("duration_ms", 0)
        emoji = step_emojis.get(step_name, "🔧")
        
        # Create collapsible section for each step
        expander_title = f"{emoji} {step_name} `({duration_ms:.2f}ms)`"
        with st.expander(expander_title, expanded=False):
            if inputs or outputs:
                trace_col1, trace_col2 = st.columns(2)
                with trace_col1:
                    if inputs:
                        for key, val in inputs.items():
                            if isinstance(val, (int, float)):
                                st.code(f"{key} = {val:.2f}" if isinstance(val, float) else f"{key} = {val}", language="python")
                            elif isinstance(val, str) and len(str(val)) > 80:
                                st.code(f"{key} = {str(val)[:100]}...", language="python")
                            else:
                                st.code(f"{key} = {val}", language="python")
                with trace_col2:
                    if outputs:
                        for key, val in outputs.items():
                            if key == "tool_calls" and isinstance(val, list):
                                # Show tool call results
                                for tool_call in val:
                                    tool_name = tool_call.get("tool", "")
                                    result = tool_call.get("result", {})
                                    st.code(f"{tool_name}: {result}", language="json")
                            elif isinstance(val, (int, float)):
                                st.code(f"{key} = {val:.3f}" if isinstance(val, float) else f"{key} = {val}", language="python")
                            elif isinstance(val, str) and len(str(val)) > 80:
                                st.code(f"{key} = {str(val)[:100]}...", language="python")
                            else:
                                st.code(f"{key} = {val}", language="python")
            
            # Add formula explanations for risk scoring
            if step_name == "assess_risk" and "risk_score" in outputs:
                with st.expander("📊 Risk Calculation Formula"):
                    st.latex(r"\text{risk\_score} = \begin{cases} 0.82 + \min(0.15, \text{margin\_ratio} \times 2) + 0.05 \times \text{climb\_factor} & \text{if predicted > ceiling} \\ 0.55 + \text{margin\_ratio} + 0.2 \times \text{climb\_factor} & \text{otherwise} \end{cases}")
                    st.caption("Where: margin_ratio = (predicted_altitude - ceiling) / ceiling")
                    st.caption("climb_factor = max(vertical_speed, 0) / 10.0")
def render_decision_card(result: dict[str, Any], event_num: int) -> None:
    """Render a decision card for a single event result."""
    decision = result["decision"]
    assessment = result["assessment"]
    latency_ms = result["latency_ms"]
    event = result["event"]
    
    # Route color coding - blue/green professional palette
    route_colors = {
        "monitor": "🟢",          # Green for monitoring
        "auto_notify": "🟡",       # Yellow for auto-alert
        "hitl_review": "🔵",      # Blue for human review
    }
    route_emoji = route_colors.get(decision.route, "⚪")
    
    # Risk band styling with professional colors
    risk_band_colors = {
        "LOW": "#d1fae5",         # Green background
        "MED": "#fef3c7",         # Yellow background
        "MEDIUM": "#fef3c7",      # Yellow background
        "HIGH": "#fee2e2",        # Light red only for HIGH risk
    }
    risk_bg = risk_band_colors.get(decision.risk_band, "#f3f4f6")
    
    # Risk text color - red only for HIGH risk
    risk_text_color = "#dc2626" if decision.risk_band == "HIGH" else "#374151"
    
    # Create collapsible card with better layout
    card_title = f"Event {event_num}: {event.drone_id} @ {event.timestamp_iso} | {route_emoji} {decision.route.replace('_', ' ').title()} | Risk Score: {decision.risk_score:.3f}"
    
    with st.expander(card_title, expanded=(event_num == 1)):
        # Main metrics row - use responsive columns
        metric_cols = st.columns(5, gap="medium")
        
        with metric_cols[0]:
            st.metric(
                label="Route",
                value=f"{route_emoji} {decision.route.replace('_', ' ').title()}"
            )
        
        with metric_cols[1]:
            st.metric(
                label="Risk Score",
                value=f"{decision.risk_score:.3f}"
            )
        
        with metric_cols[2]:
            st.metric(
                label="Confidence",
                value=f"{decision.confidence:.3f}"
            )
        
        with metric_cols[3]:
            st.markdown(
                f'<div style="background-color: {risk_bg}; padding: 1rem; border-radius: 0.5rem; text-align: center; border-left: 4px solid {risk_text_color};">'
                f'<strong style="color: {risk_text_color}; font-size: 1.1rem;">{decision.risk_band}</strong>'
                f'<div style="font-size: 0.85rem; color: var(--gray-600); margin-top: 0.25rem;">Risk Band</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        
        with metric_cols[4]:
            # Status reflects the route decision, not should_alert
            if decision.route == "hitl_review":
                status_icon = "🔄"
                status_text = "Operator Review"
                status_color = "#3b82f6"  # Blue
            elif decision.route == "auto_notify":
                status_icon = "🚨" if decision.should_alert else "✓"
                status_text = "ALERTED" if decision.should_alert else "Monitoring"
                status_color = "#dc2626" if decision.should_alert else "#059669"  # Red or Green
            else:  # monitor
                status_icon = "✓"
                status_text = "Monitoring"
                status_color = "#059669"  # Green
            
            st.markdown(
                f'<div style="background-color: #f0f9ff; padding: 1rem; border-radius: 0.5rem; text-align: center; border-left: 4px solid {status_color};">'
                f'<div style="font-size: 0.85rem; color: var(--gray-600); margin-bottom: 0.5rem;">Status</div>'
                f'<div style="font-size: 1.5rem; margin-bottom: 0.25rem;">{status_icon}</div>'
                f'<strong style="color: {status_color}; font-size: 0.95rem;">{status_text}</strong>'
                f'</div>',
                unsafe_allow_html=True
            )
        
        # Decision message area
        st.markdown("### Decision")
        st.info(decision.message, icon="ℹ️")
        
        # Details row with better proportions
        detail_col1, detail_col2 = st.columns([1.5, 1], gap="medium")
        
        with detail_col1:
            if decision.rationale:
                with st.expander("📝 Rationale & Analysis"):
                    st.markdown(decision.rationale)
            
            # Show tool trace in expandable section
            if decision.trace:
                with st.expander("🔍 Tool Call Trace & Calculations", expanded=False):
                    render_tool_trace(decision)
        
        with detail_col2:
            st.metric(label="Latency", value=f"{latency_ms:.2f} ms")
            st.markdown("### Telemetry" )
            st.caption(f"**Current Altitude:** {event.altitude_ft} ft AGL")
            st.caption(f"**Vertical Speed:** {event.vertical_speed_fps} ft/s")
            st.caption(f"**Predicted Alt:** {assessment.predicted_altitude_ft:.1f} ft")
            st.caption(f"**Ceiling:** {assessment.ceiling_ft:.0f} ft")
            margin = assessment.ceiling_ft - event.altitude_ft
            margin_color = "#059669" if margin > 0 else "#dc2626"
            st.markdown(f"<div style='color: {margin_color}; font-weight: bold;'>Margin: {margin:.1f} ft</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="sUAS Altitude Warning System",
        page_icon="�",
        layout="wide",
    )
    
    # Professional aviation UI with Bootstrap-inspired responsive design
    st.markdown("""
    <style>
    /* Root color scheme - Professional blue/green palette */
    :root {
        --primary-blue: #1e3a8a;
        --primary-blue-light: #3b82f6;
        --primary-blue-lighter: #dbeafe;
        --success-green: #059669;
        --success-green-light: #d1fae5;
        --warning-yellow: #f59e0b;
        --warning-yellow-light: #fef3c7;
        --danger-red: #dc2626;
        --danger-red-light: #fee2e2;
        --gray-50: #f9fafb;
        --gray-100: #f3f4f6;
        --gray-200: #e5e7eb;
        --gray-600: #4b5563;
        --gray-700: #374151;
    }
    
    /* Main page container - responsive layout */
    .main {
        overflow-x: hidden !important;
    }
    
    .block-container {
        padding: 1rem 2rem !important;
        max-width: 1600px !important;
    }
    
    /* Header styling */
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: var(--primary-blue);
        margin: 0 !important;
        padding: 0.5rem 0 !important;
        line-height: 1.1;
    }
    
    .sub-header {
        font-size: 0.95rem;
        color: var(--gray-600);
        margin: 0.25rem 0 0 0 !important;
        padding: 0 !important;
        line-height: 1.3;
    }
    
    /* Responsive columns with proper spacing */
    [data-testid="stColumn"] {
        gap: 1rem !important;
        padding: 0 0.5rem !important;
    }
    
    /* Section headers */
    h2, h3 {
        color: var(--primary-blue);
        font-weight: 600;
        margin: 0.8rem 0 0.5rem 0 !important;
        padding: 0 !important;
        line-height: 1.2;
        word-break: break-word;
        overflow-wrap: break-word;
    }
    
    h1 {
        margin: 0.5rem 0 0.3rem 0 !important;
        padding: 0 !important;
    }
    
    /* Metrics - proper sizing without truncation */
    [data-testid="stMetric"] {
        background: var(--gray-50);
        padding: 1rem !important;
        border-radius: 0.5rem;
        border-left: 4px solid var(--primary-blue-light);
        margin: 0.5rem 0 !important;
        min-height: 80px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        color: var(--gray-600);
        font-weight: 500;
        margin: 0 0 0.5rem 0 !important;
        padding: 0 !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--primary-blue);
        margin: 0 !important;
        padding: 0 !important;
        word-break: break-word;
        overflow-wrap: break-word;
    }
    
    /* Expanders with proper spacing */
    [data-testid="stExpander"] {
        border: 1px solid var(--gray-200) !important;
        border-radius: 0.5rem !important;
        margin: 0.5rem 0 !important;
        background: white;
    }
    
    [data-testid="stExpanderDetails"] {
        padding: 1.5rem !important;
    }
    
    /* Captions with proper wrapping */
    [data-testid="stCaption"] {
        font-size: 0.85rem;
        color: var(--gray-600);
        margin: 0.25rem 0 !important;
        padding: 0 !important;
        line-height: 1.4;
        word-break: break-word;
        overflow-wrap: break-word;
    }
    
    /* Dividers */
    hr {
        margin: 1rem 0 !important;
        border: none;
        border-top: 1px solid var(--gray-200);
        opacity: 1 !important;
    }
    
    /* Alert/info boxes */
    [data-testid="stAlert"] {
        border-radius: 0.5rem !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
        border-left: 4px solid var(--primary-blue-light);
    }
    
    /* Markdown text wrapping */
    [data-testid="stMarkdown"] {
        word-break: break-word;
        overflow-wrap: break-word;
        margin: 0.3rem 0 !important;
        padding: 0 !important;
    }
    
    [data-testid="stMarkdown"] p {
        margin: 0.2rem 0 !important;
        padding: 0 !important;
        word-break: break-word;
        overflow-wrap: break-word;
    }
    
    /* Code blocks */
    [data-testid="stCodeBlock"] {
        border-radius: 0.5rem !important;
        margin: 0.5rem 0 !important;
    }
    
    /* Selectbox and inputs */
    [data-testid="stSelectbox"],
    [data-testid="stTextInput"],
    [data-testid="stNumberInput"] {
        margin: 0.5rem 0 !important;
    }
    
    /* Buttons */
    button {
        border-radius: 0.5rem !important;
        font-weight: 500;
    }
    
    button[kind="primary"] {
        background-color: var(--primary-blue) !important;
        color: white;
    }
    
    button[kind="primary"]:hover {
        background-color: var(--primary-blue-light) !important;
    }
    
    /* Tabs */
    [data-testid="stTabs"] {
        margin: 1rem 0 !important;
    }
    
    /* Typography for better readability */
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
        line-height: 1.5;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="main-header">🚁 Unmanned Aircraft Altitude Warning System</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Prototype for real-time altitude risk assessment under 14 CFR Part 107 • Powered by LangGraph</div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    
    st.markdown("### 📂 Select Test Scenario")
    
    scenarios = list_scenario_files()
    if not scenarios:
        st.error("No scenario files found in data/scenarios/")
        return
    
    # Create dropdown with display names
    scenario_options = {display_name: path for display_name, path in scenarios}
    selected_name = st.selectbox(
        "Choose a scenario to run:",
        options=list(scenario_options.keys()),
        index=0,
    )
    
    selected_path = scenario_options[selected_name]
    
    # Clear cached results if scenario changes
    if "last_selected_scenario" in st.session_state:
        if st.session_state["last_selected_scenario"] != selected_name:
            if "results" in st.session_state:
                del st.session_state["results"]
    st.session_state["last_selected_scenario"] = selected_name
    
    # Display scenario metadata with enhanced styling
    metadata = load_scenario_metadata(selected_path)
    
    col1, col2 = st.columns(2)
    with col1:
        scenario_name = format_scenario_name(metadata["scenario_id"])
        st.metric("Test Case", scenario_name)
    with col2:
        st.metric("Telemetry Events", metadata["event_count"])
    
    with st.expander("📋 Scenario Details", expanded=False):
        st.markdown(f"**Description:**")
        st.markdown(metadata['description'])
        
        # Compact info box
        with st.expander("ℹ️ How it works (click to expand)"):
            st.markdown("""
            Each telemetry event is independently assessed by the orchestrator.  
            Event 1 might be HIGH risk while Event 2 could be LOW risk - it depends on altitude, 
            vertical speed, and predicted trajectory at that specific moment.
            """)
        
        # Preview all telemetry events
        events = load_scenario_events(selected_path)
        if events:
            st.markdown(f"**Telemetry Snapshots ({len(events)} events):**")
            for idx, event in enumerate(events, start=1):
                with st.container():
                    st.markdown(f"**Event {idx}:**")
                    detail_col1, detail_col2 = st.columns(2)
                    with detail_col1:
                        st.markdown(f"- **Aircraft ID:** `{event.drone_id}`")
                        st.markdown(f"- **Altitude:** {event.altitude_ft} ft AGL")
                        st.markdown(f"- **Vertical Speed:** {event.vertical_speed_fps} ft/s")
                    with detail_col2:
                        st.markdown(f"- **Position:** {event.lat:.4f}°N, {abs(event.lon):.4f}°W")
                        st.markdown(f"- **Timestamp:** {event.timestamp_iso}")
                    if idx < len(events):
                        st.markdown("<hr style='margin: 0.3rem 0;'>", unsafe_allow_html=True)
    
    st.markdown("<hr style='margin: 0.8rem 0;'>", unsafe_allow_html=True)
    
    # Run Analysis button and results
    st.markdown("### 🚀 Run Analysis")
    
    config_col1, config_col2 = st.columns(2)
    
    with config_col1:
        # Optional: Enable policy retrieval
        enable_retrieval = st.checkbox(
            "Enable Policy Retrieval & LLM Re-ranking (requires Weaviate running)",
            value=False,
            help="Retrieves 14 CFR Part 107 policy snippets from Weaviate and uses LLM to re-rank them for relevance"
        )
    
    with config_col2:
        # LangSmith toggle
        show_langsmith = st.toggle(
            "Show LangSmith Integration",
            value=is_langsmith_enabled(),
            disabled=not is_langsmith_enabled(),
            help="Display LangSmith tracing details (requires API key configured)"
        )
        st.session_state["show_langsmith"] = show_langsmith
    
    if st.button("▶️  Process Scenario Events", type="primary", use_container_width=True):
        # Create progress placeholder
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(event_num: int, total: int, message: str) -> None:
            progress = event_num / total
            progress_bar.progress(progress)
            status_text.text(message)
        
        try:
            results = process_scenario(selected_path, progress_callback=update_progress, enable_retrieval=enable_retrieval)
            st.session_state["results"] = results
            st.session_state["scenario_name"] = selected_name
            progress_bar.progress(1.0)
            status_text.empty()
            st.success(f"✅ Processed {len(results)} events successfully!")
        except Exception as e:
            st.error(f"❌ Error processing scenario: {str(e)}")
            st.exception(e)
    
    # Display results if available
    if "results" in st.session_state and st.session_state.get("scenario_name") == selected_name:
        st.markdown("<hr style='margin: 0.8rem 0;'>", unsafe_allow_html=True)
        
        results = st.session_state["results"]
        
        # Create tabs for Results and Trace Analysis
        tab1, tab2 = st.tabs(["📊 Results", "🔍 Trace Analysis"])
        
        with tab1:
            st.markdown("## Decision Cards")
            st.caption(f"Results for: {selected_name}")
            
            for idx, result in enumerate(results, start=1):
                render_decision_card(result, idx)
            
            # Summary at the bottom
            st.markdown("### 📈 Summary")
            summary_col1, summary_col2, summary_col3 = st.columns(3)
            
            routes = [r["decision"].route for r in results]
            alerts = sum(1 for r in results if r["decision"].should_alert)
            avg_latency = sum(r["latency_ms"] for r in results) / len(results)
            
            with summary_col1:
                st.metric("Total Events", len(results))
            with summary_col2:
                st.metric("Alerts Triggered", alerts)
            with summary_col3:
                st.metric("Avg Latency", f"{avg_latency:.2f} ms")
            
            route_counts = {route: routes.count(route) for route in set(routes)}
            st.markdown("**Routing Distribution:**")
            for route, count in route_counts.items():
                st.write(f"- {route.replace('_', ' ').title()}: {count}")
        
        with tab2:
            show_langsmith = st.session_state.get("show_langsmith", False)
            render_trace_analysis_tab(results, show_langsmith=show_langsmith)


if __name__ == "__main__":
    main()
