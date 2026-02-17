"""Streamlit demo UI for sUAS Altitude Warning System.

Real-time altitude risk assessment for small Unmanned Aircraft Systems (sUAS)
operating under 14 CFR Part 107. Runs process_event() directly through LangGraph orchestrator.

Interactive telemetry enhancements:
1) Telemetry attributes: do not display empty/None attributes in event cards / telemetry sections.
2) Event selection: use a dropdown (selectbox) instead of a slider.
3) Telemetry "Play" control: animates the marker along the projected path (t -> t+8s)
   for the *selected* event, before running the main orchestrator analysis.

Notes:
- Streamlit isn't a true real-time animation engine; the "Play" button uses a short,
  frame-by-frame loop (9 frames) that updates a placeholder chart.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

import streamlit as st
import plotly.graph_objects as go

# ----------------------------
# CSS loader (simple)
# ----------------------------

def _load_css(css_name: str = "demo_ui.css") -> None:
    """Load CSS from a file next to this script (default: demo_ui.css)."""
    try:
        css_path = Path(__file__).with_name(css_name)
        if css_path.exists():
            st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    except Exception:
        # Keep UI functional even if CSS is missing
        pass

from altitude_warning.orchestrator import Orchestrator
from altitude_warning.simulator import load_scenario_events

# ----------------------------
# Scenario discovery utilities
# ----------------------------

def get_scenarios_dir() -> Path:
    """Return path to scenarios directory.

    Assumes repo layout:
      <project_root>/
        src/altitude_warning/demo_ui.py
        data/scenarios/*.json
    """
    return Path(__file__).resolve().parents[2] / "data" / "scenarios"

def list_scenario_files() -> list[tuple[str, Path]]:
    """Return list of (display_name, file_path) tuples for available scenarios."""
    scenarios_dir = get_scenarios_dir()

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

def load_scenario_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_scenario_metadata(path: Path) -> dict[str, Any]:
    data = load_scenario_json(path)
    return {
        "description": data.get("description", "No description available"),
        "event_count": len(data.get("events", [])),
        "risk_category": data.get("risk_category", "UNKNOWN"),
        "faa_guidance": data.get("faa_guidance", ""),
        "scenario_id": data.get("scenario_id", path.stem),
        "ceiling_ft": data.get("ceiling_ft", None),
    }

def format_scenario_name(scenario_id: str) -> str:
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
    return scenario_id.replace("feature1_", "").replace("_", " ").title()

# ----------------------------
# Orchestrator processing
# ----------------------------

def process_scenario(
    scenario_path: Path,
    progress_callback=None,
    enable_retrieval: bool = False,
) -> list[dict[str, Any]]:
    orchestrator = Orchestrator(trace_enabled=True, enable_policy_retrieval=enable_retrieval)
    events = load_scenario_events(scenario_path)

    results: list[dict[str, Any]] = []
    for idx, event in enumerate(events, start=1):
        if progress_callback:
            progress_callback(idx, len(events), f"Processing Event {idx}/{len(events)}: {event.drone_id}")

        decision, assessment, _policy_context, latency_ms = orchestrator.process_event(event)
        results.append(
            {
                "event": event,
                "decision": decision,
                "assessment": assessment,
                "latency_ms": latency_ms,
            }
        )
    return results

def is_langsmith_enabled() -> bool:
    return bool(os.getenv("LANGCHAIN_API_KEY"))

# ----------------------------
# Helpers: "show only if not empty"
# ----------------------------

def _is_empty(val: Any) -> bool:
    """Treat None, empty string, and empty containers as empty. 0 is NOT empty."""
    if val is None:
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    if isinstance(val, (list, dict, tuple, set)) and len(val) == 0:
        return True
    return False

def _maybe_caption(label: str, val: Any, fmt: Optional[str] = None) -> None:
    """Write a caption only if val is not empty."""
    if _is_empty(val):
        return
    if fmt is not None and isinstance(val, (int, float)):
        st.caption(f"{label}: {val:{fmt}}")
    else:
        st.caption(f"{label}: {val}")

# ----------------------------
# Interactive telemetry plot
# ----------------------------

def _parse_ts(ts: str) -> datetime:
    # Handles timestamps like "2026-02-13T20:00:00Z"
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone(timezone.utc)

def _project_altitudes(event: Any, horizon_s: int = 8, step_s: int = 1) -> tuple[list[int], list[float]]:
    dts = list(range(0, max(1, horizon_s) + 1, max(1, step_s)))
    alt0 = float(getattr(event, "altitude_ft", 0.0) or 0.0)
    vz = float(getattr(event, "vertical_speed_fps", 0.0) or 0.0)
    proj = [alt0 + vz * dt for dt in dts]
    return dts, proj

def _event_label(i: int, e: Any) -> str:
    ts = getattr(e, "timestamp_iso", "")
    drone = getattr(e, "drone_id", "")
    alt = getattr(e, "altitude_ft", None)
    vz = getattr(e, "vertical_speed_fps", None)
    # Keep it compact and stable
    parts = [f"Event {i+1}"]
    if not _is_empty(drone):
        parts.append(str(drone))
    if not _is_empty(ts):
        parts.append(str(ts))
    if not _is_empty(alt):
        parts.append(f"alt={alt}ft")
    if not _is_empty(vz):
        parts.append(f"vz={vz}ft/s")
    return " • ".join(parts)

def render_telemetry_plot(
    events: list[Any],
    selected_idx: int,
    ceiling_ft: float,
    highlight_dt: Optional[int] = None,
) -> go.Figure:
    """Build Plotly figure. Optionally highlight a moving marker along the projection."""
    xs = []
    ys = []
    hover = []
    for e in events:
        t = _parse_ts(e.timestamp_iso)
        xs.append(t)
        ys.append(float(getattr(e, "altitude_ft", 0.0) or 0.0))

        # Only include non-empty fields in hover
        lines = []
        for k in ["drone_id", "altitude_ft", "vertical_speed_fps", "ground_speed_fps", "heading_deg", "wind_mps", "gust_mps"]:
            v = getattr(e, k, None)
            if not _is_empty(v):
                lines.append(f"{k}={v}")
        hover.append("<br>".join(lines) if lines else "Telemetry snapshot")

    idx = max(0, min(selected_idx, len(events) - 1))
    e0 = events[idx]
    t0 = _parse_ts(e0.timestamp_iso)

    dts, proj = _project_altitudes(e0, horizon_s=8, step_s=1)
    proj_x = [t0 + timedelta(seconds=dt) for dt in dts]

    fig = go.Figure()

    # Historical snapshots
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines+markers",
            name="Telemetry altitude",
            hovertext=hover,
            hoverinfo="text",
        )
    )

    # Selected snapshot marker
    fig.add_trace(
        go.Scatter(
            x=[t0],
            y=[float(getattr(e0, "altitude_ft", 0.0) or 0.0)],
            mode="markers",
            name="Selected snapshot",
            marker=dict(size=12),
            hovertext=[f"Selected event {idx+1}<br>{e0.timestamp_iso}"],
            hoverinfo="text",
        )
    )

    # Projection curve
    fig.add_trace(
        go.Scatter(
            x=proj_x,
            y=proj,
            mode="lines+markers",
            name="Projected (t+8s)",
            hoverinfo="skip",
        )
    )

    # Moving marker along projection (for Play)
    if highlight_dt is not None:
        dt_i = max(0, min(int(highlight_dt), len(dts) - 1))
        fig.add_trace(
            go.Scatter(
                x=[proj_x[dt_i]],
                y=[proj[dt_i]],
                mode="markers",
                name="Drone (playback)",
                marker=dict(size=14),
                hoverinfo="skip",
            )
        )

    # Ceiling line
    xmin = min(xs + [t0])
    xmax = max(xs + [proj_x[-1]])
    fig.add_trace(
        go.Scatter(
            x=[xmin, xmax],
            y=[ceiling_ft, ceiling_ft],
            mode="lines",
            name=f"Ceiling ({ceiling_ft:.0f} ft)",
            line=dict(dash="dash"),
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        height=380,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="Time (UTC)",
        yaxis_title="Altitude (ft AGL)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig

# ----------------------------
# Trace + decision card UI (minimal)
# ----------------------------

def get_trace_statistics(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {}
    all_steps = []
    step_timings: dict[str, list[float]] = {}

    for result in results:
        decision = result["decision"]
        if not getattr(decision, "trace", None):
            continue
        for step in decision.trace:
            step_name = step.get("name", "unknown")
            duration_ms = step.get("duration_ms", 0)
            all_steps.append((step_name, duration_ms))
            step_timings.setdefault(step_name, []).append(duration_ms)

    total_latency_ms = sum(r["latency_ms"] for r in results)
    return {
        "total_events": len(results),
        "total_steps": len(all_steps),
        "total_latency_ms": total_latency_ms,
        "step_timings": step_timings,
        "step_average_timings": {k: (sum(v) / len(v)) for k, v in step_timings.items()},
    }

def render_trace_analysis_tab(results: list[dict[str, Any]], show_langsmith: bool = False) -> None:
    if not results:
        st.info("No results available. Process a scenario first.")
        return

    st.markdown("### Execution summary")
    stats = get_trace_statistics(results)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Events", stats["total_events"])
    with c2:
        st.metric("Total Steps", stats["total_steps"])
    with c3:
        st.metric("Total Latency", f"{stats['total_latency_ms']:.2f} ms")
    with c4:
        avg = stats["total_latency_ms"] / max(1, stats["total_events"])
        st.metric("Avg/Event", f"{avg:.2f} ms")

    if show_langsmith and is_langsmith_enabled():
        st.info("LangSmith is enabled; runs will appear in your LangSmith project.")

def render_decision_card(result: dict[str, Any], event_num: int) -> None:
    decision = result["decision"]
    assessment = result["assessment"]
    latency_ms = result["latency_ms"]
    event = result["event"]

    route_emoji = {"monitor": "🟢", "auto_notify": "🟡", "hitl_review": "🔵"}.get(decision.route, "⚪")
    title = f"Event {event_num}: {event.drone_id} @ {event.timestamp_iso} | {route_emoji} {decision.route}"

    with st.expander(title, expanded=(event_num == 1)):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Risk Band", getattr(decision, "risk_band", ""))
        with c2:
            st.metric("Risk Score", f"{getattr(decision, 'risk_score', 0.0):.3f}")
        with c3:
            st.metric("Confidence", f"{getattr(decision, 'confidence', 0.0):.3f}")
        with c4:
            st.metric("Latency", f"{latency_ms:.2f} ms")

        if not _is_empty(getattr(decision, "message", "")):
            st.markdown("Decision message")
            st.info(getattr(decision, "message", ""), icon="ℹ️")

        st.markdown("Telemetry")
        _maybe_caption("Altitude (ft AGL)", getattr(event, "altitude_ft", None))
        _maybe_caption("Vertical speed (ft/s)", getattr(event, "vertical_speed_fps", None))
        _maybe_caption("Predicted (ft)", getattr(assessment, "predicted_altitude_ft", None), fmt=".1f")
        _maybe_caption("Ceiling (ft)", getattr(assessment, "ceiling_ft", None), fmt=".0f")

# ----------------------------
# Main UI
# ----------------------------

def main() -> None:
    st.set_page_config(page_title="🚁 Real-Time sUAS Telemetry to Risk Decision Workflow", page_icon="🚁", layout="wide")
    _load_css("demo_ui.css")

    st.title("🚁 sUAS Telemetry to Risk Decision Workflow")
    st.caption("Scenario-based telemetry to policy-constrained risk decisions")
    st.divider()

    # --- Scenario selection (single source of truth) ---
    scenarios = list_scenario_files()
    if not scenarios:
        st.error("No scenario files found in data/scenarios/")
        return

    scenario_options = {display_name: path for display_name, path in scenarios}
    scenario_names = list(scenario_options.keys())

    SCENARIO_KEY = "selected_scenario_name"
    if SCENARIO_KEY not in st.session_state:
        st.session_state[SCENARIO_KEY] = scenario_names[0]

    # One compact selector line; value persists via session_state key
    st.selectbox(
        label="Select scenario",
        options=scenario_names,
        key=SCENARIO_KEY,
        label_visibility="collapsed",
        help="Choose a scenario to view/run",
    )

    selected_name = st.session_state[SCENARIO_KEY]
    selected_path = scenario_options[selected_name]

    metadata = load_scenario_metadata(selected_path)
    ceiling_ft = float(metadata["ceiling_ft"] or 300.0)
    # Telemetry plot (no orchestrator needed)
    st.divider()
    st.subheader("Telemetry & linear projection")

    events = load_scenario_events(selected_path)
    if not events:
        st.info("Scenario has no telemetry events.")
        return

    # Event dropdown (instead of slider)
    labels = [_event_label(i, e) for i, e in enumerate(events)]
    label_to_idx = {labels[i]: i for i in range(len(labels))}
    selected_label = st.selectbox("Select event", options=labels, index=0)
    selected_event_idx = label_to_idx[selected_label]

    # Playback controls (just for telemetry section)
    if "telemetry_play_dt" not in st.session_state:
        st.session_state["telemetry_play_dt"] = None

    colA, colB, colC = st.columns([1, 1, 3])
    with colA:
        play = st.button("▶ Play (up to 8 seconds)", use_container_width=True)
    with colB:
        reset = st.button("⟲ Reset", use_container_width=True)

    if reset:
        st.session_state["telemetry_play_dt"] = None

    chart_ph = st.empty()

    if play:
        # Frame-by-frame update (9 frames). This blocks briefly but is reliable for a demo.
        import time
        for dt in range(0, 9):
            fig = render_telemetry_plot(events, selected_event_idx, ceiling_ft=ceiling_ft, highlight_dt=dt)
            chart_ph.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
            time.sleep(0.18)
        st.session_state["telemetry_play_dt"] = 8

    # If not playing, render static chart (or the last frame after play)
    if not play:
        fig = render_telemetry_plot(
            events,
            selected_event_idx,
            ceiling_ft=ceiling_ft,
            highlight_dt=st.session_state.get("telemetry_play_dt", None),
        )
        chart_ph.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})

    # Orchestrator section
    st.divider()
    st.subheader("Run analysis")

    col1, col2 = st.columns(2)
    with col1:
        enable_retrieval = st.checkbox(
            "Enable Policy Retrieval & LLM Re-ranking (requires Weaviate running)",
            value=False,
        )
    with col2:
        show_langsmith = st.toggle(
            "Show LangSmith Integration",
            value=is_langsmith_enabled(),
            disabled=not is_langsmith_enabled(),
        )
        st.session_state["show_langsmith"] = show_langsmith

    if st.button("Analyze scenario events", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(event_num: int, total: int, message: str) -> None:
            progress_bar.progress(event_num / max(total, 1))
            status_text.text(message)

        try:
            results = process_scenario(
                selected_path,
                progress_callback=update_progress,
                enable_retrieval=enable_retrieval,
            )
            st.session_state["results"] = results
            st.session_state["scenario_path"] = str(selected_path)
            progress_bar.progress(1.0)
            status_text.empty()
            st.success(f"Processed {len(results)} events successfully.")
        except Exception as e:
            st.error(f"Error processing scenario: {str(e)}")
            st.exception(e)

    if "results" in st.session_state and st.session_state.get("scenario_path") == str(selected_path):
        results = st.session_state["results"]
        tab1, tab2 = st.tabs(["Results", "Trace analysis"])
        with tab1:
            for idx, result in enumerate(results, start=1):
                render_decision_card(result, idx)
        with tab2:
            render_trace_analysis_tab(results, show_langsmith=st.session_state.get("show_langsmith", False))

if __name__ == "__main__":
    main()
