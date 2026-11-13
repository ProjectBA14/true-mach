"""Central Relay Controller & State Machine orchestrating Modules B, C, D, and E."""

from __future__ import annotations
import os
from typing import Any, Dict, Optional, Tuple

from src.gatekeeper.clarifier import (
    extract_parameters,
    generate_counter_question,
    inspect_boundary_conditions,
    merge_turn_parameters,
)
from src.gatekeeper.schemas import (
    AircraftDesignState,
    ComplianceReport,
    PhysicsSolutionBundle,
)
from src.physics_engine.aero_solver import (
    AerodynamicDomainError,
    solve_aerodynamics,
)
from src.physics_engine.compliance import evaluate_compliance
from src.retrieval.standards_router import (
    classify_regulatory_category,
    retrieve_regulatory_citations,
)


class OrchestrationResult:
    """Encapsulates the response payload for a single user turn."""
    def __init__(
        self,
        assistant_chat_markdown: str,
        state: AircraftDesignState,
        solution: Optional[PhysicsSolutionBundle] = None,
        compliance_report: Optional[ComplianceReport] = None,
        is_halted: bool = False,
        error_message: Optional[str] = None,
    ):
        self.assistant_chat_markdown = assistant_chat_markdown
        self.state = state
        self.solution = solution
        self.compliance_report = compliance_report
        self.is_halted = is_halted
        self.error_message = error_message


def format_verified_narrative(
    state: AircraftDesignState,
    solution: PhysicsSolutionBundle,
    compliance: ComplianceReport,
) -> str:
    """Deterministic, structured narrative summary built strictly around verified numbers."""
    intent_title = (state.calculation_intent or "aerodynamic analysis").replace("_", " ").title()
    category_title = compliance.regulatory_category.replace("_", " ")

    status_badges = {
        "PASS": "🟢 **COMPLIANT [PASS]**",
        "WARNING": "🟡 **MARGINAL COMPLIANCE [WARNING]**",
        "FAIL": "🔴 **NON-COMPLIANT [FAIL]**",
    }
    badge = status_badges.get(compliance.overall_status, "⚪ **STATUS PENDING**")

    lines = [
        f"### {badge} — {intent_title}",
        f"**Governing Airworthiness Standard:** {category_title} (*{compliance.certification_level_description}*)",
        "",
        "#### Primary Solved Aerodynamic Metrics",
    ]

    if solution.aspect_ratio is not None:
        lines.append(f"- **Aspect Ratio ($AR$):** `{solution.aspect_ratio:.3f}`")
    if solution.wing_loading_n_m2 is not None:
        lines.append(f"- **Wing Loading ($W/S$):** `{solution.wing_loading_n_m2:.1f} N/m²` (`{solution.wing_loading_kg_m2:.1f} kg/m²`)")
    if solution.lift_coefficient_cl is not None:
        lines.append(f"- **Lift Coefficient ($C_L$):** `{solution.lift_coefficient_cl:.5f}`")
    if solution.induced_drag_coefficient_cdi is not None:
        lines.append(f"- **Induced Drag Coefficient ($C_{{Di}}$):** `{solution.induced_drag_coefficient_cdi:.6f}`")
    if solution.induced_drag_force_newtons is not None:
        lines.append(f"- **Induced Drag Force ($D_i$):** `{solution.induced_drag_force_newtons:.2f} N`")
    if solution.stall_speed_vs0_knots is not None:
        lines.append(f"- **Landing Stall Speed ($V_{{s0}}$):** `{solution.stall_speed_vs0_knots:.2f} knots` (`{solution.stall_speed_vs0_m_s:.2f} m/s`)")
    if solution.mach_number is not None:
        lines.append(f"- **Cruise Mach ($M_\\infty$):** `{solution.mach_number:.4f}`")
    if solution.drag_divergence_mach_number is not None:
        lines.append(f"- **Drag Divergence Mach ($M_{{dd}}$):** `{solution.drag_divergence_mach_number:.4f}` (Critical Mach $M_{{cr}} \\approx {solution.critical_mach_number or 0:.4f}$)")
    if solution.wave_drag_coefficient_cdw is not None and solution.wave_drag_coefficient_cdw > 0:
        lines.append(f"- **Wave Drag Coefficient ($C_{{Dw}}$):** `{solution.wave_drag_coefficient_cdw:.6f}`")
    if solution.prandtl_glauert_beta is not None:
        lines.append(f"- **Prandtl-Glauert Compressibility Factor ($\\beta$):** `{solution.prandtl_glauert_beta:.4f}`")

    # Regulatory Checks Summary
    lines.append("")
    lines.append("#### Regulatory & Heuristic Checks")
    for check in compliance.rule_checks:
        icon = "✅" if check.status == "PASS" else ("⚠️" if check.status == "WARNING" else "❌")
        lines.append(f"- {icon} **{check.metric_name}**: `{check.computed_value}` {check.metric_unit} ({check.status}) — *{check.regulation_reference}*")

    # Advisory Section
    if compliance.design_advisory is not None:
        advisory = compliance.design_advisory
        lines.append("")
        lines.append("#### 📐 AeroSandbox Parameter-Sweep Design Advisory")
        lines.append(f"> **Action Recommended:** {advisory.recommendation_summary}")
        if state.calculation_intent == "wing_sizing" and (advisory.percentage_change == 0.0 or advisory.original_value_si == advisory.recommended_value_si):
            lines.append(
                f"- Solved minimum compliant wingspan: `{advisory.recommended_value_si} {advisory.unit_si}` "
                f"(AR = {advisory.projected_metric_value})"
            )
        else:
            lines.append(
                f"- Parameter Swept: `{advisory.swept_parameter_name}` from `{advisory.original_value_si} {advisory.unit_si}` "
                f"to `{advisory.recommended_value_si} {advisory.unit_si}` ({advisory.percentage_change:+.1f}%)"
            )
        lines.append(f"- Projected `{advisory.projected_metric_name}`: `{advisory.projected_metric_value} {advisory.projected_metric_unit}`")

    return "\n".join(lines)


