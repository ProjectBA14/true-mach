"""Gemini-Style Single-Column Streamlit Interface for AeroGuard-RAG."""

from __future__ import annotations
import os
from pathlib import Path
import streamlit as st

from src.gatekeeper.schemas import AircraftDesignState
from src.orchestrator import process_user_turn

# 1. Page Configuration
st.set_page_config(
    page_title="AeroGuard-RAG | Aerospace Workstation",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Gemini-Inspired Dark Theme CSS
st.markdown(
    """
    <style>
    /* Dark canvas & typography */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #131314 !important;
        color: #E3E3E3 !important;
        font-family: 'Google Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }
    
    /* Center main chat container at max 780px with natural page scrolling */
    .main .block-container {
        max-width: 780px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 7.5rem !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }

    /* Hide default header background & Streamlit footer */
    header[data-testid="stHeader"] {
        background-color: rgba(19, 19, 20, 0.85) !important;
        backdrop-filter: blur(12px) !important;
    }
    footer {
        visibility: hidden !important;
    }

    /* Collapsible Left Sidebar (#1E1F20) */
    section[data-testid="stSidebar"] {
        background-color: #1E1F20 !important;
        border-right: 1px solid #2D2F31 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stSidebarContent"] {
        background-color: #1E1F20 !important;
        padding: 1.25rem 1rem !important;
    }

    /* Parameter Chips in Sidebar */
    .sidebar-chip {
        background-color: #282A2C;
        color: #C4C7C5;
        padding: 7px 12px;
        border-radius: 12px;
        font-size: 0.82rem;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid #3C4043;
    }
    .sidebar-chip span {
        color: #9AA0A6;
    }
    .sidebar-chip b {
        color: #E3E3E3;
        font-family: monospace;
    }

    /* User Message Bubble: Right-aligned rounded dark bubble (#282A2C) */
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
        background-color: transparent !important;
        flex-direction: row-reverse !important;
        gap: 12px !important;
        margin-bottom: 1.2rem !important;
    }
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) div[data-testid="stChatMessageContent"] {
        background-color: #282A2C !important;
        color: #E3E3E3 !important;
        border-radius: 18px !important;
        padding: 12px 18px !important;
        max-width: 82% !important;
        margin-left: auto !important;
        border: 1px solid #3C4043 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25) !important;
    }

    /* Assistant Message: Clean unboxed markdown */
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) {
        background-color: transparent !important;
        padding: 0 !important;
        margin-top: 1rem !important;
        margin-bottom: 2rem !important;
        gap: 14px !important;
    }
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) div[data-testid="stChatMessageContent"] {
        background-color: transparent !important;
        color: #E3E3E3 !important;
        padding: 0 !important;
        border: none !important;
    }

    /* Floating Pill Chat Composer */
    div[data-testid="stBottom"] {
        background: linear-gradient(180deg, rgba(19, 19, 20, 0) 0%, rgba(19, 19, 20, 0.9) 35%, #131314 100%) !important;
        padding-bottom: 1.25rem !important;
    }
    div[data-testid="stChatInput"] {
        background-color: transparent !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        max-width: 780px !important;
        margin: 0 auto !important;
    }
    div[data-testid="stChatInput"] > div {
        background-color: #1E1F20 !important;
        border-radius: 28px !important;
        border: 1px solid #3C4043 !important;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.45) !important;
    }
    div[data-testid="stChatInput"] > div:focus-within {
        border-color: #8AB4F8 !important;
        box-shadow: 0 4px 20px rgba(138, 180, 248, 0.2) !important;
    }

    /* Inline Compliance Status Banners */
    .status-banner-pass {
        background-color: rgba(22, 101, 52, 0.25);
        color: #4ADE80;
        padding: 8px 14px;
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.86rem;
        margin: 12px 0 10px 0;
        border: 1px solid rgba(74, 222, 128, 0.35);
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .status-banner-warning {
        background-color: rgba(133, 77, 14, 0.25);
        color: #FACC15;
        padding: 8px 14px;
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.86rem;
        margin: 12px 0 10px 0;
        border: 1px solid rgba(250, 204, 21, 0.35);
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .status-banner-fail {
        background-color: rgba(153, 27, 27, 0.25);
        color: #F87171;
        padding: 8px 14px;
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.86rem;
        margin: 12px 0 10px 0;
        border: 1px solid rgba(248, 113, 113, 0.35);
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Inline Advisory Callout Card */
    .advisory-box {
        background-color: #201A12;
        border-left: 3px solid #D97706;
        padding: 10px 14px;
        border-radius: 8px;
        margin: 10px 0 14px 0;
        font-size: 0.88rem;
        color: #F8FAFC;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 3. Session State Initialization
if "aircraft_design_state" not in st.session_state:
    st.session_state.aircraft_design_state = AircraftDesignState()

state: AircraftDesignState = st.session_state.aircraft_design_state

# 4. Collapsible Left Sidebar (#1E1F20)
with st.sidebar:
    st.markdown("### ✈️ AeroGuard-RAG")
    st.caption("Neuro-Symbolic Aerodynamics & Airworthiness Workstation")

    if st.button("➕ New Analysis", use_container_width=True):
        st.session_state.aircraft_design_state = AircraftDesignState()
        st.rerun()

    st.divider()

    st.markdown("##### 📌 Active Design State")
    chips = [
        ("Span (b)", f"{state.wingspan.numerical_value} {state.wingspan.unit_string}" if state.wingspan else "—"),
        ("Area (S)", f"{state.wing_area.numerical_value} {state.wing_area.unit_string}" if state.wing_area else "—"),
        ("Mass (m)", f"{state.aircraft_mass.numerical_value} {state.aircraft_mass.unit_string}" if state.aircraft_mass else "—"),
        ("Speed (V)", f"{state.true_airspeed.numerical_value} {state.true_airspeed.unit_string}" if state.true_airspeed else "—"),
        ("Altitude (h)", f"{state.altitude.numerical_value} {state.altitude.unit_string}" if state.altitude else "0 m (ISA)"),
        ("Sweep (Λ)", f"{state.wing_sweep_degrees:.1f}°" if state.wing_sweep_degrees is not None else "0.0°"),
        ("Passengers", f"{state.passenger_count}" if state.passenger_count else "—"),
        ("Category", (state.regulatory_category or "FAA Part 23").replace("_", " ")),
    ]
    for label, val in chips:
        st.markdown(
            f'<div class="sidebar-chip"><span>{label}</span><b>{val}</b></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # System Status Information
    groq_active = bool(os.getenv("GROQ_APIKEY") or os.getenv("GROQ_API_KEY"))
    gemini_active = bool(os.getenv("Gemini_APIKEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_APIKEY"))
    provider = "Groq LLaMA-3.3-70B" if groq_active else ("Gemini 2.5 Flash" if gemini_active else "Local Deterministic")
    st.caption(f"**Extractor:** `{provider}`")

    index_exists = Path("data/lightrag_storage/ingestion_manifest.json").exists()
    idx_label = "🟢 Indexed Ready" if index_exists else "🟡 Index Pending"
    st.caption(f"**LightRAG Store:** `{idx_label}`")

# 5. Main Chat Stream (Max Width 780px, Natural Scrolling)
if not state.conversation_history:
    st.markdown(
        """
        <div style="text-align: center; padding: 48px 0 24px 0;">
            <div style="font-size: 2.6rem; margin-bottom: 8px;">✈️</div>
            <h2 style="font-size: 1.85rem; font-weight: 600; color: #E3E3E3; margin-bottom: 8px;">
                AeroGuard-RAG
            </h2>
            <p style="color: #9AA0A6; font-size: 0.98rem; max-width: 560px; margin: 0 auto 24px auto; line-height: 1.5;">
                Deterministic neuro-symbolic aerodynamic workstation. Sizing, induced & transonic wave drag,
                and FAA Part 23/25 airworthiness compliance verification powered by AeroSandbox, SymPy, and Pint.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Render Chat History
for msg in state.conversation_history:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(msg["content"])

            # Inline Telemetry: Status Banner & 3-Column Metric Strip
            comp_data = msg.get("compliance")
            sol_data = msg.get("solution")

            if comp_data:
                overall_status = comp_data.get("overall_status", "PASS")
                banner_classes = {
                    "PASS": ("status-banner-pass", "🟢 COMPLIANT — ALL FAA & NASA THRESHOLDS SATISFIED"),
                    "WARNING": ("status-banner-warning", "🟡 MARGINAL COMPLIANCE — NEAR REGULATORY BOUNDARY"),
                    "FAIL": ("status-banner-fail", "🔴 NON-COMPLIANT — REGULATORY OR HEURISTIC LIMIT EXCEEDED"),
                }
                b_class, b_text = banner_classes.get(overall_status, ("status-banner-pass", "STATUS VERIFIED"))
                st.markdown(f'<div class="{b_class}">{b_text}</div>', unsafe_allow_html=True)

            if sol_data:
                # 3-Column Inline Metric Strip
                col1, col2, col3 = st.columns(3)
                with col1:
                    if sol_data.get("aspect_ratio") is not None:
                        st.metric("Aspect Ratio (AR)", f"{sol_data['aspect_ratio']:.3f}")
                    elif sol_data.get("wing_loading_n_m2") is not None:
                        st.metric("Wing Loading (W/S)", f"{sol_data['wing_loading_n_m2']:.1f} N/m²")
                    if sol_data.get("lift_coefficient_cl") is not None:
                        st.metric("Lift Coeff (CL)", f"{sol_data['lift_coefficient_cl']:.4f}")

                with col2:
                    if sol_data.get("induced_drag_coefficient_cdi") is not None:
                        st.metric("Induced Drag (CDi)", f"{sol_data['induced_drag_coefficient_cdi']:.6f}")
                    if sol_data.get("drag_divergence_mach_number") is not None:
                        st.metric("Drag Divergence (Mdd)", f"{sol_data['drag_divergence_mach_number']:.4f}")
                    elif sol_data.get("induced_drag_force_newtons") is not None:
                        st.metric("Induced Drag (Di)", f"{sol_data['induced_drag_force_newtons']:.1f} N")

                with col3:
                    if sol_data.get("stall_speed_vs0_knots") is not None:
                        st.metric("Stall Speed (Vs0)", f"{sol_data['stall_speed_vs0_knots']:.1f} kts", f"{sol_data.get('stall_speed_vs0_m_s', 0.0):.1f} m/s")
                    if sol_data.get("mach_number") is not None:
                        st.metric("Cruise Mach (M)", f"{sol_data['mach_number']:.4f}")
                    elif sol_data.get("wave_drag_coefficient_cdw") is not None:
                        st.metric("Wave Drag (CDw)", f"{sol_data['wave_drag_coefficient_cdw']:.6f}")

            # Inline Expandable Drawer 1: Pint Dimensional Normalization Trace
            conversions = msg.get("unit_conversions")
            if conversions:
                with st.expander("⚖️ Pint Dimensional Normalization Trace", expanded=False):
                    table_rows = [
                        {
                            "Parameter": rec["parameter_name"],
                            "User Input": f"{rec['input_value']} {rec['input_unit']}",
                            "SI Base Unit": f"{rec['si_value']} {rec['si_unit']}",
                        }
                        for rec in conversions
                    ]
                    st.table(table_rows)

            # Inline Expandable Drawer 2: Symbolic & Substituted Mathematical Traces (SymPy)
            if sol_data and sol_data.get("equation_traces"):
                with st.expander("📐 Symbolic & Substituted Mathematical Traces (SymPy)", expanded=False):
                    for eq in sol_data["equation_traces"]:
                        st.markdown(f"**{eq['equation_name']}** *(Ref: `{eq['source_citation_id']}`)*")
                        st.latex(eq["symbolic_latex"])
                        st.latex(eq["substituted_latex"])
                        st.divider()

            # Inline Expandable Drawer 3: Verbatim NASA / FAA Regulatory Citations
            citations = msg.get("citations")
            if citations:
                with st.expander(f"📜 Verbatim NASA & FAA Regulatory Citations ({len(citations)})", expanded=False):
                    for cit in citations:
                        st.markdown(f"**📑 {cit['document_title']}** — *{cit['section_or_report_number']}*")
                        st.caption(f"Source: `{cit['source_pdf_filename']}` | Relevance: `{cit['relevance_score']:.2f}`")
                        st.markdown(f"> *\"{cit['verbatim_excerpt']}\"*")
                        st.divider()

            # Inline Parameter Sweep Trajectory (if WARNING or FAIL)
            if comp_data and comp_data.get("design_advisory"):
                advisory = comp_data["design_advisory"]
                if advisory.get("sweep_trajectory"):
                    with st.expander("📈 View AeroSandbox Parameter Sweep Trajectory"):
                        sweep_records = [
                            {
                                "Swept Val": row["swept_parameter_value_si"],
                                "AR": row["computed_aspect_ratio"],
                                "CDi": row["computed_cdi"],
                                "Di (N)": row["computed_induced_drag_newtons"],
                                "Vs0 (kts)": row["computed_stall_speed_knots"],
                                "Compliant?": "✅ PASS" if row["achieves_compliance"] else "❌ FAIL",
                            }
                            for row in advisory["sweep_trajectory"]
                        ]
                        st.dataframe(sweep_records, use_container_width=True)

# 6. Floating Dark Pill Chat Input Composer
user_input = st.chat_input("Enter aircraft parameters, flight condition, or ask an airworthiness question...")
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.spinner("Analyzing boundary conditions & executing deterministic physics..."):
        result = process_user_turn(user_input, state)
        st.session_state.aircraft_design_state = result.state

    st.rerun()
