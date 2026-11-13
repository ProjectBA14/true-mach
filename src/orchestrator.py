"""Central Relay Controller & State Machine orchestrating Modules B, C, D, and E."""

from __future__ import annotations
import os
import re
from typing import Any, Dict, Optional, Tuple
import aerosandbox as asb

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
    RuleCheckResult,
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


def should_clear_prior_aircraft(user_prompt: str, current_state: AircraftDesignState) -> bool:
    """Determine whether a turn is a standalone new inquiry rather than an incremental modification."""
    # Never clear if we are waiting for missing parameters from the previous turn
    if current_state.pipeline_status == "HALTED_MISSING_PARAMS":
        return False

    prompt_lower = user_prompt.lower()

    # Check for incremental modification signals
    modification_keywords = [
        "increase", "decrease", "reduce", "raise", "lower", "change", "set ", "modify",
        "update", "adjust", "what if", "now ", "instead of", "with a wing area of",
        "with wingspan", "how about", "new wing", "new area", "new span"
    ]
    if any(kw in prompt_lower for kw in modification_keywords):
        return False

    # Standalone flight condition prompt (e.g. "380 knots true airspeed at 25,000 ft")
    is_standalone_flight = bool(
        re.search(r"\b(?:knots|kts|mach|m/s)\b", prompt_lower)
        and re.search(r"\b(?:ft|feet|fl|altitude|flight\s*level|m)\b", prompt_lower)
        and not re.search(r"\b(?:wingspan|span|wing\s*area|area)\b", prompt_lower)
    )

    # Brand new aircraft calculation inquiry
    is_new_aircraft_spec = bool(
        re.search(r"\b(?:calculate|compute|solve|for a|run|evaluate|audit)\b", prompt_lower)
        and re.search(r"\b(?:aircraft|plane|jet|transport|prototype|airframe)\b", prompt_lower)
    )

    return is_standalone_flight or is_new_aircraft_spec


def clear_aircraft_state(state: AircraftDesignState) -> None:
    """Clear prior aircraft parameters for a clean standalone flight condition or new aircraft."""
    state.wingspan = None
    state.wing_area = None
    state.aircraft_mass = None
    state.passenger_count = None
    state.true_airspeed = None
    state.altitude = None
    state.oswald_efficiency_factor = 0.80
    state.zero_lift_drag_coefficient_cd0 = 0.025
    state.maximum_lift_coefficient_clmax = None
    state.available_thrust = None
    state.center_of_gravity_position = None
    state.neutral_point_position = None
    state.mean_aerodynamic_chord = None
    state.fuel_mass = None
    state.propeller_efficiency = None
    state.specific_fuel_consumption = None
    state.incompressible_pressure_coefficient_cp0 = None
    state.airfoil_thickness_ratio = None
    state.wing_sweep_degrees = None
    state.airfoil_technology_factor = None
    state.unit_conversions = []
    state.latest_physics_solution = None
    state.latest_compliance_report = None
    state.missing_parameters = []
    state.pipeline_status = "INITIALIZED"