def process_user_turn(
    user_prompt: str,
    state: AircraftDesignState,
    prefer_local_extractor: bool = False,
) -> OrchestrationResult:
    """Central 5-Module Sequential Relay Execution."""
    # Record user message in history
    state.conversation_history.append({"role": "user", "content": user_prompt})

    # MODULE B: Intent & Parameter Extraction
    turn_params = extract_parameters(user_prompt, prefer_local=prefer_local_extractor)
    state = merge_turn_parameters(state, turn_params)

    # Check for Out of Scope (extraterrestrial atmospheres, spaceflight, orbital mechanics)
    if state.calculation_intent == "out_of_scope":
        state.pipeline_status = "OUT_OF_SCOPE_HALT"
        msg = (
            "⚠️ **Query Out of Aerodynamic Scope**\n\n"
            "The requested inquiry involves extraterrestrial atmospheric flight (e.g., Mars, Venus, Titan), "
            "orbital/spacecraft mechanics, or high-temperature material creep, which fall strictly outside "
            "AeroGuard-RAG's fixed-wing Earth atmospheric aerodynamics and FAA Part 23/25 airworthiness scope.\n\n"
            "The AeroSandbox International Standard Atmosphere (ISA) and aerodynamic equations model Earth atmospheric flight only. "
            "Please provide fixed-wing Earth atmospheric design or airworthiness compliance criteria."
        )
        state.conversation_history.append({"role": "assistant", "content": msg})
        return OrchestrationResult(
            assistant_chat_markdown=msg,
            state=state,
            is_halted=True,
        )

    # Conceptual & Regulatory Q&A Handling
    if state.calculation_intent == "regulatory_qa":
        # Clear any previous turn's physics solution or compliance report
        state.latest_physics_solution = None
        state.latest_compliance_report = None
        state.unit_conversions = []
        state.missing_parameters = []

        # Determine category based on user query
        if "transport" in user_prompt.lower() or "part 25" in user_prompt.lower() or (state.passenger_count and state.passenger_count > 19):
            state.regulatory_category = "FAA_14_CFR_PART_25"
            state.certification_level = "Transport Category Airplane (> 19 pax or > 19,000 lbs MTOW)"
        else:
            state.regulatory_category = "FAA_14_CFR_PART_23"
            state.certification_level = "FAA 14 CFR Part 23 (Normal/Commuter Category Airplanes)"

        # Query LightRAG / standards router directly
        retrieve_regulatory_citations(state)

        # Grounded narrative summary of the airworthiness regulations
        summary_lines = [
            f"### 📜 Regulatory & Airworthiness Standards Guide — {state.regulatory_category.replace('_', ' ')}",
            f"**Certification Level:** {state.certification_level}",
            "",
            "#### Governing Standards & Thresholds:",
        ]
        if state.regulatory_category == "FAA_14_CFR_PART_23":
            summary_lines.extend([
                "- **Applicability (§ 23.2005):** Governs airplanes with seating capacity <= 19 passengers and MTOW <= 19,000 lbs (8,618 kg) across Certification Levels 1 through 4.",
                "- **Landing Stall Speed ($V_{s0}$) (§ 23.2110 / Historic § 23.49):** For standard single-engine and commuter airplanes, maximum landing stall speed $V_{s0}$ must not exceed **61 knots** calibrated airspeed.",
                "- **Balked Landing Climb Gradient (§ 23.2120):** Must maintain at least a **8.33%** (1:12) steady climb gradient in the landing configuration.",
                "- **Static Longitudinal Stability (§ 23.2135):** The airframe must demonstrate positive stick-force stability with a static margin ($SM = (x_{np} - x_{cg}) / \\bar{c}$) typically between **+5% and +25% MAC**.",
                "- **Subsonic Efficiency (NASA SP-367):** Induced drag follows $C_{Di} = \\frac{C_L^2}{\\pi \\cdot AR \\cdot e}$. High aspect ratio planforms ($AR \\ge 6.5$) are recommended to minimize vortex drag.",
            ])
        else:
            summary_lines.extend([
                "- **Applicability (§ 25.1):** Governs transport category airplanes with passenger capacity > 19 or MTOW > 19,000 lbs (8,618 kg).",
                "- **Reference Stall Speed ($V_{SR}$) (§ 25.103):** 1-g reference stall speed governs operational margins ($V_{\\text{REF}} \\ge 1.23 V_{SR0}$).",
                "- **Supercritical High-AR Wing Design (NASA CP-2208):** Modern transport aircraft utilize supercritical airfoils and high aspect ratios ($AR \\ge 7.0-8.5$) to delay transonic drag rise.",
            ])

        summary_lines.append("\n*Verbatim regulatory citations and excerpts from FAA/NASA sources have been populated in the audit panel.*")
        narrative = "\n".join(summary_lines)
        state.conversation_history.append({
            "role": "assistant",
            "content": narrative,
            "citations": [c.model_dump() for c in state.retrieved_citations] if state.retrieved_citations else [],
        })
        state.pipeline_status = "COMPLETED_VERIFIED"
        return OrchestrationResult(
            assistant_chat_markdown=narrative,
            state=state,
            solution=None,
            compliance_report=None,
            is_halted=False,
        )

    # Inspect Boundary Conditions
    is_ready, missing = inspect_boundary_conditions(state)

    # Classify regulatory category early if possible
    classify_regulatory_category(state)

    if not is_ready:
        counter_question = generate_counter_question(state)
        state.conversation_history.append({"role": "assistant", "content": counter_question})
        return OrchestrationResult(
            assistant_chat_markdown=counter_question,
            state=state,
            is_halted=True,
        )

    # MODULE C: Standards & Citation Routing
    classify_regulatory_category(state)
    retrieve_regulatory_citations(state)

    # MODULE D: Deterministic Physics Solving
    try:
        solution, conversions = solve_aerodynamics(state)
        state.latest_physics_solution = solution
        state.unit_conversions = conversions
    except AerodynamicDomainError as domain_err:
        state.pipeline_status = "DOMAIN_ERROR"
        err_msg = f"❌ **Aerodynamic Domain Error:** {str(domain_err)}"
        state.conversation_history.append({"role": "assistant", "content": err_msg})
        return OrchestrationResult(
            assistant_chat_markdown=err_msg,
            state=state,
            is_halted=True,
            error_message=str(domain_err),
        )
    except Exception as exc:
        state.pipeline_status = "DOMAIN_ERROR"
        err_msg = f"❌ **Physics Calculation Error:** {str(exc)}"
        state.conversation_history.append({"role": "assistant", "content": err_msg})
        return OrchestrationResult(
            assistant_chat_markdown=err_msg,
            state=state,
            is_halted=True,
            error_message=str(exc),
        )

    # MODULE E: Compliance Grading & Parameter Sweep
    compliance_report = evaluate_compliance(solution, state, state.regulatory_category)
    state.latest_compliance_report = compliance_report
    state.pipeline_status = "COMPLETED_VERIFIED"

    # Format narrative
    narrative = format_verified_narrative(state, solution, compliance_report)
    state.conversation_history.append({
        "role": "assistant",
        "content": narrative,
        "solution": solution.model_dump() if solution else None,
        "compliance": compliance_report.model_dump() if compliance_report else None,
        "citations": [c.model_dump() for c in state.retrieved_citations] if state.retrieved_citations else [],
        "unit_conversions": [u.model_dump() for u in state.unit_conversions] if state.unit_conversions else [],
    })

    return OrchestrationResult(
        assistant_chat_markdown=narrative,
        state=state,
        solution=solution,
        compliance_report=compliance_report,
        is_halted=False,
    )