def process_user_turn(
    user_prompt: str,
    state: AircraftDesignState,
    prefer_local_extractor: bool = False,
) -> OrchestrationResult:
    """Central 5-Module Sequential Relay Execution."""
    # Record user message in history
    state.conversation_history.append({"role": "user", "content": user_prompt})

    # Clear prior aircraft state on standalone new inquiries
    if should_clear_prior_aircraft(user_prompt, state):
        clear_aircraft_state(state)

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

    # Conceptual, Formula, Lookup, and Verification Handling
    if state.calculation_intent == "regulatory_qa":
        # Clear any previous turn's physics solution or compliance report
        state.latest_physics_solution = None
        state.latest_compliance_report = None
        state.unit_conversions = []
        state.missing_parameters = []
        user_lower = user_prompt.lower()

        # 1. Single-Metric Verification (e.g., "Vs0 = 64 kts—does that pass Part 23?")
        vs0_match = re.search(
            r"\b(?:vs0|v_s0|vso|stall\s*speed)\s*(?:=|is|of|:)?\s*(-?\d+(?:\.\d+)?)\s*(knots|kts|m/s|mps)?\b",
            user_lower,
        )
        if vs0_match:
            val_raw = float(vs0_match.group(1))
            unit_raw = vs0_match.group(2) or "knots"
            val_kts = val_raw if unit_raw in ["knots", "kts"] else val_raw / 0.514444
            val_mps = val_kts * 0.514444

            state.regulatory_category = "FAA_14_CFR_PART_23"
            state.certification_level = "FAA 14 CFR Part 23 (Normal/Commuter Category Airplanes)"
            limit_kts = 61.0
            is_pass = val_kts <= limit_kts
            status_str = "PASS" if is_pass else "FAIL"

            rule_check = RuleCheckResult(
                rule_id="RULE-REG-VS0",
                metric_name="stall_speed_vs0_knots",
                computed_value=round(val_kts, 2),
                metric_unit="knots",
                threshold_description=f"Maximum landing stall speed <= {limit_kts:.1f} knots (14 CFR § 23.2110 / Historic § 23.49)",
                status=status_str,
                regulation_reference="14 CFR § 23.2110 (Historic § 23.49)",
                source_document="14 CFR Part 23",
            )
            comp_report = ComplianceReport(
                regulatory_category=state.regulatory_category,
                certification_level_description=state.certification_level,
                overall_status=status_str,
                rule_checks=[rule_check],
            )
            solution = PhysicsSolutionBundle(
                stall_speed_vs0_knots=round(val_kts, 2),
                stall_speed_vs0_m_s=round(val_mps, 2),
            )
            state.latest_compliance_report = comp_report
            state.latest_physics_solution = solution
            state.pipeline_status = "COMPLETED_VERIFIED"
            retrieve_regulatory_citations(state)

            badge = "🔴 **NON-COMPLIANT [FAIL]**" if not is_pass else "🟢 **COMPLIANT [PASS]**"
            narrative = (
                f"### {badge} — Single-Metric Airworthiness Verification\n"
                f"**Governing Airworthiness Standard:** {state.regulatory_category.replace('_', ' ')} (*{state.certification_level}*)\n\n"
                f"#### Verification Result\n"
                f"- **Landing Stall Speed ($V_{{s0}}$):** `{val_kts:.2f} knots` (`{val_mps:.2f} m/s`)\n"
                f"- **Regulatory Threshold:** Maximum `61.0 knots` (*14 CFR § 23.2110 / Historic § 23.49*)\n"
                f"- **Compliance Status:** **{status_str}**\n\n"
                f"> **Airworthiness Finding:** {rule_check.threshold_description}\n\n"
                f"*Verbatim citations and excerpts from FAA Part 23 have been populated in the audit panel.*"
            )
            state.conversation_history.append({
                "role": "assistant",
                "content": narrative,
                "solution": solution.model_dump(),
                "compliance": comp_report.model_dump(),
                "citations": [c.model_dump() for c in state.retrieved_citations] if state.retrieved_citations else [],
            })
            return OrchestrationResult(
                assistant_chat_markdown=narrative,
                state=state,
                solution=solution,
                compliance_report=comp_report,
                is_halted=False,
            )

        # 2. Category Classification Check (e.g., "Is 19,500 lbs with 18 passengers Part 23 or Part 25?")
        is_category_query = bool(
            re.search(r"\b(?:part\s*23\s*(?:or|vs\.?)\s*part\s*25|which\s+category|what\s+category|is\s+(?:it\s+)?part\s*23|is\s+(?:it\s+)?part\s*25)\b", user_lower)
            or (re.search(r"\b(?:part\s*23|part\s*25)\b", user_lower) and re.search(r"\b(?:passenger|passengers|pax|seat|seats|lbs?|pounds?|kg)\b", user_lower))
        )
        mass_match = re.search(r"(-?\d+(?:,\d+)?(?:\.\d+)?)\s*(lbs?|pounds?|kg|kgs|kilograms?)\b", user_lower)
        pax_match = re.search(r"(\d+)\s*(?:passenger|passengers|pax|seat|seats|seater)\b", user_lower)

        if is_category_query and (mass_match or pax_match):
            mass_lbs = None
            mass_kg = None
            if mass_match:
                val = float(mass_match.group(1).replace(",", ""))
                unit = mass_match.group(2)
                if unit in ["lbs", "lb", "pound", "pounds"]:
                    mass_lbs = val
                    mass_kg = val * 0.45359237
                else:
                    mass_kg = val
                    mass_lbs = val / 0.45359237

            pax = int(pax_match.group(1)) if pax_match else (state.passenger_count or 0)

            # Determine category: Part 25 if MTOW > 19,000 lbs OR passengers > 19
            is_part_25 = (mass_lbs is not None and mass_lbs > 19000.0) or (pax > 19)
            if is_part_25:
                state.regulatory_category = "FAA_14_CFR_PART_25"
                state.certification_level = "Transport Category Airplane (> 19 pax or > 19,000 lbs MTOW)"
            else:
                state.regulatory_category = "FAA_14_CFR_PART_23"
                state.certification_level = "FAA 14 CFR Part 23 (Normal/Commuter Category Airplanes)"

            retrieve_regulatory_citations(state)

            category_name = "FAA 14 CFR Part 25 (Transport Category)" if is_part_25 else "FAA 14 CFR Part 23 (Normal/Commuter Category)"
            reasons = []
            if mass_lbs is not None:
                if mass_lbs > 19000.0:
                    reasons.append(f"Maximum Takeoff Weight of **{mass_lbs:,.0f} lbs** ({mass_kg:,.1f} kg) exceeds the Part 23 upper limit of **19,000 lbs (8,618 kg)** per 14 CFR § 23.2005.")
                else:
                    reasons.append(f"Maximum Takeoff Weight of **{mass_lbs:,.0f} lbs** ({mass_kg:,.1f} kg) is within the Part 23 threshold (<= 19,000 lbs).")
            if pax > 0:
                if pax > 19:
                    reasons.append(f"Seating capacity of **{pax} passengers** exceeds the Part 23 passenger limit (<= 19 passengers) per 14 CFR § 23.2005.")
                else:
                    reasons.append(f"Seating capacity of **{pax} passengers** is within the Part 23 limit (<= 19 passengers).")

            narrative = (
                f"### 📋 Airworthiness Category Classification\n"
                f"**Determined Standard:** **{category_name}**\n\n"
                f"#### Governing Evaluation Criteria:\n"
                + "\n".join(f"- {r}" for r in reasons) +
                f"\n\n> **Regulatory Summary:** Under **14 CFR § 23.2005** and **14 CFR § 25.1**, an aircraft exceeding "
                f"**19,000 lbs (8,618 kg) MTOW** OR **19 passengers** cannot be certified under Part 23 and is strictly "
                f"classified as a **Part 25 Transport Category** airplane.\n\n"
                f"*Verbatim citations and excerpts have been populated in the audit panel.*"
            )
            state.pipeline_status = "COMPLETED_VERIFIED"
            state.conversation_history.append({
                "role": "assistant",
                "content": narrative,
                "citations": [c.model_dump() for c in state.retrieved_citations] if state.retrieved_citations else [],
            })
            return OrchestrationResult(
                assistant_chat_markdown=narrative,
                state=state,
                solution=None,
                compliance_report=None,
                is_halted=False,
            )

        # 3. Atmospheric Lookup (AeroSandbox ISA: air density, speed of sound)
        is_isa_lookup = bool(
            re.search(r"\b(?:isa|atmosphere|density|speed\s+of\s+sound|atmospheric\s+properties)\b", user_lower)
            and re.search(r"(-?\d+(?:,\d+)?(?:\.\d+)?)\s*(?:ft|feet|m|meter|meters|fl)\b", user_lower)
        )
        if is_isa_lookup:
            alt_match = re.search(r"(-?\d+(?:,\d+)?(?:\.\d+)?)\s*(ft|feet|m|meter|meters)\b", user_lower)
            fl_match = re.search(r"\bfl\s*(\d+)\b", user_lower)
            if alt_match:
                val = float(alt_match.group(1).replace(",", ""))
                unit = alt_match.group(2)
                alt_m = val * 0.3048 if unit in ["ft", "feet"] else val
            elif fl_match:
                alt_m = float(fl_match.group(1)) * 100.0 * 0.3048
            else:
                alt_m = 0.0

            atmo = asb.Atmosphere(altitude=alt_m)
            rho = float(atmo.density())
            a = float(atmo.speed_of_sound())
            p = float(atmo.pressure())
            temp_k = float(atmo.temperature())
            temp_c = temp_k - 273.15
            alt_ft = alt_m / 0.3048

            solution = PhysicsSolutionBundle(
                air_density_kg_m3=round(rho, 5),
                speed_of_sound_m_s=round(a, 2),
            )
            state.latest_physics_solution = solution
            state.pipeline_status = "COMPLETED_VERIFIED"

            narrative = (
                f"### 🌐 International Standard Atmosphere (ISA) Properties\n"
                f"**Flight Altitude:** `{alt_ft:,.0f} ft` (`{alt_m:,.1f} m`)\n\n"
                f"- **Air Density ($\\rho$):** `{rho:.5f} kg/m³` (`{rho * 0.00194032:.6f} slug/ft³`)\n"
                f"- **Speed of Sound ($a$):** `{a:.2f} m/s` (`{a / 0.514444:.2f} knots`, `{a * 2.23694:.2f} mph`)\n"
                f"- **Ambient Pressure ($p$):** `{p:,.1f} Pa` (`{p / 100.0:.2f} hPa`, `{p * 0.000145038:.3f} psi`)\n"
                f"- **Ambient Temperature ($T$):** `{temp_k:.2f} K` (`{temp_c:.2f} °C`, `{temp_c * 9/5 + 32:.2f} °F`)\n\n"
                f"#### Deterministic Governing Equations:\n"
                f"$$\\rho = \\frac{{p}}{{R \\cdot T}}, \\quad a = \\sqrt{{\\gamma \\cdot R \\cdot T}}\n$$\n\n"
                f"*Values computed deterministically using the AeroSandbox 1976 Standard Atmosphere model.*"
            )
            state.conversation_history.append({
                "role": "assistant",
                "content": narrative,
                "solution": solution.model_dump(),
            })
            return OrchestrationResult(
                assistant_chat_markdown=narrative,
                state=state,
                solution=solution,
                compliance_report=None,
                is_halted=False,
            )

        # 4. Standard Formula & Aerodynamic Analysis Guidance Lookup
        is_formula_lookup = bool(
            re.search(r"\b(?:advice\s+on|formula|formulas|equation|equations|whats?\s+(?:the\s+)?formula|what\s+is\s+(?:the\s+)?formula)\b", user_lower)
        )
        if is_formula_lookup:
            state.pipeline_status = "COMPLETED_VERIFIED"
            retrieve_regulatory_citations(state)
            narrative = (
                "### 📐 Standard Aerodynamic Analysis Governing Equations\n\n"
                "Here are the core deterministic equations used in fixed-wing aerodynamic analysis under FAA and NASA standards:\n\n"
                "#### 1. Lift & Wing Geometry\n"
                "- **Aspect Ratio ($AR$):**\n"
                "  $$AR = \\frac{b^2}{S}$$\n"
                "- **Dynamic Pressure ($q_\\infty$):**\n"
                "  $$q_\\infty = \\frac{1}{2} \\rho_\\infty V_\\infty^2$$\n"
                "- **Lift Coefficient ($C_L$):**\n"
                "  $$C_L = \\frac{W}{q_\\infty \\cdot S} = \\frac{m \\cdot g_0}{\\frac{1}{2} \\rho_\\infty V_\\infty^2 \\cdot S}$$\n\n"
                "#### 2. Induced Drag (Vortex Drag)\n"
                "- **Induced Drag Coefficient ($C_{Di}$):**\n"
                "  $$C_{Di} = \\frac{C_L^2}{\\pi \\cdot AR \\cdot e}$$\n"
                "- **Induced Drag Force ($D_i$):**\n"
                "  $$D_i = q_\\infty \\cdot S \\cdot C_{Di} = \\frac{2 \\cdot W^2}{\\pi \\cdot \\rho_\\infty \\cdot V_\\infty^2 \\cdot b^2 \\cdot e}$$\n"
                "  *(Source: NASA SP-367 Ch. 4)*\n\n"
                "#### 3. Airworthiness Stall Speed\n"
                "- **Landing Stall Speed ($V_{s0}$):**\n"
                "  $$V_{s0} = \\sqrt{\\frac{2 \\cdot m \\cdot g_0}{\\rho \\cdot S \\cdot C_{L,\\max}}}$$\n"
                "  *(Threshold: 14 CFR § 23.2110 / § 23.49 maximum limit = 61.0 knots)*\n\n"
                "#### 4. Compressibility & Transonic Aerodynamics\n"
                "- **Mach Number ($M_\\infty$):**\n"
                "  $$M_\\infty = \\frac{V_\\infty}{a}$$\n"
                "- **Prandtl-Glauert Compressibility Factor ($\\beta$):**\n"
                "  $$\\beta = \\sqrt{1 - M_\\infty^2}, \\quad C_p = \\frac{C_{p,0}}{\\beta}$$\n"
                "  *(Source: NACA Report 1135)*\n"
                "- **Korn Drag Divergence Mach Number ($M_{dd}$):**\n"
                "  $$M_{dd} = \\frac{\\kappa_A}{\\cos \\Lambda} - \\frac{t/c}{\\cos^2 \\Lambda} - 0.10 \\cdot C_L$$\n"
                "  *(Source: NASA TM-81336 / Mason)*\n\n"
                "*All equations are solved deterministically using SymPy, AeroSandbox, and Pint without LLM approximation.*"
            )
            state.conversation_history.append({
                "role": "assistant",
                "content": narrative,
                "citations": [c.model_dump() for c in state.retrieved_citations] if state.retrieved_citations else [],
            })
            return OrchestrationResult(
                assistant_chat_markdown=narrative,
                state=state,
                solution=None,
                compliance_report=None,
                is_halted=False,
            )

        # 5. General Airworthiness Standards QA
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
        if state.pipeline_status == "DOMAIN_ERROR":
            err_msg = (
                f"❌ **Aerodynamic Domain Error:** Physical input values must be strictly positive. "
                f"Received non-physical or negative value for {', '.join(missing)}."
            )
            state.conversation_history.append({"role": "assistant", "content": err_msg})
            return OrchestrationResult(
                assistant_chat_markdown=err_msg,
                state=state,
                is_halted=True,
                error_message=err_msg,
            )
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

